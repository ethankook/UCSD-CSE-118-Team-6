using UnityEngine;
using TMPro;
using UnityEngine.Accessibility;
using System.Threading.Tasks;
using System.Collections;

public class AppController : MonoBehaviour
{
    const string SERVER_URL = "http://192.168.0.110:6543/";

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

    async void Start()
    {
        SocketService.SendRequest(SocketService.Method.GET, SERVER_URL, null, null, (response) => 
        {
            if(response.isSuccess)
            {
                LogService.Log($"Server Response: {response.data}");
            } else 
            {
                LogService.Log($"Server Error: {response.error}");
            }
        });
        await SocketService.ConnectSocket($"ws://{SERVER_URL}/ws");
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

    public async void ToggleRecording()
    {
        if (!isRecording)
        {
            // START
            bool success = MicService.StartRecording();
            if (success)
            {
                isRecording = true;
                statusText.text = "Status: Recording...";
                statusText.color = Color.red;
            }
        }
        else
        {
            // STOP
            isRecording = false;
            statusText.text = "Status: Processing...";
            statusText.color = Color.yellow;

            // 1. Get Audio
            AudioClip clip = MicService.StopRecording();

            if (clip != null)
            {
                // 2. Transcribe (Local VR)
                string text = await MicService.TranscribeAudio(clip);
                LogService.Log(text);
                statusText.text = "Status: Idle";
                statusText.color = Color.white;

                // 3. Send to Server (Cloud) via SocketService
                // Example: Sending the text to a backend for logging or translation
                string jsonBody = $"{{\"text\": \"{text}\"}}";
                SocketService.SendRequest(SocketService.Method.POST, SERVER_URL, null, jsonBody, (response) => 
                {
                    if(response.isSuccess) Debug.Log("Server confirmed receipt");
                    else Debug.LogError("Server Error: " + response.error);
                });
            }
            else
            {
                statusText.text = "Status: Error (No Audio)";
                LogService.Log("Error: No audio recorded.");
            }
        }
    }
}