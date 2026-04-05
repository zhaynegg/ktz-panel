"""WebSocket endpoint for real-time telemetry streaming (>= 1 Hz)."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.auth import get_current_user_from_websocket
from app.services.simulator import get_simulator_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["streaming"])


@router.websocket("/ws/telemetry")
async def telemetry_ws(ws: WebSocket) -> None:
    """
    Real-time telemetry stream.

    Client receives JSON frames and may send control commands:
      { "action": "set_state", "value": "CRUISING" }
      { "action": "trigger_anomaly", "value": "OVERHEAT" }
      { "action": "set_load", "value": "10" }
      { "action": "refuel_full", "value": "" }
    """
    try:
        get_current_user_from_websocket(ws)
    except Exception:
        await ws.close(code=1008)
        return

    await ws.accept()
    service = get_simulator_service()
    queue = service.subscribe()

    logger.info("WebSocket client connected")

    async def _send_loop() -> None:
        try:
            while True:
                frame = await queue.get()
                await ws.send_text(json.dumps(frame, default=str))
        except (WebSocketDisconnect, Exception):
            pass

    async def _recv_loop() -> None:
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                    action = msg.get("action", "")
                    value = msg.get("value", "")

                    if action == "set_state":
                        service.set_state(value)
                        logger.info("Client set state -> %s", value)
                    elif action == "trigger_anomaly":
                        service.trigger_anomaly(value)
                        logger.info("Client triggered anomaly -> %s", value)
                    elif action == "set_load":
                        service.set_load_multiplier(int(value))
                        logger.info("Client set load multiplier -> %s", value)
                    elif action == "refuel_full":
                        service.refuel_full()
                        logger.info("Client refueled locomotive to 100%%")
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    await ws.send_text(json.dumps({"error": str(e)}))
        except (WebSocketDisconnect, Exception):
            pass

    send_task = asyncio.create_task(_send_loop())
    recv_task = asyncio.create_task(_recv_loop())

    try:
        await asyncio.gather(send_task, recv_task)
    except Exception:
        pass
    finally:
        service.unsubscribe(queue)
        send_task.cancel()
        recv_task.cancel()
        logger.info("WebSocket client disconnected")
