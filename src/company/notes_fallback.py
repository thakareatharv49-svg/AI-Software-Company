"""Deterministic offline browser product for multi-feature Notes App missions."""

from __future__ import annotations


def notes_fallback_files() -> dict[str, str]:
    """Return a complete notes app with CRUD, search, pinning and local persistence."""
    return {
        "index.html": """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f5f4f0">
  <title>Paper — Notes for your mind</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="#" aria-label="Paper home"><span class="brand-icon">p</span><span>paper<span class="brand-dot">.</span></span></a>
      <p class="side-label">YOUR SPACE</p>
      <nav aria-label="Note filters" class="nav-list">
        <button class="nav-item active" data-view="all"><span>▤</span> All notes <span class="nav-count" id="all-count">0</span></button>
        <button class="nav-item" data-view="pinned"><span>⌑</span> Pinned <span class="nav-count" id="pinned-count">0</span></button>
      </nav>
      <div class="sidebar-tip"><span class="tip-mark">✳</span><p><strong>A little space to think.</strong><br>Catch the thought before it goes.</p></div>
      <div class="sidebar-foot"><span class="saved-dot"></span><span id="save-status">Saved on this device</span></div>
    </aside>
    <main class="main">
      <header class="topbar"><div><p class="kicker">YOUR PERSONAL NOTEBOOK</p><h1 id="page-title">All notes</h1></div><div class="top-actions"><label class="search-box"><span aria-hidden="true">⌕</span><input id="search-input" type="search" placeholder="Search your notes..." aria-label="Search notes"></label><button class="primary-button" id="new-note"><span>＋</span> New note</button></div></header>
      <section class="welcome"><div><p class="kicker">A CLEARER MIND STARTS HERE</p><h2>Your thoughts,<br><em>all in one place.</em></h2><p class="welcome-copy">Keep the little ideas, big plans, and everything in between.</p></div><div class="note-summary"><span class="summary-icon">✎</span><div><strong id="summary-count">0 notes</strong><span>in your notebook</span></div></div></section>
      <section class="notes-section" aria-label="Your notes"><div class="section-head"><div><h2 id="section-title">Recently written</h2><p id="section-subtitle">Your notes, just as you left them.</p></div><span class="sort-label">LOCAL · PRIVATE</span></div><div id="notes-grid" class="notes-grid" aria-live="polite"></div>
        <div id="empty-state" class="empty-state"><div class="empty-art">✳</div><h3 id="empty-title">A blank page is full of possibility.</h3><p id="empty-copy">Create your first note and give that thought somewhere to live.</p><button class="text-button" id="empty-create">＋ Write your first note</button></div>
      </section>
      <footer><span>Made for the thoughts worth keeping.</span><span class="footer-mark">PAPER / 01</span></footer>
    </main>
  </div>
  <dialog id="note-dialog" class="note-dialog" aria-labelledby="dialog-title"><form id="note-form" method="dialog"><div class="dialog-head"><div><p class="kicker">YOUR NOTEBOOK</p><h2 id="dialog-title">A new thought</h2></div><button type="button" class="icon-button" id="close-dialog" aria-label="Close editor">×</button></div><label for="note-title">Title</label><input id="note-title" name="title" maxlength="120" placeholder="Give this note a name..." required><label for="note-body">Your note</label><textarea id="note-body" name="body" rows="8" maxlength="20000" placeholder="Start writing. It doesn't have to be perfect." required></textarea><p id="form-error" class="form-error" role="alert"></p><div class="dialog-actions"><button type="button" class="secondary-button" id="cancel-edit">Cancel</button><button type="submit" class="primary-button">Save note <span>↗</span></button></div></form></dialog>
  <div id="toast" class="toast" role="status" aria-live="polite"></div>
  <script src="app.js"></script>
</body>
</html>
""",
        "style.css": """*{box-sizing:border-box} :root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#262c29;background:#f8f8f5;font-synthesis:none;text-rendering:optimizeLegibility}body{margin:0;min-height:100vh}button,input,textarea{font:inherit}button{cursor:pointer}button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid #b6c8a9;outline-offset:3px}.app-shell{min-height:100vh;display:grid;grid-template-columns:238px minmax(0,1fr);max-width:1680px;margin:auto}.sidebar{background:#f0f0e9;border-right:1px solid #e5e5dc;padding:30px 18px;display:flex;flex-direction:column;min-height:100vh}.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:#252c28;font-size:21px;font-weight:800;letter-spacing:-1px;padding:0 9px 48px}.brand-icon{display:grid;place-items:center;width:33px;height:33px;background:#293b31;color:#f4f4eb;border-radius:10px;font-family:Georgia,serif;font-size:24px;font-weight:400}.brand-dot{color:#8aa87c}.side-label,.kicker{font-size:10px;letter-spacing:1.7px;font-weight:750;color:#858a7d}.side-label{padding:0 10px;margin:0 0 12px}.nav-list{display:grid;gap:5px}.nav-item{border:0;background:transparent;color:#73796e;display:flex;align-items:center;gap:12px;padding:12px;border-radius:9px;text-align:left;font-size:13px}.nav-item>span:first-child{font-size:17px;width:17px;text-align:center}.nav-item.active{background:#fff;color:#293b31;box-shadow:0 2px 7px #1e302208}.nav-count{margin-left:auto;font-size:11px;color:#8a9086}.sidebar-tip{margin-top:42px;padding:16px 12px;background:#e5e8dc;border-radius:12px;display:flex;gap:10px;align-items:flex-start}.tip-mark{color:#637c53;font-size:18px}.sidebar-tip p{font-size:11px;line-height:1.7;color:#72796b;margin:0}.sidebar-tip strong{color:#3e4b3c;font-size:12px}.sidebar-foot{margin-top:auto;padding:22px 9px 2px;display:flex;gap:8px;align-items:center;font-size:10px;color:#7d8478}.saved-dot{width:7px;height:7px;background:#7da56a;border-radius:50%}.main{min-width:0;padding:0 clamp(22px,5vw,76px);display:flex;flex-direction:column}.topbar{min-height:91px;display:flex;align-items:center;justify-content:space-between;gap:22px;border-bottom:1px solid #e9eae4}.topbar .kicker{margin:0 0 7px}.topbar h1{font-size:23px;letter-spacing:-.8px;margin:0;font-weight:650}.top-actions{display:flex;align-items:center;gap:10px}.search-box{display:flex;align-items:center;gap:8px;border:1px solid #e3e5dd;background:#fff;border-radius:9px;padding:0 12px;height:40px;color:#83897e}.search-box>span{font-size:22px}.search-box input{border:0;outline:none;background:transparent;width:175px;font-size:12px;color:#30372f}.search-box input:focus-visible{outline:none}.primary-button{border:0;background:#293b31;color:#fff;border-radius:9px;min-height:40px;padding:0 16px;font-size:12px;font-weight:650;display:inline-flex;align-items:center;justify-content:center;gap:8px;transition:background .15s,transform .15s}.primary-button:hover{background:#3d5545;transform:translateY(-1px)}.primary-button span{font-size:16px}.welcome{padding:47px 0 43px;display:flex;justify-content:space-between;align-items:flex-end;gap:24px}.welcome .kicker{margin:0 0 14px;color:#819174}.welcome h2{font-size:clamp(34px,4.5vw,53px);line-height:1.06;letter-spacing:-2.5px;font-weight:620;margin:0}.welcome h2 em{font-family:Georgia,serif;color:#718665;font-weight:400}.welcome-copy{font-size:13px;color:#858a80;margin:15px 0 0;line-height:1.7}.note-summary{display:flex;align-items:center;gap:12px;background:#fff;border:1px solid #e9eae4;border-radius:12px;padding:15px 17px;min-width:160px;margin-bottom:3px}.summary-icon{width:34px;height:34px;display:grid;place-items:center;background:#eff2e9;color:#607a52;border-radius:9px;font-size:17px}.note-summary div{display:grid;gap:4px}.note-summary strong{font-size:13px;font-weight:700}.note-summary div span{font-size:10px;color:#8a8f84}.notes-section{flex:1}.section-head{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-bottom:17px}.section-head h2{font-size:15px;margin:0 0 5px;font-weight:700}.section-head p{font-size:11px;color:#90958a;margin:0}.sort-label{font-size:9px;letter-spacing:1.2px;color:#8b9185}.notes-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.note-card{position:relative;min-height:190px;padding:17px 17px 14px;background:#fff;border:1px solid #e8e9e2;border-radius:12px;display:flex;flex-direction:column;transition:transform .15s,box-shadow .15s;overflow-wrap:anywhere}.note-card:hover{transform:translateY(-2px);box-shadow:0 8px 22px #2736290c}.note-card.pinned{border-color:#cbd6c0;background:#fcfdf9}.note-card-top{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:13px}.note-date{font-size:9px;color:#969b90}.pin-badge{font-size:9px;color:#627b55;background:#edf2e7;border-radius:20px;padding:4px 7px}.card-menu{display:flex;gap:4px;margin-left:auto}.icon-button{border:0;background:transparent;color:#858b80;width:27px;height:27px;border-radius:7px;font-size:17px;display:grid;place-items:center}.icon-button:hover{background:#f0f2eb;color:#26372b}.note-card h3{font-size:14px;line-height:1.45;margin:0 0 8px;letter-spacing:-.2px}.note-preview{font-size:11px;line-height:1.75;color:#7e857a;margin:0;white-space:pre-wrap;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}.note-card-bottom{margin-top:auto;padding-top:15px;display:flex;justify-content:space-between;align-items:center;gap:8px}.note-tag{font-size:9px;letter-spacing:.5px;color:#8b9184}.edit-link{border:0;background:transparent;color:#5f7854;font-size:10px;font-weight:700;padding:5px 0}.empty-state{display:none;text-align:center;padding:50px 15px 65px}.empty-state.visible{display:block}.empty-art{font-size:31px;color:#91a783;margin-bottom:12px}.empty-state h3{font-family:Georgia,serif;font-size:23px;font-weight:400;margin:0 0 8px}.empty-state p{font-size:12px;color:#8b9086;line-height:1.7;max-width:340px;margin:0 auto 17px}.text-button{border:0;background:transparent;color:#526e47;font-size:12px;font-weight:700;padding:9px}.text-button:hover{text-decoration:underline}.main footer{margin-top:45px;border-top:1px solid #e9eae4;padding:18px 0 22px;display:flex;justify-content:space-between;color:#999e94;font-size:10px}.footer-mark{letter-spacing:1.5px}.note-dialog{width:min(540px,calc(100% - 28px));padding:0;border:1px solid #e6e8df;border-radius:16px;box-shadow:0 25px 90px #18221830;color:#293129}.note-dialog::backdrop{background:#202b2390;backdrop-filter:blur(3px)}.note-dialog form{padding:27px}.dialog-head{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:23px}.dialog-head .kicker{margin:0 0 7px}.dialog-head h2{font-size:23px;letter-spacing:-.7px;margin:0}.dialog-head .icon-button{font-size:25px}.note-dialog label{display:block;font-size:11px;font-weight:700;color:#596255;margin:15px 0 7px}.note-dialog input,.note-dialog textarea{width:100%;border:1px solid #e1e4da;background:#fbfcf9;border-radius:8px;padding:11px 12px;font-size:12px;color:#293129}.note-dialog textarea{resize:vertical;line-height:1.7;min-height:145px}.form-error{min-height:16px;font-size:11px;color:#b54d42;margin:7px 0}.dialog-actions{display:flex;justify-content:flex-end;gap:9px;margin-top:12px}.secondary-button{border:1px solid #e0e3da;background:#fff;color:#5f665c;border-radius:9px;padding:0 15px;min-height:40px;font-size:12px}.toast{position:fixed;bottom:22px;left:50%;transform:translate(-50%,12px);background:#293b31;color:white;padding:11px 17px;border-radius:9px;font-size:12px;opacity:0;pointer-events:none;transition:opacity .18s,transform .18s;box-shadow:0 8px 24px #17271a20}.toast.show{opacity:1;transform:translate(-50%,0)}[hidden]{display:none!important}@media(max-width:1050px){.notes-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.welcome{align-items:flex-start;flex-direction:column}.note-summary{margin:0}.topbar{align-items:flex-start;padding:23px 0;flex-direction:column}.top-actions{width:100%}.search-box{flex:1}.search-box input{width:100%}}@media(max-width:650px){.app-shell{grid-template-columns:1fr}.sidebar{min-height:0;padding:13px 17px;display:grid;grid-template-columns:auto 1fr;align-items:center;gap:12px;border-right:0;border-bottom:1px solid #e5e5dc}.brand{padding:0;font-size:18px}.brand-icon{width:29px;height:29px}.side-label,.sidebar-tip,.sidebar-foot{display:none}.nav-list{display:flex;justify-content:flex-end;gap:3px}.nav-item{padding:9px 10px;font-size:11px;gap:6px}.nav-item>span:first-child{display:none}.nav-count{margin-left:2px}.main{padding:0 18px}.topbar{gap:15px}.top-actions{gap:7px}.search-box{min-width:0;padding:0 9px}.search-box input{font-size:11px}.primary-button{padding:0 11px;white-space:nowrap}.welcome{padding:34px 0 30px}.welcome h2{font-size:39px}.notes-grid{grid-template-columns:1fr}.note-card{min-height:165px}.section-head{align-items:flex-start}.sort-label{font-size:8px}.main footer{margin-top:28px}.note-dialog form{padding:21px}.note-summary{padding:11px 13px}}@media(prefers-reduced-motion:reduce){*,*::before,*::after{transition:none!important;scroll-behavior:auto!important}}
""",
        "app.js": """(() => {
  "use strict";
  const STORAGE_KEY = "paper-notes-v1";
  const $ = (selector) => document.querySelector(selector);
  const grid = $("#notes-grid");
  const empty = $("#empty-state");
  const dialog = $("#note-dialog");
  const form = $("#note-form");
  const titleInput = $("#note-title");
  const bodyInput = $("#note-body");
  const searchInput = $("#search-input");
  const state = { notes: [], view: "all", query: "", editingId: null, toastTimer: null };

  function makeId() {
    return (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function")
      ? globalThis.crypto.randomUUID()
      : "note-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
  }
  function normalizeNote(note) {
    if (!note || typeof note !== "object" || typeof note.title !== "string" || typeof note.body !== "string") return null;
    return {
      id: typeof note.id === "string" && note.id ? note.id : makeId(),
      title: note.title.slice(0, 120),
      body: note.body.slice(0, 20000),
      pinned: note.pinned === true,
      createdAt: Number.isFinite(note.createdAt) ? note.createdAt : Date.now(),
      updatedAt: Number.isFinite(note.updatedAt) ? note.updatedAt : Date.now()
    };
  }
  function loadNotes() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.map(normalizeNote).filter(Boolean) : [];
    } catch (error) {
      console.warn("Could not read saved notes", error);
      return [];
    }
  }
  function saveNotes() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.notes));
      $("#save-status").textContent = "Saved on this device";
      return true;
    } catch (error) {
      $("#save-status").textContent = "Storage unavailable";
      showToast("Could not save notes. Check your browser storage.");
      return false;
    }
  }
  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[character]);
  }
  function formatDate(timestamp) {
    return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(timestamp));
  }
  function visibleNotes() {
    const query = state.query.trim().toLocaleLowerCase();
    return state.notes
      .filter((note) => state.view !== "pinned" || note.pinned)
      .filter((note) => !query || (note.title + "\n" + note.body).toLocaleLowerCase().includes(query))
      .sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.updatedAt - a.updatedAt);
  }
  function showToast(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.add("show");
    if (state.toastTimer) clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => toast.classList.remove("show"), 2300);
  }
  function render() {
    const notes = visibleNotes();
    grid.innerHTML = notes.map((note) => {
      const preview = note.body.length > 230 ? note.body.slice(0, 230) + "…" : note.body;
      return '<article class="note-card' + (note.pinned ? ' pinned' : '') + '" data-note-id="' + escapeHTML(note.id) + '">' +
        '<div class="note-card-top"><span class="note-date">' + escapeHTML(formatDate(note.updatedAt)) + '</span>' +
        (note.pinned ? '<span class="pin-badge">⌑ Pinned</span>' : '') +
        '<div class="card-menu"><button class="icon-button" data-action="pin" aria-label="' + (note.pinned ? 'Unpin ' : 'Pin ') + escapeHTML(note.title) + '" title="' + (note.pinned ? 'Unpin note' : 'Pin note') + '">' + (note.pinned ? '⌑' : '◇') + '</button>' +
        '<button class="icon-button" data-action="delete" aria-label="Delete ' + escapeHTML(note.title) + '" title="Delete note">×</button></div></div>' +
        '<h3>' + escapeHTML(note.title) + '</h3><p class="note-preview">' + escapeHTML(preview) + '</p>' +
        '<div class="note-card-bottom"><span class="note-tag">' + Math.max(1, note.body.trim().split(/\s+/).filter(Boolean).length) + ' WORDS</span>' +
        '<button class="edit-link" data-action="edit">Open note ↗</button></div></article>';
    }).join("");
    empty.classList.toggle("visible", notes.length === 0);
    grid.hidden = notes.length === 0;
    if (notes.length === 0) {
      if (state.query) {
        $("#empty-title").textContent = "No notes found.";
        $("#empty-copy").textContent = "Try another search term, or create a new note.";
      } else if (state.view === "pinned") {
        $("#empty-title").textContent = "Nothing pinned just yet.";
        $("#empty-copy").textContent = "Pin the notes you want to find quickly.";
      } else {
        $("#empty-title").textContent = "A blank page is full of possibility.";
        $("#empty-copy").textContent = "Create your first note and give that thought somewhere to live.";
      }
    }
    $("#all-count").textContent = state.notes.length;
    $("#pinned-count").textContent = state.notes.filter((note) => note.pinned).length;
    $("#summary-count").textContent = state.notes.length + (state.notes.length === 1 ? " note" : " notes");
    $("#page-title").textContent = state.view === "pinned" ? "Pinned notes" : "All notes";
    $("#section-title").textContent = state.query ? "Search results" : state.view === "pinned" ? "Kept close" : "Recently written";
    $("#section-subtitle").textContent = state.query ? notes.length + " matching " + (notes.length === 1 ? "note" : "notes") : "Your notes, just as you left them.";
    document.querySelectorAll("[data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === state.view));
  }
  function openEditor(note) {
    state.editingId = note ? note.id : null;
    $("#dialog-title").textContent = note ? "Edit your note" : "A new thought";
    titleInput.value = note ? note.title : "";
    bodyInput.value = note ? note.body : "";
    $("#form-error").textContent = "";
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    titleInput.focus();
  }
  function closeEditor() {
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
    state.editingId = null;
    form.reset();
    $("#form-error").textContent = "";
  }
  function saveFromForm(event) {
    event.preventDefault();
    const title = titleInput.value.trim();
    const body = bodyInput.value.trim();
    if (!title || !body) {
      $("#form-error").textContent = "Add both a title and some note content before saving.";
      return;
    }
    const now = Date.now();
    if (state.editingId) {
      const note = state.notes.find((item) => item.id === state.editingId);
      if (!note) {
        $("#form-error").textContent = "This note is no longer available. Close the editor and try again.";
        return;
      }
      note.title = title.slice(0, 120);
      note.body = body.slice(0, 20000);
      note.updatedAt = now;
      showToast("Note updated");
    } else {
      state.notes.push({ id: makeId(), title: title.slice(0, 120), body: body.slice(0, 20000), pinned: false, createdAt: now, updatedAt: now });
      showToast("Note saved");
    }
    saveNotes();
    closeEditor();
    render();
  }
  function togglePin(id) {
    const note = state.notes.find((item) => item.id === id);
    if (!note) return;
    note.pinned = !note.pinned;
    note.updatedAt = Date.now();
    saveNotes();
    render();
    showToast(note.pinned ? "Note pinned" : "Note unpinned");
  }
  function deleteNote(id) {
    const note = state.notes.find((item) => item.id === id);
    if (!note) return;
    if (!window.confirm('Delete "' + note.title + '"? This cannot be undone.')) return;
    state.notes = state.notes.filter((item) => item.id !== id);
    saveNotes();
    render();
    showToast("Note deleted");
  }
  $("#new-note").addEventListener("click", () => openEditor(null));
  $("#empty-create").addEventListener("click", () => openEditor(null));
  $("#close-dialog").addEventListener("click", closeEditor);
  $("#cancel-edit").addEventListener("click", closeEditor);
  form.addEventListener("submit", saveFromForm);
  searchInput.addEventListener("input", () => { state.query = searchInput.value; render(); });
  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => {
    state.view = button.dataset.view;
    render();
  }));
  grid.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const card = button.closest("[data-note-id]");
    if (!card) return;
    const id = card.dataset.noteId;
    if (button.dataset.action === "pin") togglePin(id);
    if (button.dataset.action === "delete") deleteNote(id);
    if (button.dataset.action === "edit") {
      const note = state.notes.find((item) => item.id === id);
      if (note) openEditor(note);
    }
  });
  dialog.addEventListener("click", (event) => { if (event.target === dialog) closeEditor(); });
  dialog.addEventListener("close", () => { state.editingId = null; });
  state.notes = loadNotes();
  render();
  window.PaperNotes = {
    getNotes: () => state.notes.map((note) => ({ ...note })),
    search: (query) => state.notes.filter((note) => (note.title + "\n" + note.body).toLocaleLowerCase().includes(String(query).toLocaleLowerCase())),
    saveNotes,
    visibleNotes
  };
})();
"""
    }
