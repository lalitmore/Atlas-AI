# Home Wi-Fi local verification — 2026-10-23

This report records the earlier local run: frontend at `http://localhost:3000`, backend at
`http://localhost:8000`. The servers were subsequently stopped before publishing the
source to GitHub; this report does not imply they are currently running.
No deployment, Cloud Run/Vercel operation, deployment
configuration change, or school-network work was performed in this task.
Pre-existing uncommitted work was preserved.

## Results

| Step | Result | Evidence |
| --- | --- | --- |
| 1. Preflight | PASS after credential correction | Python 3 resolved Gemini to IPv4/IPv6 addresses outside the network-restricted sandbox. Both configured models returned `OK` in minimal calls with the updated file key. |
| 2. Hybrid models | PASS | The working tree already contained separate settings/factories. Live SDK requests used Flash-Lite three times and Flash once. |
| 3. Trailing model turns | PASS; no production role fix needed | Installed ADK 2.3.0 converts sibling replies to user context and appends a user continuation when necessary. Existing SDK-boundary regression tests pass; real requests also ended in user turns. |
| 4. Live browser flow, map, PDF | PASS for execution/export; travel-content caveats below | Final exact Japan request completed in 37.9 seconds. Five stages started in order, followed by complete, with no error. Real Search metadata, two map pins, and the downloaded PDF were inspected. |
| 5. Final checks | PASS | Backend: 42 tests and Ruff. Frontend: build, lint, TypeScript, 7 stream/link tests. Git exclusions/history checked. |

## Runtime configuration and key precedence

The pipeline `.env` has a nonempty `GOOGLE_API_KEY`,
`GOOGLE_GENAI_USE_VERTEXAI=FALSE`, `ENABLE_SEARCH_GROUNDING=TRUE`, and
`ITINERARY_MODEL=gemini-3.6-flash`. `DEFAULT_MODEL` uses its code default.
No key value was printed or included in the evidence.

The original file key returned 401 and the user replaced it. A separate inherited
`GOOGLE_API_KEY` then shadowed the file because environment variables take
precedence. This key passed intake but returned 429 during Search research. Direct
SDK calls with the updated file key succeeded, including uncapped grounded research.
An ADK diagnostic confirmed its SDK credential did not match the file. This was a
credential-selection issue, not an output-token-limit issue; no cap was added.

For local startup, clear inherited credential variables for the server process:

```sh
cd backend
source .venv/bin/activate
env -u GOOGLE_API_KEY -u GEMINI_API_KEY uvicorn atlas.api.main:app --reload --port 8000
```

```sh
cd frontend
npm run dev -- --hostname localhost
```

Final listeners were `127.0.0.1:8000` and `[::1]:3000`. The normal backend was
restarted after verification without the temporary audit wrapper; health returned
`{"status":"ok"}`.

| Agent | Final model |
| --- | --- |
| intake_agent | gemini-3.5-flash-lite |
| grounded_research_agent | gemini-3.5-flash-lite |
| structured_research_agent | gemini-3.5-flash-lite |
| route_optimizer | Deterministic Python; no model |
| itinerary_agent | gemini-3.6-flash |

## Real request and grounding evidence

The browser submitted exactly:

> 10 days in Japan in October, me and my vegetarian girlfriend, we love anime, food, nature, and photography, budget around $4,500, and we hate early mornings

Final stages: intake → research → structure → optimize → itinerary → complete.
The result has Tokyo on days 1–5 and Kyoto on days 6–10. Day numbers are exactly
1–10 and match the optimizer's area allocations. Every first activity is at 10:30
or 11:00 AM. Transport includes airport arrival, IC cards/local transit, and the
direct Tokyo–Kyoto Shinkansen. The transfer day's food is in Kyoto. Shigetsu is
scheduled for a 1 PM lunch rather than after service or at dinner.

Search was proved by provider metadata, not just the application's boolean flag:
six web queries, sixteen web sources, and thirty grounding supports. Queries
included `Tokyo Kyoto transport time train 2026`,
`Japan train pass price 2026 JR pass`, and restaurant searches for each base.
The research returned named menus, broth/dashi suitability, service hours, and
specific seasonal/event findings. The PDF and browser result came from unmodified
live provider responses, not test fixtures.

The four real SDK request role lists were `[user]`, `[user,user]`,
`[user,user,user]`, and `[user,user,user,user]`. Each credential matched the updated
pipeline file. Evidence is in ignored `output/local-verification/`:
`final-live-evidence.json`, `gemini-requests.jsonl`, `gemini-responses.jsonl`,
`events.jsonl`, and `japan-live.json`.

ADK source evidence: `flows/llm_flows/contents.py` presents other agents' replies
as user context; `models/google_llm.py` calls `_maybe_append_user_content` before
the SDK; `models/base_llm.py` appends a user continuation when the final role is
not user. Existing `backend/tests/test_request_roles.py` also deliberately supplies
`[user,model]` and observes `[user,model,user]`, preserving the model history.

## Bugs and corrections

