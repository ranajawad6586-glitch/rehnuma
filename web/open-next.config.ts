// @opennextjs/cloudflare build config. Defaults are right for this app: it is fully dynamic
// (every page is a client component talking to /api/*), so no incremental cache is configured.
import { defineCloudflareConfig } from "@opennextjs/cloudflare";

export default defineCloudflareConfig({});
