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
    """Represents a single WebSocket client."""

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
    """Holds all state and logic for connected clients, translations, and broadcasts."""

    def __init__(self):
        self.active_connections: List[ClientConnection] = []
        self.lang_groups: Dict[str, List[ClientConnection]] = {}
        self.clients_by_id: Dict[str, ClientConnection] = {}

        api_key = os.environ.get("DEEPL_API_KEY")
        self.translator = deepl.Translator(api_key) if api_key else None

        # One Raspberry Pi client per manager
        self.pi_client_id: Optional[str] = None

    # --------- helper: lookup ----------

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
        role: DisplayRole,
        source_id: Optional[str],
        target_id: Optional[str],
        text: str,
    ) -> str:
        if role == DisplayRole.INCOMING and source_id:
            return f"[from {source_id}] {text}"
        if role == DisplayRole.OUTGOING and target_id:
            return f"[to {target_id}] {text}"
        return text

    # --------- lifecycle ---------

    async def connect(self, websocket: WebSocket, is_pi: bool = False):
        """Accept a new WebSocket and register a client."""
        await websocket.accept()

        client = ClientConnection(websocket=websocket, preferred_lang="en")
        self.active_connections.append(client)
        self.clients_by_id[client.client_id] = client
        self.add_to_lang_group(client, client.preferred_lang)

        if is_pi:
            self.pi_client_id = client.client_id
            print(f"[PI] Registered Raspberry Pi client on connect: {self.pi_client_id}")

        print(
            f"Client connected. Total: {len(self.active_connections)} "
            f"client_id={client.client_id}, is_pi={is_pi}"
        )

        # tell client its ID
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
        """Cleanly remove a client when the WebSocket closes."""
        client = self.get_client_by_ws(websocket)
        if client is None:
            return

        if client in self.active_connections:
            self.active_connections.remove(client)
        self.remove_from_all_lang_groups(client)

        if client.client_id in self.clients_by_id:
            del self.clients_by_id[client.client_id]

        if self.pi_client_id == client.client_id:
            self.pi_client_id = None
            print("[PI] Raspberry Pi client disconnected, cleared pi_client_id")

        print("Client disconnected. Total:", len(self.active_connections))

    # --------- language group management ---------

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
        client = self.get_client_by_ws(websocket)
        if client and client.preferred_lang != new_lang:
            self.remove_from_all_lang_groups(client)
            client.preferred_lang = new_lang
            self.add_to_lang_group(client, new_lang)
            print(f"Client language updated to {new_lang}")

    # --------- translation only ---------

    def translate_text(self, text: str, target_lang: str, source_lang: str) -> str:
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
                target_lang=target_lang,
            )
            return result.text
        except Exception as e:
            print(f"[DEEPL ERROR] {e}")
            return f"[{target_lang} untranslated] {text}"

    # --------- 1-to-1 messaging ---------

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

    # --------- broadcast chat (ws -> all other clients) ---------

    async def broadcast_chat_from_ws(self, websocket: WebSocket, text: str):
        source_client = self.get_client_by_ws(websocket)
        source_id = source_client.client_id if source_client else None
        now = str(asyncio.get_event_loop().time())

        for client in self.active_connections:
            if client is source_client:
                continue

            display_text = self.build_display_text(
                role=DisplayRole.INCOMING,
                source_id=source_id,
                target_id=client.client_id,
                text=text,
            )
            payload = ChatPayload(
                source_id=source_id,
                target_id=client.client_id,
                source_lang=None,
                target_lang=None,
                original_text=text,
                translated_text=text,
                display_text=display_text,
                time=now,
            )
            await client.websocket.send_text(
                json.dumps(payload.model_dump(), ensure_ascii=False)
            )

    # --------- broadcast subtitles (/subtitle) ---------

    async def broadcast_translated(
        self,
        text: str,
        source_lang: str,
        source_client_id: Optional[str] = None,
    ):
        loop_time = str(asyncio.get_event_loop().time())

        for target_lang, clients in self.lang_groups.items():
            translated_text = await asyncio.to_thread(
                self.translate_text, text, target_lang, source_lang
            )

            for client in clients:
                if source_client_id and client.client_id == source_client_id:
                    continue

                display_text = self.build_display_text(
                    role=DisplayRole.INCOMING,
                    source_id=source_client_id,
                    target_id=client.client_id,
                    text=translated_text,
                )
                payload = ChatPayload(
                    source_id=source_client_id,
                    target_id=client.client_id,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    original_text=text,
                    translated_text=translated_text,
                    display_text=display_text,
                    time=loop_time,
                )
                await client.websocket.send_text(
                    json.dumps(payload.model_dump(), ensure_ascii=False)
                )

    # --------- low-level broadcast (raw string) ---------

    async def broadcast_raw(self, message: str):
        for client in self.active_connections:
            await client.websocket.send_text(message)
