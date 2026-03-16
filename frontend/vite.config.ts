import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Serve assets relative to the current path so GitHub Pages can host the site under /CaseTrace/.
  base: "./",
  plugins: [react()],
  server: {
    port: 5173,
  },
});
