from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    notification_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationReadResponse(BaseModel):
    """Returned after marking a notification as read."""
    id: int
    is_read: bool
