"""
API Dependencies

Re-exports common dependencies from core modules for API routes.
"""

from app.core.auth import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_role,
)
from app.core.database import get_db


# Re-export admin dependency
get_current_admin_user = require_admin

__all__ = [
    "get_current_user",
    "get_current_user_optional", 
    "get_current_admin_user",
    "require_admin",
    "require_role",
    "get_db",
]
