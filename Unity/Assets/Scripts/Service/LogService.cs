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

        string formattedMessage = logString;
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
            case LogType.Log:
                Log(logString);
                return;
            case LogType.Assert:
                formattedMessage = $"<color=magenta>{logString}</color>";
                break;
            default:
                break;
        }
        logTextBox.AddTextEntry(formattedMessage);
    }
    public static void Log(string message)
    {
        if (instance.enableLoggingInConsole)
        {
            Debug.Log(message);
        }
        if (instance.enableLoggingOnUI && instance.logTextBox != null)
        {
            instance.logTextBox.AddTextEntry(message);
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
            instance.logTextBox.AddTextEntry($"<color=red>{message}</color>");
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
            instance.logTextBox.AddTextEntry($"<color=yellow>{message}</color>");
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
