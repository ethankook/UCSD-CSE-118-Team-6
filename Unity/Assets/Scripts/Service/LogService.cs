using UnityEngine;

public class LogService : MonoBehaviour
{
    static LogService instance;
    
    [SerializeField]
    private bool enableLoggingOnUI = true;

    [SerializeField]
    private bool enableLoggingInConsole = true;
    [SerializeField]
    private TextBoxUI logTextBox;
    void Awake()
    {
        instance = this;
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
