// Runtime reverse proxy: forwards /api/* to the FastAPI backend (API_PROXY_TARGET), read at
// REQUEST time (not build time). This keeps the browser same-origin (no CORS, no exposed keys)
// and works on any host — including Render — without build args. Streams bodies (PDF downloads).
import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const RAW_TARGET = process.env.API_PROXY_TARGET || "http://localhost:8000";
// Allow a bare hostname (e.g. Render's `fromService host`) — default it to https.
const TARGET = RAW_TARGET.startsWith("http") ? RAW_TARGET : `https://${RAW_TARGET}`;

async function handler(req: NextRequest, ctx: { params: { path: string[] } }) {
  const search = req.nextUrl.search;
  const target = `${TARGET}/${ctx.params.path.join("/")}${search}`;

  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");

  const init: RequestInit & { duplex?: "half" } = {
    method: req.method,
    headers,
    redirect: "manual",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  const res = await fetch(target, init);

  // Strip hop-by-hop / length headers so the streamed body isn't mismatched.
  const respHeaders = new Headers(res.headers);
  respHeaders.delete("content-encoding");
  respHeaders.delete("content-length");
  respHeaders.delete("transfer-encoding");

  return new Response(res.body, { status: res.status, headers: respHeaders });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
