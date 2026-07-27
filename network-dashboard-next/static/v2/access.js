import { api } from "/assets/api.js";

let profiles = [];

function selectedProfile(form) {
  const user = form.querySelector('[name="user"]')?.value || "";
  return profiles.find(profile => profile.user === user) || null;
}

function fill(form) {
  const profile = selectedProfile(form);
  if (!profile) return;
  const sections = form.querySelector('[name="sections"]');
  const readonly = form.querySelector('[name="readonly"]');
  if (sections) sections.value = (profile.sections || []).join(", ");
  if (readonly) readonly.checked = Boolean(profile.readonly);
}

async function enhance() {
  if (!location.hash.includes("security")) return;
  const form = document.querySelector('form[data-form="access-profile"]');
  if (!form || form.dataset.enhanced === "true") return;
  form.dataset.enhanced = "true";
  try {
    const overview = await api("/api/v2/admin/security/overview");
    profiles = overview.access?.profiles || [];
    fill(form);
    form.querySelector('[name="user"]')?.addEventListener("change", () => fill(form));
    const sections = form.querySelector('[name="sections"]');
    if (sections) {
      sections.addEventListener("input", () => {
        const count = sections.value.split(",").map(value => value.trim()).filter(Boolean).length;
        sections.setCustomValidity(count ? "" : "Minst en sektion måste väljas");
      });
    }
  } catch {
    form.dataset.enhanced = "false";
  }
}

const observer = new MutationObserver(enhance);
observer.observe(document.querySelector("#v2-content"), { childList: true, subtree: true });
window.addEventListener("hashchange", enhance);
enhance();
