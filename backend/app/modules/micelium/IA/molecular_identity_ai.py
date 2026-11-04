from __future__ import annotations

import uuid

from app.modules.chemistry.parameters import validated_calculations as validated

from app.modules.micelium.mapping import max_consecutive_carbon_run

from app.modules.micelium.IA.headgroup_classifier import classify_cationic_headgroup
from app.modules.micelium.IA.chemistry_rules import (
    clamp,
    detect_counterion,
    detect_head_group,
    estimate_amphiphilicity,
    estimate_tail_count,
    estimate_tail_type,
    is_probable_commercial_mixture,
    normalize_smiles_text,
    route_for_class,
    split_active_and_counterion,
    split_salt_components,
    stable_hash,
)
from app.modules.micelium.IA.constants import AI_MODULE_VERSION
from app.modules.micelium.IA.schemas import (
    MolecularDescriptorSet,
    MolecularIdentityRequest,
    MolecularIdentityResult,
)


try:
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors
except Exception:  # pragma: no cover
    Chem = None
    Crippen = None
    Descriptors = None
    Lipinski = None
    rdMolDescriptors = None


class MolecularIdentityAI:
    """
    IA 1: identidade molecular + descritores + classificação inicial.

    A molécula completa e o componente ativo são separados quando o SMILES contém sal.
    Exemplo:
    SDS = dodecil sulfato ativo + Na+
    CTAB = cátion surfactante ativo + Br-
    """

    engine_name = "molecular_identity_ai"
    engine_version = AI_MODULE_VERSION

    def analyze(self, request: MolecularIdentityRequest) -> MolecularIdentityResult:
        smiles = normalize_smiles_text(request.smiles)

        if not smiles:
            raise ValueError("SMILES vazio ou inválido.")

        if Chem is None:
            raise RuntimeError("RDKit necessário para validar identidade molecular.")
        full_mol = Chem.MolFromSmiles(smiles)
        if full_mol is None:
            raise ValueError("SMILES inválido para identidade molecular.")
        structure = validated.profile(full_mol)
        active_component = Chem.MolToSmiles(structure.active, canonical=True)
        salt_components = [Chem.MolToSmiles(f, canonical=True) for f in structure.others]
        counterion_component = ".".join(salt_components) or None
        counterion_label = detect_counterion(smiles)

        descriptors = self._build_descriptors(
            smiles=smiles,
            active_component_smiles=active_component,
            counterion_component_smiles=counterion_component,
            salt_components=salt_components,
            name=request.name,
        )

        head_group = structure.head if structure.head != "none" else None
        surfactant_class = structure.surfactant_class
        head_confidence = 0.9
        cationic_head = classify_cationic_headgroup(active_component)
        descriptors.head_group = head_group
        descriptors.tail_type = "linear" if structure.linear_hydrocarbon else "complex_or_branched"
        descriptors.tail_carbon_count = structure.tail_c
        descriptors.tail_count = structure.tail_count
        descriptors.counterion = counterion_label
        descriptors.has_counterion = any(sum(a.GetFormalCharge() for a in f.GetAtoms()) != 0 for f in structure.others)
        descriptors.is_commercial_mixture = is_probable_commercial_mixture(request.name, smiles)
        if surfactant_class == "cationic":
            descriptors.head_area_a2 = cationic_head.head_area_a2
            descriptors.ammonium_subtype = cationic_head.ammonium_subtype
        descriptors.amphiphilicity_score = estimate_amphiphilicity(
            tail_carbon_count=structure.tail_c, head_group=head_group,
            logp=descriptors.logp, tpsa=descriptors.tpsa)
        descriptors.polarity_score = clamp((descriptors.tpsa or 0.0) / 130.0)
        descriptors.hydrophobicity_score = clamp(((descriptors.logp or 0.0) + 1.0) / 7.0)
        is_surfactant = structure.is_surfactant
        packing = validated.packing_estimate(structure)
        descriptors.head_area_a2 = packing["head_area_a2"]
        descriptors.raw_descriptors["packing_estimate"] = packing
        descriptors.raw_descriptors["shared_calculations"] = validated.VERSION

        class_confidence = self._estimate_class_confidence(
            is_surfactant=is_surfactant,
            head_confidence=head_confidence,
            descriptors=descriptors,
        )

        route_to = route_for_class(surfactant_class)
        molecule_id = str(uuid.uuid5(uuid.NAMESPACE_URL, descriptors.structural_hash))

        return MolecularIdentityResult(
            molecule_id=molecule_id,
            name=request.name,
            cas=request.cas,
            smiles=request.smiles,
            canonical_smiles=descriptors.canonical_smiles,
            inchikey=descriptors.inchikey,
            structural_hash=descriptors.structural_hash,
            is_surfactant=is_surfactant,
            surfactant_class=surfactant_class,
            class_confidence=class_confidence,
            route_to=route_to,
            descriptors=descriptors,
            provenance={
                "engine": self.engine_name,
                "engine_version": self.engine_version,
                "classification_scope": "input formal charge; no full pH speciation",
                "class_confidence_calibrated": False,
                "rdkit_available": Chem is not None,
                "input_unit": request.unit,
                "input_concentration": request.concentration,
                "ammonium_subtype": cationic_head.ammonium_subtype,
                "head_area_a2": cationic_head.head_area_a2,
                "klevens_a": cationic_head.klevens_a,
                "klevens_b": cationic_head.klevens_b,
                "headgroup_notes": cationic_head.notes,
            },
        )

    def _build_descriptors(
        self,
        *,
        smiles: str,
        active_component_smiles: str,
        counterion_component_smiles: str | None,
        salt_components: list[str],
        name: str | None,
    ) -> MolecularDescriptorSet:
        if Chem is None:
            return self._fallback_descriptors(
                smiles=smiles,
                active_component_smiles=active_component_smiles,
                counterion_component_smiles=counterion_component_smiles,
                salt_components=salt_components,
                name=name,
            )

        full_mol = Chem.MolFromSmiles(smiles)
        active_mol = Chem.MolFromSmiles(active_component_smiles)

        if full_mol is None:
            return self._fallback_descriptors(
                smiles=smiles,
                active_component_smiles=active_component_smiles,
                counterion_component_smiles=counterion_component_smiles,
                salt_components=salt_components,
                name=name,
            )

        if active_mol is None:
            active_mol = full_mol
            active_component_smiles = smiles

        canonical_full = Chem.MolToSmiles(full_mol, canonical=True)
        canonical_active = Chem.MolToSmiles(active_mol, canonical=True)
        isomeric = Chem.MolToSmiles(full_mol, canonical=True, isomericSmiles=True)

        inchi = None
        inchikey = None

        try:
            inchi = Chem.MolToInchi(full_mol)
            inchikey = Chem.MolToInchiKey(full_mol)
        except Exception:
            inchi = None
            inchikey = None

        formula = rdMolDescriptors.CalcMolFormula(full_mol) if rdMolDescriptors else None
        formal_charge = sum(atom.GetFormalCharge() for atom in full_mol.GetAtoms())
        active_formal_charge = sum(atom.GetFormalCharge() for atom in active_mol.GetAtoms())

        atom_count = full_mol.GetNumAtoms()
        heavy_atom_count = full_mol.GetNumHeavyAtoms()
        hetero_atom_count = sum(
            1
            for atom in active_mol.GetAtoms()
            if atom.GetAtomicNum() not in {1, 6}
        )

        structural_hash = stable_hash(
            canonical_full,
            canonical_active,
            inchikey,
            formal_charge,
            formula,
        )

        return MolecularDescriptorSet(
            canonical_smiles=canonical_active,
            canonical_smiles_full=canonical_full,
            active_component_smiles=canonical_active,
            counterion_component_smiles=counterion_component_smiles,
            salt_components=salt_components,
            isomeric_smiles=isomeric,
            inchi=inchi,
            inchikey=inchikey,
            structural_hash=structural_hash,
            formula=formula,
            molar_mass=float(Descriptors.MolWt(full_mol)) if Descriptors else None,
            exact_mass=float(Descriptors.ExactMolWt(full_mol)) if Descriptors else None,
            active_component_molar_mass=float(Descriptors.MolWt(active_mol)) if Descriptors else None,
            active_component_exact_mass=float(Descriptors.ExactMolWt(active_mol)) if Descriptors else None,
            atom_count=atom_count,
            heavy_atom_count=heavy_atom_count,
            hetero_atom_count=hetero_atom_count,
            formal_charge=formal_charge,
            active_component_formal_charge=active_formal_charge,
            hbd=int(Lipinski.NumHDonors(active_mol)) if Lipinski else None,
            hba=int(Lipinski.NumHAcceptors(active_mol)) if Lipinski else None,
            tpsa=float(rdMolDescriptors.CalcTPSA(active_mol)) if rdMolDescriptors else None,
            logp=float(Crippen.MolLogP(active_mol)) if Crippen else None,
            rotatable_bonds=int(Lipinski.NumRotatableBonds(active_mol)) if Lipinski else None,
            rings=int(rdMolDescriptors.CalcNumRings(active_mol)) if rdMolDescriptors else None,
            aromatic_rings=int(rdMolDescriptors.CalcNumAromaticRings(active_mol)) if rdMolDescriptors else None,
            fraction_csp3=float(rdMolDescriptors.CalcFractionCSP3(active_mol)) if rdMolDescriptors else None,
            raw_descriptors={
                "components": split_salt_components(smiles),
                "rdkit_sanitized": True,
                "active_component_used_for_descriptors": True,
            },
        )

    def _fallback_descriptors(
        self,
        *,
        smiles: str,
        active_component_smiles: str,
        counterion_component_smiles: str | None,
        salt_components: list[str],
        name: str | None,
    ) -> MolecularDescriptorSet:
        canonical = normalize_smiles_text(active_component_smiles or smiles)
        canonical_full = normalize_smiles_text(smiles)
        formal_charge = self._estimate_formal_charge_from_text(smiles)
        active_formal_charge = self._estimate_formal_charge_from_text(active_component_smiles)
        carbon_count = len([char for char in active_component_smiles if char == "C"])
        hetero_count = sum(active_component_smiles.count(token) for token in ["N", "O", "S", "P", "F", "Cl", "Br", "I"])
        structural_hash = stable_hash(canonical_full, canonical, formal_charge, name)

        return MolecularDescriptorSet(
            canonical_smiles=canonical,
            canonical_smiles_full=canonical_full,
            active_component_smiles=canonical,
            counterion_component_smiles=counterion_component_smiles,
            salt_components=salt_components,
            structural_hash=structural_hash,
            formal_charge=formal_charge,
            active_component_formal_charge=active_formal_charge,
            hetero_atom_count=hetero_count,
            raw_descriptors={
                "components": split_salt_components(smiles),
                "rdkit_sanitized": False,
                "estimated_carbon_count": carbon_count,
            },
        )

    def _estimate_formal_charge_from_text(self, smiles: str) -> int:
        positive = smiles.count("+")
        negative = smiles.count("-")
        return positive - negative

    def _estimate_class_confidence(
        self,
        *,
        is_surfactant: bool,
        head_confidence: float,
        descriptors: MolecularDescriptorSet,
    ) -> float:
        if not is_surfactant:
            return 0.2 if descriptors.head_group else 0.05

        tail_term = clamp(((descriptors.tail_carbon_count or 0) - 5) / 12.0)
        amph_term = descriptors.amphiphilicity_score
        counterion_term = 0.08 if descriptors.has_counterion else 0.0
        rdkit_term = 0.08 if descriptors.molar_mass else 0.0

        return clamp(0.30 * head_confidence + 0.28 * tail_term + 0.26 * amph_term + counterion_term + rdkit_term)
