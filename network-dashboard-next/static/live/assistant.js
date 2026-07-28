import { api, query } from "/assets/api.js";
import { dateTime, emptyState, errorState, escapeHtml, skeleton } from "/assets/ui.js";

let dialog = null;
let thread = null;
let composer = null;
let readOnly = true;
let mediaRecorder = null;
let mediaStream = null;
let recordingTimer = null;

function ensureUi() {
  if (dialog) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "assistant-fab";
  button.setAttribute("aria-label", "Öppna familjeassistenten");
  button.innerHTML = "<span>✦</span><span>Fråga appen</span>";
  document.body.append(button);

  dialog = document.createElement("dialog");
  dialog.id = "assistant-dialog";
  dialog.className = "sheet sheet--assistant";
  dialog.innerHTML = `
    <form method="dialog" class="sheet__header">
      <div><p class="eyebrow">Lokal och bekräftelsestyrd</p><h2>Familjeassistent</h2></div>
      <button class="icon-button" value="cancel" aria-label="Stäng">×</button>
    </form>
    <div class="sheet__body">
      <div class="assistant-examples">
        <button type="button" data-assistant-example="Vad ska jag göra?">Vad är viktigast?</button>
        <button type="button" data-assistant-example="Var finns laddaren?">Hitta en sak</button>
        <button type="button" data-assistant-example="Lägg mjölk på inköpslistan">Lägg till inköp</button>
        <button type="button" data-assistant-example="Påminn mig om tandläkaren">Skapa påminnelse</button>
      </div>
      <div id="assistant-thread" class="assistant-thread" aria-live="polite"></div>
      <form id="assistant-composer" class="assistant-composer">
        <textarea name="message" required maxlength="500" placeholder="Fråga om appen eller föreslå en åtgärd…"></textarea>
        <button class="button" type="button" data-assistant-voice hidden aria-label="Diktera">🎙</button>
        <button class="button button--primary" data-assistant-send>Skicka</button>
      </form>
    </div>`;
  document.body.append(dialog);
  thread = dialog.querySelector("#assistant-thread");
  composer = dialog.querySelector("#assistant-composer");
  button.addEventListener("click", open);
  composer.addEventListener("submit", submit);
  dialog.addEventListener("click", handleClick);
  configureVoice();
  appendAssistant("Hej! Jag kan söka i familjeappen och föreslå säkra åtgärder. Inget skrivs utan att du bekräftar det.");
}

