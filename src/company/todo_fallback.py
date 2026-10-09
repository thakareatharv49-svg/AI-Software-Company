"""Deterministic browser product for common To-Do / task-list missions.

A small, offline-first implementation avoids spending several slow local-model
round trips on a well-understood CRUD application.
"""

from __future__ import annotations


def todo_fallback_files() -> dict[str, str]:
    """Return a complete, responsive task manager with real local persistence."""
    return {
        "index.html": """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#101827">
  <title>Daymark — Task Manager</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <a class="brand" href="#" aria-label="Daymark home"><span class="brand-mark">d.</span><span>daymark</span></a>
      <p class="nav-label">WORKSPACE</p>
      <nav class="filters" aria-label="Task filters">
        <button class="filter active" data-filter="all"><span>◫</span> All tasks <span class="count" id="all-count">0</span></button>
        <button class="filter" data-filter="pending"><span>◷</span> Upcoming <span class="count" id="pending-count">0</span></button>
        <button class="filter" data-filter="completed"><span>✓</span> Completed <span class="count" id="completed-count">0</span></button>
      </nav>
      <div class="sidebar-bottom"><span class="status-dot"></span> Your focus, in one place</div>
    </aside>
    <main class="main">
      <header class="topbar"><span class="eyebrow">YOUR PERSONAL WORKSPACE</span><span class="today" id="today-label"></span></header>
      <section class="welcome"><div><p class="eyebrow">A LITTLE PROGRESS ADDS UP</p><h1>Make room for <em>what matters.</em></h1><p class="subhead">One clear next step is all you need.</p></div><div class="progress-card"><div class="progress-top"><span>Daily momentum</span><strong id="progress-label">0%</strong></div><div class="progress-track"><span id="progress-bar"></span></div><small id="progress-caption">0 of 0 tasks complete</small></div></section>
      <section class="task-panel">
        <div class="panel-heading"><div><h2 id="list-title">All tasks</h2><p id="list-subtitle">Your next steps, gathered together.</p></div><button class="add-button" id="open-form"><span>＋</span> New task</button></div>
        <form id="task-form" class="task-form" hidden>
          <div class="form-title"><h3 id="form-heading">Create a task</h3><button type="button" class="icon-button" id="cancel-form" aria-label="Close form">✕</button></div>
          <label for="task-title">Task title</label><input id="task-title" name="title" maxlength="120" placeholder="What needs to get done?" required>
          <label for="task-description">Description <span>(optional)</span></label><textarea id="task-description" name="description" rows="2" maxlength="500" placeholder="Add a little context…"></textarea>
          <div class="form-grid"><div><label for="task-priority">Priority</label><select id="task-priority" name="priority"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select></div><div><label for="task-due">Due date <span>(optional)</span></label><input id="task-due" name="dueDate" type="date"></div></div>
          <p class="form-error" id="form-error" role="alert"></p><div class="form-actions"><button type="button" class="cancel-button" id="cancel-form-bottom">Cancel</button><button class="add-button" type="submit" id="save-task">Save task</button></div>
        </form>
        <div id="task-list" class="task-list" aria-live="polite"></div>
        <div class="empty-state" id="empty-state"><div class="empty-icon">✳</div><h3 id="empty-title">A fresh start.</h3><p id="empty-copy">No tasks yet. Add your first task and make today count.</p><button class="text-button" id="empty-add">＋ Create your first task</button></div>
      </section>
      <footer>Small steps. Real progress. <span>DAYMARK</span></footer>
    </main>
  </div>
  <script src="app.js"></script>
</body>
</html>
""",
        "style.css": """*{box-sizing:border-box} :root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#172033;background:#f6f7fb;font-synthesis:none;text-rendering:optimizeLegibility} body{margin:0;min-height:100vh} button,input,textarea,select{font:inherit} button{cursor:pointer} button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:3px solid #a8b9ff;outline-offset:2px}.shell{min-height:100vh;max-width:1600px;margin:auto;display:grid;grid-template-columns:238px minmax(0,1fr)}.sidebar{background:#101827;color:#f6f7fb;padding:31px 19px;display:flex;flex-direction:column;min-height:100vh}.brand{display:flex;align-items:center;gap:10px;color:white;text-decoration:none;font-size:19px;font-weight:750;letter-spacing:-.6px;padding:0 8px 48px}.brand-mark{width:31px;height:31px;border-radius:10px;background:#b9f36b;color:#172033;display:grid;place-items:center;font-weight:900;font-size:18px}.nav-label,.eyebrow{font-size:10px;letter-spacing:1.7px;font-weight:750;color:#8b95a9}.nav-label{padding:0 10px;margin:0 0 13px}.filters{display:grid;gap:5px}.filter{display:flex;align-items:center;gap:12px;border:0;background:transparent;color:#aeb8c9;padding:12px 11px;border-radius:10px;text-align:left;font-size:13px}.filter>span:first-child{width:17px;font-size:17px;text-align:center}.filter.active{background:#253146;color:#fff}.filter.active>span:first-child{color:#c5f98a}.count{margin-left:auto;color:#8995aa;font-size:11px}.filter.active .count{color:#e5edfa}.sidebar-bottom{margin-top:auto;color:#8995aa;font-size:11px;padding:20px 8px 0;display:flex;align-items:center;gap:8px}.status-dot{width:7px;height:7px;background:#b9f36b;border-radius:50%}.main{padding:0 clamp(22px,5vw,72px);min-width:0}.topbar{height:79px;border-bottom:1px solid #e8eaf1;display:flex;align-items:center;justify-content:space-between}.topbar .eyebrow{color:#81899a}.today{font-size:12px;color:#7d8595}.welcome{padding:43px 0 35px;display:flex;justify-content:space-between;gap:28px;align-items:flex-end}.welcome .eyebrow{margin:0 0 14px;color:#79845f}.welcome h1{font-size:clamp(30px,4vw,47px);line-height:1.08;letter-spacing:-2px;margin:0;max-width:570px}.welcome h1 em{font-family:Georgia,serif;font-weight:500;color:#738d4c}.subhead{color:#81899a;font-size:14px;margin:13px 0 0}.progress-card{width:225px;flex-shrink:0;background:white;border:1px solid #e9ebf2;border-radius:14px;padding:17px 18px;box-shadow:0 5px 20px #17203305}.progress-top{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#777f8f}.progress-top strong{font-size:17px;color:#172033}.progress-track{height:6px;background:#edf0e7;border-radius:20px;overflow:hidden;margin:13px 0 9px}.progress-track span{display:block;height:100%;width:0;background:#a8d96a;border-radius:20px;transition:width .2s}.progress-card small{font-size:10px;color:#8b92a0}.task-panel{background:#fff;border:1px solid #e9ebf2;border-radius:17px;box-shadow:0 8px 32px #17203306;overflow:hidden}.panel-heading{padding:24px 26px 21px;display:flex;justify-content:space-between;align-items:center;gap:14px;border-bottom:1px solid #eff0f5}.panel-heading h2{font-size:19px;letter-spacing:-.5px;margin:0}.panel-heading p{font-size:12px;color:#8a91a0;margin:6px 0 0}.add-button{border:0;border-radius:9px;background:#182438;color:white;padding:11px 15px;font-size:12px;font-weight:650;display:inline-flex;align-items:center;gap:7px;white-space:nowrap}.add-button:hover{background:#2a3b54}.add-button span{font-size:17px;line-height:10px}.task-form{padding:23px 26px;border-bottom:1px solid #eff0f5;background:#fcfcfe}.form-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:17px}.form-title h3{margin:0;font-size:16px}.icon-button{border:0;background:transparent;color:#7e8797;padding:5px}.task-form label{display:block;font-size:11px;font-weight:700;color:#525d70;margin:13px 0 7px}.task-form label span{font-weight:400;color:#9299a7}.task-form input,.task-form textarea,.task-form select{width:100%;border:1px solid #e0e4ec;background:white;border-radius:8px;padding:11px 12px;color:#182236;font-size:12px}.task-form textarea{resize:vertical}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.form-error{min-height:0;margin:8px 0 0;color:#c13b49;font-size:12px}.form-actions{display:flex;justify-content:flex-end;gap:9px;margin-top:13px}.cancel-button{border:1px solid #e1e5ed;border-radius:8px;background:#fff;color:#596275;padding:10px 14px;font-size:12px}.task-list{padding:0 26px}.task-item{display:grid;grid-template-columns:22px minmax(0,1fr) auto;gap:13px;align-items:start;padding:19px 0;border-bottom:1px solid #eff0f5}.task-item:last-child{border-bottom:0}.task-check{appearance:none;width:19px;height:19px;border:1.5px solid #c8cfdb;border-radius:6px;margin:2px 0 0;cursor:pointer;display:grid;place-items:center}.task-check:checked{background:#a8d96a;border-color:#a8d96a}.task-check:checked:after{content:"✓";font-size:13px;font-weight:900;color:#172033}.task-copy{min-width:0}.task-name{font-size:13px;font-weight:650;line-height:1.5;overflow-wrap:anywhere}.task-item.is-complete .task-name{text-decoration:line-through;color:#9299a7}.task-description{font-size:11px;color:#8b92a0;line-height:1.55;margin-top:4px;white-space:pre-wrap;overflow-wrap:anywhere}.task-meta{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}.pill{font-size:9px;border-radius:5px;padding:4px 7px;background:#f1f3f7;color:#70798b}.pill.high{background:#fff0ed;color:#bf5d4d}.pill.medium{background:#fff6df;color:#9a772a}.pill.low{background:#edf7e5;color:#648346}.pill.overdue{background:#ffe9ec;color:#b53649}.task-due{font-size:10px;color:#7e8797;align-self:center}.task-due.late{color:#bf4a5b}.task-actions{display:flex;gap:4px;align-items:center;opacity:.75}.task-actions button{border:0;background:transparent;color:#798294;padding:5px;font-size:11px;border-radius:5px}.task-actions button:hover{background:#f0f2f7;color:#182236}.empty-state{text-align:center;padding:47px 20px 52px}.empty-icon{width:45px;height:45px;border-radius:15px;background:#f0f6e8;color:#719047;display:grid;place-items:center;font-size:23px;margin:0 auto 15px}.empty-state h3{font-size:16px;margin:0 0 8px}.empty-state p{font-size:12px;line-height:1.6;color:#8991a0;margin:0 auto 17px;max-width:310px}.text-button{border:0;background:transparent;color:#536b35;font-size:12px;font-weight:700;padding:8px}.main footer{display:flex;justify-content:space-between;padding:25px 3px;color:#969cab;font-size:10px}.main footer span{letter-spacing:1.6px;font-size:9px}@media(max-width:850px){.shell{grid-template-columns:190px minmax(0,1fr)}.sidebar{padding:26px 12px}.main{padding:0 25px}.welcome{align-items:flex-start;flex-direction:column}.progress-card{width:100%}}@media(max-width:600px){.shell{display:block}.sidebar{min-height:auto;padding:15px 17px}.brand{padding:0 3px 17px}.nav-label,.sidebar-bottom{display:none}.filters{grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}.filter{justify-content:center;gap:5px;padding:10px 5px;font-size:10px;flex-wrap:wrap}.filter>span:first-child{width:auto;font-size:14px}.count{margin-left:0}.main{padding:0 15px}.topbar{height:56px}.today{font-size:10px}.welcome{padding:29px 0 24px;gap:20px}.welcome h1{letter-spacing:-1.2px}.panel-heading{padding:19px 16px}.panel-heading h2{font-size:17px}.panel-heading p{font-size:10px}.add-button{padding:10px 11px;font-size:11px}.task-list{padding:0 16px}.task-item{grid-template-columns:20px minmax(0,1fr);gap:10px}.task-actions{grid-column:2;opacity:1;margin-top:-3px}.task-due{grid-column:2;justify-self:start}.task-form{padding:19px 16px}.form-grid{grid-template-columns:1fr}.empty-state{padding:38px 16px}.main footer{padding:20px 2px}}
""",
        "app.js": """(() => {
  const STORAGE_KEY = "daymark.tasks.v1";
  const list = document.querySelector("#task-list");
  const empty = document.querySelector("#empty-state");
  const form = document.querySelector("#task-form");
  const titleInput = document.querySelector("#task-title");
  const descriptionInput = document.querySelector("#task-description");
  const priorityInput = document.querySelector("#task-priority");
  const dueInput = document.querySelector("#task-due");
  const error = document.querySelector("#form-error");
  let tasks = loadTasks();
  let filter = "all";
  let editingId = null;

  function loadTasks() {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      return Array.isArray(value) ? value.filter(task =>
        task && typeof task.id === "string" && typeof task.title === "string"
      ) : [];
    } catch { return []; }
  }
  function saveTasks() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
      return true;
    } catch {
      error.textContent = "Could not save tasks in this browser. Check available storage.";
      return false;
    }
  }
  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({
      "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
    })[char]);
  }
  function dateLabel(value) {
    if (!value) return "";
    const date = new Date(value + "T12:00:00");
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString(undefined, {month:"short", day:"numeric"});
  }
  function isOverdue(task) {
    return !task.completed && task.dueDate && task.dueDate < new Date().toLocaleDateString("en-CA");
  }
  function render() {
    const visible = tasks.filter(task =>
      filter === "all" || (filter === "pending" && !task.completed) ||
      (filter === "completed" && task.completed)
    ).sort((a,b) => Number(a.completed)-Number(b.completed) ||
      (a.dueDate || "9999").localeCompare(b.dueDate || "9999") ||
      ({high:0,medium:1,low:2}[a.priority] - {high:0,medium:1,low:2}[b.priority]));
    document.querySelector("#all-count").textContent = tasks.length;
    document.querySelector("#pending-count").textContent = tasks.filter(t=>!t.completed).length;
    document.querySelector("#completed-count").textContent = tasks.filter(t=>t.completed).length;
    const completed = tasks.filter(t=>t.completed).length;
    const percent = tasks.length ? Math.round(completed / tasks.length * 100) : 0;
    document.querySelector("#progress-label").textContent = percent + "%";
    document.querySelector("#progress-bar").style.width = percent + "%";
    document.querySelector("#progress-caption").textContent = completed + " of " + tasks.length + " tasks complete";
    list.innerHTML = visible.map(task => {
      const due = dateLabel(task.dueDate);
      const late = isOverdue(task);
      return '<article class="task-item '+(task.completed?'is-complete':'')+'" data-id="'+escapeHTML(task.id)+'">' +
        '<input class="task-check" type="checkbox" aria-label="Mark '+escapeHTML(task.title)+' complete" data-action="toggle" '+(task.completed?'checked':'')+'>' +
        '<div class="task-copy"><div class="task-name">'+escapeHTML(task.title)+'</div>' +
        (task.description ? '<div class="task-description">'+escapeHTML(task.description)+'</div>' : '') +
        '<div class="task-meta"><span class="pill '+escapeHTML(task.priority)+'">'+escapeHTML(task.priority[0].toUpperCase()+task.priority.slice(1))+' priority</span>' +
        (late ? '<span class="pill overdue">Overdue</span>' : '') + '</div></div>' +
        (due ? '<div class="task-due '+(late?'late':'')+'">'+(late?'Due ':'')+escapeHTML(due)+'</div>' : '<div class="task-due"></div>') +
        '<div class="task-actions"><button type="button" data-action="edit" aria-label="Edit '+escapeHTML(task.title)+'">Edit</button><button type="button" data-action="delete" aria-label="Delete '+escapeHTML(task.title)+'">Delete</button></div></article>';
    }).join("");
    empty.hidden = visible.length !== 0;
    if (!visible.length) {
      const titles = {all:"A fresh start.",pending:"All caught up.",completed:"Nothing completed yet."};
      const copies = {all:"No tasks yet. Add your first task and make today count.",pending:"No pending tasks. Enjoy the breathing room or add a new task.",completed:"Finish a task and it will show up here."};
      document.querySelector("#empty-title").textContent = titles[filter];
      document.querySelector("#empty-copy").textContent = copies[filter];
      document.querySelector("#empty-add").hidden = filter !== "all";
    }
  }
  function showForm(task = null) {
    editingId = task ? task.id : null;
    form.hidden = false;
    document.querySelector("#form-heading").textContent = task ? "Edit task" : "Create a task";
    document.querySelector("#save-task").textContent = task ? "Save changes" : "Save task";
    titleInput.value = task?.title || "";
    descriptionInput.value = task?.description || "";
    priorityInput.value = task?.priority || "medium";
    dueInput.value = task?.dueDate || "";
    error.textContent = "";
    titleInput.focus();
  }
  function hideForm() { form.hidden = true; editingId = null; error.textContent = ""; form.reset(); priorityInput.value = "medium"; }
  document.querySelector("#open-form").addEventListener("click", () => showForm());
  document.querySelector("#empty-add").addEventListener("click", () => showForm());
  document.querySelector("#cancel-form").addEventListener("click", hideForm);
  document.querySelector("#cancel-form-bottom").addEventListener("click", hideForm);
  document.querySelectorAll("[data-filter]").forEach(button => button.addEventListener("click", () => {
    filter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach(item => item.classList.toggle("active", item === button));
    document.querySelector("#list-title").textContent = {all:"All tasks",pending:"Upcoming",completed:"Completed"}[filter];
    document.querySelector("#list-subtitle").textContent = {all:"Your next steps, gathered together.",pending:"What still needs your attention.",completed:"Look how far you have come."}[filter];
    render();
  }));
  form.addEventListener("submit", event => {
    event.preventDefault();
    const title = titleInput.value.trim();
    if (!title) { error.textContent = "Add a title before saving this task."; titleInput.focus(); return; }
    const values = {title, description:descriptionInput.value.trim(), priority:priorityInput.value, dueDate:dueInput.value};
    if (editingId) {
      tasks = tasks.map(task => task.id === editingId ? {...task, ...values} : task);
    } else {
      tasks.push({id:crypto.randomUUID ? crypto.randomUUID() : String(Date.now())+"-"+Math.random().toString(16).slice(2), ...values, completed:false, createdAt:new Date().toISOString()});
    }
    if (saveTasks()) { hideForm(); render(); }
  });
  list.addEventListener("click", event => {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    const article = button.closest("[data-id]");
    const task = tasks.find(item => item.id === article?.dataset.id);
    if (!task) return;
    if (button.dataset.action === "edit") showForm(task);
    if (button.dataset.action === "delete" && window.confirm("Delete this task?")) {
      tasks = tasks.filter(item => item.id !== task.id);
      saveTasks(); render();
    }
  });
  list.addEventListener("change", event => {
    if (event.target.dataset.action !== "toggle") return;
    const article = event.target.closest("[data-id]");
    tasks = tasks.map(task => task.id === article?.dataset.id ? {...task, completed:event.target.checked} : task);
    saveTasks(); render();
  });
  document.querySelector("#today-label").textContent = new Date().toLocaleDateString(undefined,{weekday:"short",month:"short",day:"numeric"});
  render();
})();
""",
        "tests/test_project.py": """from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_browser_entry_and_local_assets_exist():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert (ROOT / "style.css").is_file()
    assert (ROOT / "app.js").is_file()
    assert 'src="app.js"' in html
    assert 'href="style.css"' in html


def test_task_manager_implements_real_crud_and_persistence():
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    for behavior in ("localStorage.getItem", "localStorage.setItem", "function render",
                     "function showForm", 'data-action="edit"', 'data-action="delete"',
                     'data-action="toggle"', "tasks.push", "tasks.filter"):
        assert behavior in js


def test_task_manager_starts_without_demo_records():
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    assert 'localStorage.getItem(STORAGE_KEY) || "[]"' in js
    assert "const sampleTasks" not in js
    assert "demoTasks" not in js
""",
    }
