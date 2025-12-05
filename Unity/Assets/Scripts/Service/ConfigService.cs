using UnityEngine;

public class ConfigService : MonoBehaviour
{
    [SerializeField] private string serverUrl;

    [Header("Theme Colors")]
    [SerializeField] private Color colorPrimary = Color.white;
    [SerializeField] private Color colorSecondary = Color.gray;
    [SerializeField] private Color colorText = Color.black;
    [SerializeField] private Color colorWarning = Color.yellow;
    [SerializeField] private Color colorError = Color.red;
    [SerializeField] private Color colorAssertion = Color.magenta;

    // Expose as static read-only to the rest of the code
    public static string SERVER_URL { get; private set; }

    public static Color COLOR_PRIMARY { get; private set; }
    public static Color COLOR_SECONDARY { get; private set; }
    public static Color COLOR_TEXT { get; private set; }
    public static Color COLOR_WARNING { get; private set; }
    public static Color COLOR_ERROR { get; private set; }
    public static Color COLOR_ASSERTION { get; private set; }


    [Header("Icons")]
    [SerializeField]
    private Sprite warningIcon;
    [SerializeField]
    private Sprite errorIcon;
    [SerializeField]
    private Sprite infoIcon;
    [SerializeField]
    private Sprite assertionIcon;
    [SerializeField]
    private Sprite chatIcon;
    [SerializeField]
    private Sprite defaultIcon;


    public static Sprite WARNING_ICON {get; private set; }
    public static Sprite ERROR_ICON {get; private set; }
    public static Sprite INFO_ICON {get; private set; }
    public static Sprite ASSERTION_ICON {get; private set; }
    public static Sprite CHAT_ICON {get; private set; }
    public static Sprite DEFAULT_ICON {get; private set; }

    [field: SerializeField]
    public static string Preferred_Language_Code { get; private set; }

    [field: SerializeField]
    public static string Source_id { get; private set; } 



    [SerializeField]
    private string displayName = "Meta QUESTER";

    public static string DISPLAY_NAME { get; private set; }

    void Awake()
    {
        SERVER_URL = serverUrl;
        COLOR_PRIMARY = colorPrimary;
        COLOR_SECONDARY = colorSecondary;
        COLOR_TEXT = colorText;
        COLOR_WARNING = colorWarning;
        COLOR_ERROR = colorError;
        COLOR_ASSERTION = colorAssertion;

        WARNING_ICON = warningIcon;
        ERROR_ICON = errorIcon;
        INFO_ICON = infoIcon;
        ASSERTION_ICON = assertionIcon;
        CHAT_ICON = chatIcon;
        DEFAULT_ICON = defaultIcon;

        DISPLAY_NAME = displayName;

        SetPreferredLanguage(LanguageCode.English);
    }


    public static void SetPreferredLanguage(LanguageCode lang)
    {
        Preferred_Language_Code = LanguageCodeExtensions.ToLanguageString(lang);
        SocketService.SendSocketMessage(new SocketSetLangMessage());
    }

    public static void SetSourceId(string sourceId)
    {
        Source_id = sourceId;
    }

    [ContextMenu("Print Config")]
    public void PrintConfig()
    {
        LogService.Log($"Preferred Language Code: {Preferred_Language_Code}\nDisplay Name: {DISPLAY_NAME}\nsource_id: {Source_id}");
    }

    [ContextMenu("Debug Set Language to English")]
    private void DebugSetLanguage()
    {
        SetPreferredLanguage(LanguageCode.Italian);
    }
}