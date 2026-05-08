import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt

import auth
import collector

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/logs/{container_name:path}")
async def ws_logs(
    websocket: WebSocket,
    container_name: str,
    token: str = Query(...),
) -> None:
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        if not payload.get("sub"):
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    q = collector.subscribe(container_name)

    try:
        while True:
            try:
                entry = await asyncio.wait_for(q.get(), timeout=30)
                await websocket.send_text(json.dumps(entry))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WebSocket closed: %s", e)
    finally:
        collector.unsubscribe(container_name, q)
