export class ApiError extends Error {
  constructor(message, status = 0, payload = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

const inflight = new Map();

function keyFor(path, options) {
  const method = (options.method || "GET").toUpperCase();
  return method === "GET" ? path : "";
}

export async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const requestKey = keyFor(path, options);
  if (requestKey && inflight.has(requestKey)) return inflight.get(requestKey);

  const run = async () => {
    const headers = new Headers(options.headers || {});
    headers.set("Accept", "application/json");
    if (options.body !== undefined && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
    if (method !== "GET" && method !== "HEAD") {
      headers.set("X-Requested-With", "network-dashboard-next");
    }

    const response = await fetch(path, {
      credentials: "same-origin",
      cache: "no-store",
      ...options,
      method,
      headers,
      body: options.body === undefined || options.body instanceof FormData
        ? options.body
        : JSON.stringify(options.body),
    });

    const text = await response.text();
    let payload = null;
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = { message: text };
      }
    }
    if (!response.ok) {
      const detail = payload?.detail || payload?.error?.message || payload?.message;
      throw new ApiError(detail || `Anropet misslyckades (${response.status})`, response.status, payload);
    }
    return payload;
  };

  const promise = run().finally(() => {
    if (requestKey) inflight.delete(requestKey);
  });
  if (requestKey) inflight.set(requestKey, promise);
  return promise;
}

export function query(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  });
  return `${url.pathname}${url.search}`;
}

export async function accessControl() {
  return api("/api/access-control");
}
