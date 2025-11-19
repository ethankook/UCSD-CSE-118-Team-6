# activate venv
source .venv/bin/activate

# run the server
uvicorn main:app --reload

# go to
http://localhost:8000/

in dev console paste:

```
const ws1 = new WebSocket("ws://localhost:8000/ws");

ws1.onopen = () => {
  console.log("ws1 connected");
  ws1.send(JSON.stringify({ type: "set_lang", lang: "es" })); // Spanish
};

ws1.onmessage = (event) => {
  console.log("ws1 from server:", event.data);
};

ws1.onclose = () => {
  console.log("ws1 closed");
};
```

separate dev console: 
```
const ws2 = new WebSocket("ws://localhost:8000/ws");

ws2.onopen = () => {
  console.log("ws2 connected");
  ws2.send(JSON.stringify({ type: "set_lang", lang: "zh" })); // Chinese
};

ws2.onmessage = (event) => {
  console.log("ws2 from server:", event.data);
};

ws2.onclose = () => {
  console.log("ws2 closed");
};
```

Server console should show both websockets joining and the total increasing. It should also show the client language being updated since we send a set_lang request to the server.


Amazon translate is not included in aws free tier, so we will ahve to use another free translation api like DeepL.