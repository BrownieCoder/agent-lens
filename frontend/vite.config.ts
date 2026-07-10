import { defineConfig } from "vite";

export default defineConfig({
  esbuild: { jsx: "automatic" },
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000", rewrite: (path) => path.replace(/^\/api/, "") } },
  },
});
