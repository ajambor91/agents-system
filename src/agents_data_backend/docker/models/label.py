from dataclasses import dataclass
import datetime

@dataclass
class Label:
    app_name: str
    service_name: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    hashkey: str

    def to_dict(self) -> dict [str, str]:
        return {
            'app_name': self.app_name,
            'service_name': self.service_name,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'hashkey': self.hashkey
        }



