// Loaded only by the download handler. The PDF renderer never enters the initial page bundle.
import { Document, Font, Link, Page, StyleSheet, Text, View } from "@react-pdf/renderer";
import type { ReactNode } from "react";
import type { CompletePayload, DayPlan } from "@/lib/atlas";
import { atlasUrl, directionsUrl, flightsUrl, foodUrl, fullRouteUrl, hotelsUrl, placeUrl } from "@/lib/links";

export interface ItineraryPdfProps {
  data: CompletePayload;
  request: string;
  origin?: string;
  generatedAt?: Date;
}

const fontRequirements = (data: CompletePayload, request: string, origin?: string) => {
  const text = JSON.stringify(data) + request + (origin ?? "");
  return {
    japanese: /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]/u.test(text),
    korean: /\p{Script=Hangul}/u.test(text),
  };
};
let registeredBase = "";
let registeredCjkBase = "";
let registeredKoreanBase = "";

/** Register paths, not remote CDN assets. CJK is requested only for a CJK-containing export. */
export function registerItineraryPdfFonts(data: CompletePayload, request: string, origin?: string, fontBase = "/fonts") {
  const base = fontBase.replace(/\/$/, "");
  if (registeredBase !== base) {
    Font.register({ family: "AtlasNoto", fonts: [
      { src: `${base}/NotoSans-Regular.ttf`, fontWeight: 400 },
      { src: `${base}/NotoSans-Bold.ttf`, fontWeight: 700 },
    ] });
    registeredBase = base;
  }
  const needs = fontRequirements(data, request, origin);
  if (needs.japanese && registeredCjkBase !== base) {
    Font.register({ family: "AtlasCjk", src: `${base}/NotoSansJP-Regular.ttf` });
    registeredCjkBase = base;
  }
  if (needs.korean && registeredKoreanBase !== base) {
    Font.register({ family: "AtlasKorean", src: `${base}/NotoSansKR-Regular.ttf` });
    registeredKoreanBase = base;
  }
  Font.registerHyphenationCallback((word) => [word]);
}

const colors = { ink: "#0E1216", muted: "#5A6470", line: "#D7D8D2", blue: "#1D4ED8", pale: "#F4F7FD" };
const styles = StyleSheet.create({
  page: { paddingTop: 38, paddingBottom: 58, paddingHorizontal: 40, fontSize: 9.5, color: colors.ink },
  body: { fontSize: 9.5, lineHeight: 1.5 },
  brand: { fontSize: 10, fontWeight: 700, color: colors.blue, letterSpacing: 1.5, marginBottom: 12 },
  title: { fontSize: 26, fontWeight: 700, lineHeight: 1.2, marginBottom: 10 },
  summary: { fontSize: 10.5, marginBottom: 12, color: colors.muted },
  metadata: { marginBottom: 4 },
  bold: { fontWeight: 700 },
  muted: { color: colors.muted },
  label: { fontSize: 8, color: colors.muted, marginBottom: 2 },
  quote: { backgroundColor: "#F4F4F1", borderLeftWidth: 2, borderLeftColor: colors.blue, padding: 10, marginTop: 10, marginBottom: 10 },
  notice: { backgroundColor: colors.pale, padding: 10, marginTop: 4, marginBottom: 10, fontSize: 8.5 },
  section: { fontSize: 15, fontWeight: 700, color: colors.blue, marginTop: 18, marginBottom: 8 },
  subheading: { fontSize: 10, fontWeight: 700, marginBottom: 4 },
  item: { marginBottom: 4 },
  route: { borderBottomWidth: 1, borderBottomColor: colors.line, paddingVertical: 6 },
  routeTitle: { fontSize: 11, fontWeight: 700 },
  link: { color: colors.blue, textDecoration: "underline", fontSize: 9 },
  links: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginTop: 6 },
  transport: { backgroundColor: colors.pale, padding: 10, marginTop: 8, marginBottom: 9 },
  city: { fontSize: 16, fontWeight: 700, marginTop: 16, marginBottom: 4 },
  day: { borderWidth: 1, borderColor: colors.line, borderRadius: 6, padding: 12, marginBottom: 10 },
  dayKicker: { fontSize: 8, fontWeight: 700, color: colors.blue, marginBottom: 3 },
  dayTitle: { fontSize: 12, fontWeight: 700, lineHeight: 1.3, marginBottom: 7 },
  activity: { marginBottom: 3 },
  foodHeading: { fontSize: 8, fontWeight: 700, color: colors.muted, marginTop: 6, marginBottom: 3 },
  notes: { fontSize: 8.5, color: colors.muted, borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 6, marginTop: 7 },
  booking: { borderTopWidth: 1, borderTopColor: colors.line, paddingTop: 10, marginBottom: 12 },
  footer: { position: "absolute", bottom: 24, left: 40, right: 40, height: 23, borderTopWidth: 1, borderTopColor: colors.line, fontFamily: "AtlasNoto", fontSize: 8, color: colors.muted },
  footerLink: { position: "absolute", top: 8, left: 0, height: 13, fontSize: 8, color: colors.blue, textDecoration: "underline" },
  footerPage: { position: "absolute", top: 8, right: 0, height: 13, fontSize: 8 },
});