1. Invalid file credential: user replaced it after the 401 preflight.
2. Inherited credential shadowed the updated file and caused research 429s: local
   startup clears inherited key variables; README documents the precedence.
3. Research details were lost during synthesis and the writer could add restaurants
   from memory: give the writer original findings, retain menus/hours/sources during
   synthesis, and require researched dietary options with dish notes.
4. Shigetsu was scheduled at 2:30 PM despite its 11:00–14:00 service: require
   researched service windows, distinguish lunch-only venues, and flag unknown meals.
5. A dated festival was placed on a numbered day without confirmed travel dates:
   use evergreen activities and put conditional events in open items.
6. The summary called Tokyo–Kyoto eastbound: describe named visit order without
   introducing unsupported compass directions.
7. A Tokyo restaurant was reused after arriving in Kyoto and Tokyo districts became
   separate hotel bases: keep dining in the day's city and consolidate nearby districts.
8. CARTO displayed `API KEY REQUIRED` behind valid pins: use OpenStreetMap standard
   tiles with attribution. The final live map shows real tiles and numbered pins 1–2.
9. README incorrectly said Search was disabled by default: corrected the table.

The temporary recorder initially failed to serialize a Pydantic schema class; this
was corrected in ignored audit tooling before an outbound model call. A minimal
probe's unsupported `thinking_budget=0` setting was removed from the probe only.
The sandboxed build could not fetch Google Fonts; the network-enabled build passed
without changing font or deployment configuration.

## PDF verification

Final artifact: `output/pdf/live-japan/atlas-japan-10-days.pdf`.
It is an exact copy of the browser download
`atlas-japan-10-days (1).pdf` in the browser's downloads folder; the browser added its collision suffix to
the suggested slug `atlas-japan-10-days.pdf`.

The PDF has six A4 pages, 98,592 bytes, and embedded Latin/Japanese fonts.
All 117 checked string fields (itinerary, food, transport, open items, brief
interests/assumptions/missing information, and original request) are present.
Japanese strings including `九州じゃんがら`, `天龍寺`, and `篩月` extract correctly
and render without missing-glyph boxes. All six pages were rendered and visually
reviewed for clipping/overlap. The 116 URI annotations have 17 unique destinations;
their set exactly matches URLs computed from the final live payload by the actual
`frontend/src/lib/links.ts` exports. No unexpected or missing links were found.

Evidence: `pdf-audit.json`, `expected-links.json`, `pdf-extracted-text.txt`,
`final-contact-sheet.png`, `final-page-*.png`, and `live-map.png` in the ignored
verification directory. Earlier live exports are retained separately as diagnostic
evidence and are not the final deliverable.

## Files changed in this task

- `README.md`: correct model/grounding/map documentation, local key precedence,
  fallback instructions, and localhost-only frontend startup.
- `backend/atlas/agents/pipeline/.env` (ignored): explicit Search flag and verified
  itinerary model; the user replaced the credential.
- `backend/atlas/agents/research/prompt.py`: dining, locality, service-time, source,
  and native-name research; preserve those details during synthesis.
- `backend/atlas/agents/itinerary/prompt.py`: original findings, dietary checks,
  realistic timing, conditional dated events, local dining, and native names.
- `backend/atlas/schemas/destination_research.py`: align the candidate-base field
  description with city grouping and practical trip duration.
- `backend/tests/conftest.py`: isolate offline model settings from local fallbacks.
- `frontend/src/components/RouteMap.tsx`: replace the failing tile provider.
- This report and ignored verification/PDF artifacts.

No changes to deployment configuration or the existing hybrid agent wiring were
needed in this task.

## Git and remaining manual checks

`git check-ignore -v` confirms `.env` files and `output/` are ignored.
`git log --all --oneline -- backend/atlas/agents/pipeline/.env .env` returned no
commits. A broader filename history scan found only the intentional `.env.example`
template, not a real `.env`, in available local Git history.

Exact calendar dates, weekday closures, table/ticket availability, and a confirmed
flight connection cannot be established from a month-only request. Before booking:

1. Choose the October year/start date and flight times; map days 1–10 onto those dates.
2. Check each venue's official booking page for that date, service window, and
   vegetarian menu; select the explicitly vegan ramen at the mixed-menu Jangara.
3. Confirm the generated restaurant spelling against the official site. In particular,
   Gemini wrote “Uno Yokiko”; the [official restaurant](https://en.soymilkramen.com/)
   uses “Uno Yukiko.” The export intentionally preserves the actual live response.
4. Check evening temple access/last admission and temporary event dates before
   following the suggested activity times. Search grounding does not guarantee every
   generated factual detail or transliteration is correct.

Primary menu checks: [Jangara Harajuku](https://kyushujangara.co.jp/en/shoplist/harajuku/),
[Vegan Sushi Tokyo](https://vcook.co.jp/vegansushitokyo/en),
[AIN SOPH](https://www.ain-soph.jp/english),
[mumokuteki](https://mumokuteki.com/cafe/en/), and
[Shigetsu](https://www.tenryuji.com/en/shigetsu/index.html).
