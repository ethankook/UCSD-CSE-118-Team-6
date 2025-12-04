using System;
using UnityEngine;

public enum SocketMessageType
{
    chat,
    heartbeat,
    error,
    set_lang,
}

[Serializable]
public struct SocketMessage
{
    public SocketMessageType type;
    public string source_id;
    public string target_id;
    public string source_lang;
    public string target_lang;
    public string original_text;
    public string translated_text;
    public string display_text;
    public float time;

    public SocketMessage(SocketMessageType type, string sourceId, string targetId, string sourceLang, string targetLang, string originalText, string translatedText, string displayText, float time)
    {
        this.type = type;
        source_id = sourceId;
        target_id = targetId;
        source_lang = sourceLang;
        target_lang = targetLang;
        original_text = originalText;
        translated_text = translatedText;
        display_text = displayText;
        this.time = time;
    }

    public string ToJson()
    {
        return JsonUtility.ToJson(this);
    }

    public static SocketMessage FromJson(string json)
    {
        return JsonUtility.FromJson<SocketMessage>(json);
    }

}

public struct SocketSetLangMessage
{
    public string type;
    public string lang;

    public SocketSetLangMessage(string lang)
    {
        type = SocketMessageType.set_lang.ToString();
        this.lang = lang;
    }
}