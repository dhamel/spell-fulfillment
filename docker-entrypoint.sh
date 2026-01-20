#!/bin/bash
set -e

echo "=== Spell Fulfillment Application Starting ==="

# Wait for database to be ready
echo "Waiting for database..."
max_retries=30
counter=0
until python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os

async def check_db():
    engine = create_async_engine(os.environ.get('DATABASE_URL'))
    async with engine.connect() as conn:
        await conn.execute('SELECT 1')
    await engine.dispose()

asyncio.run(check_db())
" 2>/dev/null; do
    counter=$((counter + 1))
    if [ $counter -ge $max_retries ]; then
        echo "Error: Database not available after $max_retries attempts"
        exit 1
    fi
    echo "Database not ready, retrying in 2 seconds... ($counter/$max_retries)"
    sleep 2
done
echo "Database is ready!"

# Run migrations
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations complete!"
fi

# Create admin user if specified
if [ -n "$ADMIN_USERNAME" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "Checking admin user..."
    python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.models.operator import Operator
from app.core.security import get_password_hash
from sqlalchemy import select
import os

async def ensure_admin():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Operator).where(Operator.username == os.environ['ADMIN_USERNAME'])
        )
        if not result.scalar_one_or_none():
            admin = Operator(
                username=os.environ['ADMIN_USERNAME'],
                password_hash=get_password_hash(os.environ['ADMIN_PASSWORD']),
                is_active=True
            )
            db.add(admin)
            await db.commit()
            print(f'Admin user created: {os.environ[\"ADMIN_USERNAME\"]}')
        else:
            print('Admin user already exists')

asyncio.run(ensure_admin())
"
fi

echo "Starting application..."
exec "$@"
