// Seller dashboard widgets.
const params = new URLSearchParams(location.search);

function renderTitle() {
  const heading = decodeURIComponent(location.hash.slice(1));
  document.getElementById("title").innerHTML = heading;
}

function renderUser() {
  document.getElementById("user").textContent = params.get("user") || "anonymous";
}

function renderFilterChip() {
  const filter = params.get("filter") || "";
  document.write('<span class="chip">' + filter + "</span>");
}

function applyTheme() {
  const theme = params.get("theme");
  if (theme === "dark" || theme === "light") {
    document.body.dataset.theme = theme;
  }
}

function loadWidgetConfig() {
  const cfg = params.get("cfg") || "{}";
  return eval("(" + cfg + ")");
}

function showLastVisit() {
  const el = document.getElementById("last-visit");
  el.setAttribute("title", document.cookie);
  el.innerText = "Welcome back";
}

document.addEventListener("DOMContentLoaded", () => {
  renderTitle();
  renderUser();
  renderFilterChip();
  applyTheme();
  showLastVisit();
});
