# LUVIA Frontend — Weather Intelligence for India

A standalone React + Vite frontend for LUVIA. It can run in **synthetic demo mode** without the LUVIA backend, then be configured to request event data from FastAPI after you verify the API schema.

## Requirements

- Node.js 20 or newer (Node.js 22 LTS recommended)
- npm (installed with Node.js)
- Internet access for installing npm packages and loading OpenStreetMap map tiles

## Install and run (Windows PowerShell)

1. Extract the ZIP.
2. Copy the extracted `frontend` folder into your local LUVIA repository, beside `backend`.
3. Open the `frontend` folder in VS Code, or open a terminal and run:

```powershell
cd path	o\Luviarontend
npm install
Copy-Item .env.example .env
npm run dev
```

4. Open the local URL printed by Vite (normally `http://127.0.0.1:5173`).

## Demo mode

The default `.env.example` sets:

```env
VITE_USE_MOCK_DATA=true
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_REFRESH_INTERVAL=30000
```

All records in demo mode are synthetic. They are explicitly marked in the interface. Map selection, search, filters, summary statistics, state treemap, charts and theme selection work with the demo records. One incident intentionally has multiple source records so the incident counts can demonstrate de-duplication.

Restart the Vite server after changing `.env` values.

## Connecting to FastAPI

1. Start your existing FastAPI backend using your established project command.
2. Open `http://127.0.0.1:8000/docs` (adjust the port if yours differs) and inspect the actual `GET /events` endpoint and response schema.
3. Set `VITE_USE_MOCK_DATA=false` and `VITE_API_BASE_URL=http://127.0.0.1:8000` in `.env`.
4. If your response is not a JSON array or an object with an `events` array, update the `getEvents()` response normalization in `src/services/eventService.js` to match your real schema.
5. Configure FastAPI CORS to allow your Vite origin during local development, normally `http://127.0.0.1:5173` and/or `http://localhost:5173`.

### API contract status

The repository could not be cloned or inspected in this build environment because outbound DNS/network access was unavailable. Therefore **no backend route has been independently verified**. `GET /events` is an explicitly labelled candidate integration point based on the project brief, not a claim that its contract is confirmed. The frontend does not call the proposed `/map` or `/analytics` routes. Those views derive charts from the loaded event array.

The verification action is deliberately disabled for demo records. `POST /verify?event_id=...` is left as a candidate in `src/services/verificationService.js` and must be confirmed against FastAPI `/docs` before live use, including HTTP method, query/body fields, and response shape.

If the live request fails, the UI displays an error and does **not** silently replace the response with synthetic data.

## Map and licensing

The map uses Leaflet and OpenStreetMap tiles with attribution. A network connection is required for tiles. Map tiles and the geographic boundaries rendered by the basemap are not bundled into the ZIP. Review the tile provider's usage policy before production deployment or heavy traffic. This version does not bundle a separate administrative state-boundary GeoJSON asset.

## Themes

- Dawn: 05:00–07:59 local time
- Morning: 08:00–15:59
- Evening: 16:00–18:59
- Night: 19:00–04:59

These are configurable local clock ranges, not astronomical sunrise/sunset calculations. Use the theme selector to choose a manual theme or return to Automatic.

## Refresh behavior

The event service polls on a configurable interval (default 30 seconds), prevents overlapping requests, and displays the last successful fetch time. Actual freshness depends on backend ingestion and source update schedules. Polling is not a push-based real-time stream.

## Build

```powershell
npm run build
npm run preview
```

## Main files

- `src/App.jsx` — navigation, theme state and page routing
- `src/features/live-map/LiveMapPage.jsx` — search, filters and dashboard layout
- `src/components/IndiaMap.jsx` — Leaflet map and event markers
- `src/components/EventDetails.jsx` — incident details and source links
- `src/components/StateTreemap.jsx` — clickable state activity tiles
- `src/features/analytics/AnalyticsPage.jsx` — charts derived from the event array
- `src/features/verification/VerificationPage.jsx` — status review table
- `src/services/eventService.js` — demo/live data boundary and response normalization
- `src/hooks/useWeatherData.js` — polling, loading and error state
- `src/styles/global.css` — responsive layout and four themes

## Current limitations

- Backend route and schema integration is not verified in this environment.
- Separate state-boundary geometry is not bundled; basemap borders depend on the tile provider.
- Evidence media is linked only when a source URL is provided; no video is invented or embedded.
- Verification actions are not enabled until the backend contract is confirmed.
- Demo data is synthetic and must not be presented as actual weather intelligence.
- npm install, browser interaction tests and production build could not be run in this environment because package-registry/network access is unavailable. Run the commands above locally and share any error output for debugging.


## Connecting to the existing LUVIA FastAPI backend

The following response shapes were confirmed from the running API documentation and responses supplied during setup:

- `GET /events` returns an object containing an `events` array.
- `GET /events/{event_id}` returns an object with an `event` object and a `sources` array.
- `GET /map` returns an object containing an `events` array.
- `GET /analytics` returns `total_events`, `verified_events`, `events_by_severity`, and `events_by_type`.
- `POST /verify` requires the integer query parameter `event_id`. The frontend asks for confirmation before sending this request.

### Switch from demo mode to backend mode

1. Keep the FastAPI backend running at `http://127.0.0.1:8000`.
2. In this `frontend` directory, open `.env` (create it by copying `.env.example` if it does not exist).
3. Set these values:

   ```env
   VITE_USE_MOCK_DATA=false
   VITE_API_BASE_URL=http://127.0.0.1:8000
   VITE_REFRESH_INTERVAL=30000
   ```

4. Stop and restart the Vite server after changing `.env` (`Ctrl+C`, then `npm run dev`). Vite reads environment variables at startup.
5. Check the browser's dashboard badge. It should say `CONNECTED DATA` when the API request succeeds.

The frontend polls `GET /events` at the configured interval and keeps the previous successful data visible if a later refresh fails. It does not silently fall back to demo data in live mode. Event detail panels fetch `GET /events/{event_id}` to display available source records.

### If the browser reports a network or CORS error

Open `http://127.0.0.1:8000/docs` and confirm the backend is still running. If the browser console specifically reports CORS, configure the existing FastAPI CORS middleware to allow the local frontend origin `http://127.0.0.1:5173`; do not disable CORS or allow all origins in production. No backend files are changed by this frontend package.

### Data-quality notes from the inspected sample

The sample `/events` response contained `severity: "unknown"`, null credibility scores, and some null states. `/analytics` returned 1,959 total events and 0 verified events at the time of inspection. The frontend preserves unknown/missing values rather than fabricating severity or scores. The sample timestamps appeared older than the current date, so the default “Last 24 hours” filter may hide them; choose “All available time” to inspect older records.

`POST /verify` can run backend logic and may alter server-side verification state. The UI therefore requires an explicit confirmation before calling it. Test first with an event you are comfortable verifying. The backend remains unchanged by this frontend deliverable.
