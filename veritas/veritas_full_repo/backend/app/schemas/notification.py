from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: int
    kind: str
    title: str
    body: Optional[str] = None
    link_page: Optional[str] = None
    link_anchor: Optional[str] = None
    created_at: datetime
    read_at: Optional[datetime] = None
    is_read: bool


class NotificationListResponse(BaseModel):
    data: List[NotificationRead]
    unread_count: int
