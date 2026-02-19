# PR #1251: Add health check endpoint
from datetime import datetime, timezone
from typing import TypedDict

class HealthStatus(TypedDict):
    status: str
    timestamp: str
    version: str
    checks: dict[str, bool]

def check_health(db, cache, version: str = "1.0.0") -> HealthStatus:
    """Run all health checks and return status."""
    checks = {
        "database": _check_db(db),
        "cache": _check_cache(cache),
    }
    return {
        "status": "healthy" if all(checks.values()) else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "checks": checks,
    }

def _check_db(db) -> bool:
    try:
        db.execute("SELECT 1")
        return True
    except Exception:
        return False

def _check_cache(cache) -> bool:
    try:
        cache.ping()
        return True
    except Exception:
        return False
