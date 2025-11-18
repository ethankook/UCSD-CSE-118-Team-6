from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Optional

# handles client connections and their preferred languages
class ClientConnection:
    def __init__(self, websocket: WebSocket, preferred_lang: str = "en"):
        self.websocket = websocket
        self.preferred_lang = preferred_lang

# manages multiple client connections
class ConnectionManager:
    def __init__ (self):
        self.active_connections: List[ClientConnection] = []
        self.lang_groups: Dict[str, List[ClientConnection]] = {}


    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        client = ClientConnection(websocket=websocket, preferred_lang="en")
        self.active_connections.append(client)
        self.add_to_lang_group(client, client.preferred_lang)
        

    def add_to_lang_group(self, client: ClientConnection, lang: str):
        self.lang_groups.setdefault(lang, []).append(client)

    def remove_from_lang_group(self, client: ClientConnection, lang: str):
        group = self.lang_groups.get(lang, [])
        if client in group:
            group.remove(client)
        if group == []:
            del self.lang_groups[lang]

    def remove_from_all_lang_groups(self, client: ClientConnection):
        for lang, group in self.lang_groups.items():
            if client in group:
                self.remove_from_lang_group(client, lang)


    def find_client(self, websocket: WebSocket) -> Optional[ClientConnection]:
        for client in self.active_connections:
            if client.websocket is websocket:
                return client
        return None
    
    def disconnect(self, websocket: WebSocket):
        client = self.find_client(websocket)
        if client is not None:
            self.active_connections.remove(client)
            remove_from_all_lang_groups(client)


    async def update_client_lang(self, websocket: WebSocket, new_lang: str):
        client = self.find_client(websocket)
        if client is not None:
            if client.preferred_lang != new_lang:
                self.remove_from_all_lang_groups(client)
                client.preferred_lang = new_lang
                self.add_to_lang_group(client, client.preferred_lang)


    # dummy translation function
    def translate_message(self, message: str, target_lang: str, source_lang: str) -> str:
        if target_lang == source_lang:
            return message
        return f"[{target_lang}] {message}"

    async def send_personal_message(self, message: str, websocket: WebSocket):
        client = self.find_client(websocket)
        if client is not None:
            await client.websocket.send_text(message)

    async def broadcast_raw(self, message: str):
        for client in self.active_connections:
            await client.websocket.send_text(message)

    async def broadcast(self, message: str, source_lang: str):
        for target_lang, clients in self.lang_groups.items():
            translated_message = self.translate_message(message, target_lang, source_lang)
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


