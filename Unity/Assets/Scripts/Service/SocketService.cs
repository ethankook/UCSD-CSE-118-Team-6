using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Text;
using System;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Net.Sockets;
using System.Threading.Tasks;
using System.Threading;

// A simple response wrapper
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
    static SocketService instance;

    private static ClientWebSocket socket;
    // Define supported methods
    public enum Method { GET, POST, PUT, DELETE }

    void Awake()
    {
        instance = this;
    }
    /// <summary>
    /// Sends an HTTP Request (REST Style)
    /// </summary>
    /// <param name="method">GET, POST, etc.</param>
    /// <param name="url">Target URL</param>
    /// <param name="queryParams">Dictionary of query parameters (optional)</param>
    /// <param name="bodyJson">JSON string for body (optional)</param>
    /// <param name="callback">Action to run when finished</param>
    public static void SendRequest(Method method, string url, Dictionary<string, string> queryParams, string bodyJson, Action<NetworkResponse> callback)
    {
        instance.StartCoroutine(instance.RequestRoutine(method, url, queryParams, bodyJson, callback));
    }

    private IEnumerator RequestRoutine(Method method, string url, Dictionary<string, string> queryParams, string bodyJson, Action<NetworkResponse> callback)
    {
        // 1. Construct Query String
        if (queryParams != null && queryParams.Count > 0)
        {
            url += "?";
            foreach (var param in queryParams)
            {
                url += $"{UnityWebRequest.EscapeURL(param.Key)}={UnityWebRequest.EscapeURL(param.Value)}&";
            }
            url = url.TrimEnd('&');
        }

        // 2. Create Request
        UnityWebRequest request = new UnityWebRequest(url, method.ToString());
        
        // 3. Attach Body (if exists and not GET)
        if (!string.IsNullOrEmpty(bodyJson) && method != Method.GET)
        {
            byte[] bodyRaw = Encoding.UTF8.GetBytes(bodyJson);
            request.uploadHandler = new UploadHandlerRaw(bodyRaw);
            request.SetRequestHeader("Content-Type", "application/json");
        }

        request.downloadHandler = new DownloadHandlerBuffer();

        LogService.Log($"Sending {method} request to {url}");
        
        // 4. Send and Wait
        yield return request.SendWebRequest();

        // 5. Handle Response
        NetworkResponse response = new NetworkResponse
        {
            statusCode = request.responseCode,
            data = request.downloadHandler.text,
            error = request.error
        };

        callback?.Invoke(response);
        request.Dispose();
    }

    // --- Placeholder for Future Socket.IO Implementation ---
    // If you need real-time streaming later, you would initialize your Socket.IO client here.
    public static async Task ConnectSocket(string socketURL) 
    {
        LogService.Log($"Connect to socket at {socketURL} ...");
        socket = new ClientWebSocket();
        try
        {
            Uri uri = new Uri(socketURL);
            await socket.ConnectAsync(uri, System.Threading.CancellationToken.None);
            LogService.Log("Socket connected!");
            await ReceiveLoop();
        }
        catch (Exception ex)
        {
            LogService.Log($"Socket connection error: {ex.Message}");
        }
    }

private static async Task ReceiveLoop()
    {
        // Create a buffer to hold incoming data
        var buffer = new ArraySegment<byte>(new byte[2048]);

        while (socket.State == WebSocketState.Open)
        {
            // This line waits here until a message arrives
            WebSocketReceiveResult result = await socket.ReceiveAsync(buffer, CancellationToken.None);

            // If the server sends a Close request
            if (result.MessageType == WebSocketMessageType.Close)
            {
                // --- EVENT: ON CLOSE ---
                LogService.Log("Server closed the connection. (OnClose)");
                await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, CancellationToken.None);
            }
            else
            {
                // Decode the bytes into a string
                string message = Encoding.UTF8.GetString(buffer.Array, 0, result.Count);

                // --- EVENT: ON MESSAGE ---
                LogService.Log("Message Received: " + message);
                
                // Handle your JSON or logic here:
                // HandleMessage(message); 
            }
        }
    }
    
    public static void EmitSocketEvent(string eventName, string data)
    {
        LogService.Log($"TODO: Emit {eventName} with {data}");
    }

    void OnDestroy()
    {
        if (socket != null)
        {
            socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", System.Threading.CancellationToken.None);
        }
    }
}