# PaceForge

AI-enhanced running plan generator for Garmin watches.

PaceForge analyses your Garmin Connect fitness data (VO2 max, HRV, training readiness, race predictions, recent activities) and generates personalised training plans for half marathons, marathons, and Hyrox events. Plans are pushed as structured workouts directly to your Garmin watch via Garmin Connect.

## Features

- **Garmin Connect integration** — reads fitness metrics, uploads structured workouts with pace/HR targets
- **VDOT pace calculator** — derives training zones (Easy, Marathon, Threshold, Interval, Repetition) from your race performance using the Daniels & Gilbert formula
- **Plan templates** — progressive-overload plans for Half Marathon (12 wk), Marathon (16 wk), and Hyrox (10 wk)
- **AI coaching** (Phase 3) — LLM-powered plan adaptation and conversational coaching
- **Streamlit dashboard** — visualise fitness profile, generate plans, push to Garmin in one click

## Quick Start

```bash
# Clone and install
git clone https://github.com/<you>/paceforge.git
cd paceforge
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your Garmin credentials

# Run the API server
uvicorn paceforge.api.app:app --reload

# Run the dashboard (separate terminal)
streamlit run src/paceforge/dashboard.py
```

## Configuration

Set via environment variables or `.env` file (prefix `PACEFORGE_`):

| Variable | Description |
|----------|-------------|
| `PACEFORGE_GARMIN_EMAIL` | Garmin Connect email |
| `PACEFORGE_GARMIN_PASSWORD` | Garmin Connect password |
| `PACEFORGE_OPENAI_API_KEY` | OpenAI API key (optional, for AI coach) |

## Running Tests

```bash
pytest tests/ -v
```

## Architecture

```
src/paceforge/
├── api/          # FastAPI backend
├── engine/       # VDOT calculator, plan generator, templates
├── garmin/       # Garmin Connect client wrapper
├── models/       # Pydantic data models
└── dashboard.py  # Streamlit frontend
```

## License

MIT
