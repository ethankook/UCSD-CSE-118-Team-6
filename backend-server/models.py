# models.py
from enum import Enum
from typing import Optional

from pydantic import BaseModel


# -----------------------------
# MESSAGE TYPES
# -----------------------------

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


# -----------------------------
# PAYLOADS SENT OVER WEBSOCKET
# -----------------------------

class ChatPayload(BaseModel):
    """
    Generic chat / subtitle payload.

    - original_text: what the sender actually said
    - translated_text: what the receiver should see
    - display_text: final string that the client can render directly
    """
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
    """
    Sent once when a client connects.

    Lets the client know:
      - its client_id
      - its current preferred_lang
      - whether it's registered as the Pi
    """
    type: MessageType = MessageType.HELLO
    client_id: str
    preferred_lang: str
    is_pi: bool
    time: str


class SetLangPayload(BaseModel):
    """
    Acknowledgement after a client changes its language.
    """
    type: MessageType = MessageType.SET_LANG
    text: str
    lang: str
    client_id: Optional[str] = None
    time: str


class ErrorPayload(BaseModel):
    """
    Error messages for invalid types, bad payloads, etc.
    """
    type: MessageType = MessageType.ERROR
    text: str
    time: str


class HeartbeatPayload(BaseModel):
    """
    Periodic server heartbeat.
    """
    type: MessageType = MessageType.HEARTBEAT
    text: str
    time: str
