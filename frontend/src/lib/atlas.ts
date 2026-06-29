// The single seam between the frontend and the Atlas backend: types that mirror the
// backend's JSON, plus a helper that POSTs to /api/plan and yields parsed SSE events.

export interface FoodStop {
  meal: string;
  name: string;
}

export interface DayPlan {
  day_number: number;
  area: string;
  title: string;
  activities: string[];
  food: FoodStop[];
  notes: string;
}


export interface Itinerary {
  destination: string;
  total_days: number;
  summary: string;
  day_plans: DayPlan[];
  open_items: string[];
}

export interface RouteStop {
  name: string;
  region: string;
  latitude: number;
  longitude: number;
  weight: number;
  days: number;
  day_start: number;
  day_end: number;
}

export interface CompletePayload {
  trip_brief: Record<string, unknown>;
  optimized_route: RouteStop[];
  itinerary: Itinerary;
}

export interface CityTransport {
  area: string;
  getting_here: string;
  getting_around: string;
}

export interface Itinerary {
  destination: string;
  total_days: number;
  summary: string;
  day_plans: DayPlan[];
  transport: CityTransport[];
  open_items: string[];
}

// The discrete events our backend emits over SSE.
export type PlanEvent =
  | { type: "stage"; name: string; label: string }
  | { type: "complete"; data: CompletePayload }
  | { type: "error"; message: string };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// POST the request and yield each SSE event as it streams in. Native EventSource is
// GET-only, so we read the response body stream and parse SSE frames by hand.
export async function* streamPlan(request: string): AsyncGenerator<PlanEvent> {
  const res = await fetch(`${API_BASE}/api/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`Request failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Frames are separated by a blank line — \n\n OR \r\n\r\n depending on the server.
    const frames = buffer.split(/\r?\n\r?\n/);   // CHANGED: was split("\n\n")
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      let eventName = "message";
      let dataStr = "";
      for (const line of frame.split(/\r?\n/)) {  // CHANGED: was frame.split("\n")
        if (line.startsWith(":")) continue;
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
      }
      if (!dataStr) continue;

      const payload = JSON.parse(dataStr);
      if (eventName === "stage") yield { type: "stage", name: payload.name, label: payload.label };
      else if (eventName === "complete") yield { type: "complete", data: payload as CompletePayload };
      else if (eventName === "error") yield { type: "error", message: payload.message };
    }
  }
}