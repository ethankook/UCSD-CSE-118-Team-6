# activate venv
source .venv/bin/activate

# run the server
uvicorn main:app --reload

# go to
http://localhost:8000/

in dev console paste:
A) start server
uvicorn main:app --reload

B) connect 2 “headsets”

Open browser console tab 1:

const ws1 = new WebSocket("ws://localhost:8000/ws");
ws1.onopen = () => ws1.send(JSON.stringify({ type: "set_lang", lang: "es" }));
ws1.onmessage = e => console.log("ws1:", e.data);


Open browser console tab 2:

const ws2 = new WebSocket("ws://localhost:8000/ws");
ws2.onopen = () => ws2.send(JSON.stringify({ type: "set_lang", lang: "zh" }));
ws2.onmessage = e => console.log("ws2:", e.data);


You should see:

Language set to es

Language set to zh

C) trigger translation

In another terminal:

curl -X POST http://localhost:8000/subtitle \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello everyone, welcome to the demo","source_lang":"en"}'


Expected:

ws1 console prints Spanish translation

ws2 console prints Chinese translation

If DeepL fails, you’ll see your fallback like:
[ES untranslated] Hello everyone...
