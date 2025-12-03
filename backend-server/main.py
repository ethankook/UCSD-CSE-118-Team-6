# main.py
import asyncio
import json
import os
import random

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from connection_manager import ConnectionManager
from models import (
    ErrorPayload,
    HeartbeatPayload,
    MessageType,
    SetLangPayload,
)

# ENV + APP SETUP

# Load environment variables (DEEPL_API_KEY, etc.)
load_dotenv()
print("DEEPL_API_KEY loaded:", bool(os.environ.get("DEEPL_API_KEY")))

app = FastAPI()
manager = ConnectionManager()


# WEBSOCKET ENDPOINT
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint.

    Clients connect here (no HTTP subtitles at all):

      - Normal client:
          ws://<host>:8000/ws

      - Pi client:
          ws://<host>:8000/ws?role=pi

    Message types (JSON):
      1) set_lang
         { "type": "set_lang", "lang": "en" }

      2) chat  (group chat, per-target translation)
         { "type": "chat", "text": "Hello everyone" }

      3) personal_chat (1-to-1 chat with translation)
         { "type": "personal_chat", "to_client_id": "<uuid>", "text": "Hi!" }
    """
    role = websocket.query_params.get("role")
    is_pi = role == "pi"

    # Register the WebSocket + send hello payload
    await manager.connect(websocket, is_pi=is_pi)

    try:
        while True:
            # 1) Receive raw WebSocket frame
            raw_data = await websocket.receive_text()

            # 2) Parse JSON
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                error = ErrorPayload(
                    text="Invalid JSON",
                    time=str(asyncio.get_event_loop().time()),
                )
                await websocket.send_text(
                    json.dumps(error.model_dump(), ensure_ascii=False)
                )
                continue

            # 3) Interpret message type
            raw_type = data.get("type")
            try:
                msg_type = MessageType(raw_type)
            except ValueError:
                error = ErrorPayload(
                    text=f"Unknown message type: {raw_type}",
                    time=str(asyncio.get_event_loop().time()),
                )
                await websocket.send_text(
                    json.dumps(error.model_dump(), ensure_ascii=False)
                )
                continue

            # 4) Handle each message type
            if msg_type == MessageType.SET_LANG:
                # Client wants to update its preferred language.
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
                # Group chat:
                text = data.get("text", "")
                await manager.broadcast_chat_from_ws(websocket, text)

            elif msg_type == MessageType.PERSONAL_CHAT:
                # 1-to-1 chat:
                text = data.get("text", "")
                to_client_id = data.get("to_client_id")

                if not text or not to_client_id:
                    error = ErrorPayload(
                        text="Missing 'text' or 'to_client_id' for personal_chat",
                        time=str(asyncio.get_event_loop().time()),
                    )
                    await websocket.send_text(
                        json.dumps(error.model_dump(), ensure_ascii=False)
                    )
                    continue

                await manager.send_personal_message_from_ws(
                    websocket=websocket,
                    target_client_id=to_client_id,
                    text=text,
                )

            else:
                # HELLO, ERROR, HEARTBEAT are server-side only; ignore here.
                error = ErrorPayload(
                    text=f"Unsupported WebSocket type from client: {raw_type}",
                    time=str(asyncio.get_event_loop().time()),
                )
                await websocket.send_text(
                    json.dumps(error.model_dump(), ensure_ascii=False)
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# HEARTBEAT TASK 

async def send_heartbeat():
    """
    Periodically sends a heartbeat message to all clients over WebSocket.

    No HTTP endpoints are used at all. This is purely WS.
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
            print(f"[HEARTBEAT ERROR] {e}")
            await asyncio.sleep(5)


# @app.on_event("startup")
# async def startup_event():
#     asyncio.create_task(send_heartbeat())


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="0.0.0.0", port=8000, reload=True)
