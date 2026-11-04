from __future__ import annotations

from pydantic import BaseModel, Field


class SimulationBoxCenter(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class SimulationBox3D(BaseModel):
    x: float = Field(..., gt=0)
    y: float = Field(..., gt=0)
    z: float = Field(..., gt=0)
    center: SimulationBoxCenter = Field(default_factory=SimulationBoxCenter)


class SimulationAtom3D(BaseModel):
    index: int
    element: str
    moleculeId: str
    moleculeName: str | None = None
    residueName: str | None = None
    isSolvent: bool = False
    radius: float | None = None
    color: str | None = None
    charge: float | None = None
    hybridization: str | None = None
    mass: float | None = None


class SimulationBond3D(BaseModel):
    index: int
    atomAIndex: int
    atomBIndex: int
    order: float = 1.0
    moleculeId: str
    drawAcrossPbc: bool = False


class SimulationTopology3D(BaseModel):
    id: str
    title: str
    box: SimulationBox3D
    atoms: list[SimulationAtom3D]
    bonds: list[SimulationBond3D]
    moleculeCount: int
    createdAt: str


class SimulationFrame3D(BaseModel):
    frameIndex: int
    timePs: float
    coordinates: list[tuple[float, float, float]]
    box: SimulationBox3D | None = None
    hiddenBonds: list[int] = Field(default_factory=list)


class SimulationStartMessage(BaseModel):
    type: str = "start"
    topology: SimulationTopology3D
    frame: SimulationFrame3D
    stepsPerFrame: int = Field(default=100, ge=1, le=5000)
    targetHz: int = Field(default=20, ge=1, le=60)
    temperatureK: float = Field(default=298.15, gt=0)
    frictionPerPs: float = Field(default=1.0, gt=0)
    timestepFs: float = Field(default=2.0, gt=0)
    minimize: bool = True
    minimizeMaxIterations: int = Field(default=250, ge=0, le=5000)
    geodesicPaddingNm: float = Field(default=0.45, ge=0.0, le=10.0)


