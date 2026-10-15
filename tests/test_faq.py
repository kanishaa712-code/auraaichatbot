"""Tests for Aura AI. Run from the project root with:  pytest -v"""

import os
import sys

import pytest

# Make "import app" work when pytest is run from any directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, engine, get_answer, preprocess  # noqa: E402
from faq_data import FALLBACK_ANSWER  # noqa: E402


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def ask(client, message):
    return client.post("/api/chat", json={"message": message})


# ---------- successful matches ----------
@pytest.mark.parametrize(
    "question, expected_fragment",
    [
        ("How can I reset my password?", "Forgot Password"),
        ("I forgot my password", "Forgot Password"),
        ("Where is my package?", "My Orders"),
        ("How can I track my order?", "My Orders"),
        ("What payment methods do you accept?", "credit cards"),
        ("How can I pay?", "credit cards"),
        ("Can I get a refund?", "within 24 hours"),
        ("How do I get my money back?", "within 24 hours"),
        ("Do you offer exchanges?", "exchange policy"),
        ("How long does delivery take?", "3 to 5 business days"),
        ("Can I cancel my order?", "before it is shipped"),
    ],
)
def test_known_questions_return_correct_answer(client, question, expected_fragment):
    response = ask(client, question)
    assert response.status_code == 200
    data = response.get_json()
    assert expected_fragment in data["answer"]
    assert 0.3 <= data["score"] <= 1.0


# ---------- fallback ----------
@pytest.mark.parametrize(
    "question",
    ["What is the capital of France?", "Do you sell gift cards?", "???", "the a of"],
)
def test_unknown_questions_use_fallback(client, question):
    response = ask(client, question)
    assert response.status_code == 200
    assert response.get_json()["answer"] == FALLBACK_ANSWER


def test_engine_marks_unknown_as_unmatched():
    assert engine.ask("Tell me a joke about penguins").matched is False
    assert engine.ask("Where is my order?").matched is True


# ---------- response shape ----------
def test_response_only_exposes_answer_and_score(client):
    data = ask(client, "Can I get a refund?").get_json()
    assert set(data.keys()) == {"answer", "score"}


# ---------- validation / errors ----------
def test_empty_message_rejected(client):
    assert ask(client, "   ").status_code == 400


def test_missing_message_rejected(client):
    assert client.post("/api/chat", json={}).status_code == 400


def test_non_json_body_rejected(client):
    response = client.post("/api/chat", data="hello", content_type="text/plain")
    assert response.status_code == 400


def test_too_long_message_rejected(client):
    assert ask(client, "a" * 501).status_code == 400


def test_get_on_chat_endpoint_not_allowed(client):
    assert client.get("/api/chat").status_code == 405


# ---------- preprocessing ----------
def test_preprocess_lowercases_and_removes_punctuation_and_stopwords():
    assert preprocess("How can I RESET my password?!") == ["reset", "password"]


def test_preprocess_keeps_not():
    assert "not" in preprocess("I do not remember my password")
    assert "not" in preprocess("I can't log in")


def test_get_answer_shape():
    result = get_answer("Where is my package?")
    assert isinstance(result["answer"], str)
    assert isinstance(result["score"], float)


# ---------- routes and static files ----------
def test_index_page_loads_and_uses_statics_paths(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "/statics/style.css" in html
    assert "/statics/script.js" in html
    assert "/statics/ai.png" in html


@pytest.mark.parametrize("path", ["/statics/style.css", "/statics/script.js", "/statics/ai.png"])
def test_static_files_are_served(client, path):
    assert client.get(path).status_code == 200
