import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect

from db import AsyncSessionLocal
from features.execution.activity_format import evaluation_row_to_activity
from features.execution.broadcaster import CHANNEL, subscribe_activity_events
from features.execution.orchestrator import list_evaluations
from utils.logging import get_logger

logger = get_logger(__name__)


async def stream_execution_activity(websocket: WebSocket) -> None:
    await websocket.accept()
    async with AsyncSessionLocal() as session:
        history = await list_evaluations(session, limit=50)
    for row in reversed(history):
        await websocket.send_json(evaluation_row_to_activity(row))

    pubsub = await subscribe_activity_events()
    if pubsub is None:
        try:
            while True:
                await asyncio.sleep(30)
        except WebSocketDisconnect:
            return
        return

    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if not data:
                continue
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = {"raw": data}
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        logger.info("execution_ws_disconnect")
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.close()
