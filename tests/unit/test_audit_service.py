import uuid

from finrag_core.services.audit_service import AuditAction, AuditService


class TestAuditService:
    def test_log_does_not_raise(self):
        service = AuditService()
        service.log(
            action=AuditAction.DOCUMENT_UPLOAD,
            user_id=uuid.uuid4(),
            resource_id=uuid.uuid4(),
            metadata={"filename": "test.pdf"},
        )

    def test_log_without_optional_fields(self):
        AuditService().log(action=AuditAction.USER_LOGIN, user_id=uuid.uuid4())
