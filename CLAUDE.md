# Spell Fulfillment - Project Context

## Overview
Automated Etsy order fulfillment system for a digital spell shop. Fetches orders from Etsy, generates personalized AI spell responses using Claude, and delivers via email after manual review.

## Tech Stack
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL
- **AI:** Anthropic Claude API for spell generation
- **Frontend:** Jinja2 templates + HTMX + TailwindCSS (CDN)
- **Auth:** JWT tokens with bcrypt password hashing
- **Background Jobs:** APScheduler
- **Email:** SendGrid API

## Project Structure
```
app/
├── main.py              # FastAPI entry point
├── config.py            # Pydantic settings (loads from .env)
├── api/
│   ├── deps.py          # Shared dependencies (get_db, get_current_user)
│   ├── dashboard.py     # HTML page routes
│   └── v1/              # API endpoints
├── core/security.py     # Password hashing, JWT creation
├── db/session.py        # Async SQLAlchemy session
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response schemas
├── services/            # Business logic
│   ├── etsy/            # OAuth, API client, order fetching
│   ├── claude/          # Spell generation
│   └── fulfillment/     # Email delivery
└── workers/             # Background job definitions

frontend/templates/      # Jinja2 HTML templates
migrations/              # Alembic database migrations
```

## Common Commands
```bash
# Install dependencies
pip install -e .

# Start PostgreSQL (Docker)
docker-compose up db -d

# Run database migrations
alembic upgrade head

# Create admin user
python scripts/create_admin.py

# Run development server
uvicorn app.main:app --reload

# Run with Docker
docker-compose up
```

## Environment Variables
Required in `.env`:
- `SECRET_KEY` - JWT signing key
- `DATABASE_URL` - PostgreSQL connection string
- `ETSY_API_KEY` / `ETSY_API_SECRET` - From Etsy Developer Portal
- `ANTHROPIC_API_KEY` - Claude API key
- `SENDGRID_API_KEY` - For email delivery

## Key Concepts

### Two-Stage Fulfillment
1. **Etsy auto-delivers** stock PDF when customer purchases
2. **App sends personalized follow-up** email with AI-generated spell after review

### Order Flow
`New Order → Generate Spell (Claude) → Review in Dashboard → Approve → Email Sent`

### Order Statuses
- `pending` - New order, awaiting spell generation
- `generating` - Claude is generating spell
- `review` - Spell ready for operator review
- `approved` - Spell approved, ready for delivery
- `delivered` - Email sent to customer
- `failed` - Error occurred

## Database
- Uses async SQLAlchemy with asyncpg driver
- Migrations managed by Alembic
- Models in `app/models/`, schemas in `app/schemas/`

## API Authentication
- POST `/api/v1/auth/login` returns JWT token
- Include `Authorization: Bearer <token>` header on API requests
- Dashboard uses localStorage to store token

## Known Issues
- **bcrypt version warning**: passlib shows "(trapped) error reading bcrypt version" - this is non-fatal and can be ignored. bcrypt is pinned to `<5.0.0` in pyproject.toml for compatibility.

## Testing
```bash
pytest
pytest --cov=app
```
