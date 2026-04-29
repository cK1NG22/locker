import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/dashboard/",
  build: {
    outDir: "../static/dashboard",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "https://locker.up.railway.app",
    },
  },
});
