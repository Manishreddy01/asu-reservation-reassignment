from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationReadResponse, NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="List notifications",
    description="Returns notifications for a user, newest first. Filter by user_id.",
)
def list_notifications(
    user_id: int | None = Query(None, description="Filter by user ID"),
    unread_only: bool = Query(False, description="Return only unread notifications"),
    db: Session = Depends(get_db),
) -> list[Notification]:
    q = db.query(Notification)
    if user_id is not None:
        q = q.filter(Notification.user_id == user_id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    return q.order_by(Notification.created_at.desc()).all()


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationReadResponse,
    summary="Mark notification as read",
)
def mark_as_read(notification_id: int, db: Session = Depends(get_db)) -> NotificationReadResponse:
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notification_id} not found.",
        )

    notification.is_read = True
    db.commit()
    return NotificationReadResponse(id=notification.id, is_read=True)
