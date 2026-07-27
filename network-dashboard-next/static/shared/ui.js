export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function money(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat("sv-FI", { style: "currency", currency: "EUR" }).format(number);
}

export function dateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return escapeHtml(value);
  return new Intl.DateTimeFormat("sv-FI", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function badge(text, tone = "neutral") {
  return `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(text)}</span>`;
}

export function emptyState(title, detail = "") {
  return `<section class="empty"><h3>${escapeHtml(title)}</h3>${detail ? `<p>${escapeHtml(detail)}</p>` : ""}</section>`;
}

export function errorState(error) {
  const message = error?.message || "Något gick fel.";
  return `<section class="empty empty--error"><h3>Kunde inte ladda</h3><p>${escapeHtml(message)}</p><button type="button" data-retry>Försök igen</button></section>`;
}

export function skeleton(rows = 4) {
  return `<div class="skeleton-list">${Array.from({ length: rows }, () => '<div class="skeleton"></div>').join("")}</div>`;
}

export function card(title, body, options = {}) {
  const eyebrow = options.eyebrow ? `<p class="eyebrow">${escapeHtml(options.eyebrow)}</p>` : "";
  const action = options.action || "";
  return `<article class="card">${eyebrow}<header class="card__header"><h2>${escapeHtml(title)}</h2>${action}</header>${body}</article>`;
}

export function renderInto(target, html) {
  const element = typeof target === "string" ? document.querySelector(target) : target;
  if (element) element.innerHTML = html;
}

export function on(target, eventName, selector, handler) {
  target.addEventListener(eventName, (event) => {
    const match = event.target.closest(selector);
    if (match && target.contains(match)) handler(event, match);
  });
}
