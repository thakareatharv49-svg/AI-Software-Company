(() => {
  "use strict";
  const style = document.createElement("style");
  style.textContent = `
    .quick-nav-top,.quick-nav-missions{position:fixed;right:20px;z-index:1000;border:1px solid #4a5274;border-radius:999px;padding:11px 15px;background:#171d32;color:#eef2ff;font:700 13px system-ui,sans-serif;box-shadow:0 8px 28px #0008;cursor:pointer}
    .quick-nav-top{bottom:20px}.quick-nav-missions{bottom:68px;background:#5548c8;border-color:#8278ff}
    .quick-nav-top[hidden]{display:none}
    .quick-nav-top:focus-visible,.quick-nav-missions:focus-visible{outline:2px solid #b4adff;outline-offset:3px}
    @media(max-width:600px){.quick-nav-top,.quick-nav-missions{right:12px;padding:10px 13px}.quick-nav-top{bottom:12px}.quick-nav-missions{bottom:58px}}
  `;
  document.head.append(style);

  const top = document.createElement("button");
  top.type = "button";
  top.className = "quick-nav-top";
  top.textContent = "↑ Top";
  top.setAttribute("aria-label", "Scroll to top");
  top.hidden = true;
  top.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  document.body.append(top);

  const jump = document.createElement("button");
  jump.type = "button";
  jump.className = "quick-nav-missions";
  jump.textContent = "Missions ↓";
  jump.setAttribute("aria-label", "Jump to Missions");
  jump.addEventListener("click", () => {
    const target = document.getElementById("missions-section");
    if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  document.body.append(jump);

  let scheduled = false;
  window.addEventListener("scroll", () => {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(() => {
      top.hidden = window.scrollY < 280;
      scheduled = false;
    });
  }, { passive: true });
})();