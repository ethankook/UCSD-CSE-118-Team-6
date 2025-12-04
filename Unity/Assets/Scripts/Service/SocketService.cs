using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Text;
using System;
using System.Collections.Generic;
using System.Net.WebSockets; // Standard .NET Socket
using System.Threading;
using System.Threading.Tasks;
using System.Collections.Concurrent;
using System.Net.Sockets; // Thread-safe queue

// Wrapper for REST responses
[Serializable]
public class NetworkResponse
{
    public long statusCode;
    public string data;
    public string error;
    public bool isSuccess => statusCode >= 200 && statusCode < 300 && string.IsNullOrEmpty(error);
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

            // set the language after connecting
            var setLangMessage = new SocketSetLangMessage(ConfigService.Preferred_Language_Code);
            string langJson = JsonUtility.ToJson(setLangMessage);
            byte[] langBytes = Encoding.UTF8.GetBytes(langJson);
            try 
            {
                await websocket.SendAsync(
                    new ArraySegment<byte>(langBytes), 
                    WebSocketMessageType.Text, 
                    true, 
                    cancellationTokenSource.Token
                );
                LogService.Log($"Sent Preferred Language: {ConfigService.Preferred_Language_Code}");
            }
            catch (Exception e)
            {
                LogService.LogError($"Send Language Error: {e.Message}");
            }

            // Start listening in background
            _ = ReceiveLoop(); 
        }
        catch (Exception e)
        {
            LogService.LogError($"Connection Error: {e.Message}");
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
                    _executionQueue.Enqueue(() => LogService.LogWarning("Socket Closed by Server"));
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
                _executionQueue.Enqueue(() => LogService.LogError($"Receive Error: {e.Message}"));
            }
        }
    }

    private void HandleMessage(string jsonMessage)
    {
        try 
        {
            SocketMessage data = SocketMessage.FromJson(jsonMessage);

            if (data.type == SocketMessageType.heartbeat)
            {
                // Optional: Log heartbeat
                LogService.Log(data.display_text);
            }
            else if (data.type == SocketMessageType.chat)
            {
                DisplayService.AddTextEntry(data.display_text);
            }
            else
            {
                LogService.LogError($"Unknown message type: {data}");
            }
        }
        catch (Exception e)
        {
            LogService.LogError($"JSON Error: {e.Message} | Raw: {jsonMessage}");
        }
    }

    public static async void EmitSocketEvent(string type, string text)
    {
        if (instance.websocket != null && instance.websocket.State == WebSocketState.Open)
        {
            var payload = new SocketMessage
            (
                type: SocketMessageType.chat,
                sourceId: "client",
                targetId: "server",
                sourceLang: "en",
                targetLang: "es",
                originalText: text,
                translatedText: "",
                displayText: text,
                time: Time.time
            );
            string json = payload.ToJson();
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
                LogService.LogError($"Send Error: {e.Message}");
            }
        }
        else
        {
            LogService.LogError("Cannot emit: Socket not connected.");
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