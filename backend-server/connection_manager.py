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
    MessageType,
)


class ClientConnection:
    """
    Represents a single WebSocket client.

    Fields:
      - websocket: the underlying WebSocket connection
      - preferred_lang: app-level language code like "en", "es-419", "zh-hans"
      - client_id: UUID that identifies this client across messages
      - display_name: human-readable name for UI (set by headset / client)
    """

    def __init__(
        self,
        websocket: WebSocket,
        preferred_lang: str = "en",
        client_id: Optional[str] = None,
        display_name: Optional[str] = None,
    ):
        self.websocket = websocket
        self.preferred_lang = preferred_lang
        self.client_id = client_id or str(uuid.uuid4())
        # Default display name falls back to a short client id
        self.display_name = display_name or f"Client-{self.client_id[:8]}"


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

        # Optional language groups (by app-level lang code, e.g. "en", "es")
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

        # Language mapping dicts for DeepL
        # Keys are APP-level normalized codes (lowercase, may include region),
        # values are DeepL language codes.
        self.source_lang_map: Dict[str, str] = {
            # English
            "en": "EN",
            "en-us": "EN",
            "en-gb": "EN",
            # Spanish
            "es": "ES",
            "es-419": "ES",
            # Portuguese
            "pt": "PT",
            "pt-br": "PT",
            "pt-pt": "PT",
            # Chinese
            "zh": "ZH",
            "zh-hans": "ZH",
            "zh-hant": "ZH",
            # Others (1:1 to DeepL source)
            "ar": "AR",
            "bg": "BG",
            "cs": "CS",
            "da": "DA",
            "de": "DE",
            "el": "EL",
            "et": "ET",
            "fi": "FI",
            "fr": "FR",
            "he": "HE",
            "hu": "HU",
            "id": "ID",
            "it": "IT",
            "ja": "JA",
            "ko": "KO",
            "lt": "LT",
            "lv": "LV",
            "nb": "NB",
            "nl": "NL",
            "pl": "PL",
            "ro": "RO",
            "ru": "RU",
            "sk": "SK",
            "sl": "SL",
            "sv": "SV",
            "th": "TH",
            "tr": "TR",
            "uk": "UK",
            "vi": "VI",
        }

        self.target_lang_map: Dict[str, str] = {
            # English: default to US for plain "en"
            "en": "EN-US",
            "en-us": "EN-US",
            "en-gb": "EN-GB",

            # Spanish
            "es": "ES",
            "es-419": "ES-419",

            # Portuguese
            "pt": "PT-PT",
            "pt-pt": "PT-PT",
            "pt-br": "PT-BR",

            # Chinese: default plain "zh" to simplified
            "zh": "ZH-HANS",
            "zh-hans": "ZH-HANS",
            "zh-hant": "ZH-HANT",

            # Others (1:1 to DeepL target)
            "ar": "AR",
            "bg": "BG",
            "cs": "CS",
            "da": "DA",
            "de": "DE",
            "el": "EL",
            "et": "ET",
            "fi": "FI",
            "fr": "FR",
            "he": "HE",
            "hu": "HU",
            "id": "ID",
            "it": "IT",
            "ja": "JA",
            "ko": "KO",
            "lt": "LT",
            "lv": "LV",
            "nb": "NB",
            "nl": "NL",
            "pl": "PL",
            "ro": "RO",
            "ru": "RU",
            "sk": "SK",
            "sl": "SL",
            "sv": "SV",
            "th": "TH",
            "tr": "TR",
            "uk": "UK",
            "vi": "VI",
        }

    # Helper: lookup

    def get_client_by_ws(self, websocket: WebSocket) -> Optional[ClientConnection]:
        for client in self.active_connections:
            if client.websocket is websocket:
                return client
        return None

    def get_client_by_id(self, client_id: str) -> Optional[ClientConnection]:
        return self.clients_by_id.get(client_id)

    # Helper: display formatting (use display names / labels, NOT raw ids)

    @staticmethod
    def build_display_text(
        role: DisplayRole,
        source_label: Optional[str],
        target_label: Optional[str],
        text: str,
    ) -> str:
        """
        Builds a human-friendly string that clients can render directly.

        source_label / target_label should be display names if possible.
        """
        if role == DisplayRole.INCOMING and source_label:
            return f"[from {source_label}] {text}"
        if role == DisplayRole.OUTGOING and target_label:
            return f"[to {target_label}] {text}"
        return text

    # Lifecycle: connect / disconnect

    async def connect(self, websocket: WebSocket, is_pi: bool = False):
        """
        Accept a new WebSocket and register a client.
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

        # Send initial hello message with client_id + current language + display name
        hello = HelloPayload(
            client_id=client.client_id,
            preferred_lang=client.preferred_lang,
            display_name=client.display_name,
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

    # Language group management

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
                client_in_group = True
                group.remove(client)
                if not group:
                    langs_to_delete.append(lang)
        for lang in langs_to_delete:
            del self.lang_groups[lang]

    async def update_client_lang(
        self,
        websocket: WebSocket,
        new_lang: str,
        display_name: Optional[str] = None,
    ):
        """
        Update a client's preferred language and, optionally, its display name.
        """
        client = self.get_client_by_ws(websocket)
        if not client:
            return

        # Normalize app-level language (keep as-is except lowercasing)
        new_lang_norm = (new_lang or "").lower() or "en"

        if client.preferred_lang != new_lang_norm:
            self.remove_from_all_lang_groups(client)
            client.preferred_lang = new_lang_norm
            self.add_to_lang_group(client, new_lang_norm)
            print(f"[LANG] client_id={client.client_id} language updated to {new_lang_norm}")

        if display_name:
            client.display_name = display_name
            print(f"[NAME] client_id={client.client_id} display_name updated to '{display_name}'")

    # Translation helpers

    def _map_source_lang(self, lang: str) -> Optional[str]:
        norm = (lang or "").lower()
        if not norm:
            return None
        mapped = self.source_lang_map.get(norm)
        if mapped:
            return mapped
        # Fallback: first two letters uppercased
        return norm[:2].upper()

    def _map_target_lang(self, lang: str) -> Optional[str]:
        norm = (lang or "").lower()
        if not norm:
            return None
        mapped = self.target_lang_map.get(norm)
        if mapped:
            return mapped
        # Fallback: first two letters uppercased (avoid deprecated EN by mapping to EN-US)
        fallback = norm[:2].upper()
        if fallback == "EN":
            return "EN-US"
        return fallback

    def translate_text(self, text: str, target_lang: str, source_lang: str) -> str:
        """
        Core translation function.

        - source_lang / target_lang: app-level codes (e.g., "en", "es-419", "zh-hant")
        - We map them to DeepL codes using the dicts above.
        """
        if not text:
            return text

        if not self.translator:
            print("[DEEPL] Missing DEEPL_API_KEY, skipping translation")
            return f"[{target_lang} untranslated] {text}"

        deepl_source = self._map_source_lang(source_lang)
        deepl_target = self._map_target_lang(target_lang)

        if deepl_source and deepl_target and deepl_source[:2] == deepl_target[:2]:
            # Effectively same language; no translation needed
            return text

        try:
            if deepl_source:
                result = self.translator.translate_text(
                    text,
                    source_lang=deepl_source,
                    target_lang=deepl_target,
                )
            else:
                # Let DeepL auto-detect source
                result = self.translator.translate_text(
                    text,
                    target_lang=deepl_target,
                )
            return result.text
        except Exception as e:
            print(f"[DEEPL ERROR] {e}")
            return f"[{deepl_target} untranslated] {text}"

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
            incoming_label = source_client.display_name if source_client else source_client_id
            target_label = target.display_name

            incoming_display = self.build_display_text(
                role=DisplayRole.INCOMING,
                source_label=incoming_label,
                target_label=target_label,
                text=translated_text,
            )
            payload_target = ChatPayload(
                type=MessageType.PERSONAL_CHAT,
                source_id=source_client_id,
                target_id=target_client_id,
                source_lang=source_lang,
                target_lang=target_lang,
                source_display_name=incoming_label,
                target_display_name=target_label,
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
            source_label = source_client.display_name
            target_label = target.display_name if target else target_client_id

            outgoing_display = self.build_display_text(
                role=DisplayRole.OUTGOING,
                source_label=source_label,
                target_label=target_label,
                text=translated_text,
            )
            payload_source = ChatPayload(
                type=MessageType.PERSONAL_CHAT,
                source_id=source_client_id,
                target_id=target_client_id,
                source_lang=source_lang,
                target_lang=target_lang,
                source_display_name=source_label,
                target_display_name=target_label,
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
        """
        source_client = self.get_client_by_ws(websocket)
        if not source_client:
            print("[WARN] broadcast_chat_from_ws: no source client")
            return

        source_id = source_client.client_id
        source_lang = source_client.preferred_lang
        source_label = source_client.display_name
        now = str(asyncio.get_event_loop().time())

        for client in self.active_connections:
            if client is source_client:
                continue

            target_lang = client.preferred_lang
            target_label = client.display_name

            # TRANSLATION HAPPENS HERE for group chat
            translated_text = await asyncio.to_thread(
                self.translate_text,
                text,
                target_lang,
                source_lang,
            )

            display_text = self.build_display_text(
                role=DisplayRole.INCOMING,
                source_label=source_label,
                target_label=target_label,
                text=translated_text,
            )

            payload = ChatPayload(
                type=MessageType.CHAT,
                source_id=source_id,
                target_id=client.client_id,
                source_lang=source_lang,
                target_lang=target_lang,
                source_display_name=source_label,
                target_display_name=target_label,
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
