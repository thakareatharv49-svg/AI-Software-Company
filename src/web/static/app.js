(() => {
"use strict";
const $ = id => document.getElementById(id);
const terminal = new Set(["completed","blocked","failed","cancelled"]);
let selectedMissionId = null;
let pollTimer = null;
let busy = false;

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    ...options,
    headers: {"Accept":"application/json", ...(options.body ? {"Content-Type":"application/json"} : {}), ...(options.headers || {})}
  });
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch (_) { data = {detail:text}; }
  if (!response.ok) throw new Error(data.detail || ("HTTP " + response.status));
  return data;
}

function message(text, error=false) {
  $("message").textContent = text || "";
  $("message").className = "message " + (error ? "error" : "");
}

function renderMissions(items) {
  const box = $("missions");
  box.replaceChildren();
  if (!items.length) {
    const e=document.createElement("div"); e.className="empty"; e.textContent="No missions yet."; box.append(e); return;
  }
  for (const item of items) {
    const b=document.createElement("button"); b.type="button"; b.className="mission";
    b.dataset.id=item.mission.id;
    const left=document.createElement("div");
    const title=document.createElement("strong"); title.textContent=item.mission.name;
    const desc=document.createElement("p"); desc.textContent=item.mission.objective;
    left.append(title,desc);
    const pill=document.createElement("span"); pill.className="pill"; pill.textContent=item.status;
    b.append(left,pill); box.append(b);
  }
}

function renderEvents(events) {
  const box=$("events"); box.replaceChildren();
  if (!events.length) { const e=document.createElement("div"); e.className="empty"; e.textContent="Waiting for events."; box.append(e); return; }
  for (const ev of events.slice().reverse().slice(0,20)) {
    const n=document.createElement("div"); n.className="event";
    const t=document.createElement("b"); t.textContent=ev.event_type || "event";
    const m=document.createElement("div"); m.className="muted"; m.textContent=ev.payload?.message || ev.project_id || "company event";
    n.append(t,m); box.append(n);
  }
}

function action(label, name, id, cls) {
  const b=document.createElement("button"); b.type="button"; b.className=cls; b.textContent=label;
  b.dataset.action=name; b.dataset.id=id; return b;
}

async function showMission(id) {
  selectedMissionId=id;
  $("details").textContent="Loading…";
  try {
    const [job, outputs, audit] = await Promise.all([
      api("/api/missions/"+encodeURIComponent(id)+"/job"),
      api("/api/missions/"+encodeURIComponent(id)+"/outputs"),
      api("/api/missions/"+encodeURIComponent(id)+"/audit")
    ]);
    $("detail-title").textContent=job.mission.name;
    const root=document.createElement("div");
    const head=document.createElement("div"); head.className="detail-head";
    const info=document.createElement("div");
    const pill=document.createElement("span"); pill.className="pill"; pill.textContent=job.status;
    const msg=document.createElement("p"); msg.className="muted"; msg.textContent=job.message || "";
    info.append(pill,msg);
    const actions=document.createElement("div"); actions.className="actions";
    if(job.status==="queued") actions.append(action("Run Factory","run",id,"primary"));
    if(job.status==="failed" || job.status==="blocked") actions.append(action("Retry","retry",id,"secondary"));
    if(job.status!=="completed" && job.status!=="cancelled") actions.append(action("Cancel","cancel",id,"danger"));
    head.append(info,actions); root.append(head);
    const oh=document.createElement("h3"); oh.textContent="Outputs"; root.append(oh);
    if(outputs.length) for(const out of outputs) {
      const n=document.createElement("div"); n.className="event";
      const t=document.createElement("b"); t.textContent=(out.name || "output")+" · "+(out.status || "");
      n.append(t);
      if(out.repository) {
        const a=document.createElement("a"); a.href="https://github.com/"+out.repository; a.target="_blank"; a.rel="noopener"; a.className="repo"; a.textContent="Open GitHub repository ↗"; n.append(a);
      }
      root.append(n);
    } else { const e=document.createElement("div"); e.className="empty"; e.textContent="No outputs recorded yet."; root.append(e); }
    const ah=document.createElement("h3"); ah.textContent="Audit trail"; root.append(ah);
    for(const entry of audit.slice().reverse()) {
      const n=document.createElement("div"); n.className="event";
      const t=document.createElement("b"); t.textContent=entry.event_type || "event";
      const m=document.createElement("div"); m.className="muted"; m.textContent=entry.message || "";
      const time=document.createElement("time"); time.textContent=entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "";
      n.append(t,m,time); root.append(n);
    }
    $("details").replaceChildren(root);
  } catch(e) { $("details").textContent="Unable to load mission: "+e.message; }
}

