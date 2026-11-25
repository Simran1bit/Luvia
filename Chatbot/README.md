# LUVIA Weather Assistant — local integration package

This package is designed to be copied into the root of the existing LUVIA repository. It does not edit existing files automatically. LLM fallback for database retrieval failures uses `GROQ_API_KEY`.

## Important compatibility note

The package includes live Open-Meteo weather/forecast retrieval and a read-only PostgreSQL adapter that discovers a small set of conventional event/warning table names. The exact current LUVIA schema and frontend design tokens could not be inspected from this execution environment. Therefore, event/warning retrieval may require setting `LUVIA_CHAT_EVENT_TABLE` and `LUVIA_CHAT_WARNING_TABLE` to the actual table names and then mapping any nonstandard columns. It will report missing sources rather than fabricate records. The UI uses CSS variables with safe defaults; tune these to the exact LUVIA theme if needed.

## 1. Copy into LUVIA

Extract this `Chatbot` folder into the LUVIA repository root. Keep the folder name and location unchanged.

## 2. Backend setup

Activate the same Python environment used by LUVIA, then install any missing packages from `Chatbot/requirements.txt`:

```powershell
pip install -r Chatbot/requirements.txt
```

Set `DATABASE_URL` in the shell or copy the database URL from your existing backend `.env` into the environment. Do not commit credentials. For PowerShell:

```powershell
$env:DATABASE_URL = "your-existing-neon-postgres-url"
$env:LUVIA_CHAT_EVENT_TABLE = "your_actual_event_table"
$env:LUVIA_CHAT_WARNING_TABLE = "your_actual_imd_warning_table"
```

## 3. Register the router (one minimal existing-file change)

In the existing FastAPI app entrypoint (the file where `app = FastAPI(...)` is created), add:

```python
from Chatbot.backend.router import router as chatbot_router
app.include_router(chatbot_router)
```

Run the backend exactly as you currently do. Check:

- `GET http://127.0.0.1:8000/api/chatbot/health`
- `POST http://127.0.0.1:8000/api/chatbot/chat` with JSON `{"message":"What's the current weather in Delhi?","session_id":"demo"}`
- API docs: `http://127.0.0.1:8000/docs`

If your backend runs with the repository root as working directory, the import above works. If it runs with a different Python path, start it from the LUVIA root or add the root to `PYTHONPATH`.

## 4. Frontend integration

Copy `Chatbot/frontend/Chatbot.jsx` and `chatbot.css` into the React app source (or import them from their current location if your Vite configuration permits). Add it to a page/route:

```jsx
import Chatbot from "../../Chatbot/frontend/Chatbot";
// render <Chatbot /> inside the existing LUVIA page shell
```

If the frontend and backend are served from different origins, set `VITE_LUVIA_CHATBOT_API` to the full backend endpoint and add the frontend origin to the existing FastAPI CORS configuration. Prefer reusing LUVIA's existing CORS setup.

## 5. Test

```powershell
python -m pip install pytest
python -m pytest Chatbot/tests -q
```

## How it works

1. `router.py` exposes a small validated chat API.
2. `intent.py` identifies common request types and a known location/category.
3. `assistant.py` routes the question to a service.
4. `data_sources.py` is the only place that talks to external weather APIs or the LUVIA database. Database access is read-only and uses SQLAlchemy inspection plus a bounded `SELECT * ... LIMIT` against a discovered/configured table; it does not accept user SQL.
5. `knowledge.py` answers basic weather definitions and safety questions with general guidance.
6. If event or warning records cannot be retrieved, the assistant uses the configured Groq model for a general answer and explicitly avoids claiming access to live/database data.
7. The React component displays responses, retrieved records, source labels and timestamps.

## Current capabilities and limits

- Current weather and a short forecast: Open-Meteo geocoding + forecast API.
- Events: reads records from a recognized/configured LUVIA event table; filters retrieved rows by text match.
- Warnings: reads records from a recognized/configured warning table. If it cannot check the source, it explicitly says warning status cannot be confirmed.
- FAQ/safety: small curated knowledge base; database failures can fall back to Groq when `GROQ_API_KEY` is configured.
- Context: lightweight per-process session memory for the most recent location/category.
- Analytics: currently retrieves matching event rows; it does not yet implement trustworthy grouped SQL aggregates or cross-region comparisons.
- Historical data: only available when it is represented in the configured event table. A separate historical dataset adapter should be added for CSV/Parquet/ERA5 files.
- IMD: this package does not independently call an IMD endpoint; it reads persisted LUVIA warning records. It must not be treated as a live IMD alert source unless LUVIA's warning ingestion is current and healthy.
- Event details and navigation: raw matching records are shown; linking to the exact LUVIA event detail route requires mapping your frontend route and event primary key.
- Conversational intent is keyword-based, not an LLM. It is explainable, but it will not understand every phrasing.

## Extending with a new source

Add a small retrieval function in `data_sources.py` (or a separate module within this folder), return a consistent dictionary with `records`, `source`, `checked_at`, and optional `error`, then route the relevant intent in `assistant.py`. Keep source-specific queries out of the React component.

## Security

- No LLM key or third-party AI framework is required.
- Database access is read-only in this package.
- No arbitrary SQL is accepted from chat input.
- Keep database credentials in environment variables and do not expose them to Vite/client-side code.
