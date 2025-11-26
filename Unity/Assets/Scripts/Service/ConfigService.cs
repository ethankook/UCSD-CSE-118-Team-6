using UnityEngine;

public class ConfigService : MonoBehaviour
{
    [SerializeField] private string serverUrl = "http://192.168.0.110:6543/";

    [Header("Theme Colors")]
    [SerializeField] private Color colorPrimary = Color.white;
    [SerializeField] private Color colorSecondary = Color.gray;
    [SerializeField] private Color colorText = Color.black;
    [SerializeField] private Color colorWarning = Color.yellow;
    [SerializeField] private Color colorError = Color.red;

    // Expose as static read-only to the rest of the code
    public static string SERVER_URL { get; private set; }

    public static Color COLOR_PRIMARY { get; private set; }
    public static Color COLOR_SECONDARY { get; private set; }
    public static Color COLOR_TEXT { get; private set; }
    public static Color COLOR_WARNING { get; private set; }
    public static Color COLOR_ERROR { get; private set; }

    void Awake()
    {
        SERVER_URL = serverUrl;
        COLOR_PRIMARY = colorPrimary;
        COLOR_SECONDARY = colorSecondary;
        COLOR_TEXT = colorText;
        COLOR_WARNING = colorWarning;
        COLOR_ERROR = colorError;
    }
}