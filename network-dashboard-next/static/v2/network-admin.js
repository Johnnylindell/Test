import { api, query } from "/assets/api.js";
import { badge, dateTime, emptyState, errorState, escapeHtml, skeleton } from "/assets/ui.js";

const content = document.querySelector("#v2-content");
const nav = document.querySelector("#v2-nav");
const notice = document.querySelector("#v2-notice");
let readOnly = true;
let external = false;
let networkViewActive = false;

function announce(message, tone = "good") {
  notice.innerHTML = `<span class="badge badge--${escapeHtml(tone)}">${escapeHtml(message)}</span>`;
  window.setTimeout(() => { notice.innerHTML = ""; }, 6000);
}

function row(title, detail = "", end = "") {
  return `<div class="row"><div class="row__main"><strong>${escapeHtml(title)}</strong>${detail ? `<span>${escapeHtml(detail)}</span>` : ""}</div>${end}</div>`;
}

function list(items, mapper, title = "Ingen data", detail = "") {
  return items?.length ? `<div class="list">${items.map(mapper).join("")}</div>` : emptyState(title, detail);
}

function field(label, name, options = {}) {
  const type = options.type || "text";
  const value = options.value ?? "";
  const required = options.required ? " required" : "";
  const disabled = options.disabled ? " disabled" : "";
  const placeholder = options.placeholder ? ` placeholder="${escapeHtml(options.placeholder)}"` : "";
  if (type === "select") {
    return `<label class="field"><span>${escapeHtml(label)}</span><select name="${escapeHtml(name)}"${required}${disabled}>${(options.values || []).map(item => {
      const option = typeof item === "string" ? { value: item, label: item } : item;
      return `<option value="${escapeHtml(option.value)}"${String(option.value) === String(value) ? " selected" : ""}>${escapeHtml(option.label)}</option>`;
    }).join("")}</select></label>`;
  }
  return `<label class="field"><span>${escapeHtml(label)}</span><input type="${escapeHtml(type)}" name="${escapeHtml(name)}" value="${escapeHtml(value)}"${placeholder}${required}${disabled}></label>`;
}

function resultPanel(title = "Ingen kontroll körd") {
  return `<div id="network-tool-result" class="network-toolbox__result">${emptyState(title, "Resultatet visas här och lagrar aldrig credentials.")}</div>`;
}

