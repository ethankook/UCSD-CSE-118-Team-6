using UnityEngine;
using UnityEngine.Android; // Required for Quest Permissions
using System.Collections;
using System.Threading.Tasks;
using Whisper; // Assuming you are using the Whisper.unity package

public class MicService : MonoBehaviour
{
    static MicService instance;
    [Header("Dependencies")]
    public WhisperManager whisperManager; // Drag your WhisperManager prefab here

    [Header("Settings")]
    public int maxRecordingLength = 20; // Seconds
    public int sampleRate = 16000; // Whisper prefers 16k

    private AudioClip recordingClip;
    private string micDevice;
    private bool isRecording = false;

    void Awake()
    {
        instance = this;
    }
    private void Start()
    {
        // 1. CRITICAL: Request Microphone Permission on Quest/Android
        #if UNITY_ANDROID
        if (!Permission.HasUserAuthorizedPermission(Permission.Microphone))
        {
            Permission.RequestUserPermission(Permission.Microphone);
        }
        #endif

        // Get the first available microphone
        if (Microphone.devices.Length > 0)
            micDevice = Microphone.devices[0];
        else
            Debug.LogError("No Microphone Detected!");
    }

    // --- API Methods ---

    public static bool StartRecording()
    {
        if (string.IsNullOrEmpty(instance.micDevice)) return false;
        if (instance.isRecording) return false;

        // Start Unity Microphone (Loop = false to stop auto-overwrite)
        instance.recordingClip = Microphone.Start(instance.micDevice, false, instance.maxRecordingLength, instance.sampleRate);
        instance.isRecording = true;
        Debug.Log("Recording Started...");
        return true;
    }

    public static AudioClip StopRecording()
    {
        if (!instance.isRecording) return null;

        int position = Microphone.GetPosition(instance.micDevice);
        Microphone.End(instance.micDevice);
        instance.isRecording = false;

        if (instance.recordingClip == null) return null;

        // Critical: Trim the AudioClip to the actual spoken length
        // If we don't do this, Whisper processes 20 seconds of empty silence.
        AudioClip trimmedClip = instance.TrimSilence(instance.recordingClip, position);
        
        Debug.Log($"Recording Stopped. Raw: {instance.maxRecordingLength}s, Trimmed: {trimmedClip.length}s");
        return trimmedClip;
    }

    public static async Task<string> TranscribeAudio(AudioClip clip)
    {
        if (clip == null || instance.whisperManager == null) return "Error: Missing Clip or Whisper Manager";

        Debug.Log("Starting Local Transcription...");
        
        // Call the Whisper AI (Running locally on Quest CPU)
        WhisperResult result = await instance.whisperManager.GetTextAsync(clip);
        
        return result.Result;
    }

    // --- Helper: Trim Silence from the end of the buffer ---
    private AudioClip TrimSilence(AudioClip original, int endPosition)
    {
        if (endPosition <= 0) endPosition = original.samples;

        float[] samples = new float[endPosition * original.channels];
        original.GetData(samples, 0);

        AudioClip trimmed = AudioClip.Create("TrimmedClip", endPosition, original.channels, original.frequency, false);
        trimmed.SetData(samples, 0);

        return trimmed;
    }
}