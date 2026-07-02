import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server runs on :5173 and calls Sai's backend on :8000 directly (CORS is open).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
