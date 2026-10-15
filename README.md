# Aura AI — Intelligent FAQ Support Assistant

Aura AI is a web-based FAQ chatbot. A user types a question, and the backend finds the most relevant answer in an FAQ dataset using **NLP preprocessing, TF-IDF vectorization, and cosine similarity**. If nothing is similar enough, Aura replies with a polite fallback instead of guessing.

## Features

- Natural-language question matching (not exact keyword lookup)
- NLTK preprocessing: lowercase, tokenization, punctuation removal, stopword removal (keeps `not`), stemming
- TF-IDF + cosine similarity ranking with a configurable confidence threshold
- Fallback response for unknown or empty questions
- JSON API with input validation and safe error handling (no internals leaked)
- Glassmorphism pink/lavender UI with welcome screen, suggestion cards, typing indicator, error state, and responsive layout
- Enter to send, Shift+Enter for a new line, auto-resizing textarea, send button locked while waiting
- Automatic NLTK resource check with a clear error message
- Pytest suite covering matches, fallback, validation, preprocessing, and static files
- FAQ data kept in one file so it is easy to expand

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask |
| NLP | NLTK (tokenizer, stopwords, Porter stemmer) |
| Machine learning | scikit-learn (`TfidfVectorizer`, `cosine_similarity`) |
| Frontend | HTML, CSS, vanilla JavaScript |
| Testing | pytest |

## Project Structure

```text
Aura-AI-FAQ-Chatbot/
│
├── app.py              # Flask app + NLP engine + API
├── faq_data.py         # FAQ dataset and fallback message
├── requirements.txt
├── README.md
├── .gitignore
│
├── templates/
│   └── index.html      # Chat page (Jinja2 template)
│
├── statics/            # NOTE: intentionally "statics", not "static"
│   ├── style.css
│   ├── script.js
│   └── ai.png          # Aura AI avatar (replaceable)
│
└── tests/
    └── test_faq.py
```

Flask is configured with `static_folder="statics"` and `static_url_path="/statics"`, so files are served from `/statics/style.css`, `/statics/script.js`, and `/statics/ai.png`. The template uses `url_for('static', filename='...')`, which resolves to those URLs.

## Installation

```bash
# 1. Go into the project folder
cd Aura-AI-FAQ-Chatbot

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
#    Windows (PowerShell):
venv\Scripts\Activate.ps1
#    Windows (cmd):
venv\Scripts\activate.bat
#    macOS / Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

## NLTK Setup

The app downloads missing NLTK data automatically on first start. To install it manually (recommended on a fresh machine, or if you are offline later):

```bash
python -m nltk.downloader punkt_tab punkt stopwords
```

If the data cannot be found or downloaded, the app stops with a clear message listing the exact command to run.

## How to Run

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser. (Do not open `index.html` directly — it needs Flask to render.)

Run the tests:

```bash
pytest -v
```

## Example Questions

| You ask | Aura answers about |
|---|---|
| How can I reset my password? / I forgot my password | Password reset |
| Where is my package? / Track my order | Order tracking |
| What payment methods do you accept? | Payments |
| How long does delivery take? | Delivery time |
| Can I cancel my order? | Cancellation |
| Can I get a refund? / How do I get my money back? | Refunds |
| Do you offer exchanges? | Exchange policy |
| What is the capital of France? | Fallback (not in the FAQ) |

## API

`POST /api/chat`

Request:

```json
{ "message": "Where is my package?" }
```

Response:

```json
{
  "answer": "You can track your order from the 'My Orders' section of your account.",
  "score": 1.0
}
```

Errors return `{ "error": "..." }` with status `400` (bad input) or `500` (server problem).

## Architecture

```text
Browser (HTML/CSS/JS)
   │  POST /api/chat  {"message": "..."}
   ▼
Flask route  ──► validate input
   │
   ▼
preprocess()  (NLTK)
   lowercase → expand contractions → tokenize → drop punctuation
   → drop stopwords (keep "not") → stem
   │
   ▼
TfidfVectorizer.transform()  → query vector
   │
   ▼
cosine_similarity(query, every FAQ question vector)
   │
   ▼
best score ≥ 0.30 ?  ── yes ──► matched FAQ answer
                     └─ no ───► fallback message
   │
   ▼
JSON {"answer", "score"}  ──►  script.js renders the chat bubble
```

At startup, `FAQEngine` preprocesses every FAQ question once and builds the TF-IDF matrix. Each request only transforms the single user question and compares it to that matrix, so responses are fast.

## How TF-IDF Works

TF-IDF turns text into numbers so it can be compared. Each word gets a weight made of two parts:

- **Term Frequency (TF):** how often the word appears in a question.
- **Inverse Document Frequency (IDF):** how rare the word is across all FAQ questions. Words that appear everywhere (like "order") get a lower weight; distinctive words (like "refund" or "password") get a higher weight.

Multiplying them highlights the words that best identify a question. Every question becomes a vector with one weight per vocabulary word.

## How Cosine Similarity Works

Cosine similarity measures the **angle** between two vectors:

```
similarity = (A · B) / (‖A‖ × ‖B‖)
```

- `1.0` → same direction (same meaningful words)
- `0.0` → nothing in common

Because it compares direction rather than length, a short question and a longer one with the same meaning can still match well. Aura computes the similarity between the user's question and every FAQ question, takes the highest, and uses it only if it passes the threshold (`SIMILARITY_THRESHOLD = 0.30` in `app.py`).

## Design Decisions (good interview talking points)

- **Why keep `not`?** NLTK treats it as a stopword, but removing it would make "I can *not* log in" look like "I can log in". Contractions such as "can't" are expanded to keep the negation.
- **Why stemming?** It maps "exchanges", "exchanging", and "exchange" to one root so they match.
- **Why a threshold?** Without it the bot would always return *some* answer, even to unrelated questions. The threshold lets it admit it does not know.
- **Why one index per question phrasing?** Each alternate question is matched independently, which improves recall without any training.
- **Known limitation:** TF-IDF matches words, not meaning. "Can I swap my product?" only works if words overlap with the data. Synonyms must be added as extra FAQ phrasings (or handled with embeddings, see below).

## Expanding the FAQ

Open `faq_data.py` and add an entry:

```python
{
    "category": "Shipping Address",
    "answer": "You can change your address from Account > Addresses.",
    "questions": [
        "How do I change my shipping address?",
        "Can I update my delivery address?",
    ],
}
```

Restart the server. No other code changes are needed.

## Future Improvements

- Sentence embeddings (e.g. Sentence-Transformers) to understand synonyms
- Conversation memory and follow-up questions
- Admin dashboard to edit FAQs and view unanswered questions
- Logging of fallback questions to improve the dataset
- Multi-language support
- Persistent chat history and user accounts
- Deployment with Gunicorn and Docker

## Author

**Project:** Aura AI — Intelligent FAQ Support Assistant
**Author:** *Your Name* — *your.email@example.com*
**Purpose:** Internship project submission

> The bundled `statics/ai.png` is a simple generated placeholder. Replace it with your own artwork (any square PNG works; it is cropped into a circle by the UI).
