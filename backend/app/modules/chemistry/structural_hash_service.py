import hashlib
import json


class StructuralHashService:
    @staticmethod
    def create_hash(payload: dict) -> str:
        normalized = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


