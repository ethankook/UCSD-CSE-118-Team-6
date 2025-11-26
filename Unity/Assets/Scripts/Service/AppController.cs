using UnityEngine;
using TMPro;
using UnityEngine.Accessibility;
using System.Threading.Tasks;
using System.Collections;

public class AppController : MonoBehaviour
{

    private string[] debugSentences = new string[]
    {
        "Hello, welcome to our application.",
        "This is a simulated stream of translated text.",
        "Each sentence appears one after the other.",
        "This helps in testing the display functionality.",
        "Thank you for using our service!",
        "TEAM: 6"
    };
    private float DEBUG_STREAM_INTERVAL = 1.0f;

    [Header("UI")]
    public TextMeshProUGUI statusText;

    // Input mapping (adjust for your specific input system, e.g., OVRInput)
    private bool isRecording = false;

    void Start()
    {
        SocketService.SendRequest(SocketService.Method.GET, ConfigService.SERVER_URL, null, null, (response) => 
        {
            if(response.isSuccess)
            {
                LogService.Log($"Server Response: {response.data}");
            } else 
            {
                LogService.Log($"Server Error: {response.error}");
            }
        });
        SocketService.ConnectSocket($"ws://{ConfigService.SERVER_URL}/ws");
        // For debugging without mic input, simulate text stream
        StartCoroutine(SimulateTextStream());
    }

    IEnumerator SimulateTextStream() 
    {
        foreach (var sentence in debugSentences)
        {
            DisplayService.AddTextEntry(sentence);
            yield return new WaitForSeconds(DEBUG_STREAM_INTERVAL);
        }
    }
}