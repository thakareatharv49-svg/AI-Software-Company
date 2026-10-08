# ruff: noqa: E501
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["web"])

APP_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Software Company — Control Center</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#eef2ff;background:#070a13;--card:#101522;--line:#202a40;--muted:#8d99b5;--accent:#7c6cff;--good:#36d399;--bad:#fb7185}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(900px 500px at 75% -10%,#29306d 0,#10152b 38%,#070a13 72%)}button,input,textarea{font:inherit}button{cursor:pointer;border:0}.shell{display:grid;grid-template-columns:235px 1fr;min-height:100vh}.side{border-right:1px solid var(--line);padding:26px 18px;background:#090d18cc;backdrop-filter:blur(16px)}.logo{font-weight:900;font-size:21px;letter-spacing:-.5px}.logo span{color:#9488ff}.sub{color:var(--muted);font-size:12px;margin-top:6px}.nav{margin-top:35px;display:grid;gap:7px}.nav div{padding:11px 12px;border-radius:10px;color:#aeb8d0}.nav div.active{background:#191d35;color:white}.sidefoot{position:fixed;bottom:20px;color:#66718b;font-size:11px}.main{padding:30px;max-width:1500px;width:100%;margin:auto}.head{display:flex;justify-content:space-between;align-items:center;gap:20px}.eyebrow{font-size:12px;color:#8e98b5;text-transform:uppercase;letter-spacing:1.5px}.title{font-size:32px;font-weight:850;letter-spacing:-1.3px;margin:4px 0}.desc{color:var(--muted)}.live{display:flex;align-items:center;gap:8px;border:1px solid var(--line);padding:8px 12px;border-radius:999px;background:#0d1220;color:#b9c2d8;font-size:12px}.dot{width:7px;height:7px;border-radius:50%;background:var(--good);box-shadow:0 0 12px var(--good)}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}.card{background:linear-gradient(145deg,#121827,#0e1420);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 20px 60px #0004}.stat small{color:var(--muted)}.stat b{display:block;font-size:27px;margin-top:8px}.grid{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;margin-bottom:16px}.card h2{font-size:17px;margin:0 0 7px}.muted{color:var(--muted)}.stack{display:grid;gap:12px}.form{margin-top:18px}.label{font-size:12px;color:#aeb8d0;display:grid;gap:7px}.input,.textarea{width:100%;background:#090e19;border:1px solid #29334b;color:white;border-radius:10px;padding:12px;outline:none}.input:focus,.textarea:focus{border-color:#6e62ed}.textarea{min-height:110px;resize:vertical}.primary{background:linear-gradient(135deg,#786cff,#5667e9);color:white;padding:11px 16px;border-radius:10px;font-weight:800}.secondary{background:#202a3e;color:#d9e0f2;padding:11px 15px;border-radius:10px;font-weight:700}.danger{background:#341c29;color:#ffb6c4;padding:9px 12px;border-radius:9px;font-weight:700}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.message{min-height:20px;font-size:13px;margin-top:12px}.missions{max-height:430px;overflow:auto}.mission{width:100%;display:flex;text-align:left;justify-content:space-between;gap:12px;padding:13px 10px;border-bottom:1px solid #1d2639;background:transparent;color:white}.mission:hover{background:#151b2b}.mission strong{display:block}.mission p{margin:5px 0 0;color:var(--muted);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:520px}.pill{white-space:nowrap;height:max-content;padding:5px 8px;border-radius:999px;background:#1b2640;color:#b8c4e4;font-size:11px}.details{min-height:210px}.event{padding:10px 0;border-bottom:1px solid #1d2639;font-size:12px}.event b{font-size:12px}.event time{display:block;color:#65718c;margin-top:3px}.repo{display:inline-block;margin-top:7px;color:#a9a0ff;text-decoration:none}.empty{color:#66718b;font-size:13px;padding:20px 0}.progress{height:5px;background:#1c2537;border-radius:9px;overflow:hidden;margin:14px 0}.bar{height:100%;width:45%;background:linear-gradient(90deg,#7b6cff,#55d8ff);animation:pulse 1.4s infinite alternate}@keyframes pulse{to{opacity:.55}}@media(max-width:900px){.shell{grid-template-columns:1fr}.side{display:none}.main{padding:20px}.stats{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}.title{font-size:26px}}@media(max-width:520px){.stats{grid-template-columns:1fr 1fr}.head{align-items:flex-start;flex-direction:column}}
</style></head>
<body><div class="shell">
<aside class="side"><div class="logo">AI <span>Software</span><br>Company</div><div class="sub">Autonomous software factory</div>
<div class="nav"><div class="active">◆ Control Center</div><div>◇ Missions</div><div>◇ Factory</div><div>◇ GitHub Delivery</div></div>
<div class="sidefoot">Human-directed · AI-executed</div></aside>
<main class="main">
<header class="head"><div><div class="eyebrow">Control Center</div><div class="title">Build software with your company.</div><div class="desc">Give an objective. The factory plans, generates, tests, repairs and publishes.</div></div><div class="live"><i class="dot"></i><span id="live">connecting</span></div></header>

