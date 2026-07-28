import { api } from "/assets/api.js";
import { badge, emptyState, errorState, escapeHtml, skeleton } from "/assets/ui.js";

const content = document.querySelector("#v2-content");
const notice = document.querySelector("#v2-notice");
let loading = false;

const SOURCE_LABELS = {
  next_secret_file: "Next-hemlighetsfil",
  legacy_database: "Gammal databas",
  missing: "Saknas",
};

function announce(message, tone = "good") {
  if (!notice) return;
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 5500);
}

function sourceLabel(source) {
  if (SOURCE_LABELS[source]) return SOURCE_LABELS[source];
  if (source?.startsWith("environment:")) return `Miljövariabel · ${source.split(":", 2)[1]}`;
  return source || "Saknas";
}

function sourceTone(variable) {
  if (!variable.configured) return "warning";
  if (variable.source === "next_secret_file") return "good";
  return "neutral";
}

function variableRow(variable) {
  const inputType = variable.secret ? "password" : "text";
  return `<section class="credential-row" data-config-key="${escapeHtml(variable.key)}">
    <div class="credential-row__summary">
      <div><strong>${escapeHtml(variable.label)}</strong><small>${escapeHtml(variable.help || "")}</small></div>
      <div class="credential-row__status">${badge(sourceLabel(variable.source), sourceTone(variable))}<code>${escapeHtml(variable.masked || "Inte konfigurerad")}</code></div>
    </div>
    <form class="credential-form" data-config-form="${escapeHtml(variable.key)}">
      <label class="field"><span>${variable.configured ? "Ersätt värde" : "Nytt värde"}</span><input type="${inputType}" name="value" autocomplete="new-password" placeholder="${variable.secret ? "Klistra in hemligheten" : "Ange värdet"}" required></label>
      <div class="form__actions"><button class="button button--primary">${variable.configured ? "Ersätt" : "Spara"}</button>${variable.source === "next_secret_file" ? `<button class="button button--danger" type="button" data-config-clear="${escapeHtml(variable.key)}">Rensa Next-värdet</button>` : ""}</div>
    </form>
  </section>`;
}

function groupHtml(group, variables) {
  const title = group === "home_assistant" ? "Home Assistant" : "Notifieringar";
  const detail = group === "home_assistant"
    ? "Den gamla appens home_assistant_url och home_assistant_token känns igen automatiskt."
    : "Discord och Web Push kan återanvändas från gammal databas eller anges här.";
  return `<section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Skyddade variabler</p><h2>${title}</h2></div>${badge(`${variables.filter(item => item.configured).length}/${variables.length}`, variables.every(item => item.configured) ? "good" : "warning")}</div><p>${detail}</p><div class="credential-list">${variables.map(variableRow).join("")}</div></section>`;
}

function googleHtml(google) {
  return `<section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Validerade JSON-filer</p><h2>Google Workspace</h2></div>${badge(google.authenticated ? "Ansluten" : google.status || "Ej ansluten", google.authenticated ? "good" : "warning")}</div>
    <p>Client secret och OAuth-token sparas som separata filer med rättighet 0600. Filinnehållet visas aldrig i gränssnittet.</p>
    <div class="integration-upload-grid">
      <form data-google-upload="client-secret" class="upload-panel"><strong>Google client secret</strong><small>${google.client_configured ? "Konfigurerad" : "Saknas"}</small><input type="file" name="file" accept="application/json,.json" required><button class="button button--primary">${google.client_configured ? "Ersätt fil" : "Ladda upp"}</button>${google.client_configured ? `<button type="button" class="button button--danger" data-google-delete="client-secret">Radera</button>` : ""}</form>
      <form data-google-upload="token" class="upload-panel"><strong>Google OAuth-token</strong><small>${google.token_configured ? "Konfigurerad" : "Saknas"}</small><input type="file" name="file" accept="application/json,.json" required><button class="button button--primary">${google.token_configured ? "Ersätt fil" : "Ladda upp"}</button>${google.token_configured ? `<button type="button" class="button button--danger" data-google-delete="token">Radera</button>` : ""}</form>
    </div>
    <p class="helper">Alternativt kan OAuth startas från Kalender & Tasks när externa sidoeffekter har aktiverats.</p>
  </section>`;
}

function toolsHtml(data) {
  const hasLegacy = (data.variables || []).some(variable => variable.source === "legacy_database");
  const hasVapid = (data.variables || []).some(variable => variable.key === "vapid_private_key" && variable.configured);
  return `<section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Säker setup</p><h2>Import och nyckelgenerering</h2></div>${badge(data.file_permissions || "Ingen fil ännu", data.file_permissions === "0o600" ? "good" : data.file_exists ? "warning" : "neutral")}</div>
    <div class="settings-tools">
      <div><strong>Adoptera gammal konfiguration</strong><p>Kopierar endast tillåtna värden från den isolerade databaskopian till Next-hemlighetsfilen. Gammal data ändras inte.</p><button class="button button--primary" type="button" data-adopt-legacy${hasLegacy ? "" : " disabled"}>Adoptera upptäckta värden</button></div>
      <form data-vapid-generate><strong>Generera Web Push-nycklar</strong><label class="field"><span>Kontakt</span><input name="subject" value="mailto:admin@localhost" required></label><label class="check"><input type="checkbox" name="replace"> Ersätt befintliga VAPID-nycklar</label><button class="button button--primary">${hasVapid ? "Generera nya nycklar" : "Generera nycklar"}</button></form>
    </div>
  </section>`;
}