const norm = (text: string) => text.trim().toLowerCase();
// ISO calendar dates are treated as dates, without a timezone shift.
function formatDate(value?: string | null) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return value ?? "";
  const date = new Date(`${value}T12:00:00Z`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
}

function dayDate(start: string | null | undefined, day: number) {
  if (!start || !/^\d{4}-\d{2}-\d{2}$/.test(start)) return "";
  const date = new Date(`${start}T12:00:00Z`);
  if (Number.isNaN(date.getTime())) return "";
  date.setUTCDate(date.getUTCDate() + day - 1);
  return formatDate(date.toISOString().slice(0, 10));
}

function BulletList({ items }: { items: string[] }) {
  return <>{items.filter(Boolean).map((item, index) => <Text key={index} style={styles.item} orphans={2} widows={2}>{"• "}{item}</Text>)}</>;
}

function SectionTitle({ children }: { children: ReactNode }) {
  return <Text style={styles.section} minPresenceAhead={45}>{children}</Text>;
}

// Only compact cards are kept together. An unusually long day is allowed to flow onto another page.
function compactDay(day: DayPlan) {
  const text = [day.title, ...day.activities, ...day.food.map((food) => `${food.meal} ${food.name}`), day.notes].join("\n");
  return text.length < 1000 && text.split("\n").length <= 12 && day.activities.length <= 6 && day.food.length <= 4;
}

