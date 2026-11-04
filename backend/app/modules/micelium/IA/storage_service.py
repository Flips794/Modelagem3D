from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.micelium.IA.feature_builder import descriptor_snapshot_json
from app.modules.micelium.IA.schemas import (
    MiceliumAIEnvironment,
    MiceliumAIPredictionResponse,
    MolecularIdentityResult,
)
from app.modules.micelium.IA.storage_models import (
    AIPredictionORM,
    EnvironmentConditionORM,
    MiceliumMoleculeORM,
    MoleculeDescriptorSnapshotORM,
)


class MiceliumAIStorageService:
    """
    Camada de persistência opcional.
    """

    descriptor_version = "molecular_identity_ai_v0.2.0"

    def save_prediction(
        self,
        db: Session,
        response: MiceliumAIPredictionResponse,
    ) -> MiceliumAIPredictionResponse:
        molecule = self.upsert_molecule(db, response.molecule)
        environment = self.create_environment(db, response.environment)
        snapshot = self.create_descriptor_snapshot(
            db,
            response.molecule,
            response.environment,
            molecule_id=molecule.id,
        )

        prediction_id = str(uuid.uuid4())

        prediction = AIPredictionORM(
            id=prediction_id,
            molecule_id=molecule.id,
            descriptor_snapshot_id=snapshot.id,
            environment_id=environment.id,
            model_id=None,
            ai_route=response.prediction.ai_route,
            predicted_cmc_mmol_l=response.prediction.predicted_cmc_mmol_l,
            predicted_log_cmc=response.prediction.predicted_log_cmc,
            predicted_hlb=response.prediction.predicted_hlb,
            predicted_effective_hlb=response.prediction.predicted_effective_hlb,
            predicted_micelle_probability=response.prediction.micelle_probability,
            predicted_aggregation_number=response.prediction.predicted_aggregation_number,
            predicted_radius_nm=response.prediction.predicted_radius_nm,
            predicted_zeta_mv=response.prediction.predicted_zeta_mv,
            confidence_score=response.confidence.overall,
            prediction_json=response.model_dump(),
        )

        db.add(prediction)
        db.commit()

        response.saved = True
        response.database_ids = {
            "molecule_id": molecule.id,
            "environment_id": environment.id,
            "descriptor_snapshot_id": snapshot.id,
            "prediction_id": prediction_id,
        }

        return response

    def upsert_molecule(
        self,
        db: Session,
        identity: MolecularIdentityResult,
    ) -> MiceliumMoleculeORM:
        existing = (
            db.query(MiceliumMoleculeORM)
            .filter(MiceliumMoleculeORM.structural_hash == identity.structural_hash)
            .first()
        )

        descriptors = identity.descriptors

        if existing:
            existing.name = identity.name or existing.name
            existing.cas = identity.cas or existing.cas
            existing.canonical_smiles = identity.canonical_smiles
            existing.canonical_smiles_full = descriptors.canonical_smiles_full
            existing.active_component_smiles = descriptors.active_component_smiles
            existing.counterion_component_smiles = descriptors.counterion_component_smiles
            existing.inchikey = identity.inchikey
            existing.formula = descriptors.formula
            existing.molar_mass = descriptors.molar_mass
            existing.exact_mass = descriptors.exact_mass
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing

        molecule = MiceliumMoleculeORM(
            id=identity.molecule_id,
            name=identity.name,
            cas=identity.cas,
            canonical_smiles=identity.canonical_smiles,
            canonical_smiles_full=descriptors.canonical_smiles_full,
            active_component_smiles=descriptors.active_component_smiles,
            counterion_component_smiles=descriptors.counterion_component_smiles,
            inchi=descriptors.inchi,
            inchikey=identity.inchikey,
            structural_hash=identity.structural_hash,
            formula=descriptors.formula,
            molar_mass=descriptors.molar_mass,
            exact_mass=descriptors.exact_mass,
        )

        db.add(molecule)
        db.commit()
        db.refresh(molecule)
        return molecule

    def create_environment(
        self,
        db: Session,
        environment: MiceliumAIEnvironment,
    ) -> EnvironmentConditionORM:
        env = EnvironmentConditionORM(
            id=str(uuid.uuid4()),
            temperature_k=environment.temperature_k,
            pressure_atm=environment.pressure_atm,
            ph=environment.ph,
            ionic_strength_mol_l=environment.ionic_strength_mol_l,
            solvent=environment.solvent,
            solvent_polarity_index=environment.solvent_polarity_index,
            dielectric_constant=environment.dielectric_constant,
            salt_type=environment.salt_type,
            salt_concentration_mol_l=environment.salt_concentration_mol_l,
            surfactant_concentration_mmol_l=environment.surfactant_concentration_mmol_l,
            volume_ml=environment.volume_ml,
        )

        db.add(env)
        db.commit()
        db.refresh(env)
        return env

    def create_descriptor_snapshot(
        self,
        db: Session,
        identity: MolecularIdentityResult,
        environment: MiceliumAIEnvironment,
        *,
        molecule_id: str,
    ) -> MoleculeDescriptorSnapshotORM:
        descriptors = identity.descriptors

        snapshot = MoleculeDescriptorSnapshotORM(
            id=str(uuid.uuid4()),
            molecule_id=molecule_id,
            descriptor_version=self.descriptor_version,
            rdkit_version=identity.provenance.get("rdkit_version"),
            package_json=descriptor_snapshot_json(identity, environment),
            molar_mass=descriptors.molar_mass,
            logp=descriptors.logp,
            tpsa=descriptors.tpsa,
            hbd=descriptors.hbd,
            hba=descriptors.hba,
            rotatable_bonds=descriptors.rotatable_bonds,
            formal_charge=descriptors.formal_charge,
            active_component_formal_charge=descriptors.active_component_formal_charge,
            tail_carbon_count=descriptors.tail_carbon_count,
            head_group=descriptors.head_group,
            counterion=descriptors.counterion,
            surfactant_class=identity.surfactant_class,
            class_confidence=identity.class_confidence,
        )

        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot


