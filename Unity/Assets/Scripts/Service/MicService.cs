using UnityEngine;
using UnityEngine.Android; 
using System.Collections;
using System.Threading.Tasks;
using Whisper;
using TMPro;
using UnityEngine.UI;
using System.IO;
using System.Text;
using System;

public class MicService : MonoBehaviour
{
    // Color is not a compile-time constant, use readonly instead

    private static MicService instance;

    [Header("Dependencies")]
    public WhisperManager whisperManager; 

    [Header("Settings")]
    public int maxRecordingLength = 20; 

    private AudioClip recordingClip;
    private string micDevice;   
    
    // State Flags
    private bool isRecording = false;
    private bool isProcessing = false; 

    [Header("UI Elements")]
    [SerializeField] private Button RecordingButton; // Assign your UI Button here to auto-add listener
    [SerializeField] private TextMeshProUGUI RecordingButtonText;
    [SerializeField] private Image RecordingButtonBackground;
    void Awake()
    {
        if (instance == null) instance = this;
        else Destroy(gameObject);
        
        // Optional: Auto-hook button
        if (RecordingButton != null)
            RecordingButton.onClick.AddListener(OnRecordingButtonClick);
    }

    private async void Start()
    {
        // Permissions Logic
        #if UNITY_ANDROID
        if (!Permission.HasUserAuthorizedPermission(Permission.Microphone))
            Permission.RequestUserPermission(Permission.Microphone);
        #endif

        if (Microphone.devices.Length > 0)
            micDevice = Microphone.devices[0];
        else
            LogService.Log("MicService: No microphone found!");

        if (!whisperManager.IsLoaded && !whisperManager.IsLoading)
        {
            LogService.Log("MicService: Initializing Whisper Model...");
            await whisperManager.InitModel();
        }
        
        LogService.Log("MicService: Whisper Ready!");
        
        // Set Initial UI State
        UpdateUIState(false, false);
    }

    private void Update()
    {
        // Safety: If recording hits max length, auto-stop to prevent silence
        if (isRecording && Microphone.IsRecording(micDevice) == false)
        {
            // The clip finished (reached max seconds)
             _ = StopRecordingAndSendAudio(); // Fire and forget
        }
    }

    private string ConvertToWavBase64(AudioClip clip)
    {
        var samples = new float[clip.samples * clip.channels];
        clip.GetData(samples, 0);

        using (var memoryStream = new MemoryStream())
        {
            using (var writer = new BinaryWriter(memoryStream))
            {
                int channelCount = clip.channels;
                int frequency = clip.frequency;
                int sampleCount = samples.Length;
                int bitsPerSample = 16; 
                int bytesPerSample = bitsPerSample / 8;
                int byteRate = frequency * channelCount * bytesPerSample;
                int blockAlign = channelCount * bytesPerSample;

                // --- RIFF Header ---
                writer.Write(Encoding.UTF8.GetBytes("RIFF"));
                writer.Write(36 + sampleCount * bytesPerSample); // File Size - 8
                writer.Write(Encoding.UTF8.GetBytes("WAVE"));

                // --- Format Chunk ---
                writer.Write(Encoding.UTF8.GetBytes("fmt "));
                writer.Write(16); // Subchunk1Size (16 for PCM)
                writer.Write((short)1); // AudioFormat (1 for PCM)
                writer.Write((short)channelCount);
                writer.Write(frequency);
                writer.Write(byteRate);
                writer.Write((short)blockAlign);
                writer.Write((short)bitsPerSample);

                // --- Data Chunk ---
                writer.Write(Encoding.UTF8.GetBytes("data"));
                writer.Write(sampleCount * bytesPerSample); // Subchunk2Size

                // --- Write Data (Convert Float to Int16) ---
                // Unity audio is 0.0f to 1.0f (mostly). WAV expects Int16.
                foreach (var sample in samples)
                {
                    // Scale float to short range (approx -32768 to 32767)
                    short intSample = (short)(Mathf.Clamp(sample, -1f, 1f) * 32767f);
                    writer.Write(intSample);
                }
            }

            // Convert the complete byte array to Base64
            byte[] wavBytes = memoryStream.ToArray();
            return Convert.ToBase64String(wavBytes);
        }
    }

