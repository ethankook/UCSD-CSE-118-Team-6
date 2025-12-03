# main.py
import asyncio
import json
import os
import random

import uvicorn
from dotenv import load_dotenv
from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect

from connection_manager import ConnectionManager
from models import (
    ErrorPayload,
    HeartbeatPayload,
    MessageType,
    SetLangPayload,
    SubtitleBroadcastRequest,
    SubtitleOneRequest,
)

# Load environment before creating manager (for DeepL key)
load_dotenv()
print("DEEPL_API_KEY loaded:", bool(os.environ.get("DEEPL_API_KEY")))

app = FastAPI()
manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Clients:
      - Normal: ws://host:8000/ws
      - Pi:     ws://host:8000/ws?role=pi
    """
    role = websocket.query_params.get("role")
    is_pi = role == "pi"

    await manager.connect(websocket, is_pi=is_pi)

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            raw_type = data.get("type")

            # Convert to enum (or fall back to error)
            try:
                msg_type = MessageType(raw_type)
            except ValueError:
                error = ErrorPayload(
                    text="Unknown message type",
                    time=str(asyncio.get_event_loop().time()),
                )
                await websocket.send_text(
                    json.dumps(error.model_dump(), ensure_ascii=False)
                )
                continue

            if msg_type == MessageType.SET_LANG:
                new_lang = data.get("lang", "en")
                await manager.update_client_lang(websocket, new_lang)

                client = manager.get_client_by_ws(websocket)
                client_id = client.client_id if client else None

                payload = SetLangPayload(
                    text=f"Language set to {new_lang}",
                    lang=new_lang,
                    client_id=client_id,
                    time=str(asyncio.get_event_loop().time()),
                )
                await websocket.send_text(
                    json.dumps(payload.model_dump(), ensure_ascii=False)
                )

            elif msg_type == MessageType.CHAT:
                text = data.get("text", "")
                await manager.broadcast_chat_from_ws(websocket, text)

            elif msg_type == MessageType.PERSONAL_CHAT:
                text = data.get("text", "")
                from_client_id = data.get("from_client_id")
                to_client_id = data.get("to_client_id")

                await manager.send_personal_message_by_id(
                    original_text=text,
                    translated_text=text,
                    source_client_id=from_client_id,
                    target_client_id=to_client_id,
                    source_lang=None,
                    target_lang=None,
                )

            else:
                # Any WS-only message types you haven't implemented
                error = ErrorPayload(
                    text=f"Unsupported WebSocket type: {raw_type}",
                    time=str(asyncio.get_event_loop().time()),
                )
                await websocket.send_text(
                    json.dumps(error.model_dump(), ensure_ascii=False)
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/subtitle")
async def subtitle_broadcast(req: SubtitleBroadcastRequest):
    """
    Broadcast a subtitle line to all clients, translating per language group.
    """
    await manager.broadcast_translated(
        text=req.text,
        source_lang=req.source_lang,
        source_client_id=req.source_client_id,
    )
    return {
        "status": "ok",
        "mode": "broadcast",
        "original": req.text,
        "source_lang": req.source_lang,
        "source_client_id": req.source_client_id,
    }


@app.post("/subtitle_one")
async def subtitle_one(req: SubtitleOneRequest):
    """
    True 1-to-1 subtitle between two clients.
    """
    translated = manager.translate_text(req.text, req.target_lang, req.source_lang)

    await manager.send_personal_message_by_id(
        original_text=req.text,
        translated_text=translated,
        source_client_id=req.from_client_id,
        target_client_id=req.to_client_id,
        source_lang=req.source_lang,
        target_lang=req.target_lang,
    )

    return {
        "status": "ok",
        "mode": "one_to_one",
        "from_client_id": req.from_client_id,
        "to_client_id": req.to_client_id,
        "original": req.text,
        "translated": translated,
        "source_lang": req.source_lang,
        "target_lang": req.target_lang,
    }


@app.get("/debug/lang-groups")
async def debug_lang_groups():
    return {
        "lang_groups": {
            lang: len(clients)
            for lang, clients in manager.lang_groups.items()
        },
        "pi_client_id": manager.pi_client_id,
        "active_clients": len(manager.active_connections),
    }


@app.get("/")
async def root():
    return {"message": "server running"}


# -----------------------------
# Heartbeat
# -----------------------------
async def send_heartbeat():
    """
    Periodically sends a heartbeat message to all clients.
    """
    while True:
        try:
            await asyncio.sleep(1)
            payload = HeartbeatPayload(
                text=f"Server active, {random.randint(1000, 9999)}",
                time=str(asyncio.get_event_loop().time()),
            )
            if manager.active_connections:
                await manager.broadcast_raw(
                    json.dumps(payload.model_dump(), ensure_ascii=False)
                )
        except Exception as e:
            print(f"Heartbeat error: {e}")
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(send_heartbeat())


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000, reload=True)
 