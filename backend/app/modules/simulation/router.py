from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.modules.simulation.geodesic_pack import (
    repack_topology_frame_concentrically,
)
from app.modules.simulation.openmm_runner import (
    OpenMMRealtimeRunner,
    RunnerSettings,
)
from app.modules.simulation.schemas import SimulationStartMessage

router = APIRouter(prefix="/simulation", tags=["Simulation"])

_executor = ThreadPoolExecutor(max_workers=2)


@router.websocket("/stream")
async def simulation_stream(websocket: WebSocket):
    """
    WebSocket final:
    ws://127.0.0.1:8000/api/v1/simulation/stream

    Protocolo:
    1. Cliente conecta.
    2. Cliente envia mensagem start com topology/frame inicial.
    3. Backend reempacota as moléculas por geometria geodésica concêntrica.
    4. Backend cria runner OpenMM.
    5. Backend envia topology geodésica.
    6. Backend envia frames contínuos.
    """
    await websocket.accept()

    try:
        raw_start_message = await websocket.receive_json()
        start_message = SimulationStartMessage.model_validate(raw_start_message)
    except ValidationError as exc:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Mensagem start inválida: {exc}",
            }
        )
        await websocket.close(code=1003)
        return
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Falha ao receber start: {exc}",
            }
        )
        await websocket.close(code=1011)
        return

    settings = RunnerSettings(
        temperature_k=start_message.temperatureK,
        friction_per_ps=start_message.frictionPerPs,
        timestep_fs=start_message.timestepFs,
        steps_per_frame=start_message.stepsPerFrame,
        minimize=start_message.minimize,
        minimize_max_iterations=start_message.minimizeMaxIterations,
    )

    loop = asyncio.get_running_loop()

    try:
        await websocket.send_json(
            {
                "type": "status",
                "message": "Reempacotando moléculas em camadas geodésicas...",
            }
        )

        packed_topology, packed_frame = await loop.run_in_executor(
            _executor,
            lambda: repack_topology_frame_concentrically(
                topology=start_message.topology,
                frame=start_message.frame,
                padding=start_message.geodesicPaddingNm,
            ),
        )

        await websocket.send_json(
            {
                "type": "status",
                "message": "Criando sistema OpenMM e minimizando energia inicial...",
            }
        )

        runner = await loop.run_in_executor(
            _executor,
            lambda: OpenMMRealtimeRunner(
                topology=packed_topology,
                initial_frame=packed_frame,
                settings=settings,
            ),
        )

        await websocket.send_json(runner.topology_message())

        target_hz = max(1, min(60, int(start_message.targetHz)))
        sleep_seconds = 1.0 / target_hz

        while True:
            frame_message = await loop.run_in_executor(_executor, runner.step)
            await websocket.send_json(frame_message)
            await asyncio.sleep(sleep_seconds)

    except WebSocketDisconnect:
        return
    except Exception as exc:
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(exc),
                }
            )
            await websocket.close(code=1011)
        except RuntimeError:
            return


