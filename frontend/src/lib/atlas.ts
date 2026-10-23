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

// Mirrors backend/atlas/schemas/trip_brief.py.
export interface TripBrief {
  destination: string;
  duration_days: number;
  travel_window: {
    month: string | null;
    start_date: string | null;
    end_date: string | null;
    flexible: boolean;
  };
  party_size: number;
  budget: { amount: number; currency: string; basis: "total" | "per_person" | "per_day" } | null;
  interests: string[];
  constraints: {
    avoid_early_mornings: boolean;
    dietary_restrictions: string[];
    max_walking_per_day_km: number | null;
    other: string[];
  };
  assumptions: string[];
  missing_info: string[];
}

export interface CompletePayload {
  trip_brief: TripBrief;
  optimized_route: RouteStop[];
  itinerary: Itinerary;
  research_grounded?: boolean;
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
  | { type: "error"; message: string; code?: string; stage?: string | null };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// POST the request and yield each SSE event as it streams in. Native EventSource is
// GET-only, so we read the response body stream and parse SSE frames by hand.
export async function* streamPlan(request: string): AsyncGenerator<PlanEvent> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request }),
    });
  } catch {
    yield { type: "error", code: "BACKEND_UNREACHABLE", message: "Atlas couldn't reach the local server. Check that the backend is running and try again." };
    return;
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail ?? body;
    yield {
      type: "error",
      code: typeof detail?.code === "string" ? detail.code : "REQUEST_FAILED",
      message: typeof detail?.message === "string" ? detail.message
        : typeof detail === "string" ? detail : "Atlas couldn't start this request. Please try again.",
      stage: typeof detail?.stage === "string" ? detail.stage : null,
    };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Frames are separated by a blank line — \n\n OR \r\n\r\n depending on the server.
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        let eventName = "message";
        let dataStr = "";
        for (const line of frame.split(/\r?\n/)) {
          if (line.startsWith(":")) continue;
          if (line.startsWith("event:")) eventName = line.slice(6).trim();
          else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
        }
        if (!dataStr) continue;

        const payload = JSON.parse(dataStr);
        if (eventName === "stage") yield { type: "stage", name: payload.name, label: payload.label };
        else if (eventName === "complete") {
          yield { type: "complete", data: payload as CompletePayload };
          return;
        } else if (eventName === "error") {
          yield { type: "error", message: payload.message, code: payload.code, stage: payload.stage };
          return;
        }
      }
    }
    yield { type: "error", code: "INCOMPLETE_STREAM", message: "The connection ended before your plan was ready. Please try again." };
  } catch {
    yield { type: "error", code: "CONNECTION_LOST", message: "Atlas lost the connection while planning. Please try again." };
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