<section class="stats"><div class="card stat"><small>Projects</small><b id="projects">—</b></div><div class="card stat"><small>Tasks</small><b id="tasks">—</b></div><div class="card stat"><small>Agents</small><b id="agents">—</b></div><div class="card stat"><small>Factory</small><b id="factory">idle</b></div></section>

<div class="grid"><section class="card"><h2>New mission</h2><div class="muted">Describe the product, not the implementation.</div>
<form id="form" class="stack form" onsubmit="return launch(event)"><label class="label">MISSION NAME<input class="input" id="name" maxlength="200" required placeholder="Python Calculator"></label><label class="label">OBJECTIVE<textarea class="textarea" id="objective" maxlength="5000" required placeholder="Create a Python calculator with automated tests for add, subtract, multiply and divide."></textarea></label><div class="actions"><button class="primary" id="start">Launch factory</button></div></form><div class="message muted" id="message"></div></section>
<section class="card"><h2>Factory pipeline</h2><div class="muted">Every mission follows the same autonomous delivery path.</div><div class="progress" id="progress" style="display:none"><div class="bar"></div></div><div class="stack" style="margin-top:18px"><div>01 · Plan <span class="muted">→ mission controller</span></div><div>02 · Generate <span class="muted">→ local Ollama</span></div><div>03 · Validate <span class="muted">→ tests + QA + security</span></div><div>04 · Repair <span class="muted">→ autonomous retry loop</span></div><div>05 · Publish <span class="muted">→ GitHub main</span></div></div><div class="actions"><button type="button" class="secondary" id="stop">Stop company</button></div></section></div>

<div class="grid"><section class="card"><h2>Missions</h2><div id="missions" class="missions"><div class="empty">No missions yet.</div></div></section>
<section class="card"><h2>Live events</h2><div id="events" class="events"><div class="empty">Waiting for factory events.</div></div></section></div>

<section class="card details"><h2 id="detailTitle">Mission details</h2><div id="details" class="empty">Select a mission to inspect its outputs and audit trail.</div></section>
</main></div>
<script>
const $ = (id) => document.getElementById(id);
const terminal = new Set(["completed", "blocked", "failed", "cancelled"]);
let selectedMissionId = null;
let refreshBusy = false;
let watchingMissionId = null;

function esc(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? {"Content-Type": "application/json"} : {}),
      ...(options.headers || {})
    }
  });
  let data = {};
  try { data = await response.json(); } catch (_) {}
  if (!response.ok) {
    throw new Error(data.detail || ("Request failed: " + response.status));
  }
  return data;
}

function setMessage(message, error = false) {
  const node = $("message");
  node.textContent = message || "";
  node.style.color = error ? "#ff9aae" : "";
}

function setProgress(visible) {
  $("progress").style.display = visible ? "block" : "none";
}

function renderMissions(missions) {
  const container = $("missions");
  container.replaceChildren();

  if (!missions.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No missions yet.";
    container.appendChild(empty);
    return;
  }

  for (const item of missions) {
    const mission = item.mission;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mission";
    button.dataset.action = "select-mission";
    button.dataset.missionId = mission.id;

    const left = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = mission.name;
    const p = document.createElement("p");
    p.textContent = mission.objective;
    left.append(strong, p);

    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = item.status;

    button.append(left, pill);
    container.appendChild(button);
  }
}

