# connection_manager.py
import asyncio
import json
import os
import uuid
from typing import Dict, List, Optional

import deepl
from fastapi import WebSocket

from models import (
    ChatPayload,
    DisplayRole,
    HelloPayload,
)


class ClientConnection:
    """
    Represents a single WebSocket client.

    Fields:
      - websocket: the underlying WebSocket connection
      - preferred_lang: language code like "en", "es", "zh", etc.
      - client_id: UUID that identifies this client across messages
    """

    def __init__(
        self,
        websocket: WebSocket,
        preferred_lang: str = "en",
        client_id: Optional[str] = None,
    ):
        self.websocket = websocket
        self.preferred_lang = preferred_lang
        self.client_id = client_id or str(uuid.uuid4())


class ConnectionManager:
    """
    Holds all state and logic for connected clients, translations, and broadcasts.

    Key responsibilities:
      - Track active WebSocket clients
      - Track preferred language per client
      - Perform translations via DeepL
      - Broadcast group chat with translation
      - Send personal 1-to-1 messages with translation
    """

    def __init__(self):
        # All currently connected clients
        self.active_connections: List[ClientConnection] = []

        # Map client_id -> ClientConnection
        self.clients_by_id: Dict[str, ClientConnection] = {}

        # (Optional) language groups (not strictly required, but kept for flexibility)
        self.lang_groups: Dict[str, List[ClientConnection]] = {}

        # Raspberry Pi client ID (if any)
        self.pi_client_id: Optional[str] = None

        # DeepL translator setup
        api_key = os.environ.get("DEEPL_API_KEY")
        if api_key:
            self.translator = deepl.Translator(api_key)
            print("[DEEPL] Translator initialized")
        else:
            self.translator = None
            print("[DEEPL] WARNING: DEEPL_API_KEY not set; messages will not be auto-translated")

    # Helper: lookup

    def get_client_by_ws(self, websocket: WebSocket) -> Optional[ClientConnection]:
        for client in self.active_connections:
            if client.websocket is websocket:
                return client
        return None

    def get_client_by_id(self, client_id: str) -> Optional[ClientConnection]:
        return self.clients_by_id.get(client_id)

    # Helper: display formatting

    @staticmethod
    def build_display_text(
        role: DisplayRole,
        source_id: Optional[str],
        target_id: Optional[str],
        text: str,
    ) -> str:
        """
        Builds a human-friendly string that clients can render directly.
        """
        if role == DisplayRole.INCOMING and source_id:
            return f"[from {source_id}] {text}"
        if role == DisplayRole.OUTGOING and target_id:
            return f"[to {target_id}] {text}"
        return text

    # Lifecycle: connect / disconnect

    async def connect(self, websocket: WebSocket, is_pi: bool = False):
        """
        Accept a new WebSocket and register a client.

        Flow:
          1) Accept WebSocket
          2) Create ClientConnection
          3) Track in internal lists
          4) Optionally mark as Pi client
          5) Send HelloPayload (type=hello)
        """
        await websocket.accept()

        client = ClientConnection(websocket=websocket, preferred_lang="en")
        self.active_connections.append(client)
        self.clients_by_id[client.client_id] = client
        self.add_to_lang_group(client, client.preferred_lang)

        if is_pi:
            self.pi_client_id = client.client_id
            print(f"[PI] Registered Raspberry Pi client: {self.pi_client_id}")

        print(
            f"[CONNECT] client_id={client.client_id}, is_pi={is_pi}, "
            f"total_clients={len(self.active_connections)}"
        )

        # Send initial hello message with client_id + current language
        hello = HelloPayload(
            client_id=client.client_id,
            preferred_lang=client.preferred_lang,
            is_pi=is_pi,
            time=str(asyncio.get_event_loop().time()),
        )
        await client.websocket.send_text(
            json.dumps(hello.model_dump(), ensure_ascii=False)
        )

    def disconnect(self, websocket: WebSocket):
        """
        Cleanly remove a client when the WebSocket closes.
        """
        client = self.get_client_by_ws(websocket)
        if client is None:
            return

        if client in self.active_connections:
            self.active_connections.remove(client)

        if client.client_id in self.clients_by_id:
            del self.clients_by_id[client.client_id]

        self.remove_from_all_lang_groups(client)

        if self.pi_client_id == client.client_id:
            self.pi_client_id = None
            print("[PI] Raspberry Pi client disconnected; pi_client_id cleared")

        print(f"[DISCONNECT] client_id={client.client_id}, total_clients={len(self.active_connections)}")

    # Language group management (optional, but kept for potential use)

    def add_to_lang_group(self, client: ClientConnection, lang: str):
        self.lang_groups.setdefault(lang, []).append(client)

    def remove_from_lang_group(self, client: ClientConnection, lang: str):
        group = self.lang_groups.get(lang)
        if not group:
            return
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
        """
        Update a client's preferred language + regroup it.
        """
        client = self.get_client_by_ws(websocket)
        if client and client.preferred_lang != new_lang:
            self.remove_from_all_lang_groups(client)
            client.preferred_lang = new_lang
            self.add_to_lang_group(client, new_lang)
            print(f"[LANG] client_id={client.client_id} language updated to {new_lang}")

    # Translation

    def translate_text(self, text: str, target_lang: str, source_lang: str) -> str:
        """
        Core translation function.

        - source_lang: language of the original text
        - target_lang: desired language of the receiver

        Translation happens HERE, once per (target_lang, message) pair.
        This function is used by both group chat and personal chat.
        """
        if not text:
            return text

        if not self.translator:
            # No API key; just tag the message instead of translating
            print("[DEEPL] Missing DEEPL_API_KEY, skipping translation")
            return f"[{target_lang} untranslated] {text}"

        # Normalize language codes (e.g. "en" -> "EN")
        target_lang = target_lang.upper()
        source_lang = source_lang.upper()

        if target_lang == source_lang:
            return text

        try:
            result = self.translator.translate_text(
                text,
                source_lang=source_lang,
                target_lang=target_lang,
            )
            return result.text
        except Exception as e:
            print(f"[DEEPL ERROR] {e}")
            return f"[{target_lang} untranslated] {text}"

    # 1-to-1 messaging (already assumes translated_text is provided)

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
        Low-level function to actually send the ChatPayloads to sender + receiver.

        It does NOT perform translation. It just uses the translated_text you pass in.
        """
        time_str = str(asyncio.get_event_loop().time())
        target = self.get_client_by_id(target_client_id)
        source_client = (
            self.get_client_by_id(source_client_id) if source_client_id else None
        )

        # 1) send to target (incoming)
        if target:
            incoming_display = self.build_display_text(
                role=DisplayRole.INCOMING,
                source_id=source_client_id,
                target_id=target_client_id,
                text=translated_text,
            )
            payload_target = ChatPayload(
                source_id=source_client_id,
                target_id=target_client_id,
                source_lang=source_lang,
                target_lang=target_lang,
                original_text=original_text,
                translated_text=translated_text,
                display_text=incoming_display,
                time=time_str,
            )
            await target.websocket.send_text(
                json.dumps(payload_target.model_dump(), ensure_ascii=False)
            )
        else:
            print(f"[WARN] target_client_id {target_client_id} not found")

        # 2) echo back to sender (outgoing)
        if source_client:
            outgoing_display = self.build_display_text(
                role=DisplayRole.OUTGOING,
                source_id=source_client_id,
                target_id=target_client_id,
                text=translated_text,
            )
            payload_source = ChatPayload(
                source_id=source_client_id,
                target_id=target_client_id,
                source_lang=source_lang,
                target_lang=target_lang,
                original_text=original_text,
                translated_text=translated_text,
                display_text=outgoing_display,
                time=time_str,
            )
            await source_client.websocket.send_text(
                json.dumps(payload_source.model_dump(), ensure_ascii=False)
            )

    # 1-to-1 messaging from a WebSocket (does the translation)

    async def send_personal_message_from_ws(
        self,
        websocket: WebSocket,
        target_client_id: str,
        text: str,
    ):
        """
        High-level function for WebSocket "personal_chat" messages.

        Flow:
          1) Look up sender from websocket
          2) Look up target from target_client_id
          3) Use both clients' preferred_lang to compute translation
          4) Call send_personal_message_by_id(...) to push to both ends
        """
        source_client = self.get_client_by_ws(websocket)
        if not source_client:
            print("[WARN] send_personal_message_from_ws: no source client")
            return

        source_id = source_client.client_id
        source_lang = source_client.preferred_lang

        target_client = self.get_client_by_id(target_client_id)
        if not target_client:
            print(f"[WARN] target_client_id {target_client_id} not found")
            return

        target_lang = target_client.preferred_lang

        # TRANSLATION HAPPENS HERE for personal messages
        translated_text = await asyncio.to_thread(
            self.translate_text,
            text,
            target_lang,
            source_lang,
        )

        await self.send_personal_message_by_id(
            original_text=text,
            translated_text=translated_text,
            source_client_id=source_id,
            target_client_id=target_client_id,
            source_lang=source_lang,
            target_lang=target_lang,
        )

    # Broadcast chat (WebSocket -> all other clients, with translation)

    async def broadcast_chat_from_ws(self, websocket: WebSocket, text: str):
        """
        Handle a group CHAT message coming from a WebSocket client.

        Flow:
          1) Determine the sender (client_id + preferred_lang)
          2) For each other client:
               - Use sender.preferred_lang as source_lang
               - Use receiver.preferred_lang as target_lang
               - TRANSLATE text per-receiver
               - Send ChatPayload with both original and translated text
        """
        source_client = self.get_client_by_ws(websocket)
        if not source_client:
            print("[WARN] broadcast_chat_from_ws: no source client")
            return

        source_id = source_client.client_id
        source_lang = source_client.preferred_lang
        now = str(asyncio.get_event_loop().time())

        for client in self.active_connections:
            if client is source_client:
                continue

            target_lang = client.preferred_lang

            # TRANSLATION HAPPENS HERE for group chat
            translated_text = await asyncio.to_thread(
                self.translate_text,
                text,
                target_lang,
                source_lang,
            )

            display_text = self.build_display_text(
                role=DisplayRole.INCOMING,
                source_id=source_id,
                target_id=client.client_id,
                text=translated_text,
            )

            payload = ChatPayload(
                source_id=source_id,
                target_id=client.client_id,
                source_lang=source_lang,
                target_lang=target_lang,
                original_text=text,
                translated_text=translated_text,
                display_text=display_text,
                time=now,
            )
            await client.websocket.send_text(
                json.dumps(payload.model_dump(), ensure_ascii=False)
            )

    # Low-level broadcast for heartbeat (no translation)

    async def broadcast_raw(self, message: str):
        """
        Sends a raw text frame to all connected clients.
        Used for heartbeat (type=heartbeat) messages.
        """
        for client in self.active_connections:
            await client.websocket.send_text(message)
