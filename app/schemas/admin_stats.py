# app/schemas/admin_stats.py

from pydantic import BaseModel


class AdminUserStats(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    suspended_users: int
    