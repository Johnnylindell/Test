import { api } from "/assets/api.js";
import { badge, dateTime, emptyState, errorState, escapeHtml, money, skeleton } from "/assets/ui.js";

const content = document.querySelector("#v2-content");
const nav = document.querySelector("#v2-nav");
const notice = document.querySelector("#v2-notice");
let active = false;
let readOnly = true;
let selectedFile = null;
let preview = null;

function announce(message, tone = "good") {
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 5200);
}

function row(title, detail = "", end = "") {
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></div>${end}</div>`;
}

function list(items, mapper, title = "Ingen data") {
  return items?.length ? `<div class="list">${items.map(mapper).join("")}</div>` : emptyState(title);
}

async function responseError(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.error?.message || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

function renderPreview() {
  if (!preview) return emptyState("Ingen fil förhandsgranskad", "Välj en CSV- eller CAMT XML-fil.");
  const summary = preview.summary || {};
  return `<div class="stats"><div class="stat"><strong>${summary.rows || 0}</strong><span>Rader</span></div><div class="stat"><strong>${summary.new_rows || 0}</strong><span>Nya</span></div><div class="stat"><strong>${summary.duplicates || 0}</strong><span>Dubbletter</span></div></div>${list((preview.transactions || []).slice(0, 30), transaction => row(transaction.counterparty || transaction.description || "Transaktion", `${transaction.booking_date} · ${transaction.category}${transaction.duplicate ? " · redan importerad" : ""}`, `<strong>${money(transaction.amount)}</strong>`), "Inga transaktioner")}${preview.truncated ? `<p class="helper">Endast de första 500 raderna visas i preview.</p>` : ""}`;
}

function render(data) {
  const totals = data.totals || {};
  content.innerHTML = `<section class="hero"><p class="eyebrow">Lokal och granskad</p><h2>Bankimport</h2><p>Importera kontoutdrag manuellt utan att ge appen direkt åtkomst till banken.</p><div class="stats"><div class="stat"><strong>${totals.transactions || 0}</strong><span>Transaktioner</span></div><div class="stat"><strong>${money(totals.income || 0)}</strong><span>Inkomst</span></div><div class="stat"><strong>${money(totals.expenses || 0)}</strong><span>Utgifter</span></div></div></section>${readOnly ? `<section class="mode-banner"><strong>Förhandsgranskning tillgänglig</strong><span>Import och regler aktiveras först när Next lämnar skrivskyddat läge.</span></section>` : ""}<div class="grid">
    <section class="card card--wide"><div class="card__header"><div><p class="eyebrow">CSV eller CAMT</p><h2>Förhandsgranska kontoutdrag</h2></div>${badge("Ingen automatisk bankanslutning", "good")}</div><div class="toolbar"><label class="button button--primary" for="bank-file">Välj fil</label><input id="bank-file" type="file" accept=".csv,.xml,text/csv,application/xml,text/xml" hidden><button id="bank-import" class="button button--danger" type="button"${readOnly || !preview ? " disabled" : ""}>Importera förhandsgranskad fil</button></div><div id="bank-preview">${renderPreview()}</div></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Senaste</p><h2>Transaktioner</h2></div></div>${list((data.transactions || []).slice(0, 60), transaction => row(transaction.counterparty || transaction.description || "Transaktion", `${transaction.booking_date} · ${transaction.category}`, `<strong>${money(transaction.amount)}</strong>`), "Inga importerade transaktioner")}</section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Sammanställning</p><h2>Kategorier</h2></div></div>${list(data.categories || [], category => row(category.category, `${category.transactions || 0} transaktioner`, money(category.expenses || 0)), "Inga kategorier")}</section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Historik</p><h2>Importer</h2></div></div>${list(data.imports || [], item => row(item.filename, `${dateTime(item.created_at)} · ${item.imported_count || 0} nya · ${item.duplicate_count || 0} dubbletter`), "Ingen importhistorik")}</section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Automatisk kategorisering</p><h2>Regler</h2></div></div>${list(data.rules || [], rule => row(rule.pattern, `${rule.category} · prioritet ${rule.priority}`, `<button class="button button--small button--danger" data-bank-rule-delete="${escapeHtml(rule.id)}"${readOnly ? " disabled" : ""}>Radera</button>`), "Inga egna regler")}<form id="bank-rule-form" class="form"><label class="field"><span>Mönster (regex)</span><input name="pattern" required placeholder="K-Market|Prisma"></label><label class="field"><span>Kategori</span><input name="category" required placeholder="Mat"></label><label class="field"><span>Prioritet</span><input name="priority" type="number" value="100" min="0" max="10000"></label><div class="form__actions"><button class="button button--primary"${readOnly ? " disabled" : ""}>Spara regel</button></div></form></section>
  </div>`;
  bind();
}

async function load() {
  active = true;
  nav.querySelectorAll("button").forEach(button => button.classList.toggle("active", button.dataset.bankView === "true"));
  content.innerHTML = skeleton(6);
  try {
    const [data, security] = await Promise.all([
      api("/api/v2/banking/overview"),
      api("/api/v2/admin/security/overview"),
    ]);
    readOnly = Boolean(security.read_only);
    render(data);
  } catch (error) {
    content.innerHTML = errorState(error);
  }
}

async function previewFile(file) {
  selectedFile = file;
  preview = null;
  const target = document.querySelector("#bank-preview");
  target.innerHTML = skeleton(3);
  const form = new FormData();
  form.append("file", file);
  try {
    const response = await fetch("/api/v2/banking/import/preview", { method: "POST", body: form, credentials: "same-origin" });
    if (!response.ok) throw new Error(await responseError(response));
    preview = await response.json();
    target.innerHTML = renderPreview();
    document.querySelector("#bank-import")?.toggleAttribute("disabled", readOnly);
    announce("Kontoutdraget är granskat men inte importerat");
  } catch (error) {
    selectedFile = null;
    target.innerHTML = errorState(error);
  }
}

async function importFile() {
  if (!selectedFile || !preview) return announce("Förhandsgranska filen först", "warning");
  if (readOnly) return announce("Import är blockerad i parallelläge", "warning");
  if (!window.confirm(`Importera ${preview.summary?.new_rows || 0} nya transaktioner?`)) return;
  const form = new FormData();
  form.append("file", selectedFile);
  form.append("confirm", "true");
  try {
    const response = await fetch("/api/v2/banking/import", { method: "POST", body: form, credentials: "same-origin" });
    if (!response.ok) throw new Error(await responseError(response));
    const result = await response.json();
    announce(`${result.imported || 0} transaktioner importerades`);
    selectedFile = null;
    preview = null;
    await load();
  } catch (error) {
    announce(error.message || "Importen misslyckades", "danger");
  }
}

async function saveRule(event) {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    await api("/api/v2/banking/rules", {
      method: "POST",
      body: { pattern: values.pattern, category: values.category, priority: Number(values.priority || 100), active: true },
    });
    announce("Kategoriregeln sparades");
    await load();
  } catch (error) {
    announce(error.message || "Regeln kunde inte sparas", "danger");
  }
}

async function deleteRule(id) {
  if (!window.confirm("Radera kategoriregeln?")) return;
  try {
    await api(`/api/v2/banking/rules/${encodeURIComponent(id)}`, { method: "DELETE" });
    announce("Kategoriregeln raderades");
    await load();
  } catch (error) {
    announce(error.message || "Regeln kunde inte raderas", "danger");
  }
}

function bind() {
  document.querySelector("#bank-file")?.addEventListener("change", event => {
    const file = event.target.files?.[0];
    if (file) previewFile(file);
  });
  document.querySelector("#bank-import")?.addEventListener("click", importFile);
  document.querySelector("#bank-rule-form")?.addEventListener("submit", saveRule);
  content.querySelectorAll("[data-bank-rule-delete]").forEach(button => button.addEventListener("click", () => deleteRule(button.dataset.bankRuleDelete)));
}

function installNav() {
  if (!nav || nav.querySelector("[data-bank-view]")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.bankView = "true";
  button.textContent = "Bankimport";
  button.addEventListener("click", load);
  nav.append(button);
}

nav.addEventListener("click", event => {
  if (event.target.closest("[data-view]")) active = false;
});
const observer = new MutationObserver(installNav);
observer.observe(nav, { childList: true });
installNav();
