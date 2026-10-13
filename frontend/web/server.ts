import { resolve, sep, extname } from "node:path";
const root = resolve(import.meta.dir, "dist");
const backend = process.env.BACKEND_URL || "http://127.0.0.1:8000";
const port = Number(process.env.PORT || 3000);
Bun.serve({
  port,
  hostname: process.env.HOST || "127.0.0.1",
  idleTimeout: 240,
  maxRequestBodySize: 128 * 1024 * 1024,
  async fetch(request, server) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) {
      server.timeout(request, 0);
      const target = new URL(backend);
      target.pathname = url.pathname.slice(4);
      target.search = url.search;
      const headers = new Headers(request.headers);
      headers.delete("host");
      headers.delete("connection");
      try {
        return await fetch(target, {
          method: request.method,
          headers,
          body: ["GET", "HEAD"].includes(request.method)
            ? undefined
            : request.body,
          redirect: "manual",
        });
      } catch {
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
  },
});
console.log(`Interview Coach: http://localhost:${port}`);
