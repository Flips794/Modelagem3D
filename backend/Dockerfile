FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 libxrender1 libxext6 libexpat1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN python -c "from rdkit import Chem; from rdkit.Chem.Draw import rdMolDraw2D; import openmm; d = rdMolDraw2D.MolDraw2DSVG(200, 150); d.DrawMolecule(Chem.MolFromSmiles('CCO')); d.FinishDrawing(); assert '<svg' in d.GetDrawingText(); assert openmm.Platform.getNumPlatforms() > 0; print('RDKit SVG e OpenMM: OK')"
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
