using UnityEngine;
using UnityEngine.UI;

public class LogService : MonoBehaviour
{
    static LogService instance;
    
    [SerializeField]
    private bool enableLoggingOnUI = true;

    [SerializeField]
    private bool enableLoggingInConsole = true;
    [SerializeField]
    private TextBoxUI logTextBox;
    [SerializeField]
    private Button clearLogsButton;


    void Awake()
    {
        instance = this;
        if (clearLogsButton != null && logTextBox != null)
        {
            clearLogsButton.onClick.AddListener(() => ClearLogs());
        }
    }

    void OnEnable()
    {
        Application.logMessageReceived += HandleLog;
    }

    void OnDisable()
    {
        Application.logMessageReceived -= HandleLog;
    }

    void HandleLog(string logString, string stackTrace, LogType type)
    {
        if (!enableLoggingOnUI || logTextBox == null) return;

        switch (type)
        {
            case LogType.Error:
                LogError(logString);
                DisplayService.AddTextEntry(stackTrace);
                return;
            case LogType.Exception:
                LogError(logString);
                DisplayService.AddTextEntry(stackTrace);
                return;
            case LogType.Warning:
                LogWarning(logString);
                return;
            case LogType.Assert:
                LogAssertion(logString);
                return;
            case LogType.Log:
                // No special formatting
                break;
            default:
                break;
        }
    }
    public static void Log(string message)
    {
        if (instance.enableLoggingInConsole)
        {
            Debug.Log(message);
        }
        if (instance.enableLoggingOnUI && instance.logTextBox != null)
        {
            instance.logTextBox.AddTextEntry(message, ConfigService.INFO_ICON, ConfigService.COLOR_PRIMARY);
        }
    }

    public static void LogError(string message)
    {
        if (instance.enableLoggingInConsole)
        {
            Debug.LogError(message); 
        }
        if (instance.enableLoggingOnUI && instance.logTextBox != null)
        {
            instance.logTextBox.AddTextEntry(message, ConfigService.ERROR_ICON, ConfigService.COLOR_ERROR);
        }
    }
    public static void LogWarning(string message)
    {
        if (instance.enableLoggingInConsole)
        {
            Debug.LogWarning(message);
        }
        if (instance.enableLoggingOnUI && instance.logTextBox != null)
        {
            instance.logTextBox.AddTextEntry(message, ConfigService.WARNING_ICON, ConfigService.COLOR_WARNING);
        }
    }
    public static void LogAssertion(string message)
    {
        if (instance.enableLoggingInConsole)
        {
            Debug.LogAssertion(message);
        }
        if (instance.enableLoggingOnUI && instance.logTextBox != null)
        {
            instance.logTextBox.AddTextEntry(message, ConfigService.ASSERTION_ICON, ConfigService.COLOR_ASSERTION);
        }
    }
    public static void ClearLogs()
    {
        if (instance.logTextBox != null)
        {
            instance.logTextBox.ClearText();
        }
    }
}
