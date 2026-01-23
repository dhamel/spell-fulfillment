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

---

## Development Status (Last Updated: January 2026)

### Completed Implementation Phases
All 7 phases from `DEVELOPMENT_PLAN.md` are complete:
1. **Core Foundation** - Auth, models, database
2. **Etsy Integration** - OAuth, order syncing
3. **AI Spell Generation** - Claude integration with Jinja2 templates
4. **Email Delivery** - SendGrid integration
5. **Dashboard & Review** - Full HTMX-powered UI
6. **Tasks & Metrics** - Task management, satisfaction ratings, metrics dashboard
7. **Deployment** - Docker multi-stage builds, production config

### Key Files Modified Recently
- `app/api/v1/orders.py` - Added manual order intake endpoint, test order filtering
- `app/api/v1/metrics.py` - Added test order filtering to all metrics endpoints
- `app/models/order.py` - Added `is_test_order` boolean field
- `app/schemas/order.py` - Added `ManualOrderCreate`, `ManualOrderResponse` schemas
- `app/services/test_orders.py` - Now sets `is_test_order=True` on test orders
- `frontend/templates/dashboard.html` - Added manual order intake form
- `frontend/templates/orders.html` - Added test order filter toggle, TEST badge
- `frontend/templates/metrics.html` - Added test order filter toggle
- `migrations/versions/002_add_is_test_order.py` - Migration for is_test_order field

### Important Technical Notes
- **Jinja2 Templates**: Spell type prompt templates use `{{ variable }}` syntax, NOT Python `{variable}`. The generator in `app/services/claude/generator.py` uses Jinja2's `Template` class.
- **Spell Type Validation**: Test orders validate against database spell types, not hardcoded list. See `validate_spell_type()` in `app/api/v1/dev.py`.
- **Satisfaction 404s**: GET `/api/v1/spells/{id}/satisfaction` returns 404 when no rating exists yet - this is expected and handled gracefully by the frontend.
- **Order Receipt ID Prefixes**:
  - `88*` - Manual orders (production, entered manually via dashboard)
  - `99*` - Test orders (development/testing only)
  - Other - Real Etsy orders (synced from Etsy API)
- **Test Order Filtering**: By default, test orders are excluded from orders list and all metrics. Use `include_test_orders=true` query param or UI toggle to include them.

### Manual Order Intake
For entering real Etsy orders manually before API approval:
1. Dashboard → "Enter Manual Order" button
2. Fill in customer details, spell type, price, order date from Etsy receipt
3. Order is created as a production order (not test) and included in metrics
4. Proceed with normal spell generation → review → delivery flow

### Scripts Reference
- `scripts/seed_spell_types.py` - Seeds default spell types (Love, Prosperity, Protection, Healing)
- `scripts/fix_spell_type_templates.py` - Fixes legacy `{var}` placeholders to `{{ var }}`
- `scripts/create_admin.py` - Creates admin user for dashboard access
