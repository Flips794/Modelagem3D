from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.modules.molecules.schemas import MoleculeCreate, MoleculeResponse
from app.modules.molecules.service import MoleculeService
from app.core.guards import require_db_writes


router = APIRouter(prefix="/molecules", tags=["Molecules"])


@router.post("", response_model=MoleculeResponse, dependencies=[Depends(require_db_writes)])
def create_molecule(payload: MoleculeCreate, db: Session = Depends(get_db)):
    service = MoleculeService(db)
    return service.create_molecule(payload)


@router.get("", response_model=list[MoleculeResponse])
def list_molecules(db: Session = Depends(get_db)):
    service = MoleculeService(db)
    return service.list_molecules()


@router.get("/{molecule_id}", response_model=MoleculeResponse)
def get_molecule(molecule_id: UUID, db: Session = Depends(get_db)):
    service = MoleculeService(db)

    try:
        return service.get_molecule(molecule_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

