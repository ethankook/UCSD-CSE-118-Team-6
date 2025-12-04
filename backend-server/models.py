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


# SINGLE UNIFIED PAYLOAD

class ChatPayload(BaseModel):
    """
    Unified payload used for ALL messages:

    - HELLO
    - SET_LANG
    - CHAT / PERSONAL_CHAT
    - ERROR
    - HEARTBEAT

    Many fields are optional; different message types
    only use the ones they care about.
    """

    # Core envelope
    type: MessageType
    time: str

    # Generic identity fields
    source_id: Optional[str] = None     # sender client_id (for chat/personal_chat)
    target_id: Optional[str] = None     # receiver client_id (for personal_chat)
    client_id: Optional[str] = None     # for HELLO / SET_LANG

    # Language-related fields
    source_lang: Optional[str] = None   # sender language
    target_lang: Optional[str] = None   # receiver language
    lang: Optional[str] = None          # for SET_LANG (new language)
    preferred_lang: Optional[str] = None  # for HELLO

    # Text payloads
    text: Optional[str] = None          # generic text (error, heartbeat, set_lang msg)
    original_text: Optional[str] = None # what the sender actually said
    translated_text: Optional[str] = None  # translated version for receiver
    display_text: Optional[str] = None  # final string client can render directly

    # Misc
    is_pi: Optional[bool] = None        # mark if this connection is the Pi (for HELLO/chat, etc.)
