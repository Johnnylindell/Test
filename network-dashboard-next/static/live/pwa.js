import { api } from "/assets/api.js";

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
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    return { supported: false, subscribed: false, permission: Notification.permission || "unsupported" };
  }
  const worker = await registration();
  const subscription = await worker.pushManager.getSubscription();
  return {
    supported: true,
    subscribed: Boolean(subscription),
    permission: Notification.permission,
    endpoint: subscription?.endpoint || "",
  };
}

async function subscribe() {
  if (!("PushManager" in window)) throw new Error("Pushnotiser stöds inte i denna webbläsare");
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
  const worker = await registration();
  const subscription = await worker.pushManager.getSubscription();
  if (!subscription) return status();
  const endpoint = subscription.endpoint;
  await api(`/api/v2/notifications/subscriptions?endpoint=${encodeURIComponent(endpoint)}`, { method: "DELETE" });
  await subscription.unsubscribe();
  return status();
}

window.lindellsPwa = { registration, status, subscribe, unsubscribe };
registration()
  .then(() => window.dispatchEvent(new CustomEvent("lindells:pwa-ready")))
  .catch(error => console.warn("PWA registration failed", error));
