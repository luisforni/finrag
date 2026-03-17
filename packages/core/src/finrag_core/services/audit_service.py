import uuid
from datetime import datetime, timezone
from enum import Enum

from finrag_core.core.logging import get_logger

logger = get_logger(__name__)


class AuditAction(str, Enum):
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_QUERY = "document.query"
    USER_LOGIN = "user.login"
    USER_REGISTER = "user.register"


class AuditService:
    def log(
        self,
        action: AuditAction,
        user_id: uuid.UUID,
        resource_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> None:
        logger.info(
            "audit_event",
            action=action.value,
            user_id=str(user_id),
            resource_id=str(resource_id) if resource_id else None,
            timestamp=datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        )
