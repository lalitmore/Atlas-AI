"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { streamPlan, type CompletePayload, type RouteStop, type DayPlan } from "@/lib/atlas";
import { directionsUrl, flightsUrl, hotelsUrl, foodUrl, placeUrl } from "@/lib/links";

const RouteMap = dynamic(() => import("@/components/RouteMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse" style={{ background: "var(--line)" }} />,
});

const STAGES = [
  { name: "intake", label: "Understanding your request" },
  { name: "research", label: "Researching destinations, events & prices" },
  { name: "structure", label: "Organizing the findings" },
  { name: "optimize", label: "Optimizing the route" },
  { name: "itinerary", label: "Writing your day-by-day plan" },
] as const;

const EXAMPLES = [
  { label: "Japan, food & culture", icon: "🍜", text: "10 days in Japan in October, two of us, vegetarian, we love anime, food, nature and photography, budget around $4,500, and we hate early mornings" },
  { label: "California road trip", icon: "🚗", text: "A relaxed 5-day road trip along the California coast starting from San Francisco, two of us, we love scenic drives, seafood and small towns, mid-range budget" },
  { label: "Italy honeymoon", icon: "🍷", text: "7 days in Italy split between Rome and the Amalfi Coast, honeymoon for two, we love history, wine and slow mornings, comfortable budget" },
  { label: "CDMX long weekend", icon: "🎨", text: "A long weekend in Mexico City, solo traveler, into art, markets and street food, keep it affordable" },
];

const RECIPE = [
  { k: "Where + how long", d: "A place and a number of days", ex: '"10 days in Japan" or "a weekend near Lake Tahoe"' },
  { k: "When", d: "Month or season, so events & weather fit", ex: '"in October"' },
  { k: "Who", d: "How many people, and any needs", ex: '"two of us, one vegetarian"' },
  { k: "What you love", d: "Your interests drive the picks", ex: '"food, nature, anime, nightlife"' },
  { k: "Budget", d: "A rough total or per-day", ex: '"around $4,500 total"' },
  { k: "Dealbreakers", d: "Anything to avoid", ex: '"we hate early mornings"' },
];

type StageState = "pending" | "active" | "done" | "failed";
const norm = (s: string) => s.trim().toLowerCase();
const abbr = (s: string) => s.replace(/[^A-Za-z]/g, "").slice(0, 3).toUpperCase();

function Flap({ text }: { text: string }) {
  const [shown, setShown] = useState<string[]>(() => text.split("").map((c) => (c === " " ? " " : "")));
  useEffect(() => {
    const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion:reduce)").matches;
    const final = text.split("");
    if (reduce) { setShown(final); return; }
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789·";
    const ivs: number[] = [];
    final.map((c, i) => ({ c, i })).filter((x) => x.c !== " ").forEach((it, k) => {
      let ticks = 6 + k * 2;
      const iv = window.setInterval(() => {
        setShown((prev) => { const n = [...prev]; n[it.i] = ticks <= 0 ? it.c : chars[Math.floor(Math.random() * chars.length)]; return n; });
        if (ticks < 0) clearInterval(iv);
        ticks--;
      }, 45);
      ivs.push(iv);
    });
    return () => ivs.forEach(clearInterval);
  }, [text]);
  return <span className="flap">{shown.map((ch, i) => (ch === " " ? <span key={i} className="sp" /> : <span key={i}>{ch || "\u00A0"}</span>))}</span>;
}

function BoardRow({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="board-row">
      <span style={{ fontFamily: "var(--font-mono)", fontSize: ".62rem", letterSpacing: ".14em", textTransform: "uppercase", color: "#7C8794" }}>{k}</span>
      {children}
    </div>
  );
}

function LinkPill({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 font-mono text-[0.62rem] font-semibold uppercase tracking-[0.1em] text-ink transition hover:border-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue/40">
      {children}<span aria-hidden>↗</span>
    </a>
  );
}

