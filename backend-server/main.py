from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from typing import List, Dict, Optional
import json
import boto3


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

    async def connect(self, websocket: WebSocket):
        """
        Accept the WebSocket, create a new ClientConnection
        with default language 'en', and add it to active + lang group.
        """
        await websocket.accept()
        client = ClientConnection(websocket=websocket, preferred_lang="en")
        self.active_connections.append(client)
        self.add_to_lang_group(client, client.preferred_lang)
        print("Client connected. Total:", len(self.active_connections))

    def add_to_lang_group(self, client: ClientConnection, lang: str):
        """
        Add a client to the specified language group.
        """
        self.lang_groups.setdefault(lang, []).append(client)

    def remove_from_lang_group(self, client: ClientConnection, lang: str):
        """
        Remove a client from a specific language group, if present.
        Also delete the group key if it becomes empty.
        """
        if lang not in self.lang_groups:
            return

        group = self.lang_groups[lang]
        if client in group:
            group.remove(client)

        if not group:  # group is now empty
            del self.lang_groups[lang]

    def remove_from_all_lang_groups(self, client: ClientConnection):
        """
        Safely remove a client from ALL language groups.
        We collect langs to delete first so we don't modify
        the dict while iterating.
        """
        langs_to_delete: List[str] = []

        for lang, group in self.lang_groups.items():
            if client in group:
                group.remove(client)
                if not group:
                    langs_to_delete.append(lang)

        for lang in langs_to_delete:
            del self.lang_groups[lang]

    def find_client(self, websocket: WebSocket) -> Optional[ClientConnection]:
        """
        Find the ClientConnection for a given WebSocket, if it exists.
        """
        for client in self.active_connections:
            if client.websocket is websocket:
                return client
        return None

    def disconnect(self, websocket: WebSocket):
        """
        Called when a WebSocket disconnects.
        Remove the client from active connections and lang groups.
        """
        client = self.find_client(websocket)
        if client is not None:
            self.active_connections.remove(client)
            self.remove_from_all_lang_groups(client)
            print("Client disconnected. Total:", len(self.active_connections))

    async def update_client_lang(self, websocket: WebSocket, new_lang: str):
        """
        Change a client's preferred language and update lang_groups.
        """
        client = self.find_client(websocket)
        if client is not None:
            if client.preferred_lang != new_lang:
                # Remove from any previous groups (safe even if only in one)
                self.remove_from_all_lang_groups(client)
                client.preferred_lang = new_lang
                self.add_to_lang_group(client, client.preferred_lang)
                print(f"Client language updated to {new_lang}")

    def translate_message(self, message: str, target_lang: str, source_lang: str) -> str:
        """
        Use AWS Translate to translate the message from source_lang to target_lang.
        If source and target are the same, just return the original.
        """
        if target_lang == source_lang:
            return message

        translate_client = boto3.client("translate")

        response = translate_client.translate_text(
            Text=message,
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_lang,
        )

        return response["TranslatedText"]


    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Send a message to a single client (identified by websocket).
        """
        client = self.find_client(websocket)
        if client is not None:
            await client.websocket.send_text(message)

    async def broadcast_raw(self, message: str):
        """
        Send the same message to all active clients (no translation).
        """
        for client in self.active_connections:
            await client.websocket.send_text(message)

    async def broadcast(self, message: str, source_lang: str):
        """
        Send a message to all clients, translating per language group.
        """
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



@app.post("/subtitle")
async def subtitle(
    text: str = Body(..., embed=True),
    source_lang: str = Body("en", embed=True)
):
    """
    Test endpoint: simulate receiving a subtitle line from ASR.
    It broadcasts the text to all clients, translating per language group.
    """
    await manager.broadcast(text, source_lang=source_lang)
    return {"status": "ok", "original": text, "source_lang": source_lang}

@app.get("/")
async def root():
    return {"message": "server running"}
