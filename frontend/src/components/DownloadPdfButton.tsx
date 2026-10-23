"use client";

import { useRef, useState } from "react";
import type { CompletePayload } from "@/lib/atlas";

interface Props {
  data: CompletePayload;
  request: string;
  origin?: string;
}

export default function DownloadPdfButton({ data, request, origin }: Props) {
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloaded, setDownloaded] = useState(false);
  const busy = useRef(false);

  async function download() {
    if (busy.current) return;
    busy.current = true;
    setPreparing(true);
    setError(null);
    setDownloaded(false);
    let url: string | undefined;
    let started = false;
    try {
      // Both the renderer and document stay outside the initial page/SSR bundle.
      const [{ pdf }, document] = await Promise.all([
        import("@react-pdf/renderer"),
        import("./ItineraryPdf"),
      ]);
      document.registerItineraryPdfFonts(data, request, origin);
      const blob = await pdf(document.default({
        data, request, origin, generatedAt: new Date(),
      })).toBlob();
      url = URL.createObjectURL(blob);
      const slug = data.itinerary.destination.normalize("NFKD")
        .replace(/\p{Mark}/gu, "").toLowerCase()
        .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "trip";
      const link = window.document.createElement("a");
      link.href = url;
      link.download = `atlas-${slug}-${data.itinerary.total_days}-days.pdf`;
      window.document.body.appendChild(link);
      try { link.click(); started = true; setDownloaded(true); }
      finally { link.remove(); }
    } catch (cause) {
      console.error("Atlas PDF export failed", cause);
      setError("Couldn't prepare the PDF. Please try again.");
    } finally {
      // Keep the URL alive long enough for browsers to begin saving the file.
      if (url) {
        const createdUrl = url;
        if (started) window.setTimeout(() => URL.revokeObjectURL(createdUrl), 10_000);
        else URL.revokeObjectURL(createdUrl);
      }
      busy.current = false;
      setPreparing(false);
    }
  }

  return (
    <div className="mt-4">
      <button type="button" onClick={download} disabled={preparing} aria-busy={preparing}
        className="inline-flex items-center gap-2 rounded-lg border border-ink bg-panel px-4 py-2.5 font-mono text-xs font-semibold uppercase tracking-wider text-ink transition hover:border-blue hover:text-blue focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue/50 disabled:opacity-50">
        {preparing ? "Preparing PDF…" : "Download PDF"}
      </button>
      {error && <p className="mt-2 text-sm text-red-700" role="alert">{error}</p>}
      {downloaded && <p className="mt-2 text-sm text-muted" role="status">PDF download started.</p>}
    </div>
  );
}