export default function Home() {
  const [request, setRequest] = useState("");
  const [origin, setOrigin] = useState("");
  const [running, setRunning] = useState(false);
  const [startedStages, setStartedStages] = useState<string[]>([]);
  const [result, setResult] = useState<CompletePayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(0);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setElapsed((Date.now() - startRef.current) / 1000), 200);
    return () => clearInterval(id);
  }, [running]);

  async function handlePlan() {
    startRef.current = Date.now();
    setRunning(true); setStartedStages([]); setResult(null); setError(null); setElapsed(0);
    try {
      for await (const event of streamPlan(request)) {
        if (event.type === "stage") setStartedStages((p) => (p.includes(event.name) ? p : [...p, event.name]));
        else if (event.type === "complete") setResult(event.data);
        else if (event.type === "error") setError(event.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setElapsed((Date.now() - startRef.current) / 1000); setRunning(false);
    }
  }

  function stageState(name: string): StageState {
    const i = startedStages.indexOf(name);
    if (i === -1) return "pending";
    const last = i === startedStages.length - 1;
    if (last && error) return "failed";
    if (last && !result) return "active";
    return "done";
  }

  const itinerary = result?.itinerary;
  const route = result?.optimized_route ?? [];
  const showBoard = running || startedStages.length > 0 || !!result || !!error;
  const friendlyError =
    error && /429|RESOURCE_EXHAUSTED|quota/i.test(error)
      ? "Rate limit — the free tier resets daily. Try again shortly."
      : error;

  const brief = (result?.trip_brief ?? {}) as { party_size?: number; constraints?: { dietary_restrictions?: string[] } };
  const adults = brief.party_size ?? 2;
  const diet = brief.constraints?.dietary_restrictions?.[0];

  // group day_plans into stations (consecutive same-area), in itinerary order
  const stations: { area: string; days: DayPlan[] }[] = [];
  (itinerary?.day_plans ?? []).forEach((d) => {
    const last = stations[stations.length - 1];
    if (last && norm(last.area) === norm(d.area)) last.days.push(d);
    else stations.push({ area: d.area, days: [d] });
  });
  const routeAbbr = route.map((s) => abbr(s.name)).join(" · ");

  return (
    <main className="mx-auto max-w-[920px] px-7 py-12">
      <header className="flex items-center justify-between border-b-2 border-ink pb-4">
        <span className="font-display text-2xl font-bold tracking-tight">Atlas<span className="text-blue">.</span></span>
        <span className="mono-label text-muted">Departures</span>
      </header>

      <section className="pt-10">
        <p className="mono-label text-blue">Plot a trip</p>
        <h1 className="mt-3 font-display text-3xl font-bold leading-tight">Tell Atlas where you want to go.</h1>

        <textarea
          className="mt-5 w-full rounded-xl border border-line bg-panel p-4 text-sm text-ink placeholder:text-muted focus:border-blue focus:outline-none focus:ring-2 focus:ring-blue/20"
          rows={4}
          maxLength={1200}
          placeholder="Describe your trip — where, when, who's going, what you love, and a rough budget. Or tap an example below to start."
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          disabled={running}
        />

        {/* Starter examples — one tap fills the box */}
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              type="button"
              onClick={() => setRequest(ex.text)}
              disabled={running}
              className="inline-flex items-center gap-1.5 rounded-full border border-line bg-panel px-3.5 py-1.5 text-xs text-ink transition hover:border-blue hover:text-blue focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue/40 disabled:opacity-50"
            >
              <span aria-hidden>{ex.icon}</span>{ex.label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-muted">New to this? Tap an example to fill the box, then edit anything before planning.</p>

        {/* Collapsible "how to describe your trip" recipe */}
        <details className="group mt-3 overflow-hidden rounded-xl border border-line bg-panel">
          <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 font-mono text-[0.64rem] font-bold uppercase tracking-[0.14em] text-blue [&::-webkit-details-marker]:hidden">
            How to describe your trip
            <span aria-hidden className="ml-auto text-sm transition-transform duration-200 group-open:rotate-90">›</span>
          </summary>
          <div className="border-t border-line px-4 pb-4 pt-1">
            <p className="my-3 text-xs text-muted">The more of these you include, the sharper your plan — but even one sentence works.</p>
            {RECIPE.map((r) => (
              <div key={r.k} className="grid grid-cols-[120px_1fr] gap-3 border-b border-dashed border-line py-2 text-sm last:border-b-0">
                <span className="pt-0.5 font-mono text-[0.58rem] uppercase tracking-[0.12em] text-magenta">{r.k}</span>
                <span className="text-ink">{r.d} <span className="italic text-muted">— {r.ex}</span></span>
              </div>
            ))}
          </div>
        </details>

        <button
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-blue px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue/50 disabled:opacity-50"
          onClick={handlePlan}
          disabled={running || request.trim().length === 0}
        >
          {running && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />}
          {running ? "Plotting…" : "Plan my trip →"}
        </button>
      </section>

      {showBoard && (
        <section className="board mt-8 rise">
          <div className="flex items-center gap-2.5 pb-4" style={{ color: "#7C8794", fontFamily: "var(--font-mono)", fontSize: ".62rem", letterSpacing: ".18em", textTransform: "uppercase" }}>
            <span className="live-dot" /> Atlas · {result ? "trip plotted" : error ? "halted" : "plotting"} · {elapsed.toFixed(1)}s
          </div>
          {result ? (
            <>
              <BoardRow k="Destination"><Flap text={(itinerary?.destination ?? "—").toUpperCase()} /></BoardRow>
              <BoardRow k="Duration"><Flap text={`${itinerary?.total_days ?? 0} DAYS · ${adults} PAX`} /></BoardRow>
              <BoardRow k="Route"><Flap text={routeAbbr || "—"} /></BoardRow>
              <BoardRow k="Status"><Flap text="READY TO BOOK" /></BoardRow>
            </>
          ) : (
            STAGES.map((s, i) => {
              const st = stageState(s.name);
              return (
                <div className="board-row" key={s.name}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: ".62rem", letterSpacing: ".14em", color: "#7C8794" }}>STEP {String(i + 1).padStart(2, "0")}</span>
                  <span className="flex items-center gap-2.5" style={{ fontFamily: "var(--font-mono)", fontSize: ".8rem", letterSpacing: ".04em", color: st === "pending" ? "#5A6470" : "var(--board-ink)" }}>
                    {st === "done" ? <span style={{ color: "var(--board-ink)" }}>✓</span>
                      : st === "failed" ? <span style={{ color: "#F87171" }}>×</span>
                      : st === "active" ? <span className="h-3.5 w-3.5 animate-spin rounded-full" style={{ border: "2px solid rgba(255,255,255,.18)", borderTopColor: "var(--board-ink)" }} />
                      : <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#3A434F", display: "inline-block" }} />}
                    {s.label}
                  </span>
                </div>
              );
            })
          )}
          {friendlyError && !result && (
            <div className="board-row">
              <span style={{ fontFamily: "var(--font-mono)", fontSize: ".62rem", letterSpacing: ".14em", color: "#7C8794" }}>Status</span>
              <span style={{ color: "#F87171", fontFamily: "var(--font-mono)", fontSize: ".78rem" }}>{friendlyError}</span>
            </div>
          )}
        </section>
      )}

      {itinerary && (
        <section className="mt-12">
          <p className="mono-label text-blue rise">Your line</p>
          <h2 className="mt-2 font-display text-3xl font-bold rise">{itinerary.destination} · {itinerary.total_days} days</h2>
          <p className="mt-3 max-w-[52ch] rise" style={{ color: "#3a4048" }}>{itinerary.summary}</p>

          {route.length > 0 && (
            <div className="mt-6 h-80 w-full overflow-hidden rounded-2xl border border-line rise">
              <RouteMap route={route} />
            </div>
          )}

          {route.length > 0 && (
            <div className="mt-5 rounded-2xl border border-line bg-panel p-5 rise">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="font-display text-base font-semibold">Getting there</h3>
                <input
                  className="rounded-lg border border-line bg-bg px-3 py-1.5 text-sm text-ink placeholder:text-muted focus:border-blue focus:outline-none focus:ring-2 focus:ring-blue/20"
                  placeholder="Departure city (optional)" value={origin} onChange={(e) => setOrigin(e.target.value)} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <LinkPill href={directionsUrl(origin, route[0].name)}>Directions to {route[0].name}</LinkPill>
                <LinkPill href={flightsUrl(origin, route[0].name)}>Compare flights</LinkPill>
              </div>
              {!origin.trim() && <p className="mt-2 text-xs text-muted">Add your departure city for accurate drive-vs-fly and flight options.</p>}
            </div>
          )}

          <div className="line mt-8">
            {stations.map((st, i) => {
              const color = i % 2 === 0 ? "var(--blue)" : "var(--magenta)";
              const routeStop = route.find((r) => norm(r.name) === norm(st.area));
              const t = itinerary.transport?.find((x) => norm(x.area) === norm(st.area))
                ?? itinerary.transport?.find((x) => norm(x.area).includes(norm(st.area)) || norm(st.area).includes(norm(x.area)));
              const prev = stations[i - 1]?.area;
              const dStart = st.days[0].day_number, dEnd = st.days[st.days.length - 1].day_number;
              return (
                <div className="station rise" key={st.area} style={{ "--c": color, animationDelay: `${i * 60}ms` } as React.CSSProperties}>
                  <div className="node" />
                  <div className="flex flex-wrap items-baseline gap-x-3.5 gap-y-1">
                    <span className="font-display text-2xl font-bold">{st.area}</span>
                    {routeStop?.region && <span className="font-mono text-[.64rem] uppercase tracking-[.14em] text-muted">{routeStop.region}</span>}
                    <span className="ml-auto rounded-full border px-2.5 py-0.5 font-mono text-[.62rem] tracking-[.1em]" style={{ color, borderColor: color }}>
                      {dStart === dEnd ? `Day ${dStart}` : `Days ${dStart}–${dEnd}`}
                    </span>
                  </div>

                  {t && (
                    <div className="mt-2 mb-4 rounded-[10px] border border-line bg-panel p-3.5 text-sm" style={{ color: "#34404c" }}>
                      {t.getting_here && <p><span className="mr-1.5 font-mono text-[.58rem] uppercase tracking-[.14em]" style={{ color }}>Getting here</span>{t.getting_here}</p>}
                      {t.getting_around && <p className="mt-1"><span className="mr-1.5 font-mono text-[.58rem] uppercase tracking-[.14em]" style={{ color }}>Getting around</span>{t.getting_around}</p>}
                    </div>
                  )}

                  <div className="mb-3 flex flex-wrap gap-2">
                    {i > 0 && prev && <LinkPill href={directionsUrl(prev, st.area)}>Directions from {prev}</LinkPill>}
                    <LinkPill href={hotelsUrl(st.area, adults)}>Hotels</LinkPill>
                    <LinkPill href={foodUrl(st.area, diet)}>{diet ? `${diet} food` : "Restaurants"}</LinkPill>
                  </div>

                  {st.days.map((day) => (
                    <article className="ticket my-3" key={day.day_number} style={{ "--c": color } as React.CSSProperties}>
                      <div className="stub">
                        <div className="font-mono text-[.58rem] uppercase tracking-[.16em] opacity-85">Day</div>
                        <div className="font-display text-[2.1rem] font-bold leading-[.9]">{String(day.day_number).padStart(2, "0")}</div>
                        <div className="font-mono text-[.58rem] uppercase tracking-[.16em] opacity-85">{st.area}</div>
                      </div>
                      <div className="px-5 py-4">
                        <h3 className="font-display text-[1.2rem] font-semibold">{day.title}</h3>
                        <div className="mt-2 grid gap-x-6 gap-y-3.5 sm:grid-cols-2">
                          <div>
                            <div className="lbl-x" style={{ color }}>On foot</div>
                            <ul className="space-y-1 text-[.97rem]">
                              {day.activities.map((a, j) => <li key={j} className="flex gap-2"><span style={{ color }}>·</span><span>{a}</span></li>)}
                            </ul>
                          </div>
                          <div>
                            <div className="lbl-x" style={{ color }}>To eat</div>
                            <ul className="space-y-1 text-[.97rem]">
                              {day.food.map((f, j) => (
                                <li key={j}>
                                  <span className="mr-1.5 font-mono text-[.6rem] uppercase tracking-[.1em] text-muted">{f.meal}</span>
                                  <a href={placeUrl(f.name, st.area)} target="_blank" rel="noopener noreferrer" className="eat-link" style={{ "--c": color } as React.CSSProperties}>{f.name}</a>
                                </li>
                              ))}
                            </ul>
                          </div>
                          {day.notes && <p className="border-t border-dashed border-line pt-2.5 text-sm italic text-muted sm:col-span-2">{day.notes}</p>}
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              );
            })}
          </div>

          {itinerary.open_items?.length > 0 && (
            <div className="mt-2 rounded-xl border border-dashed border-ink bg-panel p-6 rise">
              <div className="mono-label text-blue">Before you go</div>
              <ul className="mt-3 space-y-1.5 text-sm">
                {itinerary.open_items.map((item, i) => <li key={i} className="flex gap-2"><span className="text-blue">·</span><span>{item}</span></li>)}
              </ul>
            </div>
          )}
        </section>
      )}
    </main>
  );
}