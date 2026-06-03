/** @type {import('next').NextConfig} */
// /api/* is proxied to the FastAPI backend by the runtime route handler at app/api/[...path]/route.ts
// (reads API_PROXY_TARGET at request time — works locally and on Render with no build args).
const nextConfig = {
  skipTrailingSlashRedirect: true,
};

export default nextConfig;
