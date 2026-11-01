import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import vm from "node:vm";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const same = (a, b) => a && b && a.length === b.length && a.every((v, i) => Object.is(v, b[i]));

// Render actual component functions and invoke their real event handlers. React's
// hook boundaries and network/browser APIs are replaced; no DOM package is needed.
function harness(fetch = async () => ({ ok: true, json: async () => ({}) })) {
  const slots = []; let cursor = 0; let effects = []; let component; let tree;
  const react = {
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = typeof initial === "function" ? initial() : initial; return [slots[i], value => { slots[i] = typeof value === "function" ? value(slots[i]) : value; }]; },
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useMemo(fn, deps) { const i = cursor++; if (!same(slots[i]?.deps, deps)) slots[i] = { deps, value: fn() }; return slots[i].value; },
    useEffect(fn, deps) { const i = cursor++; if (!same(slots[i]?.deps, deps)) effects.push(() => { slots[i]?.cleanup?.(); slots[i] = { deps, cleanup: fn() }; }); },
    useSyncExternalStore(_subscribe, snapshot) { return snapshot(); },
    createContext(value) { return { Provider: "provider", value }; },
    useContext(context) { return context.value; },
  };
  react.useCallback = (fn, deps) => react.useMemo(() => fn, deps);
  const data = new Map(); let quota = false;
  const localStorage = {
    get length() { return data.size; }, key: i => [...data.keys()][i] ?? null,
    getItem: key => data.get(key) ?? null,
    setItem(key, value) { if (quota) throw new DOMException("Full", "QuotaExceededError"); data.set(key, value); },
    removeItem: key => data.delete(key),
  };
  const window = new EventTarget();
  const document = { body: { style: { overflow: "" } }, activeElement: null };
  const globals = { localStorage, window, document, DOMException, fetch, URL, AbortSignal, FormData, Blob, crypto, setTimeout, clearTimeout, process: { env: {} } };
  const cache = new Map();
  function load(path) {
    if (cache.has(path)) return cache.get(path);
    const exports = {}; cache.set(path, exports);
    const source = ts.transpileModule(readFileSync(new URL(`../${path}`, import.meta.url), "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
    }).outputText;
    vm.runInNewContext(source, { ...globals, exports, require(name) {
      if (name === "react") return react;
      if (name === "react/jsx-runtime") return require(name);
      if (name === "@/lib/store") return load("lib/store.ts");
      if (name === "@/lib/api" || name === "./api") return load("lib/api.ts");
      if (name === "@/lib/format") return load("lib/format.ts");
      if (name === "@/lib/cards") return load("lib/cards.ts");
      return { default: function Placeholder() {} };
    } });
    return exports;
  }
  const store = load("lib/store.ts");
  store.saveProfile({ due_date: "2027-01-01", birth_date: null, tradition: "tamil_nadu", diet: "veg", city: "Bengaluru", insurer: null, parent_role: "mother", consent: { store_profile: true, save_journal: true, voice: false } });
  return {
    store, data, load, quota: () => { quota = true; },
    mount(path, props = {}, name = "default") { component = () => load(path)[name](props); return this.render(); },
    mountElement(element) { slots.length = 0; component = () => element.type(element.props); return this.render(); },
    render() { cursor = 0; tree = component(); const pending = effects; effects = []; pending.forEach(fn => fn()); return tree; },
    unmount() { slots.forEach(s => s?.cleanup?.()); },
  };
}

function nodes(node) { if (!node || typeof node !== "object") return []; if (Array.isArray(node)) return node.flatMap(nodes); return [node, ...nodes(node.props?.children)]; }
function content(node) { if (node == null || typeof node === "boolean") return ""; if (Array.isArray(node)) return node.map(content).join(""); return typeof node === "object" ? content(node.props?.children) : String(node); }
function button(tree, label) { const found = nodes(tree).find(n => n.type === "button" && content(n).includes(label)); assert.ok(found, label); return found; }
const event = { preventDefault() {} };
const response = body => ({ ok: true, status: 200, json: async () => body });
const pkg = name => ({ studio_name: name, package_name: "Basic", shoot_type: "maternity", city: "Bengaluru", price_inr: 10000, price_text: null, price_assumptions: [], inclusions: [], extras: [], duration_hours: 1, photos_taken: 50, edited_photos: 10, delivery_days: 7, album: { offered: false, price_inr: null, type: null, size: null, pages: null, photos: null }, frames: [], casting: { offered: true, price_inr: null, type: null }, rating_summary: null, location: null, contact_url: null, source_url: `https://${name}.example/`, checked_on: "2026-11-01", total_cost: 10000, cost_per_edited_photo: 1000 });

