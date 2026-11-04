from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.molecules.repository import MoleculeRepository
from app.modules.molecules.schemas import MoleculeCreate


class MoleculeService:
    def __init__(self, db: Session):
        self.repository = MoleculeRepository(db)

    def create_molecule(self, payload: MoleculeCreate):
        return self.repository.create(payload)

    def list_molecules(self):
        return self.repository.list_all()

    def get_molecule(self, molecule_id: UUID):
        molecule = self.repository.get_by_id(molecule_id)

        if molecule is None:
            raise NotFoundError("Molécula não encontrada.")

        return molecule

