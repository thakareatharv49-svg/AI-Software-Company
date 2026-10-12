(() => {
"use strict";
const $ = id => document.getElementById(id);
const terminal = new Set(["completed","blocked","failed","cancelled"]);
let selectedMissionId = null;
let pollTimer = null;
let busy = false;
let browserProductIds = new Set();

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

function ensureUiElements() {
  const main = document.querySelector(".main");
  if (main && !$("products")) {
    const section = document.createElement("section");
    section.className = "card products-card";
    section.innerHTML = '<div class="section-heading"><div><h2>Completed Products</h2><p class="muted">Open finished browser products directly from the factory.</p></div><small id="product-count" class="section-count"></small></div><div id="products" class="products"><div class="empty">Checking generated products…</div></div>';
    const stats = main.querySelector(".stats");
    if (stats) stats.insertAdjacentElement("afterend", section);
    else main.prepend(section);
  }
  if (!$("message")) {
    const form = $("mission-form");
    if (form) {
      const node = document.createElement("div");
      node.id = "message";
      node.className = "message";
      form.insertAdjacentElement("afterend", node);
    }
  }
}

function message(text, error=false) {
  const node = $("message");
  if (!node) return;
  node.textContent = text || "";
  node.className = "message " + (error ? "error" : "");
}

function renderPipeline(audit, status) {
  const steps = [["plan","Plan","Mission controller"],["generate","Generate","Local Ollama"],["validate","Validate","Tests + QA + security"],["repair","Repair","Autonomous retry loop"],["review","Review","Your acceptance checklist"],["publish","Publish","GitHub after approval"]];
  const types = audit.map(e => String(e.event_type || "").toUpperCase());
  let current = "plan";
  if (types.some(t => /GENERAT|PROJECT_STARTED|FACTORY_PROJECT_STARTED/.test(t))) current = "generate";
  if (types.some(t => /VALIDAT|TEST|QA|PROJECT_COMPLETED/.test(t))) current = "validate";
  if (types.some(t => /REPAIR/.test(t))) current = "repair";
  if (status === "completed") current = "review";
  if (types.some(t => /PRODUCT_PUBLISHED|GITHUB_PUBLISH_SUCCEEDED/.test(t))) current = "publish";
  const box = $("pipeline"); box.replaceChildren();
  const order = steps.map(s => s[0]), currentIndex = order.indexOf(current);
  for (const [key,title,desc] of steps) {
    const row=document.createElement("div"), index=order.indexOf(key);
    const done = key === "publish" ? types.some(t => /PRODUCT_PUBLISHED|GITHUB_PUBLISH_SUCCEEDED/.test(t)) : index < currentIndex;
    row.className="pipeline-step " + (done ? "done " : "") + (index===currentIndex && !done ? "active" : "");
    const marker=document.createElement("b"); marker.textContent=done ? "✓" : String(index+1).padStart(2,"0");
    const label=document.createElement("span"); label.textContent=title;
    const detail=document.createElement("small"); detail.textContent=desc;
    row.append(marker,label,detail); box.append(row);
  }
}

function renderMissions(items) {
  const visible = items.slice(0, 20);
  $("mission-count").textContent = items.length > 20 ? `Latest 20 of ${items.length}` : `${items.length} total`;
  const box = $("missions");
  box.replaceChildren();
  if (!visible.length) {
    const e=document.createElement("div"); e.className="empty"; e.textContent="No missions yet."; box.append(e); return;
  }
  for (const item of visible) {
    const b=document.createElement("button"); b.type="button"; b.className="mission";
    b.dataset.id=item.mission.id;
    const left=document.createElement("div");
    const title=document.createElement("strong"); title.textContent=item.mission.name;
    const desc=document.createElement("p"); desc.textContent=item.mission.objective;
    left.append(title,desc);
    const pill=document.createElement("span"); pill.className="pill"; pill.textContent=item.status;
    b.append(left,pill);
    if (String(item.status || "").toLowerCase() === "completed" && browserProductIds.has(item.mission.id)) {
      const open=document.createElement("a");
      open.href="/product/" + encodeURIComponent(item.mission.id);
      open.target="_blank"; open.rel="noopener";
      open.className="product-open"; open.textContent="Open Product ↗";
      open.addEventListener("click", event => event.stopPropagation());
      b.append(open);
    } box.append(b);
  }
}


function renderProducts(items) {
  if (!$("products") || !$("product-count")) return;
  const completed = Array.isArray(items) ? items : [];
  $("product-count").textContent = completed.length ? completed.length + " ready" : "";
  const box = $("products");
  box.replaceChildren();
  if (!completed.length) {
    const e = document.createElement("div");
    e.className = "empty";
    e.textContent = "No completed browser products yet.";
    box.append(e);
    return;
  }
  for (const item of completed.slice(0, 12)) {
    const card = document.createElement("div");
    card.className = "product";
    const info = document.createElement("div");
    const mission = item.mission && typeof item.mission === "object" ? item.mission : {};
    const title = document.createElement("strong");
    title.textContent = mission.name || item.name || "Generated browser product";
    const desc = document.createElement("p");
    desc.className = "muted";
    desc.textContent = mission.objective || item.objective || "Open the completed product preview.";
    info.append(title, desc);
    const open = document.createElement("a");
    open.className = "primary product-open";
    open.href = item.product_url || item.url || ("/product/" + encodeURIComponent(item.mission_id || mission.id || item.id || ""));
    open.target = "_blank";
    open.rel = "noopener";
    open.textContent = "Open Product ↗";
    card.append(info, open);
    box.append(card);
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

function suggestedRequirements(objective) {
  const clauses = String(objective || "")
    .split(/\n+|[.;]\s*/)
    .flatMap(part => part.includes(",") ? part.split(",") : [part])
    .map(part => part.replace(/^\s*[-*•]\s*/, "").trim())
    .filter(part => part.length >= 8);
  const unique = [...new Set(clauses)];
  return (unique.length ? unique : [String(objective || "Verify the requested product")])
    .slice(0, 30);
}

function reviewButton(label, onClick, className="secondary") {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

async function renderReviewPanel(root, id, job) {
  const panel = document.createElement("section");
  panel.className = "event review-panel";
  const heading = document.createElement("h3");
  heading.textContent = "Product review & approval";
  panel.append(heading);
  root.append(panel);

  let review;
  try {
    review = await api("/api/missions/" + encodeURIComponent(id) + "/review");
  } catch (error) {
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = "Review workflow unavailable: " + error.message;
    panel.append(note);
    return;
  }
  if (selectedMissionId !== id) return;

  const status = document.createElement("p");
  status.className = "muted";
  status.textContent = "Status: " + review.status.replaceAll("_", " ")
    + " · Revision " + review.revision
    + " · QA " + (review.qa_passed ? "passed" : "not verified")
    + " · Security " + (review.security_passed ? "passed" : "not verified");
  panel.append(status);

  for (const entry of review.feedback || []) {
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = "Feedback: " + entry.message;
    panel.append(note);
  }

  if ((review.status === "draft" || review.status === "changes_requested") && job.status === "completed") {
    const hint = document.createElement("p");
    hint.className = "muted";
    hint.textContent = "Edit the acceptance checklist, then submit the working product for your review.";
    const checklist = document.createElement("textarea");
    checklist.rows = 7;
    checklist.maxLength = 20000;
    checklist.setAttribute("aria-label", "Acceptance checklist, one requirement per line");
    checklist.value = review.requirements?.length
      ? review.requirements.map(item => item.description).join("\n")
      : suggestedRequirements(job.mission.objective).join("\n");
    const submit = reviewButton("Submit for review", async () => {
      const requirements = checklist.value.split("\n").map(line => line.trim()).filter(Boolean);
      if (!requirements.length) {
        message("Add at least one acceptance requirement.", true);
        return;
      }
      submit.disabled = true;
      try {
        await api("/api/missions/" + encodeURIComponent(id) + "/review/submit", {
          method: "POST",
          body: JSON.stringify({requirements: requirements.map(description => ({
            description,
            verification: "Verify this requirement in the product preview and automated checks"
          }))})
        });
        message("Product is ready for your review.");
        await showMission(id);
      } catch (error) {
        message("Could not submit product for review: " + error.message, true);
      } finally {
        submit.disabled = false;
      }
    }, "primary");
    panel.append(hint, checklist, submit);
  }

  if (review.status === "in_review") {
    const listTitle = document.createElement("h4");
    listTitle.textContent = "Acceptance checklist";
    panel.append(listTitle);
    for (const requirement of review.requirements || []) {
      const item = document.createElement("div");
      item.className = "event review-requirement";
      const description = document.createElement("strong");
      description.textContent = requirement.description;
      const detail = document.createElement("p");
      detail.className = "muted";
      detail.textContent = (requirement.verification || "Verify the expected behavior")
        + " · " + requirement.status;
      const evidence = document.createElement("input");
      evidence.type = "text";
      evidence.maxLength = 4000;
      evidence.placeholder = "Evidence or test result (optional)";
      evidence.value = requirement.evidence || "";
      evidence.setAttribute("aria-label", "Verification evidence for " + requirement.description);
      const save = reviewButton("Save verification", async () => {
        save.disabled = true;
        try {
          await api("/api/missions/" + encodeURIComponent(id) + "/review/requirements/"
            + encodeURIComponent(requirement.id), {
            method: "PATCH",
            body: JSON.stringify({
              status: selector.value,
              evidence: evidence.value.trim() || null
            })
          });
          await showMission(id);
        } catch (error) {
          message("Could not update requirement: " + error.message, true);
        } finally {
          save.disabled = false;
        }
      });
      const selector = document.createElement("select");
      for (const [value, label] of [["pending", "Not checked"], ["passed", "Passed"], ["failed", "Failed"]]) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        selector.append(option);
      }
      selector.value = requirement.status;
      item.append(description, detail, selector, evidence, save);
      panel.append(item);
    }

    const feedback = document.createElement("textarea");
    feedback.rows = 3;
    feedback.maxLength = 10000;
    feedback.placeholder = "What should the company change or add?";
    feedback.setAttribute("aria-label", "Revision feedback");
    const revise = reviewButton("Request changes & rebuild", async () => {
      if (!feedback.value.trim()) {
        message("Describe what you want changed before requesting a revision.", true);
        return;
      }
      revise.disabled = true;
      try {
        await api("/api/missions/" + encodeURIComponent(id) + "/review/feedback", {
          method: "POST",
          body: JSON.stringify({message: feedback.value.trim()})
        });
        message("Feedback saved. The company is rebuilding this mission.");
        startPolling(id);
        await showMission(id);
      } catch (error) {
        message("Could not request a revision: " + error.message, true);
      } finally {
        revise.disabled = false;
      }
    }, "secondary");
    const approve = reviewButton("Approve product", async () => {
      approve.disabled = true;
      try {
        await api("/api/missions/" + encodeURIComponent(id) + "/review/approve", {method: "POST"});
        message("Product approved. You can now publish it to GitHub.");
        await showMission(id);
      } catch (error) {
        message("Approval blocked: " + error.message, true);
      } finally {
        approve.disabled = false;
      }
    }, "primary");
    approve.disabled = !(review.requirements?.length
      && review.requirements.every(item => item.status === "passed"));
    panel.append(feedback, revise, approve);
  }

  if (review.status === "approved") {
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = "You approved this revision. Publishing will create or update its GitHub repository.";
    const publish = reviewButton("Publish approved product to GitHub", async () => {
      publish.disabled = true;
      try {
        const result = await api("/api/missions/" + encodeURIComponent(id) + "/review/publish", {method: "POST"});
        message("Published approved product to GitHub.");
        await showMission(id);
      } catch (error) {
        message("Publishing failed: " + error.message, true);
      } finally {
        publish.disabled = false;
      }
    }, "primary");
    panel.append(note, publish);
  }

  if (review.status === "published" && review.repository_url) {
    const link = document.createElement("a");
    link.href = review.repository_url;
    link.target = "_blank";
    link.rel = "noopener";
    link.className = "primary product-open";
    link.textContent = "Open approved GitHub repository ↗";
    panel.append(link);
  }
}

function renderMissionDiagnostics(root, job) {
  const plan = job && job.plan && typeof job.plan === "object" ? job.plan : {};
  const hasDiagnostics = [
    "generation_model_calls", "generation_duration_ms",
    "generation_prompt_tokens", "generation_output_tokens",
    "qa_status", "security_status"
  ].some(key => plan[key] !== null && plan[key] !== undefined);
  if (!hasDiagnostics) return;

  const panel = document.createElement("section");
  panel.className = "event";
  const heading = document.createElement("h3");
  heading.textContent = "Generation & QA diagnostics";
  panel.append(heading);

  const seconds = value => Number.isFinite(value) ? (value / 1000).toFixed(1) + " s" : "—";
  const rows = [
    ["Generation model calls", plan.generation_model_calls],
    ["Generation duration", plan.generation_duration_ms == null ? null : seconds(plan.generation_duration_ms)],
    ["Prompt tokens", plan.generation_prompt_tokens],
    ["Generated tokens", plan.generation_output_tokens],
    ["QA runner status", plan.qa_status],
    ["QA exit code", plan.qa_exit_code],
    ["QA duration", plan.qa_duration_ms == null ? null : seconds(plan.qa_duration_ms)],
    ["QA command", Array.isArray(plan.qa_command) ? plan.qa_command.join(" ") : null],
    ["Security review", plan.security_status],
    ["Security summary", plan.security_summary]
  ];
  for (const [label, value] of rows) {
    if (value === null || value === undefined || value === "") continue;
    const row = document.createElement("p");
    row.className = "muted";
    row.textContent = label + ": " + String(value);
    panel.append(row);
  }
  root.append(panel);
}

async function showMission(id) {
  selectedMissionId = id;
  const details = $("details");
  const title = $("detail-title");
  details.textContent = "Loading mission…";

  try {
    // Load the job first so selection works immediately even while the
    // factory is still generating, testing, repairing, or publishing.
    const job = await api("/api/missions/" + encodeURIComponent(id) + "/job");
    title.textContent = job.mission.name;
    renderPipeline([], job.status);

    const root = document.createElement("div");
    const head = document.createElement("div");
    head.className = "detail-head";

    const info = document.createElement("div");
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = job.status;
    const msg = document.createElement("p");
    msg.className = "muted";
    msg.textContent = job.message || "Mission is running.";
    info.append(pill, msg);

    const actions = document.createElement("div");
    actions.className = "actions";
    if (job.status === "queued") actions.append(action("Run Factory", "run", id, "primary"));
    const initialProducts = await api("/api/products").catch(() => []);
    const hasBrowserPreview = Array.isArray(initialProducts) && initialProducts.some(product => product.mission_id === id);
    if (String(job.status || "").toLowerCase() === "completed" && hasBrowserPreview) {
      const product = document.createElement("a");
      product.href = "/product/" + encodeURIComponent(id);
      product.target = "_blank";
      product.rel = "noopener";
      product.className = "primary product-open";
      product.textContent = "Open Product ↗";
      actions.append(product);
    }
    if (job.status === "failed" || job.status === "blocked") actions.append(action("Retry", "retry", id, "secondary"));
    if (job.status !== "completed" && job.status !== "cancelled") {
      actions.append(action("Cancel", "cancel", id, "danger"));
    }

    head.append(info, actions);
    root.append(head);

    const loading = document.createElement("div");
    loading.className = "empty";
    loading.textContent = "Loading outputs and audit trail…";
    root.append(loading);
    details.replaceChildren(root);

    // Outputs and audit are secondary. If either is temporarily unavailable,
    // keep the mission details visible instead of replacing the whole panel.
    const [outputsResult, auditResult, productsResult] = await Promise.allSettled([
      api("/api/missions/" + encodeURIComponent(id) + "/outputs"),
      api("/api/missions/" + encodeURIComponent(id) + "/audit"),
      api("/api/products")
    ]);

    if (selectedMissionId !== id) return;

    const outputs = outputsResult.status === "fulfilled" ? outputsResult.value : [];
    const audit = auditResult.status === "fulfilled" ? auditResult.value : [];
    const productIds = productsResult.status === "fulfilled" && Array.isArray(productsResult.value)
      ? new Set(productsResult.value.map(product => product.mission_id))
      : browserProductIds;
    const hasBrowserPreviewAfterRefresh = productIds.has(id);

    renderPipeline(audit, job.status);
    root.removeChild(loading);

    const oh = document.createElement("h3");
    oh.textContent = "Outputs";
    root.append(oh);

    if (outputs.length) {
      for (const out of outputs) {
        const n = document.createElement("div");
        n.className = "event";
        const t = document.createElement("b");
        t.textContent = (out.name || "output") + " · " + (out.status || "");
        n.append(t);
        if (job.status === "completed" && hasBrowserPreviewAfterRefresh) {
          const a = document.createElement("a");
          a.href = out.product_url || "/product/" + encodeURIComponent(id);
          a.target = "_blank";
          a.rel = "noopener";
          a.className = "primary product-open";
          a.textContent = "Open Completed Product ↗";
          n.append(a);
        }
        if (out.repository) {
          const a = document.createElement("a");
          a.href = "https://github.com/" + out.repository;
          a.target = "_blank";
          a.rel = "noopener";
          a.className = "repo";
          a.textContent = "Open GitHub repository ↗";
          n.append(a);
        }
        root.append(n);
      }
    } else {
      const e = document.createElement("div");
      e.className = "empty";
      e.textContent = "No outputs recorded yet.";
      root.append(e);
    }

    const ah = document.createElement("h3");
    ah.textContent = "Audit trail";
    root.append(ah);

    if (audit.length) {
      for (const entry of audit.slice().reverse()) {
        const n = document.createElement("div");
        n.className = "event";
        const t = document.createElement("b");
        t.textContent = entry.event_type || "event";
        const m = document.createElement("div");
        m.className = "muted";
        m.textContent = entry.message || "";
        const time = document.createElement("time");
        time.textContent = entry.timestamp ? new Date(entry.timestamp).toLocaleString() : "";
        n.append(t, m, time);
        root.append(n);
      }
    } else {
      const e = document.createElement("div");
      e.className = "empty";
      e.textContent = auditResult.status === "rejected"
        ? "Audit trail is temporarily unavailable."
        : "No audit events yet.";
      root.append(e);
    }

    renderMissionDiagnostics(root, job);
    if (job.status === "completed") {
      await renderReviewPanel(root, id, job);
    }
  } catch (e) {
    if (selectedMissionId === id) {
      title.textContent = "Mission details";
      details.textContent = "Unable to load mission: " + e.message;
    }
  }
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
$("cleanup-missions")?.addEventListener("click", async () => {
  const button = $("cleanup-missions");
  if (!confirm("Delete ALL queued and blocked missions? Completed products and generated files will be kept. This cannot be undone.")) return;
  if (button) button.disabled = true;
  try {
    const result = await api("/api/missions/cleanup", {method: "POST"});
    if (selectedMissionId && (result.deleted_ids || []).includes(selectedMissionId)) {
      selectedMissionId = null;
      $("detail-title").textContent = "Mission details";
      $("details").textContent = "Select a mission to inspect outputs and audit trail.";
    }
    message("Deleted " + result.deleted_count + " queued/blocked mission(s). Completed products and files were kept.");
    await refresh();
  } catch (e) {
    message("Cleanup failed: " + e.message, true);
  } finally {
    if (button) button.disabled = false;
  }
});

$("stop").addEventListener("click",async()=>{try{await api("/api/company/stop",{method:"POST"});message("Company stopped.");await refresh();}catch(e){message("Stop failed: "+e.message,true);}});

async function refresh() {
  ensureUiElements();
  if(busy && selectedMissionId) return;

  // Keep the core dashboard alive even if one secondary endpoint is briefly
  // unavailable. Previously Promise.all() turned one failed request into a
  // completely "offline" UI and cleared the user's useful state.
  try {
    const state = await api("/api/company/state");
    $("live").textContent = "company " + (state.status || "unknown");
  } catch (e) {
    $("live").textContent = "offline";
    message("Company state unavailable: " + e.message, true);
    return;
  }

  const [missionsResult, eventsResult, summaryResult, factoryResult, productsResult] =
    await Promise.allSettled([
      api("/api/missions"),
      api("/api/company/events"),
      api("/dashboard/summary"),
      api("/api/factory/status"),
      api("/api/products"),
    ]);

  if (missionsResult.status === "rejected") {
    message("Mission service unavailable: " + missionsResult.reason.message, true);
    return;
  }

  const missions = Array.isArray(missionsResult.value) ? missionsResult.value : [];
  const events = eventsResult.status === "fulfilled" && Array.isArray(eventsResult.value)
    ? eventsResult.value
    : [];
  const summary = summaryResult.status === "fulfilled" ? summaryResult.value : {};
  const factory = factoryResult.status === "fulfilled" ? factoryResult.value : {running: false};
  const products = productsResult.status === "fulfilled" && Array.isArray(productsResult.value)
    ? productsResult.value
    : [];
  browserProductIds = new Set(products.map(product => product.mission_id));

  $("projects").textContent = summary.projects ?? missions.length;
  $("tasks").textContent = summary.tasks ?? missions.reduce(
    (total, item) => total + (Array.isArray(item.plan?.steps) ? item.plan.steps.length : 0), 0
  );
  $("agents").textContent = summary.agents ?? "—";
  $("factory").textContent = factory.running ? "building" : (factory.continuous ? "continuous" : "idle");

  renderMissions(missions);
  renderProducts(products.map(product => ({
    mission: missions.find(item => item.mission.id === product.mission_id)?.mission
      || {name: product.mission_id, objective: "Generated browser product"},
    product_url: product.url,
    url: product.url,
  })));
  renderEvents(events);

  // Do not rebuild the selected detail panel on every 5-second refresh.
  // startPolling()/showMission() already owns live detail updates and this
  // prevents completed mission details from flickering or disappearing.
}
window.addEventListener("error",e=>message("UI error: "+e.message,true));
window.addEventListener("unhandledrejection",e=>message("UI error: "+(e.reason?.message || e.reason),true));
ensureUiElements();
refresh();
setInterval(refresh,5000);
})();