test("late clone is deleted after leaving Memory and wiping browser state", async () => {
  const clone = deferred(); const deleted = [];
  const h = harness(async (url, init) => { if (url.endsWith("/clone")) return clone.promise; if (init?.method === "DELETE") deleted.push(url); return response({}); });
  let tree = h.mount("app/memory/page.tsx");
  nodes(tree).find(n => n.props?.label === "Record my voice sample").props.onRecorded(new Blob(["audio"]));
  tree = h.render();
  // The voice consent is the final checkbox when the sample is present.
  nodes(tree).filter(n => n.type === "input" && n.props.type === "checkbox").at(-1).props.onChange({ target: { checked: true } });
  tree = h.render(); const pending = button(tree, "Create my own voice").props.onClick();
  h.unmount(); await h.store.deleteEverything(); clone.resolve(response({ voice_id: "late-voice" })); await pending;
  assert.equal(h.store.getVoiceId(), null);
  assert.equal(deleted.length, 1);
});

test("late clone cleanup failure keeps retry ID and exposes the retry problem", async () => {
  const clone = deferred();
  const h = harness(async (url, init) => url.endsWith("/clone") ? clone.promise : init?.method === "DELETE" ? { ok: false, status: 502 } : response({}));
  let tree = h.mount("app/memory/page.tsx"); nodes(tree).find(n => n.props?.label === "Record my voice sample").props.onRecorded(new Blob(["audio"])); tree = h.render();
  nodes(tree).filter(n => n.type === "input" && n.props.type === "checkbox").at(-1).props.onChange({ target: { checked: true } });
  const pending = button(h.render(), "Create my own voice").props.onClick(); h.unmount(); await h.store.deleteEverything();
  clone.resolve(response({ voice_id: "retry-late" })); await pending;
  assert.equal(h.store.getVoiceId(), "retry-late");
  assert.match(h.data.get("nestling:voice_cleanup_error") ?? "", /retry/i);
});

test("pending voice deletion cannot restore profile after leaving Memory and wiping", async () => {
  const deletion = deferred(); let calls = 0;
  const h = harness(async () => ++calls === 1 ? deletion.promise : response({}));
  h.store.setVoiceId("old-voice");
  button(h.mount("app/memory/page.tsx"), "Delete my voice").props.onClick();
  const pending = button(h.render(), "Yes, delete my voice").props.onClick();
  h.unmount(); await h.store.deleteEverything();
  assert.equal(h.data.has("nestling:profile"), false);
  deletion.resolve(response({})); await pending;
  assert.equal(h.data.has("nestling:profile"), false);
  assert.equal(h.store.getVoiceId(), null);
});

test("pending deletion cannot erase a newer voice or overwrite newer profile fields", async () => {
  const deletion = deferred(); const h = harness(async () => deletion.promise);
  h.store.setVoiceId("old-voice");
  button(h.mount("app/memory/page.tsx"), "Delete my voice").props.onClick();
  const pending = button(h.render(), "Yes, delete my voice").props.onClick();
  const profile = JSON.parse(h.data.get("nestling:profile"));
  h.store.saveProfile({ ...profile, city: "Chennai", consent: { ...profile.consent, voice: true } });
  h.store.setVoiceId("new-voice"); h.render();
  deletion.resolve(response({})); await pending;
  assert.equal(h.store.getVoiceId(), "new-voice");
  assert.equal(JSON.parse(h.data.get("nestling:profile")).city, "Chennai");
  assert.equal(JSON.parse(h.data.get("nestling:profile")).consent.voice, true);
});

