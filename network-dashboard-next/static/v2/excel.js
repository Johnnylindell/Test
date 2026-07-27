import { api } from "/assets/api.js";
import { badge, emptyState, errorState, escapeHtml, skeleton } from "/assets/ui.js";

let readOnly = true;
let selectedFile = null;

function announce(message, tone = "good") {
  const notice = document.querySelector("#v2-notice");
  if (!notice) return;
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 5200);
}

async function responseError(response) {
  try {
    const payload = await response.json();
    return payload.detail || payload.error?.message || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

async function downloadWorkbook() {
  try {
    const response = await fetch("/api/v2/budget/excel/export", {
      credentials: "same-origin",
      cache: "no-store",
    });
    if (!response.ok) throw new Error(await responseError(response));
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `lindells-budget-${new Date().toISOString().slice(0, 10)}.xlsx`;
    link.click();
    URL.revokeObjectURL(link.href);
    announce("Excel-arbetsboken skapades");
  } catch (error) {
    announce(error.message || "Excel-exporten misslyckades", "danger");
  }
}

async function previewWorkbook(file) {
  const result = document.querySelector("#excel-result");
  if (!result) return;
  selectedFile = file;
  result.innerHTML = skeleton(2);
  const form = new FormData();
  form.append("file", file);
  try {
    const response = await fetch("/api/v2/budget/excel/preview", {
      method: "POST",
      credentials: "same-origin",
      body: form,
    });
    if (!response.ok) throw new Error(await responseError(response));
    const payload = await response.json();
    const summary = payload.summary || {};
    result.innerHTML = `<div class="list"><div class="row"><div class="row__main"><strong>${escapeHtml(file.name)}</strong><span>${summary.sheets || 0} blad · ${summary.cells || 0} celler</span></div>${badge("Inte importerad", "warning")}</div>${(summary.names || []).map(name => `<div class="row"><div class="row__main"><strong>${escapeHtml(name)}</strong><span>Budgetblad</span></div></div>`).join("")}</div>`;
    document.querySelector("#excel-import")?.toggleAttribute("disabled", readOnly);
    announce("Arbetsboken är förhandsgranskad men inte importerad");
  } catch (error) {
    selectedFile = null;
    result.innerHTML = errorState(error);
  }
}

async function importWorkbook() {
  if (!selectedFile) return announce("Välj och förhandsgranska en Excel-fil först", "warning");
  if (readOnly) return announce("Excel-import är blockerad i parallelläge", "warning");
  if (!window.confirm("Importera den förhandsgranskade Excel-filen till Next-databasen?")) return;
  const form = new FormData();
  form.append("file", selectedFile);
  form.append("replace", String(Boolean(document.querySelector("#excel-replace")?.checked)));
  form.append("confirm", "true");
  const result = document.querySelector("#excel-result");
  result.innerHTML = skeleton(2);
  try {
    const response = await fetch("/api/v2/budget/excel/import", {
      method: "POST",
      credentials: "same-origin",
      body: form,
    });
    if (!response.ok) throw new Error(await responseError(response));
    const payload = await response.json();
    result.innerHTML = `<div class="row"><div class="row__main"><strong>Import klar</strong><span>${payload.changed_cells || 0} celler uppdaterades i ${payload.sheets || 0} blad</span></div>${badge("Klar", "good")}</div>`;
    announce("Excel-budgeten importerades");
  } catch (error) {
    result.innerHTML = errorState(error);
  }
}

function workspaceHtml() {
  return `<section id="excel-workspace" class="card card--wide"><div class="card__header"><div><p class="eyebrow">Versionerad arbetsbok</p><h2>Excel import och export</h2></div>${badge("Originalfilen skrivs aldrig över", "good")}</div><p>Exportera en komplett arbetsbok eller förhandsgranska en tidigare Lindells-export innan den importeras. Filen måste innehålla appens versionsmetadata.</p><div class="toolbar"><button id="excel-export" class="button button--primary" type="button">Ladda ned Excel</button><label class="button" for="excel-file">Välj Excel-fil</label><input id="excel-file" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" hidden></div><label class="check"><input id="excel-replace" type="checkbox"${readOnly ? " disabled" : ""}> Ersätt alla befintliga budgetblad vid import</label><div class="toolbar"><button id="excel-import" class="button button--danger" type="button" disabled>Importera förhandsgranskad fil</button></div><div id="excel-result">${emptyState("Ingen Excel-fil vald", "Välj en versionerad .xlsx-fil för att förhandsgranska den.")}</div></section>`;
}

async function inject() {
  const content = document.querySelector("#v2-content");
  if (!content || !location.hash.includes("budget")) return;
  const grid = content.querySelector(".grid");
  if (!grid || grid.querySelector("#excel-workspace")) return;
  try {
    const security = await api("/api/v2/admin/security/overview");
    readOnly = Boolean(security.read_only);
  } catch {
    readOnly = true;
  }
  grid.insertAdjacentHTML("beforeend", workspaceHtml());
  document.querySelector("#excel-export")?.addEventListener("click", downloadWorkbook);
  document.querySelector("#excel-file")?.addEventListener("change", event => {
    const file = event.target.files?.[0];
    if (file) previewWorkbook(file);
  });
  document.querySelector("#excel-import")?.addEventListener("click", importWorkbook);
}

const observer = new MutationObserver(inject);
observer.observe(document.querySelector("#v2-content"), { childList: true, subtree: true });
window.addEventListener("hashchange", inject);
inject();