function renderEvents(events) {
  const container = $("events");
  container.replaceChildren();

  if (!events.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Waiting for factory events.";
    container.appendChild(empty);
    return;
  }

  for (const event of events.slice().reverse().slice(0, 25)) {
    const node = document.createElement("div");
    node.className = "event";
    const title = document.createElement("b");
    title.textContent = event.event_type || "event";
    const message = document.createElement("div");
    message.className = "muted";
    message.textContent = event.payload?.message || event.project_id || "company event";
    node.append(title, message);
    container.appendChild(node);
  }
}

async function refresh() {
  if (refreshBusy) return;
  refreshBusy = true;
  try {
    const [state, missions, events, summary, factory] = await Promise.all([
      api("/api/company/state"),
      api("/api/missions"),
      api("/api/company/events"),
      api("/dashboard/summary"),
      api("/api/factory/status")
    ]);

    $("live").textContent = "company " + state.status;
    $("projects").textContent = summary.projects ?? 0;
    $("tasks").textContent = summary.tasks ?? 0;
    $("agents").textContent = summary.agents ?? 0;
    $("factory").textContent = factory.running ? "running" : "idle";
    renderMissions(missions);
    renderEvents(events);

    if (selectedMissionId && missions.some((item) => item.mission.id === selectedMissionId)) {
      await selectMission(selectedMissionId, false);
    }
  } catch (error) {
    $("live").textContent = "offline";
    setMessage(error.message, true);
  } finally {
    refreshBusy = false;
  }
}

function actionButton(label, action, id, className) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.dataset.action = action;
  button.dataset.missionId = id;
  return button;
}

async function selectMission(id, showLoading = true) {
  selectedMissionId = id;
  if (showLoading) {
    $("details").textContent = "Loading mission…";
  }

  try {
    const [job, outputs, audit] = await Promise.all([
      api("/api/missions/" + encodeURIComponent(id) + "/job"),
      api("/api/missions/" + encodeURIComponent(id) + "/outputs"),
      api("/api/missions/" + encodeURIComponent(id) + "/audit")
    ]);

    $("detailTitle").textContent = job.mission.name;

    const root = document.createElement("div");
    const top = document.createElement("div");
    top.style.display = "flex";
    top.style.justifyContent = "space-between";
    top.style.gap = "16px";

    const info = document.createElement("div");
    const status = document.createElement("span");
    status.className = "pill";
    status.textContent = job.status;
    const message = document.createElement("div");
    message.className = "muted";
    message.style.marginTop = "10px";
    message.textContent = job.message || "";
    info.append(status, message);

    const actions = document.createElement("div");
    actions.className = "actions";
    if (job.status === "queued") {
      actions.appendChild(actionButton("Run Factory", "run-factory", id, "primary"));
    }
    if (job.status === "failed" || job.status === "blocked") {
      actions.appendChild(actionButton("Retry", "retry", id, "secondary"));
    }
    if (job.status !== "completed" && job.status !== "cancelled") {
      actions.appendChild(actionButton("Cancel", "cancel", id, "danger"));
    }
    top.append(info, actions);
    root.appendChild(top);

    const outputsTitle = document.createElement("h3");
    outputsTitle.style.marginTop = "22px";
    outputsTitle.textContent = "Outputs";
    root.appendChild(outputsTitle);

    if (outputs.length) {
      for (const output of outputs) {
        const node = document.createElement("div");
        node.className = "event";
        const title = document.createElement("b");
        title.textContent = output.name + " · " + output.status;
        const type = document.createElement("div");
        type.className = "muted";
        type.textContent = output.output_type || "";
        node.append(title, type);

        if (output.repository) {
          const link = document.createElement("a");
          link.className = "repo";
          link.target = "_blank";
          link.rel = "noopener";
          link.href = "https://github.com/" + output.repository;
          link.textContent = "Open GitHub repository ↗";
          node.appendChild(link);
        }
        root.appendChild(node);
      }
    } else {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "No outputs recorded yet.";
      root.appendChild(empty);
    }

    const auditTitle = document.createElement("h3");
    auditTitle.style.marginTop = "22px";
    auditTitle.textContent = "Audit trail";
    root.appendChild(auditTitle);

    if (audit.length) {
      for (const entry of audit.slice().reverse()) {
        const node = document.createElement("div");
        node.className = "event";
        const title = document.createElement("b");
        title.textContent = entry.event_type || "event";
        const status = document.createElement("span");
        status.className = "pill";
        status.style.marginLeft = "6px";
        status.textContent = entry.status || "event";
        const message = document.createElement("div");
        message.className = "muted";
        message.textContent = entry.message || "";
        const time = document.createElement("time");
        time.textContent = entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "";
        node.append(title, status, message, time);
        root.appendChild(node);
      }
    } else {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "No audit entries.";
      root.appendChild(empty);
    }

    $("details").replaceChildren(root);
  } catch (error) {
    $("details").textContent = "Unable to load mission: " + error.message;
  }
}

