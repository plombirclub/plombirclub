import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import postcss from "postcss";
import postcssImport from "postcss-import";
import autoprefixer from "autoprefixer";
import { transformFileAsync } from "@babel/core";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const dist = path.join(root, "dist");

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function copyFile(src, dest) {
  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
}

function copyDir(srcDir, destDir) {
  if (!fs.existsSync(srcDir)) return;
  ensureDir(destDir);
  for (const entry of fs.readdirSync(srcDir, { withFileTypes: true })) {
    const src = path.join(srcDir, entry.name);
    const dest = path.join(destDir, entry.name);
    if (entry.isDirectory()) copyDir(src, dest);
    else copyFile(src, dest);
  }
}

async function buildCss() {
  const cssDir = path.join(root, "css");
  const outDir = path.join(dist, "css");
  ensureDir(outDir);

  const files = fs.readdirSync(cssDir).filter((f) => f.endsWith(".css"));
  for (const file of files) {
    const input = fs.readFileSync(path.join(cssDir, file), "utf8");
    const plugins = file === "styles.css" ? [postcssImport(), autoprefixer()] : [autoprefixer()];
    const result = await postcss(plugins).process(input, {
      from: path.join(cssDir, file),
      to: path.join(outDir, file),
    });
    fs.writeFileSync(path.join(outDir, file), result.css);
    console.log("css:", file);
  }
}

async function buildJs() {
  const jsDir = path.join(root, "js");
  const outDir = path.join(dist, "js");
  ensureDir(outDir);

  const files = fs.readdirSync(jsDir).filter((f) => f.endsWith(".js"));
  for (const file of files) {
    const result = await transformFileAsync(path.join(jsDir, file), {
      filename: file,
      cwd: jsDir,
      configFile: path.join(root, "babel.config.cjs"),
    });
    fs.writeFileSync(path.join(outDir, file), result.code);
    console.log("js:", file);
  }
}

function copyPolyfills() {
  const src = path.join(root, "node_modules", "core-js-bundle", "minified.js");
  const dest = path.join(dist, "js", "polyfills.js");
  if (!fs.existsSync(src)) {
    throw new Error("core-js-bundle не найден — выполните npm install");
  }
  copyFile(src, dest);
  console.log("js: polyfills.js (core-js-bundle)");
}

function injectPolyfillsIntoHtml(html) {
  if (html.includes("/js/polyfills.js")) return html;
  return html.replace(
    '<script src="/js/api.js"></script>',
    '<script src="/js/polyfills.js"></script>\n  <script src="/js/api.js"></script>'
  );
}

function copyStatic() {
  const indexSrc = path.join(root, "index.html");
  const indexDest = path.join(dist, "index.html");
  fs.writeFileSync(indexDest, injectPolyfillsIntoHtml(fs.readFileSync(indexSrc, "utf8")));

  copyDir(path.join(root, "pages"), path.join(dist, "pages"));
  copyDir(path.join(root, "admin"), path.join(dist, "admin"));
  copyDir(path.join(root, "images"), path.join(dist, "images"));

  for (const dir of ["pages", "admin"]) {
    const htmlDir = path.join(dist, dir);
    if (!fs.existsSync(htmlDir)) continue;
    for (const file of fs.readdirSync(htmlDir).filter((f) => f.endsWith(".html"))) {
      const content = injectPolyfillsIntoHtml(fs.readFileSync(path.join(htmlDir, file), "utf8"));
      fs.writeFileSync(path.join(htmlDir, file), content);
    }
  }

  copyFile(path.join(root, "docker-nginx.conf"), path.join(dist, "docker-nginx.conf"));
}

async function main() {
  if (fs.existsSync(dist)) {
    fs.rmSync(dist, { recursive: true, force: true });
  }
  ensureDir(dist);
  await buildCss();
  await buildJs();
  copyPolyfills();
  copyStatic();
  console.log("Build complete -> frontend/dist");
}

main().catch(function (err) {
  console.error(err);
  process.exit(1);
});
