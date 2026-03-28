import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
    include: [
      "**/*.{test,spec}.?(c|m)[jt]s?(x)",
      "**/*.smoke.test.?(c|m)[jt]s?(x)",
    ],
  },
});
