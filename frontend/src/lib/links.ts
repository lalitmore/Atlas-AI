// Deep links out to real booking/navigation sites. Atlas builds the pre-filled URL;
// the user does the actual booking on the destination site. No API key, no quota.

const enc = encodeURIComponent;

// Maps directions with NO travelmode → Google shows the most relevant modes
// (driving / transit / flight) for the route. origin is optional: when omitted,
// Maps uses the viewer's current location.
export function directionsUrl(origin: string | undefined, destination: string) {
  const o = origin?.trim() ? `&origin=${enc(origin.trim())}` : "";
  return `https://www.google.com/maps/dir/?api=1${o}&destination=${enc(destination)}`;
}

// Google Flights via a durable text query. Secondary to the directions link, which
// already surfaces flights when flying is the sensible mode.
export function flightsUrl(origin: string | undefined, destination: string) {
  const q = origin?.trim() ? `Flights to ${destination} from ${origin.trim()}` : `Flights to ${destination}`;
  return `https://www.google.com/travel/flights?q=${enc(q)}`;
}

// Booking.com search for a city. Dates omitted (we don't have a confirmed start date)
// so the user picks them; party size and one room are pre-filled.
export function hotelsUrl(city: string, adults: number) {
  const a = Math.max(1, adults || 1);
  return `https://www.booking.com/searchresults.html?ss=${enc(city)}&group_adults=${a}&group_children=0&no_rooms=1`;
}

// Maps place search for food, scoped to the trip's dietary restriction when there is one.
export function foodUrl(city: string, diet?: string) {
  const q = diet ? `${diet} restaurants in ${city}` : `restaurants in ${city}`;
  return `https://www.google.com/maps/search/?api=1&query=${enc(q)}`;
}

// A Maps search for a named place, scoped to its area to disambiguate branches.
// It's a search, not a claim the place exists or is open — the honest way to link a
// model-suggested restaurant.
export function placeUrl(name: string, area?: string) {
  const q = area ? `${name} ${area}` : name;
  return `https://www.google.com/maps/search/?api=1&query=${enc(q)}`;
}