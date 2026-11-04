from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.molecules.models import MoleculeModel
from app.modules.molecules.schemas import MoleculeCreate


class MoleculeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: MoleculeCreate) -> MoleculeModel:
        molecule = MoleculeModel(**payload.model_dump())

        self.db.add(molecule)
        self.db.commit()
        self.db.refresh(molecule)

        return molecule

    def list_all(self) -> list[MoleculeModel]:
        statement = select(MoleculeModel).order_by(MoleculeModel.created_at.desc())
        return list(self.db.scalars(statement).all())

    def get_by_id(self, molecule_id: UUID) -> MoleculeModel | None:
        return self.db.get(MoleculeModel, molecule_id)


