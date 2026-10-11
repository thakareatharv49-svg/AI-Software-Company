(() => {
  "use strict";
  const startButton = document.getElementById("run-queue");
  const stopButton = document.getElementById("stop-queue");
  const output = document.getElementById("queue-message");
  if (!startButton || !stopButton || !output) return;

  async function send(url, label) {
    startButton.disabled = true;
    stopButton.disabled = true;
    output.textContent = label;
    output.className = "message";
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Accept": "application/json" },
        cache: "no-store"
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Unable to update factory mode.");
      if (data.continuous) {
        output.textContent = "Continuous mode is on. The factory will build queued projects one by one and automatically pick up new missions.";
      } else {
        output.textContent = data.message || "The factory will stop after its current project.";
      }
    } catch (error) {
      output.textContent = error instanceof Error ? error.message : "Unable to update factory mode.";
      output.className = "message error";
    } finally {
      startButton.disabled = false;
      stopButton.disabled = false;
    }
  }

  startButton.addEventListener("click", () => {
    send("/api/factory/run-queue", "Enabling continuous factory mode…");
  });
  stopButton.addEventListener("click", () => {
    send("/api/factory/continuous/stop", "Requesting a safe stop…");
  });
})();
