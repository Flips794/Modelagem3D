from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.analysis_packages.models import AnalysisPackageModel
from app.modules.analysis_packages.schemas import AnalysisPackageCreate


class AnalysisPackageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: AnalysisPackageCreate, structural_hash: str) -> AnalysisPackageModel:
        analysis_package = AnalysisPackageModel(
            **payload.model_dump(),
            structural_hash=structural_hash,
        )

        self.db.add(analysis_package)
        self.db.commit()
        self.db.refresh(analysis_package)

        return analysis_package

    def get_by_id(self, package_id: UUID) -> AnalysisPackageModel | None:
        return self.db.get(AnalysisPackageModel, package_id)

