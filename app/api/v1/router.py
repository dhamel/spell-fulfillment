"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1 import auth, health, metrics, orders, spells, spell_types, tasks

api_router = APIRouter()

# Health check
api_router.include_router(health.router, prefix="/health", tags=["health"])

# Authentication
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Orders
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])

# Spells
api_router.include_router(spells.router, prefix="/spells", tags=["spells"])

# Spell Types
api_router.include_router(spell_types.router, prefix="/spell-types", tags=["spell-types"])

# Tasks
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])

# Metrics
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