test("current voice deletion updates consent without replacing a newer profile", async () => {
  const deletion = deferred(); const h = harness(async () => deletion.promise);
  h.store.setVoiceId("old-voice");
  button(h.mount("app/memory/page.tsx"), "Delete my voice").props.onClick();
  const pending = button(h.render(), "Yes, delete my voice").props.onClick();
  const profile = JSON.parse(h.data.get("nestling:profile"));
  h.store.saveProfile({ ...profile, city: "Chennai", consent: { ...profile.consent, voice: true } }); h.render();
  deletion.resolve(response({})); await pending;
  assert.equal(h.store.getVoiceId(), null);
  assert.equal(JSON.parse(h.data.get("nestling:profile")).city, "Chennai");
  assert.equal(JSON.parse(h.data.get("nestling:profile")).consent.voice, false);
});

test("Delete everything resets Ask conversation and rejects old response appends", async () => {
  const h = harness(); let tree = h.mount("components/AskSheet.tsx", { children: null });
  tree.props.value.setOpen(true); tree = h.render();
  const panel = nodes(tree).find(n => n.props?.setMsgs);
  panel.props.setMsgs([{ role: "me", text: "Private question" }]);
  await h.store.deleteEverything();
  panel.props.setMsgs(previous => [...previous, { role: "error" }]);
  tree = h.render(); tree.props.value.setOpen(true); tree = h.render();
  assert.equal(nodes(tree).find(n => n.props?.setMsgs).props.msgs.length, 0);
  assert.equal(nodes(tree).find(n => n.props?.setMsgs).props.initialText, "");
});

async function capture(fetch) { const h = harness(fetch); let tree = h.mount("app/celebrate/capture/page.tsx"); await nodes(tree).find(n => n.type === "form").props.onSubmit(event); return { h, tree: h.render() }; }

test("Capture ignores an estimate returned after component selections change", async () => {
  const estimate = deferred(); const { h, tree } = await capture(async url => url.endsWith("/search") ? response({ packages: [pkg("a")] }) : estimate.promise);
  const pending = button(tree, "Estimate my budget").props.onClick();
  nodes(tree).find(n => n.type === "input" && n.props.value === 10).props.onChange({ target: { value: "50" } });
  estimate.resolve(response({ label: "OBSOLETE ESTIMATE", tiers: {} })); await pending;
  assert.doesNotMatch(content(h.render()), /OBSOLETE ESTIMATE/);
});

test("Capture ignores a quote returned after its date changes", async () => {
  const draft = deferred(); const { h, tree } = await capture(async url => url.endsWith("/search") ? response({ packages: [pkg("a")] }) : draft.promise);
  const pending = button(tree, "Request quote").props.onClick();
  nodes(tree).find(n => n.type === "input" && n.props.type === "date").props.onChange({ target: { value: "2026-12-01" } });
  draft.resolve(response({ draft: "Obsolete draft", sent: false })); await pending;
  assert.equal(nodes(h.render()).filter(n => n.type === "textarea").some(n => n.props.value === "Obsolete draft"), false);
});

test("Capture switches studio without copying another studio's reply or save consent", async () => {
  const { h, tree } = await capture(async url => url.endsWith("/search") ? response({ packages: [pkg("a"), pkg("b")] }) : response({ draft: "Please quote", sent: false }));
  await button(tree, "Request quote").props.onClick(); let next = h.render();
  nodes(next).find(n => n.type === "textarea" && n.props.maxLength === 6000).props.onChange({ target: { value: "Studio A only" } });
  nodes(next).filter(n => n.type === "input" && n.props.type === "checkbox").at(-1).props.onChange({ target: { checked: true } });
  await nodes(h.render()).filter(n => n.type === "button" && content(n).includes("Request quote"))[1].props.onClick(); next = h.render();
  assert.equal(nodes(next).find(n => n.type === "textarea" && n.props.maxLength === 6000).props.value, "");
  assert.equal(button(next, "Save selected package").props.disabled, true);
});

test("casting with no listed price never displays as included", async () => {
  const { tree } = await capture(async () => response({ packages: [pkg("a")] }));
  const row = nodes(tree).find(n => n.type === "tr" && content(n).startsWith("Casting"));
  assert.doesNotMatch(content(row), /Included/);
  assert.match(content(row), /Not listed/);
});

