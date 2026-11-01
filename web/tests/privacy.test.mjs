import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import test from "node:test";
import ts from "typescript";

// Exercise the real TypeScript modules with browser/network boundaries replaced.
// No browser dependency, remote API or personal fixture is used.
function load(file, globals = {}, dependencies = {}) {
  const exports = {};
  const source = ts.transpileModule(readFileSync(new URL(`../lib/${file}.ts`, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  vm.runInNewContext(source, {
    exports, process: { env: {} }, AbortSignal, FormData, Blob, URL, setTimeout, crypto,
    require: name => dependencies[name] ?? {}, ...globals,
  });
  return exports;
}

function browser(deleteStatus = 200) {
  const data = new Map();
  const localStorage = {
    get length() { return data.size; }, key: i => [...data.keys()][i] ?? null,
    getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value),
    removeItem: key => data.delete(key),
  };
  const api = load("api", { fetch: async () => ({ ok: deleteStatus < 400, status: deleteStatus, json: async () => ({}) }) });
  const store = load("store", { localStorage }, { "./api": api });
  return { data, store };
}

test("Delete everything clears every Nestling key and preserves unrelated app data", async () => {
  const { data, store } = browser();
  data.set("another-app:notes", "keep"); data.set("nestling:future-key", "remove");
  store.setVoiceId("test-own-voice"); store.addJournalEntry("A made-up memory");
  const result = await store.deleteEverything();
  assert.equal(result.voiceDeleted, true); assert.equal(result.voiceError, false);
  assert.deepEqual([...data], [["another-app:notes", "keep"]]);
});

test("failed voice deletion keeps only the retry ID among Nestling data", async () => {
  const { data, store } = browser(502);
  store.setVoiceId("retry-voice"); store.addJournalEntry("A made-up memory");
  data.set("nestling:letters", "[]"); data.set("nestling:capture", "{}");
  const result = await store.deleteEverything();
  assert.equal(result.voiceError, true);
  assert.deepEqual([...data], [["nestling:voice_id", "retry-voice"]]);
});

test("a voice already deleted remotely is an idempotent success", async () => {
  const { data, store } = browser(404); store.setVoiceId("already-gone");
  const result = await store.deleteEverything();
  assert.equal(result.voiceError, false); assert.equal(data.size, 0);
});

test("audio requests preserve format, multipart field and explicit clone consent", async () => {
  const calls = [];
  const api = load("api", { fetch: async (url, init) => { calls.push({ url, init }); return { ok: true, json: async () => ({ text: "A made-up transcript", voice_id: "test-voice" }) }; } });
  const audio = new Blob(["test audio"], { type: "audio/mp4" });
  await api.transcribe(audio); await api.cloneVoice(audio);
  assert.equal(calls[0].init.body.get("file").name, "journal.mp4");
  assert.equal(calls[0].init.body.get("file").type, "audio/mp4");
  assert.equal(calls[1].init.body.get("sample").name, "my-voice.mp4");
  assert.equal(calls[1].init.body.get("consent"), "true");
  assert.ok(calls.every(c => c.init.signal instanceof AbortSignal));
});

test("API rejection stays an error and never becomes a successful empty response", async () => {
  const api = load("api", { fetch: async () => ({ ok: false, status: 413 }) });
  await assert.rejects(api.transcribe(new Blob(["test"], { type: "audio/webm" })), /413/);
});

test("blank example configuration still reaches the separate local API", async () => {
  let requested;
  const api = load("api", { process: { env: { NEXT_PUBLIC_API_URL: " " } }, fetch: async url => { requested = url; return { ok: true, json: async () => ({ ok: true }) }; } });
  await api.getHealth();
  assert.equal(requested, "http://localhost:8000/api/health");
});

test("exported cards retain long source links and fit text within the image", async () => {
  const drawn = []; let canvas;
  const ctx = { font: "", measureText(text) { return { width: text.length * Number.parseFloat(this.font) * 0.52 }; }, fillRect() {}, beginPath() {}, ellipse() {}, fill() {}, fillText(text, x, y) { drawn.push({ text, x, y, width: this.measureText(text).width }); } };
  canvas = { width: 0, height: 0, getContext: () => ctx, toBlob: callback => callback(new Blob(["png"], { type: "image/png" })) };
  const cards = load("cards", { document: { fonts: { ready: Promise.resolve() }, documentElement: {}, createElement: () => canvas }, getComputedStyle: () => ({ getPropertyValue: () => "" }) });
  const source = `https://trusted.example/${"very-long-source-link".repeat(20)}`;
  await cards.cardImage("A sourced weekly moment", ["About the size of a mango", "A made-up fact for this test."], `SOURCE-ID p. 4\n${source}`);
  assert.ok(drawn.some(d => d.text.includes("SOURCE-ID")));
  assert.ok(drawn.map(d => d.text).join("").includes(source));
  assert.ok(drawn.every(d => d.width <= 881 && d.y < canvas.height && d.y > 0));
});