async function runFactory(id) {
  selectedMissionId=id; message("Starting factory…");
  try {
    await api("/api/missions/"+encodeURIComponent(id)+"/factory-run",{method:"POST"});
    message("Factory is running.");
    startPolling(id);
    await showMission(id);
  } catch(e) { message("Factory start failed: "+e.message,true); await refresh(); }
}

async function startPolling(id) {
  if(pollTimer) clearInterval(pollTimer);
  pollTimer=setInterval(async () => {
    try {
      const job=await api("/api/missions/"+encodeURIComponent(id)+"/job");
      $("factory").textContent=terminal.has(job.status) ? "idle" : "running";
      await showMission(id);
      if(terminal.has(job.status)) { clearInterval(pollTimer); pollTimer=null; message("Mission "+job.status+"."); await refresh(); }
    } catch(e) { clearInterval(pollTimer); pollTimer=null; message("Factory monitor: "+e.message,true); }
  },2000);
}

async function launch(e) {
  e.preventDefault();
  if(busy) return;
  const name=$("name").value.trim(), objective=$("objective").value.trim();
  if(!name || !objective) return;
  busy=true; $("launch").disabled=true; message("Creating mission…");
  try {
    const result=await api("/api/missions",{method:"POST",body:JSON.stringify({name,objective})});
    const id=result.mission.id;
    $("mission-form").reset();
    await runFactory(id);
    await refresh();
  } catch(e) { message("Launch failed: "+e.message,true); }
  finally { busy=false; $("launch").disabled=false; }
}

$("mission-form").addEventListener("submit",launch);
$("missions").addEventListener("click",e => {
  const b=e.target.closest(".mission"); if(b) showMission(b.dataset.id);
});
$("details").addEventListener("click",e => {
  const b=e.target.closest("[data-action]"); if(!b) return;
  const id=b.dataset.id;
  if(b.dataset.action==="run") runFactory(id);
  if(b.dataset.action==="retry") (async()=>{try{await api("/api/missions/"+encodeURIComponent(id)+"/retry",{method:"POST"}); await runFactory(id);}catch(x){message("Retry failed: "+x.message,true);}})();
  if(b.dataset.action==="cancel") (async()=>{try{await api("/api/missions/"+encodeURIComponent(id)+"/cancel",{method:"POST"}); await showMission(id); await refresh();}catch(x){message("Cancel failed: "+x.message,true);}})();
});
$("stop").addEventListener("click",async()=>{try{await api("/api/company/stop",{method:"POST"});message("Company stopped.");await refresh();}catch(e){message("Stop failed: "+e.message,true);}});

async function refresh() {
  if(busy && selectedMissionId) return;
  try {
    const [state,missions,events,summary,factory]=await Promise.all([
      api("/api/company/state"),api("/api/missions"),api("/api/company/events"),api("/dashboard/summary"),api("/api/factory/status")
    ]);
    $("live").textContent="company "+state.status;
    $("projects").textContent=summary.projects ?? 0;
    $("tasks").textContent=summary.tasks ?? 0;
    $("agents").textContent=summary.agents ?? 0;
    $("factory").textContent=factory.running ? "running":"idle";
    renderMissions(missions); renderEvents(events);
    if(selectedMissionId && missions.some(x=>x.mission.id===selectedMissionId)) await showMission(selectedMissionId);
  } catch(e) { $("live").textContent="offline"; message(e.message,true); }
}
window.addEventListener("error",e=>message("UI error: "+e.message,true));
window.addEventListener("unhandledrejection",e=>message("UI error: "+(e.reason?.message || e.reason),true));
refresh();
setInterval(refresh,5000);
})();