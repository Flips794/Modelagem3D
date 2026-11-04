from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.modules.analysis_packages.schemas import AnalysisPackageCreate, AnalysisPackageResponse
from app.modules.analysis_packages.service import AnalysisPackageService


router = APIRouter(prefix="/analysis-packages", tags=["Analysis Packages"])


@router.post("", response_model=AnalysisPackageResponse)
def create_analysis_package(payload: AnalysisPackageCreate, db: Session = Depends(get_db)):
    service = AnalysisPackageService(db)
    return service.create_package(payload)


@router.get("/{package_id}", response_model=AnalysisPackageResponse)
def get_analysis_package(package_id: UUID, db: Session = Depends(get_db)):
    service = AnalysisPackageService(db)

    try:
        return service.get_package(package_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

