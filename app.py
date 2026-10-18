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

# Use NLTK data bundled inside this project.
nltk.data.path.append(
    os.path.join(os.path.dirname(__file__), "nltk_data")
)

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

SIMILARITY_THRESHOLD = 0.30
MAX_MESSAGE_LENGTH = 500
KEEP_WORDS = {"not"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

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
    """Check that required NLTK resources are available."""

    if not _tokenizer_available():
        raise RuntimeError(
            "NLTK tokenizer resource is missing. "
            "Make sure nltk_data/punkt_tab exists."
        )

    try:
        stopwords.words("english")
    except LookupError:
        raise RuntimeError(
            "NLTK stopwords resource is missing. "
            "Make sure nltk_data/corpora/stopwords exists."
        )


ensure_nltk_resources()

STOP_WORDS = set(stopwords.words("english")) - KEEP_WORDS
STEMMER = PorterStemmer()


# --------------------------------------------------------------------------- #
# Text preprocessing
# --------------------------------------------------------------------------- #

def _expand_contractions(text: str) -> str:
    """Turn contractions into forms that preserve negation."""

    text = text.replace("\u2019", "'")
    text = re.sub(r"\bcan't\b", "can not", text)
    text = re.sub(r"\bwon't\b", "will not", text)

    return re.sub(r"n't\b", " not", text)


def preprocess(text: str) -> list[str]:
    """Convert raw text into a list of normalised tokens."""

    text = _expand_contractions(text.lower())

    tokens = word_tokenize(text)

    cleaned = []

    for token in tokens:

        if not token.isalnum():
            continue

        if token in STOP_WORDS:
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
    """Indexes every FAQ question once and finds the closest one."""

    def __init__(
        self,
        faq_data: list[dict],
        threshold: float = SIMILARITY_THRESHOLD
    ):

        self.threshold = threshold

        self.questions: list[str] = []
        self.answers: list[str] = []

        for entry in faq_data:

            for question in entry["questions"]:

                self.questions.append(question)
                self.answers.append(entry["answer"])

        if not self.questions:
            raise ValueError(
                "FAQ_DATA does not contain any questions."
            )

        self.vectorizer = TfidfVectorizer(
            analyzer=preprocess
        )

        self.question_matrix = self.vectorizer.fit_transform(
            self.questions
        )

    def ask(self, message: str) -> Match:

        if not preprocess(message):

            return Match(
                FALLBACK_ANSWER,
                0.0,
                False
            )

        query_vector = self.vectorizer.transform(
            [message]
        )

        scores = cosine_similarity(
            query_vector,
            self.question_matrix
        ).ravel()

        best_index = int(scores.argmax())

        best_score = float(
            scores[best_index]
        )

        if best_score < self.threshold:

            return Match(
                FALLBACK_ANSWER,
                best_score,
                False
            )

        return Match(
            self.answers[best_index],
            best_score,
            True
        )


engine = FAQEngine(FAQ_DATA)


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #

def get_answer(message: str) -> dict:

    match = engine.ask(message)

    return {
        "answer": match.answer,
        "score": round(match.score, 2)
    }


# --------------------------------------------------------------------------- #
# Flask app
# --------------------------------------------------------------------------- #

app = Flask(
    __name__,
    static_folder="statics",
    static_url_path="/statics",
    template_folder="templates",
)


@app.get("/")
def index():

    return render_template(
        "index.html"
    )


@app.post("/api/chat")
def chat():

    payload = request.get_json(
        silent=True
    )

    if not isinstance(payload, dict):

        return jsonify(
            error="Request body must be valid JSON."
        ), 400

    message = payload.get("message")

    if not isinstance(message, str) or not message.strip():

        return jsonify(
            error="Please type a question first."
        ), 400

    message = message.strip()

    if len(message) > MAX_MESSAGE_LENGTH:

        return jsonify(
            error=(
                f"Please keep your question under "
                f"{MAX_MESSAGE_LENGTH} characters."
            )
        ), 400

    try:

        return jsonify(
            get_answer(message)
        )

    except Exception:

        logger.exception(
            "Failed to answer message"
        )

        return jsonify(
            error=(
                "Something went wrong on our side. "
                "Please try again."
            )
        ), 500


# --------------------------------------------------------------------------- #
# Error handlers
# --------------------------------------------------------------------------- #

@app.errorhandler(404)
def not_found(error):

    if request.path.startswith("/api/"):

        return jsonify(
            error="Endpoint not found."
        ), 404

    return error


@app.errorhandler(405)
def method_not_allowed(error):

    if request.path.startswith("/api/"):

        return jsonify(
            error="Method not allowed."
        ), 405

    return error


# --------------------------------------------------------------------------- #
# Local development
# --------------------------------------------------------------------------- #

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=os.environ.get(
            "FLASK_DEBUG",
            "1"
        ) == "1",
    )