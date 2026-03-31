import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.VITE_DEV_API_PROXY_TARGET || "http://127.0.0.1:6000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 7000,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
      "/health": { target: apiTarget, changeOrigin: true },
      "/ready": { target: apiTarget, changeOrigin: true },
      "/static": { target: apiTarget, changeOrigin: true },
    },
  },
});
