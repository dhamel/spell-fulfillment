# Spell Fulfillment - Architecture Reference

Quick reference for what each file handles in the application.

---

## Core Application (`app/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI entry point. Initializes app, mounts routers, starts background scheduler, configures middleware. |
| `config.py` | Environment configuration via Pydantic Settings. Loads from `.env` (database, API keys, JWT settings). |
| `core/security.py` | Password hashing (bcrypt) and JWT token creation/verification. |
| `db/session.py` | Async SQLAlchemy engine and session configuration for PostgreSQL. |
| `api/deps.py` | Shared dependencies: `get_db()` for database sessions, `get_current_user()` for JWT authentication. |

---

## API Endpoints (`app/api/v1/`)

| File | Purpose |
|------|---------|
| `router.py` | Aggregates all sub-routers into the main API router. |
| `auth.py` | Login/logout endpoints. Returns JWT token, sets secure cookie. |
| `orders.py` | Order CRUD, spell generation trigger, Etsy sync, manual order intake. |
| `spells.py` | Spell versioning, approval, delivery (email sending), satisfaction ratings, email preview. |
| `spell_types.py` | Spell category management with Jinja2 prompt templates and stock PDF uploads. |
| `etsy.py` | Etsy OAuth 2.0 flow (authorization URL, callback, token refresh), connection status. |
| `tasks.py` | Task and task type management for operator workflow. |
| `metrics.py` | Dashboard analytics: order counts, satisfaction ratings, API status. |
| `health.py` | Simple health check endpoint (`/api/v1/health`). |
| `dev.py` | Development-only: test order creation and deletion (not loaded in production). |

### Dashboard Routes (`app/api/`)

| File | Purpose |
|------|---------|
| `dashboard.py` | Serves Jinja2 HTML pages (login, dashboard, orders, tasks, metrics, settings). |

---

## Database Models (`app/models/`)

| File | Purpose |
|------|---------|
| `base.py` | Base model class with timestamp mixin (created_at, updated_at). |
| `order.py` | Etsy order entity. Enums: `OrderStatus`, `CastType`. Links to SpellType and Spell. |
| `spell.py` | AI-generated spell content with versioning, approval status, delivery tracking. |
| `spell_type.py` | Spell categories (Love, Prosperity, etc.) with Jinja2 prompt templates. |
| `operator.py` | Dashboard admin user account (username, password hash). |
| `satisfaction.py` | Customer satisfaction rating (1-5 stars) linked to delivered spells. |
| `task.py` | Task management: `TaskType` (categories) and `Task` (individual items). |
| `etsy_token.py` | OAuth 2.0 token storage (access token, refresh token, expiration). |

---

## Pydantic Schemas (`app/schemas/`)

| File | Purpose |
|------|---------|
| `order.py` | Order request/response schemas: `OrderDetail`, `ManualOrderCreate`, pagination. |
| `spell.py` | Spell schemas: `SpellDetail`, `SpellGenerateRequest`, `SatisfactionCreate`, `EmailPreview`. |
| `spell_type.py` | Spell type CRUD schemas with template and PDF status. |
| `task.py` | Task and task type request/response schemas. |
| `auth.py` | JWT token response schema. |
| `metrics.py` | Dashboard and analytics response schemas. |
| `test_order.py` | Test order creation schemas (single and bulk). |

---

## Business Logic Services (`app/services/`)

### Claude AI Integration (`app/services/claude/`)

| File | Purpose |
|------|---------|
| `client.py` | Async Claude API wrapper with retry logic and token tracking. |
| `generator.py` | Core spell generation: renders Jinja2 templates, calls Claude, creates spell versions. |
| `prompts.py` | System prompts and default prompt templates for each spell type and cast type. |

### Etsy Integration (`app/services/etsy/`)

| File | Purpose |
|------|---------|
| `oauth.py` | OAuth 2.0 PKCE flow: authorization URL, code exchange, token refresh, revocation. |
| `client.py` | Low-level HTTP client for Etsy API with authentication headers. |
| `orders.py` | Order sync service: fetches receipts from Etsy, parses to Order model, deduplicates. |
| `rate_limiter.py` | Tracks and enforces Etsy API rate limits. |
| `scheduler.py` | APScheduler background job for periodic order syncing. |

### Email Delivery (`app/services/fulfillment/`)

| File | Purpose |
|------|---------|
| `email.py` | SendGrid email sending. Three email types: cast-by-us, customer-cast, combination. Includes HTML/plain text templates and preview generation. |
| `__init__.py` | Exports email functions and classes for use by API endpoints. |

### Test Data (`app/services/`)

| File | Purpose |
|------|---------|
| `test_orders.py` | Test order creation with simulated Etsy data (99* receipt IDs). |

---

## Frontend Templates (`frontend/templates/`)

| File | Purpose |
|------|---------|
| `base.html` | Base layout with navigation, styles, and HTMX scripts. |
| `login.html` | Operator login form. |
| `dashboard.html` | Main dashboard: metrics overview, manual order entry, test order creation. |
| `orders.html` | Orders list with status/type/date filters and pagination. |
| `order_detail.html` | Single order view: spell content, generation, approval, delivery, satisfaction, email preview. |
| `tasks.html` | Task management: create, filter, complete, delete tasks. |
| `metrics.html` | Analytics dashboard with charts and period selection. |
| `settings.html` | Spell type management, Etsy connection, token status. |

---

## Database Migrations (`migrations/`)

| File | Purpose |
|------|---------|
| `env.py` | Alembic configuration for async SQLAlchemy. |
| `versions/` | Migration scripts for schema changes. |

---

## Scripts (`scripts/`)

| File | Purpose |
|------|---------|
| `create_admin.py` | Creates initial admin user for dashboard access. |
| `seed_spell_types.py` | Seeds default spell types (Love, Prosperity, Protection, Healing). |
| `fix_spell_type_templates.py` | Migrates legacy `{var}` placeholders to Jinja2 `{{ var }}` syntax. |

---

## Configuration Files (Root)

| File | Purpose |
|------|---------|
| `.env` | Environment variables (database URL, API keys). Not committed. |
| `pyproject.toml` | Python package configuration and dependencies. |
| `docker-compose.yml` | Docker services: app, PostgreSQL database. |
| `Dockerfile` | Multi-stage build for production deployment. |
| `alembic.ini` | Alembic migration tool configuration. |
| `CLAUDE.md` | Project context and instructions for Claude Code. |
| `DEVELOPMENT_PLAN.md` | Phased development plan and progress tracking. |
