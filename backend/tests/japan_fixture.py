"""Deterministic sample data for offline API/browser/PDF acceptance checks, never live research."""
from atlas.optimization import optimize_route
from atlas.schemas import DestinationResearch, Itinerary, TripBrief

JAPAN_REQUEST = (
    "10 days in Japan in October, me and my vegetarian girlfriend, we love anime, food, "
    "nature, and photography, budget around $4,500, and we hate early mornings"
)


def japan_model_responses() -> list[str]:
    brief = TripBrief.model_validate({
        "destination": "Japan", "duration_days": 10, "party_size": 2,
        "travel_window": {"month": "October", "start_date": "2026-10-23", "end_date": "2026-11-01"},
        "budget": {"amount": 4500, "currency": "USD", "basis": "total"},
        "interests": ["anime", "food", "nature", "photography"],
        "constraints": {"avoid_early_mornings": True, "dietary_restrictions": ["vegetarian"]},
        "assumptions": ["Two adults traveling together.", "Dates are illustrative for this offline sample."],
        "missing_info": ["Departure airport", "Accommodation preferences"],
    })
    research = DestinationResearch.model_validate({
        "destination": "Japan", "summary": "Tokyo, Kyoto and Osaka with relaxed starts.",
        "candidate_areas": [
            {"name": "Tokyo", "region": "Kanto", "latitude": 35.68, "longitude": 139.69,
             "why_it_fits": "Anime, parks, photography and vegetarian food.",
             "matched_interests": ["anime", "food", "nature", "photography"]},
            {"name": "Kyoto", "region": "Kansai", "latitude": 35.01, "longitude": 135.77,
             "why_it_fits": "Gardens, temples and vegetarian cuisine.",
             "matched_interests": ["food", "nature", "photography"]},
            {"name": "Osaka", "region": "Kansai", "latitude": 34.69, "longitude": 135.50,
             "why_it_fits": "Food and anime districts.", "matched_interests": ["anime", "food"]},
        ],
        "seasonal_notes": "October may be mild; verify weather and seasonal events.",
        "key_findings": ["Use trains between cities; verify timetables."],
        "assumptions": ["Offline sample, not live research."],
        "needs_grounding": ["Opening hours", "Train prices and vegetarian menus"],
    })
    route = optimize_route([
        {"name": area.name, "region": area.region, "latitude": area.latitude,
         "longitude": area.longitude, "weight": len(area.matched_interests)}
        for area in research.candidate_areas
    ], 10)
    places = {
        "Tokyo": ("浅草・Akihabara", "Sensō-ji 浅草寺", "T's Tantan Tokyo"),
        "Kyoto": ("京都の庭園", "Arashiyama 嵐山 gardens", "Vegan Ramen UZU Kyoto"),
        "Osaka": ("大阪の食とアニメ", "Dotonbori 道頓堀 and Den Den Town", "Paprika Shokudo Vegan"),
    }
    days = []
    for stop in route:
        title, activity, restaurant = places[stop["name"]]
        for _ in range(stop["days"]):
            days.append({
                "day_number": len(days) + 1, "area": stop["name"], "title": title,
                "activities": ["10:30 — Start after a relaxed breakfast.",
                               f"12:00 — Explore {activity}.",
                               "16:00 — Photography walk, then Café time."],
                "food": [{"meal": "Lunch", "name": restaurant},
                         {"meal": "Coffee", "name": "Café sample — São Paulo accents"}],
                "notes": "Vegetarian: confirm broth and sauces contain no fish. Verify all opening hours.",
            })
    itinerary = Itinerary.model_validate({
        "destination": "Japan", "total_days": 10,
        "summary": "A relaxed route through anime districts, gardens, and vegetarian food in three cities.",
        "day_plans": days,
        "transport": [{
            "area": stop["name"],
            "getting_here": "Train from the airport." if index == 0 else "Train from the previous city; verify fares and timetables.",
            "getting_around": "Local trains and easy walking; use an IC card and check last trains.",
        } for index, stop in enumerate(route)],
        "open_items": ["Book flights and hotels.", "Confirm menus and opening hours.",
                       "Offline sample: current prices and availability have not been checked."],
    })
    return [brief.model_dump_json(), "Offline sample research: verify all current details.",
            research.model_dump_json(), itinerary.model_dump_json()]
