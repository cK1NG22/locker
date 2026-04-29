import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/companion/",
  build: {
    outDir: "../static/companion",
    emptyOutDir: true,
  },
});
