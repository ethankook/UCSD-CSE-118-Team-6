using System;
using UnityEngine;

public enum SocketMessageType
{
    chat,
    heartbeat,
    error,
    set_lang,
    hello,
    headset_to_pi,
}
[Serializable]
public class SocketMessageBase
{
    public string type;
    public float time;
}

[Serializable]
public class SocketChatMessage : SocketMessageBase
{
    public string source_id;
    public string target_id;
    public string source_lang;
    public string target_lang;
    public string original_text;
    public string translated_text;
    public string display_text;
    public SocketChatMessage(string originalText)
    {
        this.type = SocketMessageType.chat.ToString();
        source_id = ConfigService.Source_id;
        target_id = null;
        source_lang = ConfigService.Preferred_Language_Code;
        target_lang = null;
        original_text = originalText;
        translated_text = null;
        display_text = null;
        time = 0f;
    }
}

public class SocketSetLangMessage : SocketMessageBase
{
    public string lang;
    public string display_name;

    public SocketSetLangMessage()
    {
        type = SocketMessageType.set_lang.ToString();
        lang = ConfigService.Preferred_Language_Code;
        display_name = ConfigService.DISPLAY_NAME;
    }
}

public class SocketHelloMessage : SocketMessageBase
{
    public string client_id;

    public SocketHelloMessage(string clientId)
    {
        type = SocketMessageType.hello.ToString();
        client_id = clientId;
    }
}

public class SocketHeartBeatMessage : SocketMessageBase
{
    public string display_text;
}

public class SocketHeadsetToPiMessage : SocketMessageBase
{
    public string text;
    public SocketHeadsetToPiMessage(string text)
    {
        this.type = SocketMessageType.headset_to_pi.ToString();
        this.text = text;
        time = 0f;
    }
}
public class SocketErrorMessage : SocketMessageBase
{
    public string text;
    public SocketErrorMessage(string errorMessage)
    {
        this.type = SocketMessageType.error.ToString();
        this.text = errorMessage;
        time = 0f;
    }
}