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
            clearLogsButton.onClick.AddListener(() => logTextBox.ClearText());
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
            instance.logTextBox.AddTextEntry(message);
        }
    }
}
