const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const appSource = fs.readFileSync(process.argv[2], "utf8");
const storage = new Map();
const elements = new Map();

class MockElement {
  constructor(selector, dataset = {}) {
    this.selector = selector;
    this.dataset = dataset;
    this.listeners = new Map();
    this.attributes = new Map();
    this.textContent = "";
    this.value = "";
    this.hidden = false;
    this.open = false;
    this._innerHTML = "";
    this.classes = new Set();
    this.classList = {
      add: (name) => this.classes.add(name),
      remove: (name) => this.classes.delete(name),
      toggle: (name, force) => {
        const enabled = force === undefined ? !this.classes.has(name) : Boolean(force);
        if (enabled) this.classes.add(name);
        else this.classes.delete(name);
        return enabled;
      },
      contains: (name) => this.classes.has(name),
    };
  }
  addEventListener(name, callback) {
    if (!this.listeners.has(name)) this.listeners.set(name, []);
    this.listeners.get(name).push(callback);
  }
  dispatch(name, event = {}) {
    event.target ??= this;
    event.preventDefault ??= () => { event.defaultPrevented = true; };
    for (const callback of this.listeners.get(name) || []) callback(event);
  }
  click() { this.dispatch("click"); }
  setAttribute(name, value) { this.attributes.set(name, value); if (name === "open") this.open = true; }
  removeAttribute(name) { this.attributes.delete(name); if (name === "open") this.open = false; }
  showModal() { this.open = true; }
  close() { this.open = false; }
  focus() {}
  reset() {
    if (this.selector === "#note-form") {
      get("#note-title").value = "";
      get("#note-body").value = "";
    }
  }
  closest(selector) {
    if (selector === "button[data-action]" && this.dataset.action) return this;
    if (selector === "[data-note-id]") return this.parentCard || null;
    return null;
  }
  set innerHTML(value) {
    this._innerHTML = value;
    if (this.selector !== "#notes-grid") return;
    this.cards = [];
    const articles = value.match(/<article\b[^>]*data-note-id="[^"]+"[^>]*>[\s\S]*?<\/article>/g) || [];
    for (const article of articles) {
      const id = (article.match(/data-note-id="([^"]+)"/) || [])[1];
      if (!id) continue;
      const card = { dataset: { noteId: id }, buttons: {} };
      for (const match of article.matchAll(/<button\b([^>]*data-action="(pin|delete|edit)"[^>]*)>/g)) {
        const button = new MockElement("button", { action: match[2] });
        button.parentCard = card;
        card.buttons[match[2]] = button;
      }
      this.cards.push(card);
    }
  }
  get innerHTML() { return this._innerHTML; }
}
function get(selector) {
  if (!elements.has(selector)) elements.set(selector, new MockElement(selector));
  return elements.get(selector);
}
const viewButtons = [
  new MockElement("view-all", { view: "all" }),
  new MockElement("view-pinned", { view: "pinned" }),
];
const grid = get("#notes-grid");
const document = {
  querySelector: get,
  querySelectorAll(selector) {
    return selector === "[data-view]" ? viewButtons : [];
  },
};
const localStorage = {
  getItem(key) { return storage.has(key) ? storage.get(key) : null; },
  setItem(key, value) { storage.set(key, String(value)); },
};
const window = { confirm: () => true };
const context = {
  document, localStorage, window, console,
  Date, Intl, JSON, Math, String, Number, Array, Object, RegExp,
  setTimeout: () => 1, clearTimeout: () => {},
  crypto: { randomUUID: () => "test-note-id" },
};
context.globalThis = context;
vm.runInNewContext(appSource, context, { timeout: 1000 });

function submit(title, body) {
  get("#note-title").value = title;
  get("#note-body").value = body;
  get("#note-form").dispatch("submit");
}
function clickCardAction(action) {
  assert.equal(grid.cards.length, 1, "expected one rendered card before " + action);
  const button = grid.cards[0].buttons[action];
  assert.ok(button, "expected " + action + " control");
  grid.dispatch("click", { target: button });
}

assert.equal(grid.cards.length, 0, "new notebook should start empty");
get("#new-note").click();
submit("Project plan", "Needle: ship the first version");
let notes = JSON.parse(storage.get("paper-notes-v1"));
assert.equal(notes.length, 1, "creating a note should persist it");
assert.equal(notes[0].title, "Project plan");
assert.equal(notes[0].body, "Needle: ship the first version");

clickCardAction("pin");
notes = JSON.parse(storage.get("paper-notes-v1"));
assert.equal(notes[0].pinned, true, "pinning should persist the pinned state");
viewButtons[1].click();
assert.equal(grid.cards.length, 1, "pinned view should include pinned notes");

get("#search-input").value = "needle";
get("#search-input").dispatch("input");
assert.equal(grid.cards.length, 1, "search should find text in note content");
get("#search-input").value = "does-not-exist";
get("#search-input").dispatch("input");
assert.equal(grid.cards.length, 0, "search should hide non-matching notes");

get("#search-input").value = "";
get("#search-input").dispatch("input");
viewButtons[0].click();
clickCardAction("edit");
assert.equal(get("#note-title").value, "Project plan", "editing should load existing title");
submit("Updated plan", "Revised content");
notes = JSON.parse(storage.get("paper-notes-v1"));
assert.equal(notes[0].title, "Updated plan", "editing should update the saved note");
assert.equal(notes[0].body, "Revised content");

clickCardAction("delete");
notes = JSON.parse(storage.get("paper-notes-v1"));
assert.equal(notes.length, 0, "confirmed deletion should remove the note");
assert.equal(grid.cards.length, 0, "deleted note should disappear from the UI");
console.log("Notes fallback behavioral checks passed: create, persistence, pin, filter, search, edit, delete.");