export default function ItineraryPdf({ data, request, origin, generatedAt = new Date() }: ItineraryPdfProps) {
  const { itinerary, trip_brief: brief, optimized_route: route } = data;
  const window = brief.travel_window;
  const constraints = brief.constraints;
  const diet = constraints?.dietary_restrictions?.join(", ");
  const adults = brief.party_size ?? 1;
  const dateRange = [formatDate(window?.start_date), formatDate(window?.end_date)].filter(Boolean).join(" - ");
  const budget = brief.budget && `${brief.budget.currency} ${brief.budget.amount.toLocaleString("en-US")} ${brief.budget.basis.replaceAll("_", " ")}`;
  const transports = (itinerary.transport ?? []).filter((transport) => transport.getting_here?.trim() || transport.getting_around?.trim());
  const intercity = transports.filter((transport) => transport.getting_here?.trim());
  const cities = [...new Set([...route.map((stop) => stop.name), ...itinerary.day_plans.map((day) => day.area), ...(itinerary.transport ?? []).map((transport) => transport.area)])];
  const stations: { area: string; days: DayPlan[] }[] = [];
  itinerary.day_plans.forEach((day) => {
    const last = stations[stations.length - 1];
    if (last && norm(last.area) === norm(day.area)) last.days.push(day);
    else stations.push({ area: day.area, days: [day] });
  });
  const matchingTransport = (area: string) => transports.find((item) => norm(item.area) === norm(area))
    ?? transports.find((item) => norm(item.area).includes(norm(area)) || norm(area).includes(norm(item.area)));
  const additionalTransport = transports.filter((transport) => !stations.some((station) => matchingTransport(station.area) === transport));
  const needs = fontRequirements(data, request, origin);
  const pageFonts = ["AtlasNoto", ...(needs.japanese ? ["AtlasCjk"] : []), ...(needs.korean ? ["AtlasKorean"] : [])];

  return (
    <Document title={`${itinerary.destination} - ${itinerary.total_days} days | Atlas AI`} author="Atlas AI" subject="Travel itinerary" language="en">
      <Page size="A4" style={[styles.page, { fontFamily: pageFonts }]}>
        <View style={styles.body}>
        <Text style={styles.brand}>ATLAS AI / YOUR TRIP</Text>
        <Text style={styles.title}>{itinerary.destination} · {itinerary.total_days} days</Text>
        {itinerary.summary && <Text style={styles.summary}>{itinerary.summary}</Text>}
        {(dateRange || window?.month || window?.flexible) && <Text style={styles.metadata}><Text style={styles.bold}>When: </Text>{dateRange || window.month || "Dates not specified"}{dateRange && window?.month ? ` (requested month: ${window.month})` : ""}{window?.flexible ? " · Flexible dates" : ""}</Text>}
        {brief.duration_days !== itinerary.total_days && <Text style={styles.metadata}><Text style={styles.bold}>Requested duration: </Text>{brief.duration_days} days</Text>}
        {norm(brief.destination) !== norm(itinerary.destination) && <Text style={styles.metadata}><Text style={styles.bold}>Requested destination: </Text>{brief.destination}</Text>}
        <Text style={styles.metadata}><Text style={styles.bold}>Travelers: </Text>{adults}{diet ? ` · Dietary needs: ${diet}` : ""}</Text>
        {budget && <Text style={styles.metadata}><Text style={styles.bold}>Budget: </Text>{budget}</Text>}
        {origin?.trim() && <Text style={styles.metadata}><Text style={styles.bold}>Departure city: </Text>{origin.trim()}</Text>}
        {!!brief.interests?.length && <Text style={styles.metadata}><Text style={styles.bold}>Interests: </Text>{brief.interests.join(", ")}</Text>}
        {constraints?.avoid_early_mornings && <Text style={styles.metadata}><Text style={styles.bold}>Pace: </Text>Avoid early mornings.</Text>}
        {constraints?.max_walking_per_day_km != null && <Text style={styles.metadata}><Text style={styles.bold}>Walking limit: </Text>{constraints.max_walking_per_day_km} km per day.</Text>}
        {!!constraints?.other?.length && <Text style={styles.metadata}><Text style={styles.bold}>Other needs: </Text>{constraints.other.join("; ")}</Text>}
        {request.trim() && <View style={styles.quote}><Text style={styles.label}>YOUR ORIGINAL REQUEST</Text><Text>{request.trim()}</Text></View>}
        <Text style={[styles.muted, { fontSize: 8 }]}>PDF generated {generatedAt.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })}</Text>
        {data.research_grounded === false && <View style={styles.notice}><Text style={styles.bold}>Draft based on general knowledge</Text><Text>This plan uses no live web research. Verify current prices, opening hours, availability, event dates, and dietary suitability before booking.</Text></View>}

        {(route.length > 0 || intercity.length > 0) && <SectionTitle>At a glance</SectionTitle>}
        {route.map((stop, index) => <View key={`${stop.name}-${index}`} style={styles.route} wrap={false}>
          <Text style={styles.routeTitle}>{index + 1}. {stop.name}{stop.region ? ` / ${stop.region}` : ""}</Text>
          <Text style={styles.muted}>{stop.days} {stop.days === 1 ? "day" : "days"} · {stop.day_start === stop.day_end ? `Day ${stop.day_start}` : `Days ${stop.day_start}-${stop.day_end}`}</Text>
        </View>)}
        {route.length > 0 && <View style={styles.links} wrap={false}><Link src={fullRouteUrl(route.map((stop) => stop.name))} style={styles.link}>Open full route in Google Maps</Link></View>}
        {intercity.length > 0 && <View style={{ marginTop: 10 }}><Text style={styles.subheading} minPresenceAhead={25}>Inter-city transport</Text>{intercity.map((transport, index) => <Text key={index} style={styles.item}><Text style={styles.bold}>{transport.area}: </Text>{transport.getting_here}</Text>)}</View>}

        {(brief.assumptions?.length > 0 || brief.missing_info?.length > 0 || itinerary.open_items?.length > 0) && <SectionTitle>Assumptions & open items</SectionTitle>}
        {!!brief.assumptions?.length && <><Text style={styles.subheading} minPresenceAhead={25}>Assumptions</Text><BulletList items={brief.assumptions} /></>}
        {!!brief.missing_info?.length && <><Text style={styles.subheading} minPresenceAhead={25}>Still to decide</Text><BulletList items={brief.missing_info} /></>}
        {!!itinerary.open_items?.length && <><Text style={styles.subheading} minPresenceAhead={25}>Before you go</Text><BulletList items={itinerary.open_items} /></>}

        {stations.length > 0 && <SectionTitle>Day-by-day itinerary</SectionTitle>}
        {stations.map((station, index) => {
          const transport = matchingTransport(station.area);
          const previous = stations[index - 1]?.area ?? origin;
          return <View key={`${station.area}-${index}`}>
            <View wrap={false} minPresenceAhead={compactDay(station.days[0]) ? 230 : 80}>
              <Text style={styles.city}>{station.area}</Text>
              {transport && <View style={styles.transport}>
                {transport.getting_here && <Text style={styles.item}><Text style={styles.bold}>Getting here: </Text>{transport.getting_here}</Text>}
                {transport.getting_around && <Text><Text style={styles.bold}>Getting around: </Text>{transport.getting_around}</Text>}
              </View>}
            </View>
            {station.days.map((day, dayIndex) => <View key={day.day_number} style={styles.day} wrap={!compactDay(day)}>
              <Text style={styles.dayKicker}>DAY {String(day.day_number).padStart(2, "0")} / {day.area}{dayDate(window?.start_date, day.day_number) ? ` / ${dayDate(window?.start_date, day.day_number)}` : ""}</Text>
              <Text style={styles.dayTitle} minPresenceAhead={30}>{day.title}</Text>
              {day.activities.map((activity, activityIndex) => <Text key={activityIndex} style={styles.activity} orphans={2} widows={2}>{activityIndex + 1}. {activity}</Text>)}
              {day.food.length > 0 && <Text style={styles.foodHeading} minPresenceAhead={24}>FOOD STOPS{diet ? ` / ${diet}` : ""}</Text>}
              {day.food.map((food, foodIndex) => <Text key={foodIndex} style={styles.item} orphans={2} widows={2}><Text style={styles.muted}>{food.meal}: </Text><Link src={placeUrl(food.name, day.area)} style={styles.link}>{food.name}</Link></Text>)}
              {day.notes && <Text style={styles.notes} orphans={2} widows={2}>{day.notes}</Text>}
              <View style={styles.links} wrap={false}><Link src={dayIndex === 0 ? directionsUrl(previous, day.area) : placeUrl(day.area)} style={styles.link}>{dayIndex === 0 && previous ? `Directions from ${previous}` : `Explore ${day.area} on Maps`}</Link></View>
            </View>)}
          </View>;
        })}

        {additionalTransport.length > 0 && <SectionTitle>Additional transport notes</SectionTitle>}
        {additionalTransport.map((transport, index) => <View key={index} style={styles.transport}>
          <Text style={styles.subheading} minPresenceAhead={25}>{transport.area}</Text>
          {transport.getting_here?.trim() && <Text style={styles.item}><Text style={styles.bold}>Getting here: </Text>{transport.getting_here}</Text>}
          {transport.getting_around?.trim() && <Text><Text style={styles.bold}>Getting around: </Text>{transport.getting_around}</Text>}
        </View>)}

        {cities.length > 0 && <SectionTitle>Booking links by city</SectionTitle>}
        {cities.map((city) => <View key={city} style={styles.booking} wrap={false}>
          <Text style={styles.subheading}>{city}</Text>
          <View style={styles.links}>
            <Link src={hotelsUrl(city, adults)} style={styles.link}>Hotels in {city}</Link>
            <Link src={flightsUrl(origin, city)} style={styles.link}>Flights to {city}</Link>
            <Link src={foodUrl(city, diet)} style={styles.link}>{diet ? `${diet} food` : "Restaurants"} in {city}</Link>
          </View>
        </View>)}
        {cities.length > 0 && <Text style={[styles.muted, { fontSize: 8 }]}>Booking and Maps links open searches. Confirm dates, party details, availability, prices, and menus on the destination site.</Text>}
        </View>

        <View fixed wrap={false} style={styles.footer}>
          <Link src={atlasUrl()} style={styles.footerLink}>Planned with Atlas AI</Link>
          <Text style={styles.footerPage} render={({ pageNumber, totalPages }) => `Page ${pageNumber} of ${totalPages}`} />
        </View>
      </Page>
    </Document>
  );
}
