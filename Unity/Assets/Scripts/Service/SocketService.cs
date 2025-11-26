using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Text;
using System;
using System.Collections.Generic;
using System.Net.WebSockets; // Standard .NET Socket
using System.Threading;
using System.Threading.Tasks;
using System.Collections.Concurrent; // Thread-safe queue

// Wrapper for REST responses
[Serializable]
public class NetworkResponse
{
    public long statusCode;
    public string data;
    public string error;
    public bool isSuccess => statusCode >= 200 && statusCode < 300 && string.IsNullOrEmpty(error);
}

// Wrapper for WebSocket messages
[Serializable]
public class SocketMessageData
{
    public string type;
    public string text;
    public string time;
    public string lang;

    public override string ToString()
    {
        return $"Type: {type}, Text: {text}, Time: {time}, Lang: {lang}";
    }
}

public class SocketService : MonoBehaviour
{
    public static SocketService instance;
    
    // Standard .NET WebSocket
    private ClientWebSocket websocket; 
    private CancellationTokenSource cancellationTokenSource;

    // Thread-safe queue to pass messages from Background Thread -> Main Thread
    private readonly ConcurrentQueue<Action> _executionQueue = new ConcurrentQueue<Action>();

    public enum Method { GET, POST, PUT, DELETE }

    void Awake()
    {
        if (instance != null && instance != this)
        {
            Destroy(this.gameObject);
            return;
        }
        instance = this;
        DontDestroyOnLoad(this.gameObject);
    }

    void Update()
    {
        // EXECUTE QUEUED ACTIONS ON MAIN THREAD
        // This replaces "DispatchMessageQueue" and prevents Quest crashes
        while (_executionQueue.TryDequeue(out Action action))
        {
            action.Invoke();
        }
    }

    // --- EXISTING REST METHOD ---
    public static void SendRequest(Method method, string url, Dictionary<string, string> queryParams, string bodyJson, Action<NetworkResponse> callback)
    {
        instance.StartCoroutine(instance.RequestRoutine(method, url, queryParams, bodyJson, callback));
    }

    private IEnumerator RequestRoutine(Method method, string url, Dictionary<string, string> queryParams, string bodyJson, Action<NetworkResponse> callback)
    {
        if (queryParams != null && queryParams.Count > 0)
        {
            url += "?";
            foreach (var param in queryParams)
                url += $"{UnityWebRequest.EscapeURL(param.Key)}={UnityWebRequest.EscapeURL(param.Value)}&";
            url = url.TrimEnd('&');
        }

        UnityWebRequest request = new UnityWebRequest(url, method.ToString());
        
        if (!string.IsNullOrEmpty(bodyJson) && method != Method.GET)
        {
            byte[] bodyRaw = Encoding.UTF8.GetBytes(bodyJson);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.SetRequestHeader("Content-Type", "application/json");
        }

        request.downloadHandler = new DownloadHandlerBuffer();
        
        yield return request.SendWebRequest();

        NetworkResponse response = new NetworkResponse
        {
            statusCode = request.responseCode,
            data = request.downloadHandler.text,
            error = request.error
        };

        callback?.Invoke(response);
        request.Dispose();
    }

    // --- NEW SOCKET IMPLEMENTATION (Standard .NET) ---

    public static async void ConnectSocket(string socketURL)
    {
        await instance.Connect(socketURL);
    }

    private async Task Connect(string url)
    {
        // Cleanup old connection
        if (websocket != null)
        {
            if (websocket.State == WebSocketState.Open)
                await websocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Restarting", CancellationToken.None);
            websocket.Dispose();
        }

        cancellationTokenSource = new CancellationTokenSource();
        websocket = new ClientWebSocket();

        try
        {
            LogService.Log($"Connecting to: {url}");
            await websocket.ConnectAsync(new Uri(url), cancellationTokenSource.Token);
            LogService.Log("Socket Connected!");

            // Start listening in background
            _ = ReceiveLoop(); 
        }
        catch (Exception e)
        {
            LogService.Log($"Connection Error: {e.Message}");
        }
    }

    private async Task ReceiveLoop()
    {
        var buffer = new byte[8192];

        try
        {
            while (websocket.State == WebSocketState.Open)
            {
                var result = await websocket.ReceiveAsync(new ArraySegment<byte>(buffer), cancellationTokenSource.Token);

                if (result.MessageType == WebSocketMessageType.Close)
                {
                    await websocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Server closed", CancellationToken.None);
                    // Queue log to main thread
                    _executionQueue.Enqueue(() => LogService.Log("Socket Closed by Server"));
                }
                else
                {
                    string message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    
                    // CRITICAL: Queue the data processing to run on the Main Thread
                    _executionQueue.Enqueue(() => HandleMessage(message));
                }
            }
        }
        catch (Exception e)
        {
            if (websocket.State != WebSocketState.Aborted)
            {
                _executionQueue.Enqueue(() => LogService.Log($"Receive Error: {e.Message}"));
            }
        }
    }

    private void HandleMessage(string jsonMessage)
    {
        try 
        {
            SocketMessageData data = JsonUtility.FromJson<SocketMessageData>(jsonMessage);

            if (data.type == "heartbeat")
            {
                // Optional: Log heartbeat
                LogService.Log($"{data}");
            }
            else if (data.type == "chat")
            {
                LogService.Log($"Chat Received: {data.text}");
                DisplayService.AddTextEntry(data.text);
            }
            else
            {
                LogService.Log($"{data}");
            }
        }
        catch (Exception e)
        {
            LogService.Log($"JSON Error: {e.Message} | Raw: {jsonMessage}");
        }
    }

    public static async void EmitSocketEvent(string type, string text)
    {
        if (instance.websocket != null && instance.websocket.State == WebSocketState.Open)
        {
            var payload = new SocketMessageData { type = type, text = text, lang = "en" };
            string json = JsonUtility.ToJson(payload);
            byte[] bytes = Encoding.UTF8.GetBytes(json);

            try 
            {
                await instance.websocket.SendAsync(
                    new ArraySegment<byte>(bytes), 
                    WebSocketMessageType.Text, 
                    true, 
                    instance.cancellationTokenSource.Token
                );
            }
            catch (Exception e)
            {
                LogService.Log($"Send Error: {e.Message}");
            }
        }
        else
        {
            LogService.Log("Cannot emit: Socket not connected.");
        }
    }

    private async void OnApplicationQuit()
    {
        if (websocket != null && websocket.State == WebSocketState.Open)
        {
            cancellationTokenSource?.Cancel();
            await websocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "App Quit", CancellationToken.None);
            websocket.Dispose();
        }
    }
}