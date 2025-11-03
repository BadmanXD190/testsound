import streamlit as st

# ========= CONFIG =========
MODEL_ID  = "6_YbLoW0i"                 # your Teachable Machine AUDIO model id
DEVICE_ID = "robotcar_umk1"             # must match ESP code
BROKER_WS = "wss://test.mosquitto.org:8081/mqtt"
TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"
SEND_INTERVAL_MS = 1000                 # avoid flooding broker (1 msg/sec)
# ==========================

st.set_page_config(page_title="TM Audio → ESP32 via MQTT", layout="centered")
st.title("🎤 Teachable Machine (Audio) → ESP32 Robot Car")
st.caption("Predicts in the browser and publishes only the class label to MQTT.")

html = f"""
<div style="font-family:system-ui,Segoe UI,Roboto,Arial">
  <button id="start" style="padding:10px 16px;border-radius:10px;">Start Listening</button>
  <div id="status" style="margin:10px 0;font-weight:600;">Idle</div>
  <div id="label" style="margin-top:12px;font-size:28px;font-weight:800;"></div>
  <div style="margin-top:8px;font-size:12px;opacity:.7;">
    Publishing to <code>{TOPIC_CMD}</code> on <code>{BROKER_WS}</code>
  </div>
</div>

<!-- TF.js + Teachable Machine Audio -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4"></script>
<script src="https://cdn.jsdelivr.net/npm/@teachablemachine/audio@0.8/dist/teachablemachine-audio.min.js"></script>

<!-- MQTT.js -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<script>
const MODEL_URL = "https://teachablemachine.withgoogle.com/models/{MODEL_ID}/";
const MQTT_URL  = "{BROKER_WS}";
const TOPIC     = "{TOPIC_CMD}";
const INTERVAL_MS = {SEND_INTERVAL_MS};

let model, mic;
let mqttClient = null;
let lastLabel = "";
let lastSent = 0;

function setStatus(s) {{
  const el = document.getElementById("status");
  if (el) el.textContent = s;
  console.log("[status]", s);
}}

function mqttConnect() {{
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

async function init() {{
  try {{
    setStatus("Loading audio model…");
    const modelURL = MODEL_URL + "model.json";
    const metadataURL = MODEL_URL + "metadata.json";
    model = await tmAudio.load(modelURL, metadataURL);

    setStatus("Requesting microphone permission…");
    mic = new tmAudio.Microphone();
    await mic.setup();
    await mic.play();

    mqttConnect();
    setStatus("Listening…");
    window.requestAnimationFrame(loop);
  }} catch (err) {{
    setStatus("Init error: " + err.message);
    console.error(err);
  }}
}}

async function loop() {{
  try {{
    const preds = await model.predict(mic);
    preds.sort((a,b)=>b.probability-a.probability);
    const label = (preds[0].className || "").trim().toUpperCase(); // "F","B","L","R","S"
    document.getElementById("label").textContent = label;
    maybePublish(label);
  }} catch (e) {{
    console.error("predict error", e);
  }}
  window.requestAnimationFrame(loop);
}}

function maybePublish(label) {{
  if (!mqttClient || !mqttClient.connected) return;
  const now = Date.now();
  if (label && (label !== lastLabel || now - lastSent > INTERVAL_MS)) {{
    mqttClient.publish(TOPIC, label, {{ qos: 0, retain: false }}, (err) => {{
      if (err) setStatus("Publish error: " + err.message);
      else setStatus("Sent: " + label);
    }});
    lastLabel = label;
    lastSent = now;
    console.log("Published", label, "->", TOPIC);
  }}
}}

document.getElementById("start").addEventListener("click", init);
</script>
"""

st.components.v1.html(html, height=380)