async function runFactory(id) {
  selectedMissionId = id;
  setProgress(true);
  setMessage("Starting factory…");
  try {
    await api("/api/missions/" + encodeURIComponent(id) + "/factory-run", {method: "POST"});
    setMessage("Factory is running.");
    await selectMission(id);
    watch(id);
  } catch (error) {
    setMessage("Factory start failed: " + error.message, true);
    await refresh();
  }
}

async function launch(event) {
  event?.preventDefault();
  const name = $("name").value.trim();
  const objective = $("objective").value.trim();

  if (!name || !objective) {
    setMessage("Mission name and objective are required.", true);
    return false;
  }

  $("start").disabled = true;
  setProgress(true);
  setMessage("Creating mission…");

  try {
    const result = await api("/api/missions", {
      method: "POST",
      body: JSON.stringify({name, objective})
    });
    const id = result.mission.id;
    $("form").reset();
    setMessage("Mission created. Starting factory…");
    await runFactory(id);
  } catch (error) {
    setMessage("Launch failed: " + error.message, true);
  } finally {
    $("start").disabled = false;
  }
  return false;
}

async function retryMission(id) {
  setProgress(true);
  setMessage("Retrying mission…");
  try {
    await api("/api/missions/" + encodeURIComponent(id) + "/retry", {method: "POST"});
    await runFactory(id);
  } catch (error) {
    setMessage("Retry failed: " + error.message, true);
  }
}

async function cancelMission(id) {
  setMessage("Cancelling mission…");
  try {
    await api("/api/missions/" + encodeURIComponent(id) + "/cancel", {method: "POST"});
    await selectMission(id);
    await refresh();
  } catch (error) {
    setMessage("Cancel failed: " + error.message, true);
  }
}

async function watch(id) {
  if (watchingMissionId === id) return;
  watchingMissionId = id;

  try {
    for (let i = 0; i < 180; i++) {
      const job = await api("/api/missions/" + encodeURIComponent(id) + "/job");
      await selectMission(id, false);
      if (terminal.has(job.status)) {
        setProgress(false);
        setMessage("Mission " + job.status + ".");
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
    setMessage("Factory is still running. You can continue using the control center.");
  } catch (error) {
    setMessage("Factory monitor stopped: " + error.message, true);
  } finally {
    watchingMissionId = null;
    await refresh();
  }
}

$("form").addEventListener("submit", launch);

$("missions").addEventListener("click", (event) => {
  const button = event.target.closest("[data-action='select-mission']");
  if (button) {
    event.preventDefault();
    selectMission(button.dataset.missionId);
  }
});

$("details").addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  event.preventDefault();

  const id = button.dataset.missionId;
  const action = button.dataset.action;

  if (action === "run-factory") runFactory(id);
  if (action === "retry") retryMission(id);
  if (action === "cancel") cancelMission(id);
});

$("stop").addEventListener("click", async (event) => {
  event.preventDefault();
  try {
    await api("/api/company/stop", {method: "POST"});
    setMessage("Company stopped.");
    await refresh();
  } catch (error) {
    setMessage("Stop failed: " + error.message, true);
  }
});

window.addEventListener("error", (event) => {
  setMessage("UI error: " + event.message, true);
});

window.addEventListener("unhandledrejection", (event) => {
  setMessage("UI error: " + (event.reason?.message || event.reason), true);
});

refresh();
setInterval(refresh, 3000);
</script></body></html>"""

@router.get("/app", response_class=HTMLResponse)
async def company_app() -> HTMLResponse:
    return HTMLResponse(APP_HTML, headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0"})
