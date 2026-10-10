(() => {
"use strict";
const $ = id => document.getElementById(id);
const terminal = new Set(["completed","failed","blocked","cancelled"]);
let workspace = null;
let projects = [];
let missions = [];
let refreshing = false;
let toastTimer = null;

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    cache: "no-store",
    ...options,
    headers: {"Accept":"application/json", ...(options.body ? {"Content-Type":"application/json"} : {}), ...(options.headers || {})}
  });
  if (response.status === 204) return null;
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch (_) { data = {detail:text}; }
  if (!response.ok) throw new Error(data.detail || ("Request failed (" + response.status + ")"));
  return data;
}
function notify(text, error = false) {
  const node = $("toast");
  node.textContent = text;
  node.style.borderColor = error ? "#8d3b55" : "";
  node.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove("show"), 4500);
}
function node(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}
function action(label, cls, handler) {
  const b = node("button", "button " + cls, label);
  b.type = "button";
  b.addEventListener("click", () => handler(b));
  return b;
}
function showMessage(text, error = false) {
  const el = $("form-message");
  el.textContent = text || "";
  el.className = "message" + (error ? " error" : "");
}
function setSignedIn(user) {
  $("signed-out").hidden = Boolean(user);
  $("workspace").hidden = !user;
  $("logout").hidden = !user;
  $("account-label").textContent = user ? (user.display_name || user.email || "Signed in") : "Not signed in";
}
function statusPill(status) {
  return node("span", "pill " + String(status || "").toLowerCase(), String(status || "unknown"));
}
function renderProjects() {
  const box = $("projects-list");
  box.replaceChildren();
  if (!projects.length) { box.append(node("p","muted","No projects yet. Create one to get started.")); return; }
  for (const project of projects) {
    const card = node("article","item");
    const top = node("div","item-top");
    const title = node("h3","",project.name);
    top.append(title,statusPill(project.status));
    card.append(top,node("p","",project.objective || project.description || "No project brief supplied."));
    if (project.repository) {
      const a=node("a","button secondary","Open repository ↗");
      a.href="https://github.com/"+project.repository; a.target="_blank"; a.rel="noopener";
      const actions=node("div","item-actions"); actions.append(a); card.append(actions);
    }
    if (project.mission_id) {
      const job=missions.find(m=>m.id===project.mission_id);
      if (job) card.append(node("p","muted",job.message || "Factory mission linked."));
    }
    const actions=node("div","item-actions");
    if (project.status === "planned" || project.status === "queued") {
      const launch=action(project.status==="queued" ? "Resume factory run ↻" : "Launch factory ✦","primary",button=>launchProject(project,button));
      actions.append(launch);
    }
    if (project.mission_id && project.status !== "planned") {
      const view=action("View run details","secondary",()=>document.getElementById("mission-"+project.mission_id)?.scrollIntoView({behavior:"smooth",block:"center"}));
      actions.append(view);
    }
    if (actions.childElementCount) card.append(actions);
    box.append(card);
  }
}
function renderMissions() {
  const box=$("missions-list"); box.replaceChildren();
  const active=missions.filter(m=>!terminal.has(m.status));
  $("mission-summary").textContent=missions.length+" runs · "+active.length+" active";
  if (!missions.length) {box.append(node("p","muted","No factory runs yet. Launch a project to see progress here."));return;}
  for (const mission of missions) {
    const card=node("article","item"); card.id="mission-"+mission.id;
    const top=node("div","item-top");
    top.append(node("h3","",mission.name),statusPill(mission.status));
    card.append(top,node("p","",mission.message || mission.objective || "No status message yet."));
    const meta=node("p","muted","Attempts: "+(mission.attempts ?? 0)+(mission.updated_at ? " · Updated "+new Date(mission.updated_at).toLocaleString() : ""));
    card.append(meta);
    const stages=Array.isArray(mission.stages) ? mission.stages : [];
    if (stages.length) {
      const completed=stages.filter(stage=>stage.status==="completed").length;
      const progress=node("div","stage-progress");
      const progressHead=node("div","stage-progress-head");
      progressHead.append(node("span","","Factory stages"),node("span","muted",completed+" / "+stages.length+" complete"));
      const meter=node("div","meter stage-meter");
      const fill=node("i","");
      fill.style.width=(completed/stages.length*100)+"%";
      meter.append(fill);
      progress.append(progressHead,meter);
      const stageList=node("div","stage-list");
      for (const stage of stages) {
        const row=node("div","stage-row");
        row.append(statusPill(stage.status),node("span","stage-name",String(stage.name||"Stage").replaceAll("_"," ")));
        if (stage.detail) row.append(node("p","stage-detail",stage.detail));
        stageList.append(row);
      }
      progress.append(stageList);
      card.append(progress);
    }
    const actions=node("div","item-actions");
    if (mission.status==="failed" || mission.status==="blocked") {
      const retry=action("Retry run ↻","primary",button=>retryMission(mission.id,button));
      actions.append(retry);
    }
    if (mission.status==="completed") {
      const preview=action("Open product ↗","primary",()=>window.open("/customer/products/"+encodeURIComponent(mission.id),"_blank","noopener"));
      actions.append(preview);
      const outputs=action("View outputs","secondary",()=>showOutputs(mission.id,card));
      actions.append(outputs);
    }
    if (actions.childElementCount) card.append(actions);
    box.append(card);
  }
}
async function showOutputs(id, card) {
  let section=card.querySelector(".output-list");
  if (section) {section.remove();return;}
  section=node("div","output-list");
  section.append(node("p","muted","Loading outputs…")); card.append(section);
  try {
    const result=await api("/api/customer/missions/"+encodeURIComponent(id)+"/outputs");
    section.replaceChildren();
    if (!result.items?.length) {section.append(node("p","muted","No output records returned."));return;}
    for (const output of result.items) {
      const row=node("div","item");
      row.append(node("h3","",output.name || "Output"),node("p","muted",output.status || "Recorded output"));
      if (output.repository) {
        const a=node("a","button secondary","Open GitHub repository ↗");
        a.href="https://github.com/"+output.repository;a.target="_blank";a.rel="noopener";row.append(a);
      }
      section.append(row);
    }
  } catch (e) {section.replaceChildren(node("p","message error","Could not load outputs: "+e.message));}
}
async function launchProject(project, button) {
  if(button) button.disabled=true;
  showMessage("Sending project to the factory…");
  try {
    const result=await api("/api/customer/projects/"+encodeURIComponent(project.id)+"/launch",{method:"POST"});
    showMessage(result.already_launched ? "This project is already linked to a factory run." : "Project accepted by the factory.");
    await refresh();
  } catch(e) {
    showMessage(e.message,true);
    notify(e.message,true);
    await refresh();
  } finally {if(button)button.disabled=false;}
}
async function retryMission(id, button) {
  if (button) { button.disabled = true; button.textContent = "Retrying…"; }
  notify("Re-queueing the failed mission…");
  try {
    await api("/api/customer/missions/" + encodeURIComponent(id) + "/retry", {method:"POST"});
    notify("Mission queued for another factory attempt.");
    await refresh();
  } catch (e) {
    notify(e.message, true);
    await refresh();
  } finally {
    if (button) { button.disabled = false; button.textContent = "Retry run ↻"; }
  }
}
async function createProject(event) {
  event.preventDefault();
  const name=$("project-name").value.trim(), objective=$("project-objective").value.trim(), description=$("project-description").value.trim();
  if(!name || !objective) {showMessage("Enter a project name and describe what it should do.",true);return;}
  $("create-project").disabled=true;showMessage("Creating project…");
  try {
    await api("/api/customer/projects",{method:"POST",body:JSON.stringify({name,objective,description})});
    $("project-form").reset();showMessage("Project created. Review it below and launch when ready.");
    await refresh();
  } catch(e) {showMessage(e.message,true);}
  finally {$("create-project").disabled=false;}
}
async function refresh() {
  if(refreshing || $("workspace").hidden) return;
  refreshing=true;
  try {
    const [workspaceData, projectData, missionData] = await Promise.all([
      api("/api/customer/workspace"),
      api("/api/customer/projects"),
      api("/api/customer/missions")
    ]);
    workspace=workspaceData;projects=projectData.items || [];missions=missionData.items || [];
    $("welcome-title").textContent="Welcome"+(workspace.user.display_name ? ", "+workspace.user.display_name.split(" ")[0] : "")+".";
    $("plan-name").textContent=(workspace.plan || "demo")+" plan · "+(workspace.subscription_status || "unknown");
    const used=Number(workspace.usage.runs_used||0), limit=Number(workspace.usage.monthly_run_limit||0);
    $("usage-label").textContent=used+" / "+limit+" monthly runs used";
    $("usage-meter").style.width=(limit ? Math.min(100,used/limit*100) : 0)+"%";
    $("project-limit").textContent=projects.length+" / "+workspace.usage.project_limit+" projects used";
    $("metric-projects").textContent=projects.length;
    $("metric-active").textContent=missions.filter(m=>!terminal.has(m.status)).length;
    $("metric-completed").textContent=missions.filter(m=>m.status==="completed").length;
    $("metric-remaining").textContent=Math.max(0,limit-used);
    renderProjects();renderMissions();
  } catch(e) {
    if(e.message==="Sign-in required" || e.message.includes("Session is invalid") || e.message.includes("401")) {
      setSignedIn(null);
    } else {notify("Workspace refresh failed: "+e.message,true);}
  } finally {refreshing=false;}
}
async function init() {
  try {
    const user=await api("/auth/me");
    setSignedIn(user);
    $("logout").addEventListener("click",async()=>{try{await api("/auth/logout",{method:"POST"});}finally{window.location.href="/customer";}});
    $("project-form").addEventListener("submit",createProject);
    $("refresh").addEventListener("click",()=>refresh());
    await refresh();
    setInterval(refresh,5000);
  } catch(e) {
    setSignedIn(null);
  }
}
init();
})();
