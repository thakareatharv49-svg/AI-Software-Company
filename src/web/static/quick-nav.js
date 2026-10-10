(() => {
  "use strict";
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