function showDialog() {
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

async function open() {
  ensureUi();
  showDialog();
  try {
    const home = await api("/api/v2/home/summary");
    readOnly = Boolean(home.runtime?.read_only);
  } catch {
    readOnly = true;
  }
  window.setTimeout(() => composer.querySelector("textarea")?.focus(), 50);
}

function appendUser(message) {
  thread.insertAdjacentHTML("beforeend", `<div class="assistant-message assistant-message--user"><p>${escapeHtml(message)}</p></div>`);
  thread.scrollTop = thread.scrollHeight;
}

function appendAssistant(message, extras = "") {
  thread.insertAdjacentHTML("beforeend", `<div class="assistant-message assistant-message--assistant"><p>${escapeHtml(message)}</p>${extras}</div>`);
  thread.scrollTop = thread.scrollHeight;
}

function renderResponse(result) {
  const results = (result.results || []).length
    ? `<div class="assistant-results">${result.results.map(item => `<button class="row" type="button" data-assistant-url="${escapeHtml(item.url || "/#home")}"><span class="row__main"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.detail || "")}</span></span><span>›</span></button>`).join("")}</div>`
    : "";
  const proposal = result.proposal
    ? `<div class="assistant-proposal"><strong>Föreslagen åtgärd</strong><small>${escapeHtml(result.proposal.description)} · giltig till ${escapeHtml(dateTime(result.proposal.expires_at))}</small><button class="button button--primary" type="button" data-assistant-confirm="${escapeHtml(result.proposal.token)}"${readOnly ? " disabled" : ""}>${readOnly ? "Bekräftelse efter aktivering" : "Bekräfta åtgärden"}</button></div>`
    : "";
  appendAssistant(result.reply || "Klart.", results + proposal);
}

async function submit(event) {
  event.preventDefault();
  const input = composer.querySelector("textarea");
  const message = input.value.trim();
  if (message.length < 2) return;
  input.value = "";
  appendUser(message);
  const pending = document.createElement("div");
  pending.className = "assistant-message assistant-message--assistant";
  pending.innerHTML = skeleton(1);
  thread.append(pending);
  thread.scrollTop = thread.scrollHeight;
  try {
    const result = await api(query("/api/v2/assistant/query", { q: message }));
    pending.remove();
    renderResponse(result);
  } catch (error) {
    pending.outerHTML = `<div class="assistant-message assistant-message--assistant">${errorState(error)}</div>`;
  }
}

async function confirmAction(token, button) {
  button.disabled = true;
  button.textContent = "Bekräftar…";
  try {
    const result = await api("/api/v2/assistant/confirm", { method: "POST", body: { token } });
    button.closest(".assistant-proposal")?.remove();
    appendAssistant(result.message || "Åtgärden är genomförd.");
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  } catch (error) {
    button.disabled = false;
    button.textContent = "Bekräfta åtgärden";
    appendAssistant(error.message || "Åtgärden kunde inte genomföras.");
  }
}

function handleClick(event) {
  const example = event.target.closest("[data-assistant-example]");
  if (example) {
    composer.querySelector("textarea").value = example.dataset.assistantExample;
    composer.requestSubmit();
    return;
  }
  const result = event.target.closest("[data-assistant-url]");
  if (result) {
    const target = new URL(result.dataset.assistantUrl, location.origin);
    if (typeof dialog.close === "function") dialog.close();
    location.hash = target.hash || "#home";
    return;
  }
  const confirmation = event.target.closest("[data-assistant-confirm]");
  if (confirmation) confirmAction(confirmation.dataset.assistantConfirm, confirmation);
}

function preferredMimeType() {
  if (!window.MediaRecorder) return "";
  return ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"]
    .find(type => MediaRecorder.isTypeSupported?.(type)) || "";
}

function stopMediaStream() {
  if (recordingTimer) window.clearTimeout(recordingTimer);
  recordingTimer = null;
  mediaStream?.getTracks().forEach(track => track.stop());
  mediaStream = null;
}

function resetVoiceButton(voice) {
  voice.disabled = false;
  voice.textContent = "🎙";
  voice.removeAttribute("data-recording");
  composer.querySelector("textarea")?.focus();
}

async function responseError(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.error?.message || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

async function transcribeRecording(blob, voice) {
  voice.disabled = true;
  voice.textContent = "…";
  const type = String(blob.type || "audio/webm").split(";", 1)[0];
  const extension = type === "audio/ogg" ? "ogg" : type === "audio/mp4" ? "m4a" : "webm";
  const body = new FormData();
  body.append("file", blob, `dictation.${extension}`);
  try {
    const response = await fetch("/api/v2/assistant/transcribe", {
      method: "POST",
      credentials: "same-origin",
      body,
    });
    if (!response.ok) throw new Error(await responseError(response));
    const result = await response.json();
    composer.querySelector("textarea").value = result.text || "";
    if (result.truncated) appendAssistant("Dikteringen var lång och kortades till assistentens maxlängd.");
  } catch (error) {
    appendAssistant(error.message || "Servertranskriberingen misslyckades.");
  } finally {
    resetVoiceButton(voice);
  }
}

async function toggleServerRecording(voice) {
  if (mediaRecorder?.state === "recording") {
    mediaRecorder.stop();
    return;
  }
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = preferredMimeType();
    mediaRecorder = mimeType
      ? new MediaRecorder(mediaStream, { mimeType })
      : new MediaRecorder(mediaStream);
    const chunks = [];
    mediaRecorder.addEventListener("dataavailable", event => {
      if (event.data?.size) chunks.push(event.data);
    });
    mediaRecorder.addEventListener("stop", () => {
      const blob = new Blob(chunks, { type: mediaRecorder.mimeType || mimeType || "audio/webm" });
      stopMediaStream();
      transcribeRecording(blob, voice);
    }, { once: true });
    mediaRecorder.addEventListener("error", () => {
      stopMediaStream();
      resetVoiceButton(voice);
      appendAssistant("Inspelningen kunde inte genomföras.");
    }, { once: true });
    mediaRecorder.start();
    voice.dataset.recording = "true";
    voice.textContent = "■";
    voice.title = "Stoppa inspelningen";
    recordingTimer = window.setTimeout(() => {
      if (mediaRecorder?.state === "recording") mediaRecorder.stop();
    }, 15000);
  } catch (error) {
    stopMediaStream();
    resetVoiceButton(voice);
    appendAssistant(error.message || "Mikrofonen kunde inte öppnas.");
  }
}

async function configureVoice() {
  const voice = dialog.querySelector("[data-assistant-voice]");
  if (!voice) return;
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let serverAvailable = false;
  try {
    const status = await api("/api/v2/assistant/transcription/status");
    serverAvailable = Boolean(status.available && window.MediaRecorder && navigator.mediaDevices?.getUserMedia);
  } catch {
    serverAvailable = false;
  }
  if (!Recognition && !serverAvailable) return;

  voice.hidden = false;
  voice.dataset.voiceMode = Recognition ? "browser" : "server";
  voice.title = Recognition ? "Diktera i webbläsaren" : "Spela in för lokal servertranskribering";

  let recognition = null;
  if (Recognition) {
    recognition = new Recognition();
    recognition.lang = "sv-SE";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.addEventListener("result", event => {
      composer.querySelector("textarea").value = event.results[0][0].transcript;
    });
    recognition.addEventListener("end", () => resetVoiceButton(voice));
    recognition.addEventListener("error", () => {
      resetVoiceButton(voice);
      if (serverAvailable) {
        voice.dataset.voiceMode = "server";
        voice.title = "Spela in för lokal servertranskribering";
        appendAssistant("Webbläsarens diktering fungerade inte. Mikrofonknappen använder nu den lokala serverfallbacken.");
      }
    });
  }

  voice.addEventListener("click", () => {
    if (voice.dataset.voiceMode === "server") {
      toggleServerRecording(voice);
      return;
    }
    voice.disabled = true;
    voice.textContent = "…";
    try {
      recognition.start();
    } catch {
      resetVoiceButton(voice);
    }
  });
}

ensureUi();
