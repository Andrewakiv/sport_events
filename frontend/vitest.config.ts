import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./app/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary"],
      include: ["app/**/*.{ts,tsx}"],
      exclude: ["app/**/*.d.ts", "app/root.tsx", "app/routes.ts"],
    },
  },
});