function render(data) {
  const grid = content.querySelector(".grid");
  if (!grid) return;
  grid.querySelector("#integration-configuration")?.remove();
  const groups = Object.groupBy
    ? Object.groupBy(data.variables || [], item => item.group)
    : (data.variables || []).reduce((result, item) => {
        (result[item.group] ||= []).push(item);
        return result;
      }, {});
  const wrapper = document.createElement("div");
  wrapper.id = "integration-configuration";
  wrapper.className = "configuration-stack card--wide";
  wrapper.innerHTML = `${toolsHtml(data)}${Object.entries(groups).map(([group, variables]) => groupHtml(group, variables)).join("")}${googleHtml(data.google || {})}`;
  grid.append(wrapper);
  bind(wrapper);
}

async function responseError(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.error?.message || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

async function load() {
  if (loading || !location.hash.includes("integrations")) return;
  const grid = content.querySelector(".grid");
  if (!grid || grid.querySelector("#integration-configuration")) return;
  loading = true;
  const placeholder = document.createElement("section");
  placeholder.id = "integration-configuration";
  placeholder.className = "card card--wide";
  placeholder.innerHTML = skeleton(4);
  grid.append(placeholder);
  try {
    render(await api("/api/v2/admin/integrations/configuration"));
  } catch (error) {
    placeholder.innerHTML = errorState(error);
  } finally {
    loading = false;
  }
}

async function saveVariable(form) {
  const key = form.dataset.configForm;
  const input = form.querySelector('[name="value"]');
  if (!input?.value.trim()) return;
  if (!window.confirm(`Spara ett nytt värde för ${key}? Det gamla värdet visas inte igen.`)) return;
  try {
    await api(`/api/v2/admin/integrations/configuration/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: { value: input.value, confirm: true },
    });
    input.value = "";
    announce("Integrationsvariabeln sparades");
    await reload();
  } catch (error) {
    announce(error.message || "Variabeln kunde inte sparas", "danger");
  }
}

async function clearVariable(key) {
  if (!window.confirm(`Rensa Next-värdet för ${key}? En äldre databas- eller miljövariabel kan då börja användas igen.`)) return;
  try {
    await api(`/api/v2/admin/integrations/configuration/${encodeURIComponent(key)}?confirm=true`, { method: "DELETE" });
    announce("Next-värdet rensades");
    await reload();
  } catch (error) {
    announce(error.message || "Variabeln kunde inte rensas", "danger");
  }
}

async function adoptLegacy() {
  if (!window.confirm("Adoptera upptäckta gamla integrationsvärden till Next-hemlighetsfilen?")) return;
  try {
    const result = await api("/api/v2/admin/integrations/configuration/adopt-legacy", {
      method: "POST",
      body: { overwrite: false, confirm: true },
    });
    announce(`${result.adopted?.length || 0} gamla värden adopterades`);
    await reload();
  } catch (error) {
    announce(error.message || "Legacyimporten misslyckades", "danger");
  }
}

async function generateVapid(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  const replace = form.querySelector('[name="replace"]')?.checked || false;
  if (!window.confirm(replace ? "Ersätta befintliga Web Push-nycklar? Befintliga prenumerationer kan behöva registreras om." : "Generera Web Push-nycklar?")) return;
  try {
    await api("/api/v2/admin/integrations/vapid/generate", {
      method: "POST",
      body: { subject: values.subject, replace, confirm: true },
    });
    announce("VAPID-nycklarna genererades");
    await reload();
  } catch (error) {
    announce(error.message || "Nycklarna kunde inte genereras", "danger");
  }
}

async function uploadGoogle(form) {
  const kind = form.dataset.googleUpload;
  const file = form.querySelector('input[type="file"]')?.files?.[0];
  if (!file) return;
  const body = new FormData();
  body.append("file", file);
  try {
    const response = await fetch(`/api/v2/admin/integrations/google/${encodeURIComponent(kind)}`, {
      method: "POST",
      credentials: "same-origin",
      body,
    });
    if (!response.ok) throw new Error(await responseError(response));
    announce("Google-filen validerades och sparades");
    await reload();
  } catch (error) {
    announce(error.message || "Google-filen kunde inte sparas", "danger");
  }
}

async function deleteGoogle(kind) {
  if (!window.confirm(`Radera Google ${kind}?`)) return;
  try {
    await api(`/api/v2/admin/integrations/google/${encodeURIComponent(kind)}?confirm=true`, { method: "DELETE" });
    announce("Google-filen raderades");
    await reload();
  } catch (error) {
    announce(error.message || "Google-filen kunde inte raderas", "danger");
  }
}

function bind(root) {
  root.querySelectorAll("[data-config-form]").forEach(form => form.addEventListener("submit", event => {
    event.preventDefault();
    saveVariable(form);
  }));
  root.querySelectorAll("[data-config-clear]").forEach(button => button.addEventListener("click", () => clearVariable(button.dataset.configClear)));
  root.querySelector("[data-adopt-legacy]")?.addEventListener("click", adoptLegacy);
  root.querySelector("[data-vapid-generate]")?.addEventListener("submit", event => {
    event.preventDefault();
    generateVapid(event.currentTarget);
  });
  root.querySelectorAll("[data-google-upload]").forEach(form => form.addEventListener("submit", event => {
    event.preventDefault();
    uploadGoogle(form);
  }));
  root.querySelectorAll("[data-google-delete]").forEach(button => button.addEventListener("click", () => deleteGoogle(button.dataset.googleDelete)));
}

async function reload() {
  content.querySelector("#integration-configuration")?.remove();
  await load();
}

const observer = new MutationObserver(load);
observer.observe(content, { childList: true, subtree: true });
window.addEventListener("hashchange", load);
load();
