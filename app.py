"""
Aura AI - Intelligent FAQ Support Assistant
===========================================

Pipeline:
    user question
      -> NLTK preprocessing (lowercase, tokenize, strip punctuation,
         remove stopwords but keep "not", stem)
      -> TF-IDF vector (scikit-learn)
      -> cosine similarity against every FAQ question
      -> best match above a threshold, otherwise a fallback answer

Run with:  python app.py   ->   http://127.0.0.1:5000
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import nltk
from flask import Flask, jsonify, render_template, request
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from faq_data import FAQ_DATA, FALLBACK_ANSWER

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
SIMILARITY_THRESHOLD = 0.30   # below this score we answer with the fallback
MAX_MESSAGE_LENGTH = 500      # reject absurdly long input
KEEP_WORDS = {"not"}          # stopwords we deliberately keep ("not" flips meaning)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("aura-ai")

# --------------------------------------------------------------------------- #
# NLTK resources
# --------------------------------------------------------------------------- #
def _tokenizer_available() -> bool:
    try:
        word_tokenize("resource check")
        return True
    except LookupError:
        return False


def ensure_nltk_resources() -> None:
    """Make sure the NLTK data we need exists; download it if it does not.

    Raises a RuntimeError with exact fix commands if it still cannot be found
    (for example when the machine is offline).
    """
    missing = []

    if not _tokenizer_available():
        # Newer NLTK uses "punkt_tab", older versions use "punkt". Try both.
        for package in ("punkt_tab", "punkt"):
            nltk.download(package, quiet=True)
        if not _tokenizer_available():
            missing.append("punkt_tab")

    try:
        stopwords.words("english")
    except LookupError:
        nltk.download("stopwords", quiet=True)
        try:
            stopwords.words("english")
        except LookupError:
            missing.append("stopwords")

    if missing:
        raise RuntimeError(
            "Missing NLTK resources: "
            + ", ".join(missing)
            + ". Install them with:\n"
            + "  python -m nltk.downloader punkt_tab punkt stopwords"
        )


ensure_nltk_resources()

STOP_WORDS = set(stopwords.words("english")) - KEEP_WORDS
STEMMER = PorterStemmer()


# --------------------------------------------------------------------------- #
# Text preprocessing
# --------------------------------------------------------------------------- #
def _expand_contractions(text: str) -> str:
    """Turn "doesn't" into "does not" so negation survives tokenization."""
    text = text.replace("\u2019", "'")  # curly apostrophe -> straight
    text = re.sub(r"\bcan't\b", "can not", text)
    text = re.sub(r"\bwon't\b", "will not", text)
    return re.sub(r"n't\b", " not", text)


def preprocess(text: str) -> list[str]:
    """Convert raw text into a list of normalised tokens.

    Steps: lowercase -> expand contractions -> tokenize -> drop punctuation
    -> drop English stopwords (except "not") -> stem.
    """
    text = _expand_contractions(text.lower())
    tokens = word_tokenize(text)
    cleaned = []
    for token in tokens:
        if not token.isalnum():      # punctuation and symbols
            continue
        if token in STOP_WORDS:      # "not" is excluded from STOP_WORDS
            continue
        cleaned.append(STEMMER.stem(token))
    return cleaned


# --------------------------------------------------------------------------- #
# FAQ engine (TF-IDF + cosine similarity)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Match:
    answer: str
    score: float
    matched: bool


class FAQEngine:
    """Indexes every FAQ question once and finds the closest one for a query."""

    def __init__(self, faq_data: list[dict], threshold: float = SIMILARITY_THRESHOLD):
        self.threshold = threshold
        self.questions: list[str] = []
        self.answers: list[str] = []

        for entry in faq_data:
            for question in entry["questions"]:
                self.questions.append(question)
                self.answers.append(entry["answer"])

        if not self.questions:
            raise ValueError("FAQ_DATA does not contain any questions.")

        # analyzer=preprocess lets the vectorizer use our NLTK pipeline.
        self.vectorizer = TfidfVectorizer(analyzer=preprocess)
        self.question_matrix = self.vectorizer.fit_transform(self.questions)

    def ask(self, message: str) -> Match:
        if not preprocess(message):
            return Match(FALLBACK_ANSWER, 0.0, False)

        query_vector = self.vectorizer.transform([message])
        scores = cosine_similarity(query_vector, self.question_matrix).ravel()
        best_index = int(scores.argmax())
        best_score = float(scores[best_index])

        if best_score < self.threshold:
            return Match(FALLBACK_ANSWER, best_score, False)
        return Match(self.answers[best_index], best_score, True)


engine = FAQEngine(FAQ_DATA)


def get_answer(message: str) -> dict:
    """Return the public API payload for a question."""
    match = engine.ask(message)
    return {"answer": match.answer, "score": round(match.score, 2)}


# --------------------------------------------------------------------------- #
# Flask app  (static folder is intentionally called "statics")
# --------------------------------------------------------------------------- #
app = Flask(
    __name__,
    static_folder="statics",
    static_url_path="/statics",
    template_folder="templates",
)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Request body must be valid JSON."), 400

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify(error="Please type a question first."), 400

    message = message.strip()
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify(
            error=f"Please keep your question under {MAX_MESSAGE_LENGTH} characters."
        ), 400

    try:
        return jsonify(get_answer(message))
    except Exception:  # noqa: BLE001 - never leak internals to the client
        logger.exception("Failed to answer message")
        return jsonify(error="Something went wrong on our side. Please try again."), 500


@app.errorhandler(404)
def not_found(error):
    if request.path.startswith("/api/"):
        return jsonify(error="Endpoint not found."), 404
    return error


@app.errorhandler(405)
def method_not_allowed(error):
    if request.path.startswith("/api/"):
        return jsonify(error="Method not allowed."), 405
    return error


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
    )
