const CACHE_NAME = "lindells-next-shell-v2";
const SHELL = [
  "/",
  "/assets/app.css",
  "/assets/api.js",
  "/assets/ui.js",
  "/live/app.js",
  "/live/pwa.js",
  "/manifest.webmanifest",
  "/app-icon.svg",
];

async function cacheShell() {
  const cache = await caches.open(CACHE_NAME);
  await Promise.allSettled(SHELL.map(async path => {
    const response = await fetch(path, { cache: "reload", credentials: "same-origin" });
    if (response.ok) await cache.put(path, response);
  }));
}

self.addEventListener("install", event => {
  event.waitUntil(cacheShell().then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

function isPrivateRequest(url) {
  return url.pathname.startsWith("/api/")
    || url.pathname.startsWith("/login")
    || url.pathname.startsWith("/logout")
    || url.pathname.startsWith("/choose-user")
    || url.pathname.startsWith("/preview-v2");
}

function isStaticAsset(url) {
  return url.pathname.startsWith("/assets/")
    || url.pathname.startsWith("/live/")
    || url.pathname === "/manifest.webmanifest"
    || url.pathname === "/app-icon.svg";
}

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || isPrivateRequest(url)) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request, { cache: "no-store" })
        .then(response => {
          if (response.ok && url.pathname === "/") {
            const copy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put("/", copy));
          }
          return response;
        })
        .catch(async () => (await caches.match("/")) || Response.error())
    );
    return;
  }

  if (!isStaticAsset(url)) return;
  event.respondWith(
    caches.match(request).then(cached => {
      const network = fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
        }
        return response;
      });
      return cached || network;
    })
  );
});

self.addEventListener("push", event => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    payload = { body: event.data ? event.data.text() : "Ny avisering" };
  }
  const title = String(payload.title || "Lindells app");
  const options = {
    body: String(payload.body || payload.message || "Ny avisering"),
    icon: "/app-icon.svg",
    badge: "/app-icon.svg",
    tag: String(payload.tag || payload.type || "lindells-notification"),
    renotify: false,
    data: { url: String(payload.url || "/#more") },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", event => {
  event.notification.close();
  const target = new URL(event.notification.data?.url || "/#more", self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(clients => {
      const existing = clients.find(client => new URL(client.url).origin === self.location.origin);
      if (existing) {
        existing.navigate(target);
        return existing.focus();
      }
      return self.clients.openWindow(target);
    })
  );
});
