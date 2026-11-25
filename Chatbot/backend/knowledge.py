"""Small curated FAQ layer. Project-specific classification details are not guessed."""
import requests
from .config import GROQ_API_KEY, GROQ_MODEL, GROQ_API_URL, REQUEST_TIMEOUT

FAQ = {
 "heatwave": "A heatwave is a prolonged period of unusually high temperatures relative to the local climate. Follow official local advisories, hydrate, avoid peak afternoon heat, and check on vulnerable people.",
 "flood": "Flooding occurs when water inundates normally dry land. Move to higher ground, avoid walking or driving through floodwater, and follow official evacuation instructions.",
 "cyclone": "A tropical cyclone is an organized rotating storm system over warm tropical waters. Follow IMD bulletins, secure loose outdoor items, and evacuate if authorities instruct you to.",
 "safety": "For severe weather, prioritize official IMD and local-authority instructions. Keep alerts enabled, prepare essentials, avoid floodwater and exposed areas during lightning, and seek shelter when advised.",
 "verification": "LUVIA records may carry verification metadata and supporting evidence. The exact verification status and method should be read from the event record; this assistant does not independently certify events.",
 "severity": "LUVIA severity should be reported from the stored severity field or existing classification logic. If that field is unavailable, the chatbot will say so rather than inventing thresholds."
}
def answer_faq(message: str):
 q=message.lower()
 for key, answer in FAQ.items():
  if key in q or (key == "safety" and any(x in q for x in ("precaution", "safe", "protect"))): return answer
 if "how does luvia" in q or "classif" in q: return FAQ["severity"]
 if "verif" in q: return FAQ["verification"]
 return "I can help with current weather, forecasts, LUVIA events, IMD warnings, historical patterns, and weather safety. Ask about a location or event category to get started."

def answer_with_llm(message: str) -> tuple[str, bool]:
 if not GROQ_API_KEY:
  return "I couldn't retrieve the requested LUVIA records, and AI fallback is not configured. Set GROQ_API_KEY to enable generated answers.", False
 try:
  response = requests.post(
   GROQ_API_URL,
   headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
   json={
    "model": GROQ_MODEL,
    "messages": [
     {
      "role": "system",
      "content": (
       "You are LUVIA's weather assistant. LUVIA data could not be retrieved. "
       "Answer general questions helpfully, but do not claim access to current "
       "weather, active warnings, or database records. Be clear when live data "
       "is unavailable and direct users to official IMD advisories."
      ),
     },
     {"role": "user", "content": message},
    ],
   },
   timeout=REQUEST_TIMEOUT,
  )
  response.raise_for_status()
  answer = response.json()["choices"][0]["message"]["content"].strip()
  if not answer:
   raise ValueError("The LLM returned an empty answer.")
  return answer, True
 except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
  return f"I couldn't retrieve the LUVIA records or generate an answer ({type(exc).__name__}). Please try again later.", False
