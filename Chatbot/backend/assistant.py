from .intent import parse_intent
from .data_sources import current_weather, get_events, get_warnings
from .knowledge import answer_faq, answer_with_llm

class LuviaAssistant:
    def __init__(self): self.sessions = {}
    def reply(self, message: str, session_id: str = "default"):
        previous = self.sessions.get(session_id, {})
        parsed = parse_intent(message, previous)
        if parsed.get("location") or parsed.get("category"):
            self.sessions[session_id] = {**previous, **{k:v for k,v in parsed.items() if v}}
        intent, location, category = parsed["intent"], parsed.get("location"), parsed.get("category")
        if intent in ("weather", "forecast"):
            if not location: return self._out("Which city or region should I check?", parsed)
            data = current_weather(location)
            if data.get("error"): return self._out(data["error"], parsed, data=data)
            current = data.get("current") or {}; daily = data.get("daily") or {}
            if intent == "forecast":
                days = daily.get("time", [])
                lines = [f"{days[i]}: {daily.get('temperature_2m_min',['?']*len(days))[i]}–{daily.get('temperature_2m_max',['?']*len(days))[i]} °C; max precipitation probability {daily.get('precipitation_probability_max',['?']*len(days))[i]}%" for i in range(min(3,len(days)))]
                text = f"Forecast for {data['location']} (Open-Meteo):\n" + "\n".join(lines)
            else:
                text = (f"Current weather in {data['location']}: {current.get('temperature_2m','?')} °C, feels like {current.get('apparent_temperature','?')} °C, humidity {current.get('relative_humidity_2m','?')}%, wind {current.get('wind_speed_10m','?')} km/h, precipitation {current.get('precipitation','?')} mm.")
            return self._out(text, parsed, data=data, sources=["Open-Meteo"])
        if intent == "warnings":
            result = get_warnings(location)
            if result.get("error"):
                text, used_llm = answer_with_llm(message)
                return self._out(text, parsed, data=result, sources=["Groq"] if used_llm else [])
            elif result["records"]: text = f"Found {len(result['records'])} matching warning record(s) in {result['source']}. Review their status, validity period and official bulletin before acting."
            else: text = f"No matching records were returned by {result['source']}. This only describes the records checked; confirm current advisories with IMD."
            return self._out(text, parsed, data=result, sources=[result.get("source", "LUVIA warnings")])
        if intent in ("events", "event_detail", "analytics"):
            result = get_events(location, category)
            if result.get("error"):
                text, used_llm = answer_with_llm(message)
                return self._out(text, parsed, data=result, sources=["Groq"] if used_llm else [])
            elif result["records"]: text = f"Retrieved {len(result['records'])} matching event record(s) from {result['source']}. The records below retain their stored verification and severity fields."
            else: text = f"No matching records were found in the retrieved sample from {result['source']}. This is not proof that no such events occurred."
            return self._out(text, parsed, data=result, sources=[result.get("source", "LUVIA database")])
        return self._out(answer_faq(message), parsed)
    def _out(self, answer, parsed, data=None, sources=None):
        return {"answer": answer, "intent": parsed.get("intent"), "location": parsed.get("location"), "category": parsed.get("category"), "data": data, "sources": sources or [], "disclaimer": "Weather and warning information can change. Follow official IMD and local-authority advisories."}