    // --- The Button Entry Point ---
    [ContextMenu("Toggle Recording")]
    public void OnRecordingButtonClick()
    {
        // Prevent clicking while AI is thinking
        if (isProcessing) return; 

        if (!isRecording)
        {
            StartRecording();
        }
        else
        {
            // We must use a fire-and-forget async call here for the button void
            _ = StopRecordingAndSendAudio(); 
        }
    }

    // --- Core Logic ---

    public void StartRecording()
    {
        if (string.IsNullOrEmpty(micDevice)) return;
        if (isRecording || isProcessing) return;

        // Start Unity Microphone
        recordingClip = Microphone.Start(micDevice, false, maxRecordingLength, ConfigService.MIC_SAMPLING_RATE);
        isRecording = true;

        UpdateUIState(true, false);
        LogService.Log("MicService: Recording Started...");
    }

    // Changed from Task<AudioClip> to Task so we can await the whole process
    public async Task StopRecordingAndTranscribe()
    {
        if (!isRecording) return;

        // 1. Capture current position
        int position = Microphone.GetPosition(micDevice);
        Microphone.End(micDevice);
        isRecording = false;

        // 2. Update UI to "Thinking" state
        UpdateUIState(false, true); 

        // 3. Trim the clip
        AudioClip trimmedClip = TrimSilence(recordingClip, position);

        // 4. Send to Whisper (Await here so UI stays in 'Thinking' mode)
        string resultText = await TranscribeAudio(trimmedClip);

        // 5. Reset UI to Idle
        isProcessing = false;
        UpdateUIState(false, false);

        // send to socket service
        SocketService.SendSocketMessage(new SocketHeadsetToPiMessage(resultText));
    }

    public async Task StopRecordingAndSendAudio()
    {
        if (!isRecording) return;

        // 1. Capture current position
        int position = Microphone.GetPosition(micDevice);
        Microphone.End(micDevice);
        isRecording = false;

        // 2. Update UI to "Thinking" state
        UpdateUIState(false, true); 

        // 3. Trim the clip
        AudioClip trimmedClip = TrimSilence(recordingClip, position);

        // 4. Convert to WAV Base64
        string wavBase64 = ConvertToWavBase64(trimmedClip);

        // 5. Send to Socket Service
        SocketService.SendSocketMessage(new SocketHeadsetAudioMessage(wavBase64));

        // 6. Reset UI to Idle
        isProcessing = false;
        UpdateUIState(false, false);
    }
    public async Task<string> TranscribeAudio(AudioClip clip)
    {
        if (clip == null || whisperManager == null) return "";

        LogService.Log("MicService: Sending to Whisper...");
        
        // Run Whisper
        WhisperResult result = await whisperManager.GetTextAsync(clip);

        // Output result
        DisplayService.AddTextEntry($"MicService Result: {result.Result}");
        
        // Assuming you have a DisplayService, otherwise delete this line:
        // DisplayService.AddTextEntry(result.Result); 

        return result.Result;
    }

    // --- Helpers ---

    private void UpdateUIState(bool recording, bool processing)
    {
        if (processing)
        {
            RecordingButtonText.text = "Thinking...";
            RecordingButtonText.color = ConfigService.COLOR_TEXT;
            RecordingButtonBackground.color = ConfigService.COLOR_PRIMARY;
        }
        else if (recording)
        {
            RecordingButtonText.text = "Stop";
            RecordingButtonText.color = ConfigService.COLOR_PRIMARY; 
            RecordingButtonBackground.color = ConfigService.COLOR_ERROR;
        }
        else
        {
            RecordingButtonText.text = "Record";
            RecordingButtonText.color = ConfigService.COLOR_TEXT;
            RecordingButtonBackground.color = ConfigService.COLOR_SECONDARY;
        }
    }

    private AudioClip TrimSilence(AudioClip original, int endPosition)
    {
        // Safety check if endPosition is 0 (happens if instant click)
        if (endPosition == 0) endPosition = 1; 

        float[] samples = new float[endPosition * original.channels];
        original.GetData(samples, 0);

        AudioClip trimmed = AudioClip.Create("TrimmedClip", endPosition, original.channels, original.frequency, false);
        trimmed.SetData(samples, 0);

        return trimmed;
    }

    [ContextMenu("Test Send transcription")]
    public void TestSendTranscription()
    {
        SocketService.SendSocketMessage(new SocketHeadsetToPiMessage("Questa è una trascrizione di prova di MicService."));
    }
}