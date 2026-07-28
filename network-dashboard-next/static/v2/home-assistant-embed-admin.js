import { api } from "/assets/api.js";
import { badge, emptyState, errorState, escapeHtml, skeleton } from "/assets/ui.js";

const content = document.querySelector("#v2-content");
const nav = document.querySelector("#v2-nav");
const notice = document.querySelector("#v2-notice");
let active = false;

function announce(message, tone = "good") {
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 6000);
}

function row(title, detail = "", end = "") {
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(title)}</strong>${detail ? `<span>${escapeHtml(detail)}</span>` : ""}</div>${end}</div>`;
}

function render(data) {
  const policy = data.policy || {};
  const status = data.ready ? badge("Redo", "good") : data.enabled ? badge("Kontrollera", "warning") : badge("Avstängd", "neutral");
  const preview = data.ready
    ? `<iframe class="home-assistant-embed-preview" src="${escapeHtml(data.frame_url)}" title="Home Assistant-förhandsvisning" loading="lazy" referrerpolicy="no-referrer" sandbox="allow-forms allow-modals allow-popups allow-same-origin allow-scripts" allow="fullscreen"></iframe><p class="helper">Om Home Assistant blockerar ramen behöver <code>use_x_frame_options</code> tillåta inbäddning. Ingen access-token läggs i iframe-adressen.</p>`
    : emptyState(
        data.enabled ? "Embed kan inte visas ännu" : "Embed är avstängd",
        data.error || (data.base_configured ? "Aktivera inställningen för att visa adminförhandsvisningen." : "Spara först Home Assistant-adressen under Integrationer."),
      );

  content.innerHTML = `<section class="hero"><p class="eyebrow">Home Assistant · admin</p><h2>Kontrollerad embed-förhandsvisning</h2><p>Administratören kan välja en relativ dashboard-sökväg och testa den i en sandboxad iframe. Familje-API:t får varken ramadress eller credentialvärden.</p><div class="stats"><div class="stat"><strong>${data.enabled ? "På" : "Av"}</strong><span>Embed</span></div><div class="stat"><strong>${data.base_configured ? "Ja" : "Nej"}</strong><span>Basadress</span></div><div class="stat"><strong>${data.ready ? "Redo" : "Ej redo"}</strong><span>Förhandsvisning</span></div></div></section>
  <div class="grid">
    <section class="card"><div class="card__header"><div><p class="eyebrow">Inställning</p><h2>Dashboard-sökväg</h2></div>${status}</div><form class="form" data-ha-embed-form><label class="field"><span>Relativ sökväg</span><input name="path" value="${escapeHtml(data.path || "/lovelace")}" placeholder="/lovelace/default_view" required></label><label class="check"><input type="checkbox" name="enabled"${data.enabled ? " checked" : ""}> Aktivera adminförhandsvisning</label><p class="helper">Endast relativa sökvägar accepteras. Basadressen hämtas från den skyddade integrationskonfigurationen.</p><div class="form__actions"><button class="button button--primary">Spara embed-inställning</button></div></form></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Skyddsgränser</p><h2>Exponering</h2></div></div><div class="list">${row("Admin-only", policy.admin_only ? "Ja" : "Nej", badge(policy.admin_only ? "Skyddat" : "Varning", policy.admin_only ? "good" : "danger"))}${row("URL i familje-API", policy.family_url_exposed ? "Exponerad" : "Dold", badge(policy.family_url_exposed ? "Varning" : "Dold", policy.family_url_exposed ? "danger" : "good"))}${row("Access-token", policy.access_token_exposed ? "Exponerad" : "Aldrig i ramen", badge(policy.access_token_exposed ? "Varning" : "Dold", policy.access_token_exposed ? "danger" : "good"))}${row("Sandbox", policy.sandboxed_preview ? "Aktiv" : "Saknas", badge(policy.sandboxed_preview ? "Aktiv" : "Varning", policy.sandboxed_preview ? "good" : "danger"))}</div></section>
    <section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Förhandsvisning</p><h2>Home Assistant-dashboard</h2></div></div>${preview}</section>
  </div>`;
}

async function load() {
  active = true;
  nav.querySelectorAll("button").forEach(button => button.classList.toggle("active", button.dataset.haEmbedView === "true"));
  content.innerHTML = skeleton(5);
  try {
    render(await api("/api/v2/admin/home-assistant-embed/overview"));
  } catch (error) {
    content.innerHTML = errorState(error);
  }
}

async function handleSubmit(event) {
  const form = event.target.closest("form[data-ha-embed-form]");
  if (!form || !active) return;
  event.preventDefault();
  const values = Object.fromEntries(new FormData(form).entries());
  if (!window.confirm("Spara Home Assistant-embedinställningen i Next-databasen?")) return;
  try {
    const result = await api("/api/v2/admin/home-assistant-embed/settings", {
      method: "PUT",
      body: { enabled: Boolean(values.enabled), path: values.path, confirm: true },
    });
    announce("Embed-inställningen sparades");
    render(result);
  } catch (error) {
    announce(error.message || "Embed-inställningen kunde inte sparas", "danger");
  }
}

function installNav() {
  if (nav.querySelector("[data-ha-embed-view]")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.haEmbedView = "true";
  button.textContent = "HA Embed";
  button.addEventListener("click", load);
  nav.append(button);
}

nav.addEventListener("click", event => {
  if (event.target.closest("[data-view], [data-operations-view], [data-network-view], [data-assistant-admin-view]")) active = false;
});
content.addEventListener("submit", handleSubmit);

const observer = new MutationObserver(installNav);
observer.observe(nav, { childList: true });
installNav();
