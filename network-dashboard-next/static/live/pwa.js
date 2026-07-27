import { api } from "/assets/api.js";

let installPrompt = null;

function decodeBase64Url(value) {
  const padding = "=".repeat((4 - value.length % 4) % 4);
  const base64 = (value + padding).replaceAll("-", "+").replaceAll("_", "/");
  const binary = atob(base64);
  return Uint8Array.from(binary, character => character.charCodeAt(0));
}

async function registration() {
  if (!("serviceWorker" in navigator)) throw new Error("Service Worker stöds inte i denna webbläsare");
  await navigator.serviceWorker.register("/sw.js", { scope: "/" });
  return navigator.serviceWorker.ready;
}

async function status() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
    return { supported: false, subscribed: false, permission: "unsupported", readOnly: false };
  }
  const [worker, home] = await Promise.all([
    registration(),
    api("/api/v2/home/summary"),
  ]);
  const subscription = await worker.pushManager.getSubscription();
  return {
    supported: true,
    subscribed: Boolean(subscription),
    permission: Notification.permission,
    endpoint: subscription?.endpoint || "",
    readOnly: Boolean(home.runtime?.read_only),
  };
}

async function subscribe() {
  if (!("PushManager" in window)) throw new Error("Pushnotiser stöds inte i denna webbläsare");
  const current = await status();
  if (current.readOnly) throw new Error("Aviseringar kan aktiveras när Next lämnar skrivskyddat parallelläge");
  const key = await api("/api/v2/notifications/public-key");
  if (!key.public_key) throw new Error("VAPID-nyckel saknas i servern");
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Tillåtelse för aviseringar gavs inte");
  const worker = await registration();
  let subscription = await worker.pushManager.getSubscription();
  if (!subscription) {
    subscription = await worker.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: decodeBase64Url(key.public_key),
    });
  }
  await api("/api/v2/notifications/subscriptions", {
    method: "POST",
    body: { subscription: subscription.toJSON() },
  });
  return status();
}

async function unsubscribe() {
  const current = await status();
  if (current.readOnly) throw new Error("Aviseringar kan ändras när Next lämnar skrivskyddat parallelläge");
  const worker = await registration();
  const subscription = await worker.pushManager.getSubscription();
  if (!subscription) return current;
  const endpoint = subscription.endpoint;
  await api(`/api/v2/notifications/subscriptions?endpoint=${encodeURIComponent(endpoint)}`, { method: "DELETE" });
  await subscription.unsubscribe();
  return status();
}

function emitNotice(message, tone = "good") {
  const target = document.querySelector("#app-notice");
  if (target) {
    target.innerHTML = `<span class="badge badge--${tone}">${String(message).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")}</span>`;
    window.setTimeout(() => { target.innerHTML = ""; }, 5200);
  }
  window.dispatchEvent(new CustomEvent("lindells:notice", { detail: { message, tone } }));
}

async function refreshPushControl() {
  const control = document.querySelector("#push-control");
  if (!control) return;
  control.disabled = true;
  try {
    const current = await status();
    control.dataset.subscribed = String(current.subscribed);
    if (current.readOnly) {
      control.innerHTML = `Aviseringar efter aktivering <span>—</span>`;
      control.title = "Pushprenumerationer sparas inte i skrivskyddat parallelläge";
      return;
    }
    control.innerHTML = current.supported
      ? `${current.subscribed ? "Stäng av aviseringar" : "Aktivera aviseringar"} <span>›</span>`
      : `Aviseringar stöds inte <span>—</span>`;
    control.disabled = !current.supported;
  } catch {
    control.innerHTML = `Aviseringar kunde inte kontrolleras <span>—</span>`;
    control.disabled = true;
  }
}

function installControls() {
  const menu = document.querySelector(".profile-menu");
  if (!menu || document.querySelector("#push-control")) return;
  const statusPanel = menu.querySelector(".status-panel");
  const push = document.createElement("button");
  push.id = "push-control";
  push.type = "button";
  push.innerHTML = `Kontrollerar aviseringar… <span>…</span>`;
  push.addEventListener("click", async () => {
    push.disabled = true;
    try {
      const current = await status();
      await (current.subscribed ? unsubscribe() : subscribe());
      emitNotice(current.subscribed ? "Aviseringar stängdes av på denna enhet" : "Aviseringar aktiverades på denna enhet");
    } catch (error) {
      emitNotice(error.message || "Aviseringarna kunde inte ändras", "danger");
    } finally {
      await refreshPushControl();
    }
  });
  statusPanel?.insertAdjacentElement("afterend", push);

  const install = document.createElement("button");
  install.id = "install-control";
  install.type = "button";
  install.hidden = !installPrompt;
  install.innerHTML = `Installera appen <span>›</span>`;
  install.addEventListener("click", async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;
    install.hidden = true;
  });
  push.insertAdjacentElement("afterend", install);
  refreshPushControl();
}

window.addEventListener("beforeinstallprompt", event => {
  event.preventDefault();
  installPrompt = event;
  const install = document.querySelector("#install-control");
  if (install) install.hidden = false;
});

window.addEventListener("appinstalled", () => {
  installPrompt = null;
  const install = document.querySelector("#install-control");
  if (install) install.hidden = true;
  emitNotice("Lindells app installerades");
});

window.lindellsPwa = { registration, status, subscribe, unsubscribe };
installControls();
registration()
  .then(() => window.dispatchEvent(new CustomEvent("lindells:pwa-ready")))
  .catch(error => console.warn("PWA registration failed", error));
