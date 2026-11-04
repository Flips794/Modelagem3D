def draw_molecule_svg(rdkit, molecule, width: int, height: int) -> str:
    try:
        prepared = rdkit.rdMolDraw2D.PrepareMolForDrawing(
            molecule,
            kekulize=True,
            addChiralHs=True,
            wedgeBonds=True,
        )
    except Exception:
        prepared = rdkit.rdMolDraw2D.PrepareMolForDrawing(
            molecule,
            kekulize=False,
            addChiralHs=True,
            wedgeBonds=True,
        )

    drawer = rdkit.rdMolDraw2D.MolDraw2DSVG(width, height)
    drawer.DrawMolecule(prepared)
    drawer.FinishDrawing()

    svg = drawer.GetDrawingText()
    return svg.replace("svg:", "")

