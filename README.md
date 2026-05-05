# Kno-Tic

A web application for detecting phishing, smishing, and social engineering attempts. Given a text message, URL, or screenshot, it returns a risk score (0–100), a threat category, and a breakdown of the psychological tactics used. With explanations designed to educate the user, not just flag the threat.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS, Axios, jsPDF |
| Backend | Python 3.11, FastAPI, SQLite |
| AI (primary) | Google Gemini 3.1 Flash-Lite |
| AI (fallback) | Groq / LLaMA 3.3 70B |
| HTTP | httpx (async, for URL analysis) |

---

## Features

- **Text analysis** — paste any message (email, SMS, WhatsApp) and get a structured risk report
- **URL analysis** — follows redirect chains, fetches page HTML, and runs heuristics for blob phishing, URL shorteners, IP-based domains, and suspicious hash fragments
- **Image analysis** — upload a screenshot; Gemini Vision extracts and analyzes the content
- **Risk gauge** — visual 0–100 score with color scale (blue → amber → orange → red)
- **Psychological indicator breakdown** — identifies tactics such as urgency, authority, fear, and impersonation, with per-indicator learning explanations
- **PDF report export** — client-side, no server round-trip
- **Analysis history** — stored locally in SQLite; searchable and filterable by category
- **Statistics panel** — total analyses, threat percentage, top tactic, category breakdown
- **User feedback** — mark any analysis as correct or incorrect
- **AI provider fallback** — if Gemini fails, the request is retried transparently with Groq

---

## Requirements

- Python 3.11 or later
- Node.js 18 or later
- A [Google Gemini API key](https://aistudio.google.com/app/apikey) (free tier is sufficient)
- Optionally, a [Groq API key](https://console.groq.com/keys) for fallback support

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/DenReanin/kno-tic.git
cd kno-tic
```

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create the environment file:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env` and add your API keys:

```
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Frontend

```bash
cd ../frontend
npm install
```

---

## Running

Open two terminals from the project root.

**Terminal 1 — backend:**

```bash
cd backend
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS / Linux
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

The application will be available at `http://localhost:5173`.

---

## Project structure

```
kno-tic/
├── backend/
│   ├── analyzer.py        # AI provider calls, URL heuristics, image analysis
│   ├── db.py              # SQLite interface
│   ├── main.py            # FastAPI routes
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   └── components/
    │       ├── HistoryPanel.jsx
    │       ├── IndicatorList.jsx
    │       ├── MessageInput.jsx
    │       ├── RiskGauge.jsx
    │       └── StatsPanel.jsx
    ├── index.html
    └── vite.config.js
```

---

## Privacy

Analysis history is stored in a local SQLite database (`backend/kno_tic.db`) and never leaves the device. Message content is sent to the configured AI provider solely for analysis and is not persisted by this application.

---

## License

MIT
