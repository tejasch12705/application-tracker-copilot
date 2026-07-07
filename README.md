# Application Tracker Copilot

A tool that solves a problem I was actively living through: tracking dozens of internship applications across scattered spreadsheets, losing track of deadlines, and spending 20+ minutes per application writing first-pass answers to take-home questions from scratch.

The tool parses job descriptions automatically, tracks each application through a pipeline, and drafts first-pass answers to application questions grounded in your actual resume via semantic retrieval — not generic LLM output.

## What it does

- Paste a job description and the tool extracts company, role, deadline, and key requirements using an LLM call
- Track each application through a status pipeline: Applied → OA/Take-home → Interview → Offer → Rejected
- When you hit a take-home question, paste it in — the tool retrieves the most relevant chunks of your resume using FAISS and drafts a first-pass answer grounded in what you've actually done
- The draft is a starting point, not a submission. The value is eliminating the blank-page problem, not replacing your judgment.

## Stack

- **Backend**: FastAPI, MongoDB (motor async driver)
- **LLM**: Groq API for JD parsing and answer generation
- **Retrieval**: FAISS + sentence-transformers (local, no extra API key)
- **Frontend**: Streamlit

## Why three features and not more

The MVP was intentionally scoped to JD parsing, pipeline tracking, and answer drafting. Everything else — deadline reminders, email integration, auto-apply — was cut. The scoping decision was a product call: ship something usable fast, use it on real applications, and only add features when real usage reveals a gap. That's still how this project works.

## Setup

Requires Python 3.11, MongoDB, and a Groq API key (free at console.groq.com).

```bash
git clone https://github.com/YOUR_USERNAME/application-tracker-copilot.git
cd application-tracker-copilot

python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in GROQ_API_KEY and MONGO_URI in .env
```

Add a plain-text copy of your resume to `data/resume.txt` — this is what the retrieval layer uses to ground answers.

## Running it

Two terminals:

```bash
# Terminal 1 — backend
source venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
source venv/bin/activate
cd frontend
streamlit run app.py
```

Frontend opens at `http://localhost:8501`. Backend API docs at `http://localhost:8000/docs`.

## Design decisions worth noting

The retrieval layer uses a local sentence-transformers model (`all-MiniLM-L6-v2`) rather than an API-based embedding model. This keeps the tool fully functional with one API key instead of two, and means embeddings are computed locally on your machine. The trade-off is slightly lower embedding quality versus a hosted model — acceptable for a single-document retrieval use case like this.

Rate limits on the free Groq tier are generous for personal use but will throttle if you parse many JDs in quick succession. Wait a few seconds between calls if that happens.
