
using System.Collections;
using UnityEngine;

public class DisplayService : MonoBehaviour
{
    static DisplayService instance;

    [SerializeField] private TextBoxUI textBox;
    void Awake()
    {
        instance = this;
    }
    public static void AddTextEntry(string text)
    {
        instance.textBox.AddTextEntry(text, ConfigService.CHAT_ICON, ConfigService.COLOR_PRIMARY);
    }
}