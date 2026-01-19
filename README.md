# Spell Fulfillment

Automated Etsy order fulfillment system for a digital spell shop. Fetches orders from Etsy, generates personalized AI spell responses using Claude, and delivers via email after manual review.

## Quick Start (Phase 1)

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- PostgreSQL (via Docker)

### Setup

1. **Clone and navigate to the project:**
   ```bash
   cd spell-fulfillment
   ```

2. **Copy the environment file and configure:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start PostgreSQL with Docker:**
   ```bash
   docker-compose up db -d
   ```

4. **Install dependencies:**
   ```bash
   pip install -e .
   ```

   > **Note:** If you see a bcrypt version warning, it's non-fatal. The bcrypt package is pinned to `<5.0.0` for passlib compatibility.

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Create admin user:**
   ```bash
   python scripts/create_admin.py
   ```
   You'll be prompted for username and password (min 8 characters).

7. **Run the app:**
   ```bash
   uvicorn app.main:app --reload
   ```

8. **Access the app:**
   Open http://localhost:8000 in your browser. You'll be redirected to the login page.

## Environment Variables

Required in `.env`:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (generate a random string) |
| `DATABASE_URL` | PostgreSQL connection string |
| `ETSY_API_KEY` | From Etsy Developer Portal |
| `ETSY_API_SECRET` | From Etsy Developer Portal |
| `ANTHROPIC_API_KEY` | Claude API key |
| `SENDGRID_API_KEY` | For email delivery |

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL
- **AI:** Anthropic Claude API
- **Frontend:** Jinja2 templates + HTMX + TailwindCSS
- **Auth:** JWT tokens with bcrypt password hashing
- **Email:** SendGrid API

## License

Private
