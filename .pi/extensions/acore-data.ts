/**
 * acore-data.ts — bridges the local acore-data MCP server (stdio) into
 * first-class pi tools.
 *
 * Spawns the project venv python (`server.py`) in the project root —
 * `.venv/bin/python3` on POSIX, `.venv/Scripts/python.exe` on Windows —
 * speaking JSON-RPC
 * over its stdio, and registers the server's tools (query, lookup, list,
 * sql, terrain) with their real names, descriptions and parameter schemas.
 * No MCP runtime, no proxy indirection, no extra dependencies.
 *
 * Committed at .pi/extensions/acore-data.ts — pi loads it automatically.
 */
import { spawn, type ChildProcess } from "node:child_process";
import { join, dirname } from "node:path";
import { existsSync, realpathSync } from "node:fs";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const CALL_TIMEOUT_MS = 300_000; // terrain pathfind / heavy SQL can be slow

// No secrets or machine-specific paths are hardcoded here. The child server
// inherits the ambient environment (DB_*, DBC_*, DATA_PATH flow through if
// set) and fills the rest in: DBC paths default to the standard AzerothCore
// layout, and DB credentials are auto-detected from worldserver.conf when
// unset. Override the project root with ACORE_DATA_ROOT.
//
// The project root is located without relying on pi's cwd (which is the
// AzerothCore checkout, not this repo, when the bridge is installed globally):
//   1. ACORE_DATA_ROOT (explicit override)
//   2. pi's cwd (running from inside the acore-data repo)
//   3. the extension's own location, symlink-resolved (the global
//      ~/.pi/agent/extensions/acore-data.ts -> <repo>/.pi/extensions/… link)
//   4. the conventional ~/acore-data install location
// Candidates are validated by the presence of server.py before use.
function resolveAcoreDataRoot(): string {
	if (process.env.ACORE_DATA_ROOT) return process.env.ACORE_DATA_ROOT;

	const candidates: string[] = [process.cwd()];

	try {
		const here = realpathSync(fileURLToPath(import.meta.url));
		// <repo>/.pi/extensions/acore-data.ts -> repo root is three levels up
		candidates.push(dirname(dirname(dirname(here))));
	} catch {
		// ignore — fall through to the next candidate
	}

	candidates.push(join(homedir(), "acore-data"));

	for (const c of candidates) {
		if (existsSync(join(c, "server.py"))) return c;
	}

	// Nothing matched: fall back to cwd so the bridge surfaces the existing
	// clear "server.py not found … set ACORE_DATA_ROOT" error.
	return process.cwd();
}

const PROJECT_ROOT = resolveAcoreDataRoot();

// ------------------------------------------------------------ JSON Schema -> typebox

function primitive(t: string, opts: object): any {
	switch (t) {
		case "string":
			return Type.String(opts);
		case "number":
		case "integer":
			return Type.Number(opts);
		case "boolean":
			return Type.Boolean(opts);
		default:
			return Type.Any();
	}
}

function schemaToTypebox(schema: any): any {
	if (!schema || typeof schema !== "object") return Type.Any();

	if (Array.isArray(schema.oneOf) || Array.isArray(schema.anyOf)) {
		const variants = (schema.oneOf ?? schema.anyOf ?? []).map(schemaToTypebox);
		return variants.length > 1 ? Type.Union(variants) : variants[0] ?? Type.Any();
	}

	if (Array.isArray(schema.enum) && schema.enum.length > 0) {
		return Type.Union(schema.enum.map((v) => Type.Literal(v)));
	}

	const opts = schema.description ? { description: schema.description } : {};
	const type = schema.type;

	if (Array.isArray(type)) {
		const variants = type.map((t) => primitive(t, opts));
		return Type.Union(variants);
	}

	switch (type) {
		case "array":
			return Type.Array(schema.items ? schemaToTypebox(schema.items) : Type.Any(), opts);
		case "object": {
			const props: Record<string, any> = {};
			const required = new Set<string>(schema.required ?? []);
			for (const [k, v] of Object.entries(schema.properties ?? {})) {
				const sub = schemaToTypebox(v);
				props[k] = required.has(k) ? sub : Type.Optional(sub);
			}
			if (Object.keys(props).length === 0) {
				// No-arg tools (e.g. dbversion): an empty object schema, NOT Any()
				// (which serializes without a `type` and is rejected by strict
				// OpenAI-compatible providers with "type: null").
				return schema.additionalProperties === true
					? Type.Record(Type.String(), Type.Any(), opts)
					: Type.Object({}, opts);
			}
			return Type.Object(props, opts);
		}
		default:
			return primitive(typeof type === "string" ? type : "string", opts);
	}
}

// ------------------------------------------------------------ stdio JSON-RPC bridge

interface McpToolDef {
	name: string;
	description?: string;
	inputSchema?: any;
}

class McpBridge {
	private proc: ChildProcess | null = null;
	private buf = "";
	private nextId = 1;
	private pending = new Map<number, { resolve: (v: any) => void; reject: (e: Error) => void }>();
	private stderr = "";

	constructor(private cwd: string) {}

