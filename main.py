import streamlit as st

MODEL_ID  = "6_YbLoW0i"                 
DEVICE_ID = "robotcar_umk1"             
BROKER_WS = "wss://test.mosquitto.org:8081/mqtt"
TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"

st.set_page_config(page_title="TM Audio (Speech Commands) → ESP32", layout="centered")
st.title("🎤 Teachable Machine Audio → ESP32 Robot Car")
st.caption("Click Start Listening to recognize your trained voice commands and send class label (F/B/L/R/S) to MQTT.")

html = """
<div style="font-family:system-ui,Segoe UI,Roboto,Arial">
  <button id="toggle" style="padding:10px 16px;border-radius:10px;">Start Listening</button>
  <div id="status" style="margin:10px 0;font-weight:600;">Idle</div>
  <div id="label" style="margin-top:12px;font-size:36px;font-weight:900;">—</div>
  <div style="margin-top:8px;font-size:12px;opacity:.7;">
    Publishes to <code>{topic}</code> on <code>{broker}</code>
  </div>
</div>

<!-- TensorFlow.js + Speech Commands -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@1.3.1/dist/tf.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@tensorflow-models/speech-commands@0.4.0/dist/speech-commands.min.js"></script>

<!-- MQTT.js -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<script>
const MODEL_URL = "https://teachablemachine.withgoogle.com/models/{model_id}/";
const MQTT_URL  = "{broker}";
const TOPIC     = "{topic}";
const PROB_THRESHOLD = 0.75;
let recognizer = null;
let listening = false;
let mqttClient = null;
let lastLabel = "";
let lastSent = 0;
const INTERVAL_MS = 1000;

// === MQTT ===
function mqttConnect() {{
  if (mqttClient && mqttClient.connected) return;
  document.getElementById("status").innerText = "Connecting MQTT…";
  mqttClient = mqtt.connect(MQTT_URL, {{
    clientId: "tm-speech-" + Math.random().toString(16).slice(2,10),
    clean: true,
    reconnectPeriod: 2000
  }});
  mqttClient.on("connect", () => setStatus("MQTT connected ✔️"));
  mqttClient.on("reconnect", () => setStatus("Reconnecting MQTT…"));
  mqttClient.on("error", e => setStatus("MQTT error: " + e.message));
}}

function mqttPublish(label) {{
  if (!mqttClient || !mqttClient.connected) return;
  mqttClient.publish(TOPIC, label, {{ qos: 0, retain: false }});
  console.log("Published", label);
}}

function setStatus(msg) {{
  document.getElementById("status").innerText = msg;
  console.log("[status]", msg);
}}

function setButton() {{
  const btn = document.getElementById("toggle");
  btn.textContent = listening ? "Stop Listening" : "Start Listening";
  btn.style.background = listening ? "#c62828" : "#2e7d32";
  btn.style.color = "white";
}}

async function createModel() {{
  const checkpointURL = MODEL_URL + "model.json";
  const metadataURL = MODEL_URL + "metadata.json";
  recognizer = speechCommands.create("BROWSER_FFT", undefined, checkpointURL, metadataURL);
  await recognizer.ensureModelLoaded();
  setStatus("Model loaded");
}}

async function startListening() {{
  mqttConnect();
  if (!recognizer) await createModel();
  const labels = recognizer.wordLabels();
  setStatus("Listening… (allow microphone)");
  listening = true;
  setButton();

  recognizer.listen(result => {{
    const scores = result.scores;
    let topIndex = 0;
    for (let i = 1; i < scores.length; i++) {{
      if (scores[i] > scores[topIndex]) topIndex = i;
    }}
    const label = labels[topIndex].trim().toUpperCase();
    const prob = scores[topIndex];
    document.getElementById("label").innerText = label + " (" + prob.toFixed(2) + ")";
    maybePublish(label, prob);
  }}, {{
    includeSpectrogram: false,
    probabilityThreshold: PROB_THRESHOLD,
    overlapFactor: 0.5
  }});
}}

function maybePublish(label, prob) {{
  const now = Date.now();
  if (prob < PROB_THRESHOLD) return;
  if (label !== lastLabel || now - lastSent > INTERVAL_MS) {{
    mqttPublish(label);
    setStatus("Sent: " + label);
    lastLabel = label;
    lastSent = now;
  }}
}}

function stopListening() {{
  if (!listening) return;
  recognizer.stopListening();
  listening = false;
  setButton();
  setStatus("Stopped (MQTT still connected)");
}}

document.getElementById("toggle").addEventListener("click", () => {{
  if (listening) stopListening();
  else startListening();
}});
</script>
""".format(model_id=MODEL_ID, broker=BROKER_WS, topic=TOPIC_CMD)

st.components.v1.html(html, height=420)
