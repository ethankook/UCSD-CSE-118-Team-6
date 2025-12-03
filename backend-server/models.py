# models.py
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class MessageType(str, Enum):
    HELLO = "hello"
    SET_LANG = "set_lang"
    CHAT = "chat"
    PERSONAL_CHAT = "personal_chat"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class DisplayRole(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    NEUTRAL = "neutral"


# ---------- WebSocket payloads sent to clients ----------

class ChatPayload(BaseModel):
    type: MessageType = MessageType.CHAT
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    original_text: str
    translated_text: str
    display_text: str
    time: str


class HelloPayload(BaseModel):
    type: MessageType = MessageType.HELLO
    client_id: str
    preferred_lang: str
    is_pi: bool
    time: str


class SetLangPayload(BaseModel):
    type: MessageType = MessageType.SET_LANG
    text: str
    lang: str
    client_id: Optional[str] = None
    time: str


class ErrorPayload(BaseModel):
    type: MessageType = MessageType.ERROR
    text: str
    time: str


class HeartbeatPayload(BaseModel):
    type: MessageType = MessageType.HEARTBEAT
    text: str
    time: str


# ---------- HTTP request bodies ----------

class SubtitleBroadcastRequest(BaseModel):
    text: str
    source_lang: str = "en"
    source_client_id: Optional[str] = None


class SubtitleOneRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str = "en"
    from_client_id: Optional[str] = None
    to_client_id: str
