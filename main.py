import streamlit as st

# ========= CONFIG =========
MODEL_ID  = "6_YbLoW0i"                 # <-- your Teachable Machine audio model id
DEVICE_ID = "robotcar_umk1"             # must match your ESP code
BROKER_WS = "wss://test.mosquitto.org:8081/mqtt"
TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"
SEND_INTERVAL_MS = 1000                 # 1s interval to avoid flooding MQTT
# ==========================

st.set_page_config(page_title="Audio TM → ESP32 via MQTT", layout="centered")
st.title("🎤 Teachable Machine (Audio) → ESP32 Robot Car")
st.caption("Listens to your voice using Teachable Machine Audio Model and publishes class labels (F/B/L/R/S) to MQTT.")

html = f"""
<div style="font-family:system-ui,Segoe UI,Roboto,Arial">
  <button id="start" style="padding:10px 16px;border-radius:10px;">Start Listening</button>
  <div id="status" style="margin:10px 0;font-weight:600;">Idle</div>
  <div id="label" style="margin-top:12px;font-size:22px;font-weight:700;"></div>
  <div style="margin-top:8px;font-size:12px;opacity:.7;">
    Publishing raw class to <code>{TOPIC_CMD}</code> on <code>{BROKER_WS}</code>
  </div>
</div>

<!-- TensorFlow.js + Teachable Machine Audio -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4"></script>
<script src="https://cdn.jsdelivr.net/npm/@teachablemachine/audio@0.8/dist/teachablemachine-audio.min.js"></script>

<!-- MQTT.js -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<script>
const MODEL_URL = "https://teachablemachine.withgoogle.com/models/{MODEL_ID}/";
const MQTT_URL  = "{BROKER_WS}";
const TOPIC     = "{TOPIC_CMD}";
const INTERVAL_MS = {SEND_INTERVAL_MS};

let model, microphone;
let mqttClient = null;
let lastLabel = "";
let lastSent = 0;

function setStatus(s) {{
  const el = document.getElementById("status");
  if (el) el.innerText = s;
}}

function mqttConnect() {{
  mqttClient = mqtt.connect(MQTT_URL, {{
    clientId: "tm-audio-" + Math.random().toString(16).slice(2,10),
    clean: true,
    reconnectPeriod: 2000
  }});
  mqttClient.on("connect", () => setStatus("MQTT connected ✔️"));
  mqttClient.on("reconnect", () => setStatus("Reconnecting MQTT..."));
  mqttClient.on("error", (e) => setStatus("MQTT error: " + e.message));
}}

async function init() {{
  setStatus("Loading audio model...");
  const modelURL = MODEL_URL + "model.json";
  const metadataURL = MODEL_URL + "metadata.json";
  model = await tmAudio.load(modelURL, metadataURL);
  setStatus("Initializing microphone...");
  microphone = new tmAudio.Microphone();
  await microphone.setup();
  await microphone.play();
  mqttConnect();
  setStatus("Listening...");
  window.requestAnimationFrame(loop);
}}

async function loop() {{
  const prediction = await model.predict(microphone);
  prediction.sort((a,b)=>b.probability-a.probability);
  const top = prediction[0];
  const label = top.className.trim().toUpperCase();
  const prob = top.probability.toFixed(3);
  document.getElementById("label").innerText = label + " (" + prob + ")";
  publishIfNeeded(label);
  window.requestAnimationFrame(loop);
}}

function publishIfNeeded(label) {{
  if (!mqttClient || !mqttClient.connected) return;
  const now = Date.now();
  if (label !== lastLabel || (now - lastSent) > INTERVAL_MS) {{
    mqttClient.publish(TOPIC, label);
    setStatus("Sent: " + label);
    lastLabel = label;
    lastSent = now;
    console.log("Published", label, "to", TOPIC);
  }}
}}

document.getElementById("start").addEventListener("click", init);
</script>
"""

st.components.v1.html(html, height=400)
