/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.VITE_DEV_API_PROXY_TARGET || "http://127.0.0.1:6000";

/** HMR uses a WebSocket; from another machine or strict networks it often fails and the tab can stay blank / “loading”. Opt in: VITE_ENABLE_HMR=1 npm run dev */
const enableHmr = process.env.VITE_ENABLE_HMR === "1" || process.env.VITE_ENABLE_HMR === "true";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{js,jsx}"],
    setupFiles: ["./src/test/setup.js"],
  },
  server: {
    host: "0.0.0.0",
    port: 7000,
    /** Fail fast if something else (e.g. the API) is already bound to 7000 — otherwise the browser shows the API instead of the SPA. */
    strictPort: true,
    hmr: enableHmr ? { port: 7000, clientPort: 7000 } : false,
    // NFS / some network filesystems: native file watching fails and Vite can hang or never finish serving.
    watch: { usePolling: true, interval: 1000 },
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true, timeout: 60000 },
      "/health": { target: apiTarget, changeOrigin: true, timeout: 60000 },
      "/ready": { target: apiTarget, changeOrigin: true, timeout: 60000 },
      "/static": { target: apiTarget, changeOrigin: true, timeout: 60000 },
    },
  },
});
