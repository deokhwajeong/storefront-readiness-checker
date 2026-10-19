// Market selection for the readiness demo. All content is already in the HTML;
// this script only shows one market panel at a time and keeps tiles in sync.
(function () {
  "use strict";
  var tiles = Array.prototype.slice.call(document.querySelectorAll(".tile"));
  var panels = Array.prototype.slice.call(document.querySelectorAll(".panel"));
  if (!tiles.length || !panels.length) return;

  function select(code, opts) {
    var found = false;
    panels.forEach(function (p) {
      var on = p.getAttribute("data-market") === code;
      p.hidden = !on;
      if (on) found = true;
    });
    if (!found) return false;
    tiles.forEach(function (t) {
      t.setAttribute("aria-pressed", String(t.getAttribute("data-market") === code));
    });
    if (opts && opts.updateHash && history.replaceState) {
      history.replaceState(null, "", "#m-" + code);
    }
    if (opts && opts.reveal) {
      var panel = document.getElementById("m-" + code);
      var r = panel.getBoundingClientRect();
      if (r.top < 0 || r.top > window.innerHeight * 0.6) {
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
    return true;
  }

  tiles.forEach(function (t) {
    t.addEventListener("click", function () {
      select(t.getAttribute("data-market"), { updateHash: true, reveal: window.innerWidth < 900 });
    });
  });

  // Arrow keys move between tiles in reading order.
  document.querySelector(".tiles").addEventListener("keydown", function (e) {
    var i = tiles.indexOf(document.activeElement);
    if (i < 0) return;
    var next = null;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = tiles[(i + 1) % tiles.length];
    if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = tiles[(i - 1 + tiles.length) % tiles.length];
    if (next) { e.preventDefault(); next.focus(); }
  });

  var fromHash = (location.hash || "").replace(/^#m-/, "");
  var initial = panels.filter(function (p) { return !p.hasAttribute("data-hide"); })[0];
  if (!(fromHash && select(fromHash))) select(initial.getAttribute("data-market"));
})();
