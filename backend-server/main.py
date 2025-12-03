import random
import json
import os
import uuid
import asyncio
from typing import List, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
import uvicorn
import deepl
from dotenv import load_dotenv

load_dotenv()
print("DEEPL_API_KEY loaded:", bool(os.environ.get("DEEPL_API_KEY")))


# -----------------------------
# Data model for a client
# -----------------------------
class ClientConnection:
    def __init__(
        self,
        websocket: WebSocket,
        preferred_lang: str = "en",
        client_id: Optional[str] = None,
    ):
        self.websocket = websocket
        self.preferred_lang = preferred_lang
        self.client_id = client_id or str(uuid.uuid4())


# -----------------------------
# Connection manager
# -----------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[ClientConnection] = []
        self.lang_groups: Dict[str, List[ClientConnection]] = {}
        self.clients_by_id: Dict[str, ClientConnection] = {}

        api_key = os.environ.get("DEEPL_API_KEY")
        self.translator = deepl.Translator(api_key) if api_key else None

        # Track which client is the Raspberry Pi (one Pi per manager)
        self.pi_client_id: Optional[str] = None

    # --------- helper: find clients ---------

    def get_client_by_ws(self, websocket: WebSocket) -> Optional[ClientConnection]:
        for client in self.active_connections:
            if client.websocket is websocket:
                return client
        return None

    def get_client_by_id(self, client_id: str) -> Optional[ClientConnection]:
        return self.clients_by_id.get(client_id)

    # --------- helper: display text formatting ---------

    @staticmethod
    def build_display_text(
        role: str,
        source_id: Optional[str],
        target_id: Optional[str],
        text: str,
    ) -> str:
        """
        role: "incoming"  -> receiver sees "[from <source>] text"
              "outgoing"  -> sender sees "[to <target>] text"
              anything else -> just text
        """
        if role == "incoming" and source_id:
            return f"[from {source_id}] {text}"
        if role == "outgoing" and target_id:
            return f"[to {target_id}] {text}"
        return text

    # --------- client lifecycle ---------

    async def connect(self, websocket: WebSocket, is_pi: bool = False):
        """Accept a new WebSocket and register a client."""
        await websocket.accept()
        client = ClientConnection(websocket=websocket, preferred_lang="en")
        self.active_connections.append(client)
        self.clients_by_id[client.client_id] = client
        self.add_to_lang_group(client, client.preferred_lang)

        # If this connection is the Pi, set pi_client_id here
        if is_pi:
            self.pi_client_id = client.client_id
            print(f"[PI] Registered Raspberry Pi client on connect: {self.pi_client_id}")

        print(
            f"Client connected. Total: {len(self.active_connections)} "
            f"client_id={client.client_id}, is_pi={is_pi}"
        )

        # tell client its ID
        hello_msg = json.dumps(
            {
                "type": "hello",
                "client_id": client.client_id,
                "preferred_lang": client.preferred_lang,
                "is_pi": is_pi,
                "time": str(asyncio.get_event_loop().time()),
            },
            ensure_ascii=False,
        )
        await client.websocket.send_text(hello_msg)

    def disconnect(self, websocket: WebSocket):
        """Cleanly remove a client when the WebSocket closes."""
        client = self.get_client_by_ws(websocket)
        if client is not None:
            self.active_connections.remove(client)
            self.remove_from_all_lang_groups(client)
            if client.client_id in self.clients_by_id:
                del self.clients_by_id[client.client_id]
            # If the Pi disconnects, clear the Pi ID
            if self.pi_client_id == client.client_id:
                self.pi_client_id = None
                print("[PI] Raspberry Pi client disconnected, cleared pi_client_id")
            print("Client disconnected. Total:", len(self.active_connections))

    # --------- language group management ---------

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

    async def update_client_lang(self, websocket: WebSocket, new_lang: str):
        client = self.get_client_by_ws(websocket)
        if client and client.preferred_lang != new_lang:
            self.remove_from_all_lang_groups(client)
            client.preferred_lang = new_lang
            self.add_to_lang_group(client, new_lang)
            print(f"Client language updated to {new_lang}")

    # --------- translation only ---------

    def translate_text(self, text: str, target_lang: str, source_lang: str) -> str:
        """
        Pure translation function. Does not send anything.
        """
        target_lang = target_lang.upper()
        source_lang = source_lang.upper()

        if target_lang == source_lang:
            return text

        if not self.translator:
            print("[DEEPL ERROR] Missing DEEPL_API_KEY")
            return f"[{target_lang} untranslated] {text}"

        try:
            result = self.translator.translate_text(
                text,
                source_lang=source_lang,
                target_lang=target_lang
            )
            return result.text
        except Exception as e:
            print(f"[DEEPL ERROR] {e}")
            return f"[{target_lang} untranslated] {text}"

    # --------- 1-to-1 messaging (chat + subtitles_one) ---------

    async def send_personal_message_by_id(
        self,
        *,
        original_text: str,
        translated_text: str,
        source_client_id: Optional[str],
        target_client_id: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
    ):
        """
        True 1-to-1:
        - receiver sees "[from <source>] <translated_text>"
        - sender sees "[to <target>] <translated_text>"
        """
        time_str = str(asyncio.get_event_loop().time())
        target = self.get_client_by_id(target_client_id)
        source_client = self.get_client_by_id(source_client_id) if source_client_id else None

        # 1) Send to target (incoming)
        if target:
            incoming_display = self.build_display_text(
                role="incoming",
                source_id=source_client_id,
                target_id=target_client_id,
                text=translated_text,
            )
            payload_target = {
                "type": "chat",
                "source_id": source_client_id,
                "target_id": target_client_id,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "original_text": original_text,
                "translated_text": translated_text,
                "display_text": incoming_display,
                "time": time_str,
            }
            await target.websocket.send_text(json.dumps(payload_target, ensure_ascii=False))
        else:
            print(f"[WARN] target_client_id {target_client_id} not found")

        # 2) Echo back to sender (outgoing) so sender sees who they sent to
        if source_client:
            outgoing_display = self.build_display_text(
                role="outgoing",
                source_id=source_client_id,
                target_id=target_client_id,
                text=translated_text,
            )
            payload_source = {
                "type": "chat",
                "source_id": source_client_id,
                "target_id": target_client_id,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "original_text": original_text,
                "translated_text": translated_text,
                "display_text": outgoing_display,
                "time": time_str,
            }
            await source_client.websocket.send_text(json.dumps(payload_source, ensure_ascii=False))

    # --------- broadcast chat (ws -> all other clients) ---------

    async def broadcast_chat_from_ws(self, websocket: WebSocket, text: str):
        """
        Broadcast a chat message from one websocket to all connected clients.
        - Does NOT send back to the sender.
        - Receivers see "[from <source>] <text>" in display_text.
        """
        source_client = self.get_client_by_ws(websocket)
        source_id = source_client.client_id if source_client else None
        now = str(asyncio.get_event_loop().time())

        for client in self.active_connections:
            if client is source_client:
                continue  # do not broadcast to self
            display_text = self.build_display_text(
                role="incoming",
                source_id=source_id,
                target_id=client.client_id,
                text=text,
            )
            payload = {
                "type": "chat",
                "source_id": source_id,
                "target_id": client.client_id,
                "source_lang": None,
                "target_lang": None,
                "original_text": text,
                "translated_text": text,
                "display_text": display_text,
                "time": now,
            }
            await client.websocket.send_text(json.dumps(payload, ensure_ascii=False))

    # --------- broadcast subtitles (HTTP /subtitle) ---------

    async def broadcast_translated(
        self,
        text: str,
        source_lang: str,
        source_client_id: Optional[str] = None,
    ):
        """
        Translate 'text' per language group and broadcast to all clients.
        - Does NOT send to the source client (if provided).
        - Receivers see "[from <source>] <translated_text>".
        """
        loop_time = str(asyncio.get_event_loop().time())

        for target_lang, clients in self.lang_groups.items():
            # Compute translated text once per target language
            translated_text = await asyncio.to_thread(
                self.translate_text, text, target_lang, source_lang
            )

            for client in clients:
                # Skip sending subtitles back to the originating client
                if source_client_id and client.client_id == source_client_id:
                    continue

                display_text = self.build_display_text(
                    role="incoming",
                    source_id=source_client_id,
                    target_id=client.client_id,
                    text=translated_text,
                )
                payload = {
                    "type": "chat",
                    "source_id": source_client_id,
                    "target_id": client.client_id,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "original_text": text,
                    "translated_text": translated_text,
                    "display_text": display_text,
                    "time": loop_time,
                }
                await client.websocket.send_text(json.dumps(payload, ensure_ascii=False))

    # --------- low-level broadcast (raw string) ---------

    async def broadcast_raw(self, message: str):
        """
        Broadcast a pre-encoded string to all clients (used for heartbeat).
        Here there's no "sender", so everyone receives it.
        """
        for client in self.active_connections:
            await client.websocket.send_text(message)


