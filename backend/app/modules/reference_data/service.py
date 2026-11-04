from __future__ import annotations

from app.modules.reference_data.repository import ReferenceDataRepository


class ReferenceDataService:
    def __init__(self, repository: ReferenceDataRepository | None = None):
        self.repository = repository or ReferenceDataRepository()

    def list_elements(self) -> dict:
        elements, source = self.repository.list_elements()

        return {
            "success": True,
            "source": source,
            "count": len(elements),
            "elements": elements,
            "items": elements,
        }

    def list_elements_raw(self) -> list[dict]:
        elements, _source = self.repository.list_elements()

        return elements