	private spawnProc(): void {
		const serverPy = join(this.cwd, "server.py");
		if (!existsSync(serverPy)) {
			const fail = new Error(
				`acore-data: server.py not found at ${serverPy}. ` +
					`Run pi from the acore-data project root, or set ACORE_DATA_ROOT.`
			);
			for (const [, p] of this.pending) p.reject(fail);
			this.pending.clear();
			throw fail;
		}
		// Venv layout differs by platform (POSIX: .venv/bin/python3,
		// Windows: .venv/Scripts/python.exe). Prefer the project venv;
		// fall back to the system python (the server degrades gracefully
		// without pymysql and warns on stderr).
		const venvCandidates = [
			join(this.cwd, ".venv", "Scripts", "python.exe"),
			join(this.cwd, ".venv", "bin", "python3"),
		].filter((c) => existsSync(c));
		const cmd =
			venvCandidates[0] ?? (process.platform === "win32" ? "python" : "python3");
		const proc = spawn(cmd, [serverPy], {
			cwd: this.cwd,
			env: process.env,
			stdio: ["pipe", "pipe", "pipe"],
		});
		this.proc = proc;
		proc.stdout?.on("data", (d) => this.onData(String(d)));
		proc.stderr?.on("data", (d) => {
			this.stderr += String(d);
			if (this.stderr.length > 8000) this.stderr = this.stderr.slice(-8000);
		});
		proc.on("error", (err) => {
			const fail = new Error(`acore-data server failed to start: ${err.message}`);
			for (const [, p] of this.pending) p.reject(fail);
			this.pending.clear();
		});
		proc.on("exit", (code) => {
			const fail = new Error(`acore-data server exited (code ${code})`);
			for (const [, p] of this.pending) p.reject(fail);
			this.pending.clear();
		});
	}

	private onData(chunk: string): void {
		this.buf += chunk;
		let nl: number;
		while ((nl = this.buf.indexOf("\n")) >= 0) {
			const line = this.buf.slice(0, nl).trim();
			this.buf = this.buf.slice(nl + 1);
			if (!line) continue;
			let msg: any;
			try {
				msg = JSON.parse(line);
			} catch {
				continue;
			}
			if (msg.id === undefined || !this.pending.has(msg.id)) continue;
			const p = this.pending.get(msg.id)!;
			this.pending.delete(msg.id);
			if (msg.error) {
				p.reject(new Error(msg.error.message ?? "JSON-RPC error"));
			} else {
				p.resolve(msg.result);
			}
		}
	}

	request(method: string, params: any, signal?: AbortSignal): Promise<any> {
		return new Promise((resolve, reject) => {
			if (!this.proc || this.proc.exitCode !== null) this.spawnProc();
			const proc = this.proc!;
			const id = this.nextId++;

			const timer = setTimeout(() => {
				this.pending.delete(id);
				reject(new Error(`acore-data ${method} timed out after ${CALL_TIMEOUT_MS / 1000}s`));
			}, CALL_TIMEOUT_MS);

			const settle = (fn: () => void) => {
				clearTimeout(timer);
				signal?.removeEventListener("abort", onAbort);
				fn();
			};

			const onAbort = () => {
				this.pending.delete(id);
				settle(() => reject(new Error("aborted")));
			};
			signal?.addEventListener("abort", onAbort, { once: true });

			this.pending.set(id, {
				resolve: (v) => settle(() => resolve(v)),
				reject: (e) => settle(() => reject(e)),
			});

			try {
				proc.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
			} catch (err) {
				this.pending.delete(id);
				settle(() => reject(err as Error));
			}
		});
	}

	shutdown(): void {
		if (this.proc && this.proc.exitCode === null) {
			this.proc.kill("SIGTERM");
			setTimeout(() => {
				if (this.proc && this.proc.exitCode === null) this.proc.kill("SIGKILL");
			}, 2000).unref();
		}
		this.proc = null;
	}
}

// ------------------------------------------------------------ extension

export default function acoreDataExtension(pi: ExtensionAPI) {
	const bridgeCwd = PROJECT_ROOT; // pi's cwd, or ACORE_DATA_ROOT override
	let bridge: McpBridge | null = null;
	let ready: Promise<McpToolDef[]> | null = null;

	const ensureTools = (): Promise<McpToolDef[]> => {
		if (!ready) {
			bridge = new McpBridge(bridgeCwd);
			ready = (async () => {
				const b = bridge!;
				await b.request("initialize", {
					protocolVersion: "2024-11-05",
					capabilities: {},
					clientInfo: { name: "pi-coding-agent", version: "1.0.0" },
				});
				// fire-and-forget notification (no id -> no response)
				b.proc?.stdin?.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n");
				const res = await b.request("tools/list", {});
				return (res.tools ?? []) as McpToolDef[];
			})();
			ready.catch(() => {
				ready = null; // allow retry on next call
			});
		}
		return ready;
	};

	pi.on("session_start", async (_event, ctx) => {
		try {
			const tools = await ensureTools();
			for (const t of tools) {
				pi.registerTool({
					name: t.name,
					label: t.name,
					description: t.description ?? `acore-data tool: ${t.name}`,
					parameters: schemaToTypebox(t.inputSchema ?? { type: "object" }),
					async execute(_toolCallId, params, signal) {
						const b = bridge!;
						const result = await b.request("tools/call", { name: t.name, arguments: params }, signal);
						const texts = (result.content ?? [])
							.filter((c: any) => c.type === "text")
							.map((c: any) => ({ type: "text" as const, text: c.text }));
						const out = texts.length > 0 ? texts : [{ type: "text" as const, text: JSON.stringify(result ?? {}) }];
						return {
							content: out,
							details: {},
							isError: result.isError === true,
						};
					},
				});
			}
			if (ctx.hasUI) {
				ctx.ui.notify(`acore-data: ${tools.length} tools registered (query, lookup, list, …)`, "info");
			}
		} catch (err) {
			if (ctx.hasUI) {
				ctx.ui.notify(`acore-data bridge failed: ${(err as Error).message}`, "error");
			}
		}
	});

	pi.on("session_shutdown", async () => {
		bridge?.shutdown();
		bridge = null;
		ready = null;
	});
}
