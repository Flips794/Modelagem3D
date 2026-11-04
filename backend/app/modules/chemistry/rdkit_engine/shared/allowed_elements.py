ALLOWED_ELEMENT_SYMBOLS = {"P", "N", "O", "K"}


def validate_allowed_symbol(symbol: str) -> None:
    if symbol not in ALLOWED_ELEMENT_SYMBOLS:
        raise ValueError(
            f"Elemento não permitido nesta etapa: {symbol}. "
            "Permitidos: P, N, O, K."
        )


def validate_allowed_elements_in_molecule(molecule) -> None:
    for atom in molecule.GetAtoms():
        validate_allowed_symbol(atom.GetSymbol())

