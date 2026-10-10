(() => {
  "use strict";
  const button = document.getElementById("run-queue");
  const output = document.getElementById("queue-message");
  if (!button || !output) return;

  button.addEventListener("click", async () => {
    button.disabled = true;
    output.textContent = "Starting queued projects…";
    output.className = "message";
    try {
      const response = await fetch("/api/factory/run-queue", {
        method: "POST",
        headers: { "Accept": "application/json" },
        cache: "no-store"
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Unable to start the factory queue.");
      if (data.status === "idle") {
        output.textContent = "No queued projects to run.";
      } else {
        output.textContent = "Factory started for " + data.queued_projects + " queued project(s). Watch Missions for live status.";
      }
    } catch (error) {
      output.textContent = error instanceof Error ? error.message : "Unable to start the factory queue.";
      output.className = "message error";
    } finally {
      button.disabled = false;
    }
  });
})();