import { resolve, sep, extname } from "node:path";
function log(event: string, context: Record<string, unknown> = {}) {
  console.log(
    JSON.stringify({
      timestamp: new Date().toISOString(),
      level: event.endsWith("failed") ? "ERROR" : "INFO",
      event,
      ...context,
    }),
  );
}
const root = resolve(import.meta.dir, "dist");
const backend = process.env.BACKEND_URL || "http://127.0.0.1:8000";
const port = Number(process.env.PORT || 3000);
Bun.serve({
  port,
  hostname: process.env.HOST || "127.0.0.1",
  idleTimeout: 240,
  maxRequestBodySize: 128 * 1024 * 1024,
  async fetch(request, server) {
    const requestId = crypto.randomUUID().replaceAll("-", "");
    const started = performance.now();
    const url = new URL(request.url);
    // Categories exclude user-supplied paths and query strings.
    const route = url.pathname.startsWith("/api/")
      ? "api"
      : url.pathname.startsWith("/assets/")
        ? "asset"
        : "page";
    const context = { request_id: requestId, method: request.method, route };
    log("web_request_started", context);
    try {
      const response = await handle();
      const headers = new Headers(response.headers);
      headers.set("X-Request-ID", requestId);
      log(
        response.status >= 400 ? "web_request_failed" : "web_request_completed",
        {
          ...context,
          status_code: response.status,
          duration_ms: Math.round((performance.now() - started) * 100) / 100,
        },
      );
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
    } catch {
      log("web_request_failed", { ...context, status_code: 500 });
      return Response.json(
        { detail: "The frontend server could not handle the request." },
        { status: 500, headers: { "X-Request-ID": requestId } },
      );
    }
    async function handle(): Promise<Response> {
      if (url.pathname.startsWith("/api/")) {
        server.timeout(request, 0);
        const target = new URL(backend);
        target.pathname = url.pathname.slice(4);
        target.search = url.search;
        const headers = new Headers(request.headers);
        headers.set("X-Request-ID", requestId);
        headers.delete("host");
        headers.delete("connection");
        try {
          log("proxy_request_started", context);
          const response = await fetch(target, {
            method: request.method,
            headers,
            body: ["GET", "HEAD"].includes(request.method)
              ? undefined
              : request.body,
            redirect: "manual",
          });
          log("proxy_response_received", {
            ...context,
            status_code: response.status,
          });
          return response;
        } catch {
          log("proxy_request_failed", context);
          return Response.json(
            { detail: "The backend is unavailable. Check the API service." },
            { status: 502 },
          );
        }
      }
      if (!["GET", "HEAD"].includes(request.method))
        return new Response("Method not allowed", { status: 405 });
      let path: string;
      try {
        path = resolve(root, "." + decodeURIComponent(url.pathname));
      } catch {
        return new Response("Bad path", { status: 400 });
      }
      if (path !== root && !path.startsWith(root + sep))
        return new Response("Not found", { status: 404 });
      let file = Bun.file(path);
      if (!(await file.exists())) {
        if (extname(path)) return new Response("Not found", { status: 404 });
        file = Bun.file(resolve(root, "index.html"));
      }
      if (!(await file.exists()))
        return new Response("Build the frontend first with bun run build.", {
          status: 503,
        });
      return new Response(request.method === "HEAD" ? null : file, {
        headers: {
          "Content-Type": file.type,
          "Cache-Control": url.pathname.startsWith("/assets/")
            ? "public, max-age=31536000, immutable"
            : "no-cache",
          "X-Content-Type-Options": "nosniff",
        },
      });
    }
  },
});
log("web_server_started", { port });
