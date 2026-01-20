# Spell Fulfillment

Automated Etsy order fulfillment system for a digital spell shop. Fetches orders from Etsy, generates personalized AI spell responses using Claude, and delivers via email after manual review.

## Features

- **Etsy Integration**: OAuth 2.0 PKCE flow, automatic order fetching, rate limiting
- **AI Spell Generation**: Claude-powered personalized spell content with versioning
- **Review Dashboard**: Approve, edit, and regenerate spells before delivery
- **Email Fulfillment**: SendGrid integration for automated spell delivery
- **Task Management**: Track follow-ups and custom tasks
- **Metrics Dashboard**: Order counts, satisfaction ratings, API usage tracking

## Quick Start (Local Development)

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

## Docker Development

Run the full stack with Docker Compose:

```bash
# Start all services (db + app with hot reload)
docker-compose up

# Or run in background
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

## Production Deployment

### Using Docker Compose (Recommended)

1. **Create production environment file:**
   ```bash
   cp .env.example .env.prod
   ```

2. **Configure production values in `.env.prod`:**
   ```bash
   # Generate a secure secret key
   python -c "import secrets; print(secrets.token_urlsafe(32))"

   # Required settings:
   SECRET_KEY=<generated-secret>
   POSTGRES_PASSWORD=<secure-database-password>
   ENVIRONMENT=production
   DEBUG=false

   # API keys
   ETSY_API_KEY=<your-key>
   ETSY_API_SECRET=<your-secret>
   ETSY_REDIRECT_URI=https://yourdomain.com/api/v1/etsy/auth/callback
   ANTHROPIC_API_KEY=<your-key>
   SENDGRID_API_KEY=<your-key>
   FROM_EMAIL=spells@yourdomain.com

   # Optional: Auto-create admin user
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=<secure-password>
   ```

3. **Deploy with production compose file:**
   ```bash
   docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d
   ```

4. **With Nginx reverse proxy (optional):**
   ```bash
   # Create nginx config directory
   mkdir -p nginx
   # Add your nginx.conf and SSL certificates

   # Start with nginx profile
   docker-compose -f docker-compose.prod.yml --env-file .env.prod --profile with-nginx up -d
   ```

### Manual Deployment

1. **Build the production image:**
   ```bash
   docker build --target production -t spell-fulfillment:latest .
   ```

2. **Run with environment variables:**
   ```bash
   docker run -d \
     --name spell-fulfillment \
     -p 8000:8000 \
     -e DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/spells \
     -e SECRET_KEY=your-secret-key \
     -e ENVIRONMENT=production \
     -v uploads:/app/uploads \
     spell-fulfillment:latest
   ```

### Database Migrations

Migrations run automatically on container startup. To disable:
```bash
RUN_MIGRATIONS=false
```

To run manually:
```bash
docker-compose exec app alembic upgrade head
```

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (generate a random string) |
| `DATABASE_URL` | PostgreSQL connection string |
| `ETSY_API_KEY` | From Etsy Developer Portal |
| `ETSY_API_SECRET` | From Etsy Developer Portal |
| `ANTHROPIC_API_KEY` | Claude API key |
| `SENDGRID_API_KEY` | For email delivery |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | `development`, `production`, or `testing` |
| `DEBUG` | `true` | Enable debug mode |
| `ETSY_REDIRECT_URI` | `http://localhost:8000/...` | OAuth callback URL |
| `ETSY_POLL_INTERVAL_MINUTES` | `5` | Order polling frequency |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `FROM_EMAIL` | `spells@example.com` | Sender email address |
| `FROM_NAME` | `Mystic Spells` | Sender display name |
| `APP_PORT` | `8000` | Port to expose (Docker) |

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL
- **AI:** Anthropic Claude API
- **Frontend:** Jinja2 templates + HTMX + TailwindCSS (CDN)
- **Auth:** JWT tokens with bcrypt password hashing
- **Background Jobs:** APScheduler
- **Email:** SendGrid API
- **Containerization:** Docker with multi-stage builds

## Project Structure

```
spell-fulfillment/
├── app/
│   ├── api/           # API endpoints
│   ├── core/          # Security utilities
│   ├── db/            # Database session
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   │   ├── etsy/      # Etsy integration
│   │   ├── claude/    # AI spell generation
│   │   └── fulfillment/ # Email delivery
│   └── workers/       # Background jobs
├── frontend/
│   └── templates/     # Jinja2 HTML templates
├── migrations/        # Alembic migrations
├── scripts/           # Utility scripts
├── docker-compose.yml       # Development setup
├── docker-compose.prod.yml  # Production setup
└── Dockerfile         # Multi-stage Docker build
```

## API Documentation

Once running, access the interactive API docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

Private
