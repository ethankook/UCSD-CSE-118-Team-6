# models.py
from enum import Enum
from typing import Optional

from pydantic import BaseModel


# MESSAGE TYPES

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


# ---------- PAYLOADS ----------

class ChatPayload(BaseModel):
    """
    Chat / subtitle payload.

    Used for:
      - type=CHAT (broadcast)
      - type=PERSONAL_CHAT (1-to-1)

    Includes:
      - IDs + display names
      - source/target languages
      - original + translated text
      - display_text for convenient rendering
    """
    type: MessageType  # CHAT or PERSONAL_CHAT

    source_id: Optional[str] = None
    target_id: Optional[str] = None

    source_display_name: Optional[str] = None
    target_display_name: Optional[str] = None

    source_lang: Optional[str] = None
    target_lang: Optional[str] = None

    original_text: Optional[str] = None
    translated_text: Optional[str] = None
    display_text: Optional[str] = None

    time: str
    is_pi: Optional[bool] = None  # optional flag if this message is from the Pi


class HelloPayload(BaseModel):
    """
    Sent once when a client connects.

    Lets the client know:
      - its client_id
      - its current preferred_lang
      - its display_name
      - whether it's registered as the Pi
    """
    type: MessageType = MessageType.HELLO
    client_id: str
    preferred_lang: str
    display_name: str
    is_pi: bool
    time: str


class SetLangPayload(BaseModel):
    """
    Acknowledgement after a client changes its language and/or display name.
    """
    type: MessageType = MessageType.SET_LANG
    text: str                 # human-readable message ("Language set to en")
    lang: str                 # new preferred language (app-level code, e.g. "en")
    client_id: Optional[str] = None
    display_name: Optional[str] = None
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
