"""Metrics schemas."""

from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    """Dashboard overview metrics."""

    orders: dict[str, int]
    tasks: dict[str, int]
    satisfaction: dict[str, float | int]
    api_status: dict[str, bool | int]


class OrderMetrics(BaseModel):
    """Order metrics by period."""

    period: str
    total: int
    by_status: dict[str, int]
    by_spell_type: dict[str, int]


class SatisfactionMetrics(BaseModel):
    """Satisfaction rating metrics."""

    average: float
    total: int
    distribution: dict[str, int]