function output(result) {
  const target = document.querySelector("#network-tool-result");
  if (target) target.innerHTML = `<pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
}

function profileRows(profiles) {
  return list(profiles, profile => row(
    profile.name || profile.id,
    `${profile.host || "värd saknas"}${profile.ports?.length ? ` · ${profile.ports.join(", ")}` : ""}`,
    `<div class="row__actions"><button class="button button--small" type="button" data-network-action="profile-probe" data-host="${escapeHtml(profile.host || "")}" data-ports="${escapeHtml((profile.ports || []).join(","))}">Testa</button><button class="button button--small button--danger" type="button" data-network-action="profile-delete" data-value="${escapeHtml(profile.id || "")}"${readOnly ? " disabled" : ""}>Ta bort</button></div>`,
  ), "Inga enhetsprofiler", "Profiler kan sparas när Next lämnar skrivskyddat läge.");
}

function render(data) {
  const overview = data.overview || {};
  const devices = data.toolbox?.status?.device_profiles || overview.devices?.profiles || [];
  const integrations = overview.integrations || [];
  const status = data.toolbox?.status || {};
  const policy = data.toolbox?.policy || {};
  const latestInternet = status.internet_history?.[0] || overview.network?.internet_latest || null;
  const lastPortScan = status.last_port_scan || overview.network?.last_port_scan || {};
  const lastNetworkScan = status.last_network_scan || {};
  const destructiveAllowed = Boolean(policy.subnet_scan_allowed && policy.wake_on_lan_allowed);

  content.innerHTML = `<section class="hero"><p class="eyebrow">Nätverksadmin · explicit kontroll</p><h2>Toolbox utan shell eller dolda skanningar</h2><p>Riktade diagnostikverktyg körs först när administratören trycker på en kontroll. Full subnätsskanning och Wake-on-LAN kräver både aktivt driftläge och bekräftelse.</p><div class="stats"><div class="stat"><strong>${devices.length}</strong><span>Enhetsprofiler</span></div><div class="stat"><strong>${integrations.filter(item => item?.configured).length}</strong><span>Integrationer</span></div><div class="stat"><strong>${destructiveAllowed ? "Redo" : "Blockerad"}</strong><span>Aktiva åtgärder</span></div></div></section>
  ${readOnly || !external ? `<section class="mode-banner"><strong>Säkert parallelläge</strong><span>DNS, ping, HTTP, TLS och riktade portkontroller är tillgängliga. Subnätsskanning, profilsparning och Wake-on-LAN är blockerade.</span></section>` : ""}
  <div class="grid">
    <section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Riktad kontroll</p><h2>Värd och portar</h2></div>${badge("Ingen shellåtkomst", "good")}</div><form class="form" data-network-form="target"><div class="network-toolbox__compact">${field("Värdnamn eller IP", "host", { required: true, placeholder: "router.lan eller 192.168.1.1" })}${field("Kontroll", "tool", { type: "select", values: [{ value: "dns", label: "DNS" }, { value: "ping", label: "Ping" }, { value: "ports", label: "Portar" }, { value: "device", label: "Enhetsprofil" }, { value: "router", label: "Routerkontroll" }] })}${field("Portar", "ports", { value: "22,53,80,443,445,8123" })}</div><div class="form__actions"><button class="button button--primary">Kör kontroll</button></div></form></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Webb</p><h2>HTTP-kontroll</h2></div></div><form class="form" data-network-form="http">${field("URL", "url", { type: "url", required: true, placeholder: "https://homeassistant.local:8123" })}<div class="form__actions"><button class="button button--primary">Kontrollera</button></div></form></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Certifikat</p><h2>TLS-kontroll</h2></div></div><form class="form" data-network-form="tls">${field("Värd", "host", { required: true, placeholder: "example.org" })}${field("Port", "port", { type: "number", value: 443, required: true })}<div class="form__actions"><button class="button button--primary">Läs certifikat</button></div></form></section>
    <section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Resultat</p><h2>Senaste kontrollen</h2></div><button class="button button--small" type="button" data-network-action="internet-check">Kontrollera internet</button></div>${resultPanel()}</section>
    <section class="card card--wide"><div class="card__header"><div><p class="eyebrow">Sparade mål</p><h2>Enhetsprofiler</h2></div>${badge(String(devices.length), "neutral")}</div>${profileRows(devices)}<form class="form" data-network-form="profile"><div class="network-toolbox__compact">${field("Profil-ID", "profile_id", { required: true, placeholder: "router" , disabled: readOnly })}${field("Namn", "name", { required: true, placeholder: "Hemrouter", disabled: readOnly })}${field("Värd", "host", { required: true, placeholder: "192.168.1.1", disabled: readOnly })}${field("Portar", "ports", { value: "22,53,80,443", disabled: readOnly })}${field("MAC", "mac", { placeholder: "AA:BB:CC:DD:EE:FF", disabled: readOnly })}</div><div class="form__actions"><button class="button button--primary"${readOnly ? " disabled" : ""}>Spara profil</button></div></form></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Lagrad status</p><h2>Senaste observationer</h2></div></div><div class="list">${row("Internet", latestInternet ? (latestInternet.ok ? "Tillgängligt" : "Problem") : "Inte kontrollerat", latestInternet ? badge(latestInternet.ok ? "OK" : "Fel", latestInternet.ok ? "good" : "danger") : "")}${row("Portkontroll", lastPortScan.scanned_at ? dateTime(lastPortScan.scanned_at) : "Ingen")}${row("Subnätsskanning", lastNetworkScan.scanned_at ? `${lastNetworkScan.device_count || 0} enheter · ${dateTime(lastNetworkScan.scanned_at)}` : "Ingen")}${row("Liveprober vid sidladdning", data.toolbox?.live_probes_performed ? "Ja" : "Nej", badge(data.toolbox?.live_probes_performed ? "Varning" : "Nej", data.toolbox?.live_probes_performed ? "warning" : "good"))}</div></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Säkerhetspolicy</p><h2>Skyddsgränser</h2></div></div><div class="network-toolbox__policy">${badge(policy.targeted_probes_allowed ? "Riktade prober tillåtna" : "Prober blockerade", policy.targeted_probes_allowed ? "good" : "warning")}${badge(policy.subnet_scan_allowed ? "Subnätsskanning redo" : "Subnätsskanning blockerad", policy.subnet_scan_allowed ? "warning" : "good")}${badge(policy.wake_on_lan_allowed ? "Wake-on-LAN redo" : "Wake-on-LAN blockerad", policy.wake_on_lan_allowed ? "warning" : "good")}${badge(policy.arbitrary_shell_exposed ? "Shell exponerad" : "Ingen shell", policy.arbitrary_shell_exposed ? "danger" : "good")}${badge(policy.secrets_exposed ? "Hemligheter exponerade" : "Hemligheter dolda", policy.secrets_exposed ? "danger" : "good")}</div></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Aktiv skanning</p><h2>Privat subnät</h2></div></div><form class="form" data-network-form="subnet">${field("Nät", "network", { required: true, value: "192.168.1.0/24", disabled: !destructiveAllowed })}${field("Portar", "ports", { value: "22,80,443", disabled: !destructiveAllowed })}<label class="check"><input type="checkbox" name="confirm"${!destructiveAllowed ? " disabled" : ""}> Jag bekräftar aktiv skanning av detta privata nät</label><div class="form__actions"><button class="button button--warning"${!destructiveAllowed ? " disabled" : ""}>Skanna nät</button></div></form></section>
    <section class="card"><div class="card__header"><div><p class="eyebrow">Kontrollerad signal</p><h2>Wake-on-LAN</h2></div></div><form class="form" data-network-form="wol">${field("MAC", "mac", { required: true, placeholder: "AA:BB:CC:DD:EE:FF", disabled: !destructiveAllowed })}${field("Broadcast", "broadcast", { value: "255.255.255.255", disabled: !destructiveAllowed })}${field("Port", "port", { type: "number", value: 9, disabled: !destructiveAllowed })}<label class="check"><input type="checkbox" name="confirm"${!destructiveAllowed ? " disabled" : ""}> Jag bekräftar att magic packet ska skickas</label><div class="form__actions"><button class="button button--warning"${!destructiveAllowed ? " disabled" : ""}>Väck enhet</button></div></form></section>
  </div>`;
}

function parsePorts(value) {
  return String(value || "").split(",").map(item => Number(item.trim())).filter(Number.isInteger);
}

async function load() {
  networkViewActive = true;
  nav.querySelectorAll("button").forEach(button => button.classList.toggle("active", button.dataset.networkView === "true"));
  content.innerHTML = skeleton(6);
  try {
    const [overview, toolbox, security] = await Promise.all([
      api("/api/v2/admin/homelab/overview"),
      api("/api/v2/admin/homelab/toolbox/status"),
      api("/api/v2/admin/security/overview"),
    ]);
    readOnly = Boolean(security.read_only);
    external = Boolean(security.external_side_effects);
    render({ overview, toolbox, security });
  } catch (error) {
    content.innerHTML = errorState(error);
  }
}

async function runGet(path) {
  const target = document.querySelector("#network-tool-result");
  if (target) target.innerHTML = skeleton(2);
  try {
    output(await api(path));
  } catch (error) {
    if (target) target.innerHTML = errorState(error);
  }
}

async function mutate(path, options, message) {
  try {
    const result = await api(path, options);
    announce(message);
    output(result);
    return result;
  } catch (error) {
    announce(error.message || "Åtgärden misslyckades", "danger");
    return null;
  }
}

async function handleSubmit(event) {
  const form = event.target.closest("form[data-network-form]");
  if (!form || !networkViewActive) return;
  event.preventDefault();
  const values = Object.fromEntries(new FormData(form).entries());
  const kind = form.dataset.networkForm;
  if (kind === "target") {
    const paths = {
      dns: "/api/v2/admin/homelab/toolbox/dns",
      ping: "/api/v2/admin/homelab/toolbox/ping",
      ports: "/api/v2/admin/homelab/toolbox/ports",
      device: "/api/v2/admin/homelab/toolbox/device",
      router: "/api/v2/admin/homelab/toolbox/router",
    };
    const params = { host: values.host };
    if (["ports", "device"].includes(values.tool)) params.ports = values.ports;
    return runGet(query(paths[values.tool] || paths.dns, params));
  }
  if (kind === "http") return runGet(query("/api/v2/admin/homelab/toolbox/http", { url: values.url }));
  if (kind === "tls") return runGet(query("/api/v2/admin/homelab/toolbox/tls", { host: values.host, port: values.port }));
  if (kind === "profile") {
    const profileId = values.profile_id;
    const result = await mutate(`/api/v2/admin/homelab/devices/${encodeURIComponent(profileId)}`, { method: "PUT", body: { name: values.name, host: values.host, ports: parsePorts(values.ports), mac: values.mac || "", notes: "" } }, "Enhetsprofilen sparades");
    if (result) await load();
    return;
  }
  if (kind === "subnet") {
    if (!values.confirm) return announce("Bekräfta subnätsskanningen först", "warning");
    return mutate("/api/v2/admin/homelab/toolbox/subnet-scan", { method: "POST", body: { network: values.network, ports: parsePorts(values.ports), confirm: true } }, "Subnätsskanningen slutfördes");
  }
  if (kind === "wol") {
    if (!values.confirm) return announce("Bekräfta Wake-on-LAN först", "warning");
    return mutate("/api/v2/admin/homelab/toolbox/wake-on-lan", { method: "POST", body: { mac: values.mac, broadcast: values.broadcast, port: Number(values.port || 9), confirm: true } }, "Wake-on-LAN skickades");
  }
}

async function handleClick(event) {
  const target = event.target.closest("[data-network-action]");
  if (!target || !networkViewActive) return;
  const action = target.dataset.networkAction;
  if (action === "internet-check") return runGet("/api/v2/admin/homelab/toolbox/internet");
  if (action === "profile-probe") {
    return runGet(query("/api/v2/admin/homelab/toolbox/device", { host: target.dataset.host, ports: target.dataset.ports }));
  }
  if (action === "profile-delete") {
    if (!window.confirm("Ta bort enhetsprofilen?")) return;
    const result = await mutate(`/api/v2/admin/homelab/devices/${encodeURIComponent(target.dataset.value)}`, { method: "DELETE" }, "Enhetsprofilen togs bort");
    if (result) await load();
  }
}

function installNav() {
  if (nav.querySelector("[data-network-view]")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.networkView = "true";
  button.textContent = "Nätverk";
  button.addEventListener("click", load);
  nav.append(button);
}

nav.addEventListener("click", event => {
  if (event.target.closest("[data-view], [data-operations-view], [data-assistant-admin-view]")) {
    networkViewActive = false;
  }
});
content.addEventListener("submit", handleSubmit);
content.addEventListener("click", handleClick);

const observer = new MutationObserver(installNav);
observer.observe(nav, { childList: true });
installNav();
