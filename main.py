import streamlit as st

# ========= CONFIG =========
MODEL_ID  = "6_YbLoW0i"                 # your Teachable Machine AUDIO model id
DEVICE_ID = "robotcar_umk1"             # must match ESP code
BROKER_WS = "wss://test.mosquitto.org:8081/mqtt"
TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"
SEND_INTERVAL_MS = 1000                 # throttle MQTT publishes (ms)
# ==========================

st.set_page_config(page_title="TM Audio → ESP32 via MQTT", layout="centered")
st.title("🎤 Teachable Machine (Audio) → ESP32 Robot Car")
st.caption("Click Start Listening to classify audio in the browser and send only the class label (F/B/L/R/S) to MQTT.")

html = f"""
<div style="font-family:system-ui,Segoe UI,Roboto,Arial">
  <button id="toggle" style="padding:10px 16px;border-radius:10px;">Start Listening</button>
  <div id="status" style="margin:10px 0;font-weight:600;">Idle</div>
  <div id="label" style="margin-top:12px;font-size:44px;font-weight:900;">—</div>
  <div style="margin-top:8px;font-size:12px;opacity:.7;">
    Publishes to <code>{TOPIC_CMD}</code> on <code>{BROKER_WS}</code>
  </div>
</div>

<!-- TF.js and Teachable Machine Audio -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4"></script>
<script src="https://cdn.jsdelivr.net/npm/@teachablemachine/audio@0.8/dist/teachablemachine-audio.min.js"
        onload="window.tmAudio = window.tmAudio || window.teachablemachine.audio;"></script>

<!-- MQTT.js -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<script>
const MODEL_URL   = "https://teachablemachine.withgoogle.com/models/{MODEL_ID}/";
const MQTT_URL    = "{BROKER_WS}";
const TOPIC       = "{TOPIC_CMD}";
const INTERVAL_MS = {SEND_INTERVAL_MS};

let model = null;
let mic = null;
let mqttClient = null;
let listening = false;
let rafId = null;

let lastLabel = "";
let lastSent = 0;

function setStatus(s) {{
  const el = document.getElementById("status");
  if (el) el.textContent = s;
  console.log("[status]", s);
}}

function setButton() {{
  const b = document.getElementById("toggle");
  if (!b) return;
  b.textContent = listening ? "Stop Listening" : "Start Listening";
}}

function mqttConnect() {{
  if (mqttClient && mqttClient.connected) return;
  setStatus("Connecting MQTT…");
  mqttClient = mqtt.connect(MQTT_URL, {{
    clientId: "tm-audio-" + Math.random().toString(16).slice(2,10),
    clean: true,
    reconnectPeriod: 2000
  }});
  mqttClient.on("connect", () => setStatus("MQTT connected ✔️"));
  mqttClient.on("reconnect", () => setStatus("Reconnecting MQTT…"));
  mqttClient.on("error", (e) => setStatus("MQTT error: " + e.message));
}}

function mqttDisconnect() {{
  if (mqttClient) {{
    try {{ mqttClient.end(true); }} catch (_) {{}}
    mqttClient = null;
  }}
}}

async function ensureModel() {{
  // Wait for tmAudio to be available
  if (!window.tmAudio) {{
    setStatus("Loading audio runtime…");
    await new Promise(resolve => {{
      const check = setInterval(() => {{
        if (window.tmAudio) {{ clearInterval(check); resolve(); }}
      }}, 150);
    }});
  }}
  if (!model) {{
    setStatus("Loading audio model…");
    const modelURL = MODEL_URL + "model.json";
    const metadataURL = MODEL_URL + "metadata.json";
    model = await window.tmAudio.load(modelURL, metadataURL);
  }}
}}

async function startListening() {{
  if (listening) return;
  try {{
    await ensureModel();

    if (!mic) {{
      setStatus("Requesting microphone…");
      mic = new window.tmAudio.Microphone();
      await mic.setup();
    }}
    await mic.play();

    mqttConnect();
    listening = true;
    setButton();
    setStatus("Listening…");
    loop();
  }} catch (err) {{
    console.error(err);
    setStatus("Init error: " + err.message);
  }}
}}

function stopListening() {{
  listening = false;
  setButton();
  if (rafId) cancelAnimationFrame(rafId);
  if (mic) {{ try {{ mic.stop(); }} catch(_) {{}} }}
  mqttDisconnect();
  setStatus("Stopped");
}}

async function loop() {{
  if (!listening) return;
  try {{
    const preds = await model.predict(mic);
    preds.sort((a,b)=>b.probability-a.probability);
    const label = (preds[0].className || "").trim().toUpperCase(); // e.g., "F"
    document.getElementById("label").textContent = label || "—";
    maybePublish(label);
  }} catch (e) {{
    console.error("predict error", e);
  }}
  rafId = requestAnimationFrame(loop);
}}

function maybePublish(label) {{
  if (!label) return;
  if (!mqttClient || !mqttClient.connected) return;
  const now = Date.now();
  if (label !== lastLabel || now - lastSent > INTERVAL_MS) {{
    mqttClient.publish(TOPIC, label, {{ qos: 0, retain: false }});
    setStatus("Sent: " + label);
    lastLabel = label;
    lastSent = now;
  }}
}}

document.getElementById("toggle").addEventListener("click", () => {{
  if (listening) stopListening();
  else startListening();
}});
</script>
"""

st.components.v1.html(html, height=420)
