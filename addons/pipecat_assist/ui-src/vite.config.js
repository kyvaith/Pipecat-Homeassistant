import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
import { defineConfig } from "vite";

const version = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8")).version;

export default defineConfig({
  base: "./",
  plugins: [
    react(),
    {
      name: "pipecat-cache-bust-ui",
      enforce: "post",
      transformIndexHtml(html) {
        return html.replace(/(src|href)="\.\/(index\.(?:js|css))"/g, `$1="./$2?v=${version}"`);
      },
    },
  ],
  build: {
    assetsDir: ".",
    emptyOutDir: true,
    outDir: "../app/ui",
    rollupOptions: {
      output: {
        assetFileNames: "[name][extname]",
        chunkFileNames: "[name].js",
        entryFileNames: "[name].js",
      },
    },
  },
});
