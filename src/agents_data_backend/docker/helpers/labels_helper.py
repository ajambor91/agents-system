from models import Label
from datetime import datetime
import hashlib

class LabelsHelper:

    def __new__(cls):
        raise Exception("Static only class, cannot create")

    @staticmethod
    def create_label_from(
        *,
        app_name: str,
        service_name: str,
        created_at: datetime | str | None = None,
        updated_at: datetime | str | None = None
    ) -> Label:

        if not isinstance(created_at, datetime):
            created_at = (
                datetime.fromisoformat(created_at)
                if created_at else datetime.now()
            )

        if not isinstance(updated_at, datetime):
            updated_at = (
                datetime.fromisoformat(updated_at)
                if updated_at else datetime.now()
            )

        hashkey_str = (
            f"{app_name}:{service_name}:"
            f"{created_at.timestamp()}:{updated_at.timestamp()}"
        )

        hashkey = hashlib.sha256(
            hashkey_str.encode("utf-8")
        ).hexdigest()

        return Label(
            app_name=app_name,
            service_name=service_name,
            created_at=created_at,
            updated_at=updated_at,
            hashkey=hashkey
        )

    @staticmethod
    def compare_labels(source: Label, compare: Label) -> bool: