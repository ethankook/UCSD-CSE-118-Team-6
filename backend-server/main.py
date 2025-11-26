from random import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
import uvicorn
from typing import List, Dict, Optional
import json
import os
import deepl
import asyncio
from dotenv import load_dotenv
load_dotenv()

print("DEEPL_API_KEY loaded:", bool(os.environ.get("DEEPL_API_KEY")))


# handles client connections and their preferred languages
class ClientConnection:
    def __init__(self, websocket: WebSocket, preferred_lang: str = "en"):
        self.websocket = websocket
        self.preferred_lang = preferred_lang


# manages multiple client connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[ClientConnection] = []
        self.lang_groups: Dict[str, List[ClientConnection]] = {}

        # Create DeepL translator ONCE (not per message)
        api_key = os.environ.get("DEEPL_API_KEY")
        self.translator = deepl.Translator(api_key) if api_key else None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        client = ClientConnection(websocket=websocket, preferred_lang="en")
        self.active_connections.append(client)
        self.add_to_lang_group(client, client.preferred_lang)
        print("Client connected. Total:", len(self.active_connections))

    def add_to_lang_group(self, client: ClientConnection, lang: str):
        self.lang_groups.setdefault(lang, []).append(client)

    def remove_from_lang_group(self, client: ClientConnection, lang: str):
        if lang not in self.lang_groups:
            return
        group = self.lang_groups[lang]
        if client in group:
            group.remove(client)
        if not group:
            del self.lang_groups[lang]

    def remove_from_all_lang_groups(self, client: ClientConnection):
        langs_to_delete: List[str] = []
        for lang, group in self.lang_groups.items():
            if client in group:
                group.remove(client)
                if not group:
                    langs_to_delete.append(lang)
        for lang in langs_to_delete:
            del self.lang_groups[lang]

    def find_client(self, websocket: WebSocket) -> Optional[ClientConnection]:
        for client in self.active_connections:
            if client.websocket is websocket:
                return client
        return None

    def disconnect(self, websocket: WebSocket):
        client = self.find_client(websocket)
        if client is not None:
            self.active_connections.remove(client)
            self.remove_from_all_lang_groups(client)
            print("Client disconnected. Total:", len(self.active_connections))

    async def update_client_lang(self, websocket: WebSocket, new_lang: str):
        client = self.find_client(websocket)
        if client and client.preferred_lang != new_lang:
            self.remove_from_all_lang_groups(client)
            client.preferred_lang = new_lang
            self.add_to_lang_group(client, new_lang)
            print(f"Client language updated to {new_lang}")

    def translate_message(self, message: str, target_lang: str, source_lang: str) -> str:
        """
        Translate using DeepL API Free.
        Reads key from env var DEEPL_API_KEY.
        """
        target_lang = target_lang.upper()
        source_lang = source_lang.upper()

        if target_lang == source_lang:
            return message

        if not self.translator:
            print("[DEEPL ERROR] Missing DEEPL_API_KEY")
            return f"[{target_lang} untranslated] {message}"

        try:
            result = self.translator.translate_text(
                message,
                source_lang=source_lang,
                target_lang=target_lang
            )
            return result.text
        except Exception as e:
            print(f"[DEEPL ERROR] {e}")
            return f"[{target_lang} untranslated] {message}"

    async def send_personal_message(self, message: str, websocket: WebSocket):
        client = self.find_client(websocket)
        if client:
            await client.websocket.send_text(message)

    async def broadcast_raw(self, message: str):
        for client in self.active_connections:
            await client.websocket.send_text(message)

    async def broadcast(self, message: str, source_lang: str):
        """
        Translate once per language group and send to each client in that group.
        """
        for target_lang, clients in self.lang_groups.items():
            # optional: avoid blocking event loop too long
            translated_message = await asyncio.to_thread(
                self.translate_message, message, target_lang, source_lang
            )
            for client in clients:
                await client.websocket.send_text(translated_message)


manager = ConnectionManager()
app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            msg_type = data.get("type")

            if msg_type == "set_lang":
                new_lang = data.get("lang", "en")
                await manager.update_client_lang(websocket, new_lang)
                await manager.send_personal_message(f"Language set to {new_lang}", websocket)

            elif msg_type == "chat":
                text = data.get("text", "")
                await manager.send_personal_message(f"You said: {text}", websocket)
                await manager.broadcast_raw(f"[CHAT] {text}")

            else:
                await manager.send_personal_message("Unknown message type", websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/subtitle")
async def subtitle(
    text: str = Body(..., embed=True),
    source_lang: str = Body("en", embed=True)
):
    await manager.broadcast(text, source_lang=source_lang)
    return {"status": "ok", "original": text, "source_lang": source_lang}


@app.get("/")
async def root():
    return {"message": "server running"}

async def send_heartbeat():
    """
    Periodically sends a heartbeat message to all clients.
    """
    while True:
        try:
            # Wait for 1 second
            await asyncio.sleep(1)
            
            # Construct a JSON message
            heartbeat_msg = json.dumps({
                "type": "heartbeat",
                "text": f"Server active, {random.randint(1000,9999)}",
                "time": str(asyncio.get_event_loop().time())
            })
            
            # Use your existing broadcast_raw method to avoid DeepL translation costs
            if manager.active_connections:
                await manager.broadcast_raw(heartbeat_msg)
                
        except Exception as e:
            print(f"Heartbeat error: {e}")
            await asyncio.sleep(5) # Wait longer if error occurs

# 2. Register the task on startup
@app.on_event("startup")
async def startup_event():
    # This runs the function in the background without blocking the server
    asyncio.create_task(send_heartbeat())


if __name__ == "__main__":
   uvicorn.run(app="main:app", host="0.0.0.0", port=6543, reload=True)
   