test("quota failures preserve journal and letter drafts and show an error", () => {
  const h = harness(); let tree = h.mount("app/memory/page.tsx");
  nodes(tree).find(n => n.type === "textarea" && n.props.maxLength === 10000).props.onChange({ target: { value: "Keep my journal draft" } });
  nodes(tree).find(n => n.type === "textarea" && n.props.maxLength === 2500).props.onChange({ target: { value: "Keep my letter draft" } });
  h.quota(); tree = h.render();
  nodes(tree).filter(n => n.type === "form")[0].props.onSubmit(event);
  nodes(h.render()).filter(n => n.type === "form")[1].props.onSubmit(event);
  tree = h.render();
  assert.equal(nodes(tree).find(n => n.type === "textarea" && n.props.maxLength === 10000).props.value, "Keep my journal draft");
  assert.equal(nodes(tree).find(n => n.type === "textarea" && n.props.maxLength === 2500).props.value, "Keep my letter draft");
  assert.ok(nodes(tree).some(n => n.props?.role === "alert"));
});

test("Capture save failure shows an error instead of a saved confirmation", async () => {
  const { h, tree } = await capture(async url => url.endsWith("/search") ? response({ packages: [pkg("a")] }) : response({ draft: "Please quote", sent: false }));
  await button(tree, "Request quote").props.onClick(); let next = h.render();
  nodes(next).filter(n => n.type === "input" && n.props.type === "checkbox").at(-1).props.onChange({ target: { checked: true } }); h.quota();
  button(h.render(), "Save selected package").props.onClick(); next = h.render();
  assert.ok(nodes(next).some(n => n.props?.role === "alert"));
  assert.doesNotMatch(content(next), /budget saved to Today/);
});

test("Partner uses the current postpartum week instead of only generic pregnancy prompts", async () => {
  const h = harness(async url => url.endsWith("/today") ? response({ stage: { life_stage: "postpartum", week: null, baby_age_weeks: 2 }, tip: null, cards: [], tradition_card: false, disclaimer: "" }) : response({ title: "Bag", when: "Before delivery", sections: [] }));
  h.store.saveProfile({ birth_date: "2026-10-18", due_date: null, consent: { store_profile: true, save_journal: true, voice: false } });
  h.mount("components/JourneyContent.tsx", { partner: true }, "ReadyJourney");
  await new Promise(setImmediate);
  const tree = h.render();
  assert.match(content(tree), /baby.*week 3/i);
  assert.match(content(tree), /first weeks|after birth/i);
});

test("late remote cleanup errors are visible from the root provider on any route", async () => {
  const h = harness(async () => ({ ok: false, status: 502 }));
  await h.store.finishVoiceClone("retry-voice", h.store.getPrivacyEpoch(), false);
  const tree = h.mount("components/AskSheet.tsx", { children: "Welcome" });
  assert.ok(nodes(tree).some(n => n.props?.role === "alert" && /retry/i.test(content(n))));
});

test("Ask does not claim a journal save succeeded when browser storage is full", () => {
  const h = harness();
  const res = { answer: "A made-up answer", escalate: false, refused: false, route: "journal", guardian: { level: "calm", rules_fired: [], unsafe: [] }, sources: [], how_i_answered: [], verification: null, save: true, error: false, lesson: null };
  const root = h.mount("components/AskPanel.tsx", { msgs: [{ role: "nestling", question: "My memory", res }], setMsgs() {} });
  const answer = nodes(root).find(n => n.props?.res === res);
  h.mountElement(answer); h.quota();
  button(h.render(), "Save to my journal").props.onClick();
  const tree = h.render();
  assert.doesNotMatch(content(tree), /Saved to your journal/);
  assert.ok(nodes(tree).some(n => n.props?.role === "alert"));
});

test("a successful current clone remains usable and remote retry errors clear after deletion succeeds", async () => {
  let fail = true;
  const h = harness(async () => fail ? { ok: false, status: 502 } : response({}));
  assert.equal(await h.store.finishVoiceClone("current-voice", h.store.getPrivacyEpoch(), true), "ready");
  assert.equal(h.store.getVoiceId(), "current-voice");
  await h.store.deleteEverything();
  assert.equal(h.store.getVoiceId(), "current-voice");
  fail = false;
  assert.equal((await h.store.deleteEverything()).voiceError, false);
  assert.equal(h.store.getVoiceId(), null);
  assert.equal(h.data.size, 0);
});

test("a stored voice removed elsewhere does not survive in an unnecessary in-memory fallback", () => {
  const h = harness(); h.store.setVoiceId("stored-voice");
  h.data.delete("nestling:voice_id");
  assert.equal(h.store.getVoiceId(), null);
});
