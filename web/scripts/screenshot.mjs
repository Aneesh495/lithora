// Capture a screenshot of the running atlas for documentation and as evidence
// that the UI renders real data. Requires the dev server to be running on the
// given URL and puppeteer available (it ships with the mermaid CLI used for
// diagrams). Usage: node scripts/screenshot.mjs <url> <out.png>

import puppeteer from "puppeteer";

const url = process.argv[2] ?? "http://localhost:5173/";
const out = process.argv[3] ?? "docs/atlas.png";

const browser = await puppeteer.launch({
  headless: true,
  args: [
    "--no-sandbox",
    "--enable-unsafe-swiftshader",
    "--use-gl=angle",
    "--use-angle=swiftshader",
    "--enable-webgl",
    "--ignore-gpu-blocklist",
    "--enable-features=Vulkan",
  ],
});
const page = await browser.newPage();
await page.setViewport({ width: 1400, height: 900 });
await page.goto(url, { waitUntil: "networkidle2", timeout: 60000 });
// Give Cesium time to initialize the globe and load the region data.
await new Promise((r) => setTimeout(r, 5000));

// Optionally exercise controls: switch to the residual layer and enable the
// earthquake context, so the screenshot shows a scientifically meaningful view.
if (process.argv[4] === "residual") {
  await page.select("#layer", "residual");
  await page.click("#showQuakes");
  await new Promise((r) => setTimeout(r, 2500));
}

await page.screenshot({ path: out });
await browser.close();
console.log("wrote", out);
