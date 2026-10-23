/** Offline rendering of the same document downloaded in the browser.
 * Run from frontend/: node tests/render-itinerary-pdf.mjs tests/fixtures/japan.json ../output/pdf/atlas-japan-sample.pdf
 * Input JSON: { data: CompletePayload, request: string, origin?: string, generatedAt?: ISO string }.
 */
import { readFile, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { build } from "esbuild";
import { renderToBuffer } from "@react-pdf/renderer";

async function main() {
  const [input, output, fontBase] = process.argv.slice(2);
  if (!input || !output) throw new Error("Usage: node tests/render-itinerary-pdf.mjs <fixture.json> <output.pdf>");
  const fixture = JSON.parse(await readFile(path.resolve(input), "utf8"));
  if (!fixture.data?.itinerary || typeof fixture.request !== "string") throw new Error("Fixture must include data.itinerary and request.");
  const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  // ESM preserves the renderer's import-only dependency exports without changing the app's module mode.
  const temporary = await mkdtemp(path.join(project, "tests/.pdf-render-"));
  try {
    const entry = path.join(temporary, "document.mjs");
    await build({ entryPoints: [path.join(project, "src/components/ItineraryPdf.tsx")], bundle: true, packages: "external", platform: "node", format: "esm", jsx: "automatic", outfile: entry, tsconfig: path.join(project, "tsconfig.json") });
    const { default: ItineraryPdf, registerItineraryPdfFonts } = await import(pathToFileURL(entry).href);
    registerItineraryPdfFonts(fixture.data, fixture.request, fixture.origin, fontBase || path.join(project, "public/fonts"));
    const result = await renderToBuffer(ItineraryPdf({ ...fixture, generatedAt: fixture.generatedAt ? new Date(fixture.generatedAt) : new Date() }));
    const target = path.resolve(output);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, result);
    console.log(`Rendered ${result.length.toLocaleString("en-US")} bytes to ${target}`);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
