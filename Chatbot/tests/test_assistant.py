from Chatbot.backend import assistant as assistant_module
from Chatbot.backend import knowledge


def test_event_database_failure_uses_llm_fallback(monkeypatch):
    monkeypatch.setattr(
        assistant_module,
        "get_events",
        lambda location, category: {
            "records": [],
            "source": "LUVIA database",
            "error": "Database is unavailable.",
        },
    )
    monkeypatch.setattr(
        assistant_module,
        "answer_with_llm",
        lambda message: ("General answer without live records.", True),
    )

    result = assistant_module.LuviaAssistant().reply("Show recent floods in India")

    assert result["answer"] == "General answer without live records."
    assert result["sources"] == ["Groq"]
    assert result["data"]["error"] == "Database is unavailable."


def test_warning_database_failure_uses_llm_fallback(monkeypatch):
    monkeypatch.setattr(
        assistant_module,
        "get_warnings",
        lambda location: {
            "records": [],
            "source": "LUVIA database",
            "error": "Database is unavailable.",
        },
    )
    monkeypatch.setattr(
        assistant_module,
        "answer_with_llm",
        lambda message: ("Check official advisories for current warnings.", True),
    )

    result = assistant_module.LuviaAssistant().reply("Any active warnings in Delhi?")

    assert result["answer"] == "Check official advisories for current warnings."
    assert result["sources"] == ["Groq"]


def test_llm_fallback_uses_groq_chat_completions(monkeypatch):
    request = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Generated answer."}}]}

    def fake_post(url, **kwargs):
        request["url"] = url
        request.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(knowledge, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(knowledge, "GROQ_MODEL", "test-model")
    monkeypatch.setattr(knowledge.requests, "post", fake_post)

    answer, used_llm = knowledge.answer_with_llm("Explain flood safety")

    assert answer == "Generated answer."
    assert used_llm
    assert request["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["json"]["model"] == "test-model"
    assert request["json"]["messages"][-1]["content"] == "Explain flood safety"