# -----------------------------
# FastAPI app + endpoints
# -----------------------------
manager = ConnectionManager()
app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint.

    Clients:
      - Normal: ws://host:6543/ws
      - Pi:     ws://host:6543/ws?role=pi

    Messages:
      - { "type": "set_lang", "lang": "es" }
      - { "type": "chat", "text": "hello" }
      - {
          "type": "personal_chat",
          "text": "hi",
          "from_client_id": "<id>",
          "to_client_id": "<id>"
        }
    """
    role = websocket.query_params.get("role")
    is_pi = (role == "pi")

    await manager.connect(websocket, is_pi=is_pi)

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            msg_type = data.get("type")

            if msg_type == "set_lang":
                new_lang = data.get("lang", "en")
                await manager.update_client_lang(websocket, new_lang)

                client = manager.get_client_by_ws(websocket)
                client_id = client.client_id if client else None

                set_lang_msg = {
                    "type": "set_lang",
                    "text": f"Language set to {new_lang}",
                    "lang": new_lang,
                    "client_id": client_id,
                    "time": str(asyncio.get_event_loop().time()),
                }
                await websocket.send_text(json.dumps(set_lang_msg, ensure_ascii=False))

            elif msg_type == "chat":
                text = data.get("text", "")
                # broadcast chat from this websocket to all others
                await manager.broadcast_chat_from_ws(websocket, text)

            elif msg_type == "personal_chat":
                # 1-to-1 message over WebSocket (no translation here)
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
                error_payload = {
                    "type": "error",
                    "text": "Unknown message type",
                    "time": str(asyncio.get_event_loop().time()),
                }
                await websocket.send_text(json.dumps(error_payload, ensure_ascii=False))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/subtitle")
async def subtitle_broadcast(
    text: str = Body(..., embed=True),
    source_lang: str = Body("en", embed=True),
    source_client_id: Optional[str] = Body(None, embed=True),
):
    """
    Broadcast a subtitle line to all clients, translating per language group.
    The originating client (source_client_id) will NOT receive its own subtitle.
    """
    await manager.broadcast_translated(
        text=text,
        source_lang=source_lang,
        source_client_id=source_client_id,
    )
    return {
        "status": "ok",
        "mode": "broadcast",
        "original": text,
        "source_lang": source_lang,
        "source_client_id": source_client_id,
    }


@app.post("/subtitle_one")
async def subtitle_one(
    text: str = Body(..., embed=True),
    source_lang: str = Body("en", embed=True),
    target_lang: str = Body("en", embed=True),
    from_client_id: Optional[str] = Body(None, embed=True),
    to_client_id: str = Body(..., embed=True),
):
    """
    True 1-to-1 subtitle:
    - text: original text
    - source_lang: language of text
    - target_lang: language receiver should see
    """
    translated = manager.translate_text(text, target_lang, source_lang)

    # send to receiver + echo to sender with clear IDs
    await manager.send_personal_message_by_id(
        original_text=text,
        translated_text=translated,
        source_client_id=from_client_id,
        target_client_id=to_client_id,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    return {
        "status": "ok",
        "mode": "one_to_one",
        "from_client_id": from_client_id,
        "to_client_id": to_client_id,
        "original": text,
        "translated": translated,
        "source_lang": source_lang,
        "target_lang": target_lang,
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
            heartbeat_msg = json.dumps(
                {
                    "type": "heartbeat",
                    "text": f"Server active, {random.randint(1000, 9999)}",
                    "time": str(asyncio.get_event_loop().time()),
                }
            )
            if manager.active_connections:
                await manager.broadcast_raw(heartbeat_msg)
        except Exception as e:
            print(f"Heartbeat error: {e}")
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(send_heartbeat())


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="0.0.0.0", port=6543, reload=True)
