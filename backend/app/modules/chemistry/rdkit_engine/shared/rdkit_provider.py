class RDKitProvider:
    """
    Centraliza os imports do RDKit.

    Assim as funções parse_2d, graph_to_smiles e futuras funções
    não precisam repetir imports do RDKit em vários arquivos.
    """

    def __init__(self):
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors, rdDepictor, rdMolDescriptors
            from rdkit.Chem.Draw import rdMolDraw2D
            from rdkit.Geometry import Point3D
        except ImportError as error:
            raise RuntimeError(
                "RDKit não está instalado neste ambiente. "
                "Instale com: python -m pip install rdkit"
            ) from error

        self.Chem = Chem
        self.Descriptors = Descriptors
        self.rdDepictor = rdDepictor
        self.rdMolDescriptors = rdMolDescriptors
        self.rdMolDraw2D = rdMolDraw2D
        self.Point3D = Point3D


