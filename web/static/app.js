// VERDICT viewer. Routes: #/ (overview), #/q/<id> (question). All text is inserted as text, never HTML.

const state = { questions: [], runs: [], run: null, results: {}, filter: "all", search: "", selected: new Set() };
const app = document.getElementById("app");
const runSelect = document.getElementById("run");

// ---------- helpers ----------
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}
const api = (path) => fetch(path).then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)));
const fmt = (v) => (v === null || v === undefined ? "—" : typeof v === "string" ? v : JSON.stringify(v));
const pill = (text, cls = text) => h("span", { class: `pill ${cls}` }, text);
const fileUrl = (path) => "/files/" + path.split("/").map(encodeURIComponent).join("/");
const truncate = (s, n = 4000) => (s.length > n ? s.slice(0, n) + `\n… (${s.length - n} more characters)` : s);

// ---------- data ----------
async function loadRun(id) {
  state.run = id;
  if (id && !state.results[id]) {
    const rows = await api(`/api/runs/${encodeURIComponent(id)}/results`);
    state.results[id] = Object.fromEntries(rows.map((r) => [r.question_id, r]));
  }
}
const results = () => (state.run ? state.results[state.run] || {} : {});

async function init() {
  [state.questions, state.runs] = await Promise.all([api("/api/questions"), api("/api/runs")]);
  runSelect.replaceChildren(
    ...(state.runs.length
      ? state.runs.map((r) => h("option", { value: r.id }, `${r.id} · ${r.meta.agent || "?"} · ${r.meta.model || "?"}`))
      : [h("option", { value: "" }, "no runs yet")])
  );
  runSelect.onchange = async () => { await loadRun(runSelect.value); route(); };
  await loadRun(state.runs[0]?.id || null);
  window.onhashchange = route;
  route();
}

function route() {
  const m = location.hash.match(/^#\/q\/(.+)$/);
  window.scrollTo(0, 0);
  if (m) showQuestion(decodeURIComponent(m[1]));
  else showOverview();
}

// ---------- overview ----------
function showOverview() {
  const res = results();
  const graded = state.questions.filter((q) => q.graded);
  const ran = graded.filter((q) => res[q.id]);
  const count = (v) => ran.filter((q) => res[q.id].verdict === v).length;
  const correct = ran.filter((q) => res[q.id].answer_correct).length;
  const errors = ran.filter((q) => res[q.id].error).length;
  const flagged = ran.filter((q) => (res[q.id].audit || []).length).length;
  const meta = state.runs.find((r) => r.id === state.run)?.meta || {};

  const header = h("section", {},
    h("h1", {}, "Results"),
    state.run
      ? h("div", { class: "meta" },
          ...[["agent", meta.agent], ["model", meta.model], ["effort", meta.effort], ["isolation", meta.isolation],
              ["started", meta.started_at && new Date(meta.started_at).toLocaleString()], ["commit", meta.git_commit?.slice(0, 8)]]
            .filter(([, v]) => v).map(([k, v]) => h("span", {}, `${k} `, h("b", {}, v))))
      : h("p", { class: "muted" }, "No runs yet. Start one with ", h("code", {}, "uv run verdict run"), "."),
  );

  const tiles = state.run && h("section", { class: "tiles" },
    tile(`${correct}/${ran.length}`, "answers correct", "acc"),
    tile(count("ACCEPT"), "ACCEPT", "ok"),
    tile(count("ESCALATE"), "ESCALATE", "warn"),
    tile(count("REJECT"), "REJECT", "bad"),
    tile(errors, "agent errors", errors ? "bad" : ""),
    tile(flagged, "audit flags", flagged ? "warn" : ""),
  );
  const bar = state.run && ran.length && h("div", { class: "bar", title: "ACCEPT / ESCALATE / REJECT" },
    ...[["ACCEPT", "var(--ok)"], ["ESCALATE", "var(--warn)"], ["REJECT", "var(--bad)"]].map(([v, c]) =>
      h("span", { style: `width:${(100 * count(v)) / ran.length}%;background:${c}` })));

  app.replaceChildren(header, tiles || "", bar || "", ledger(res));
}

function tile(n, label, cls = "") {
  return h("div", { class: `tile ${cls}` }, h("div", { class: "n" }, n), h("div", { class: "l" }, label));
}

function ledger(res) {
  const filters = [
    ["all", "All"], ["ACCEPT", "ACCEPT"], ["ESCALATE", "ESCALATE"], ["REJECT", "REJECT"],
    ["notrun", "Not in this run"], ["ungraded", "Not graded yet"],
  ];
  const matches = (q) => {
    const r = res[q.id];
    const f = state.filter;
    if (f === "ungraded" && q.graded) return false;
    if (f === "notrun" && (!q.graded || r)) return false;
    if (["ACCEPT", "ESCALATE", "REJECT"].includes(f) && r?.verdict !== f) return false;
    const s = state.search.toLowerCase();
    return !s || `${q.id} ${q.title} ${q.prompt}`.toLowerCase().includes(s);
  };

  const body = h("tbody");
  const selbar = h("div", { class: "selbar" });
  const renderRows = () => {
    body.replaceChildren(...state.questions.filter(matches).map((q) => row(q, res[q.id], renderSel)));
  };
  const renderSel = () => {
    const ids = [...state.selected];
    selbar.classList.toggle("show", ids.length > 0);
    const cmd = "uv run verdict run " + ids.map((id) => `-q ${id}`).join(" ");
    selbar.replaceChildren(
      h("span", { class: "small muted" }, `${ids.length} selected`),
      h("code", {}, cmd),
      h("button", { class: "btn", onclick: () => navigator.clipboard.writeText(cmd) }, "Copy command"),
      h("button", { class: "btn ghost", onclick: () => { state.selected.clear(); renderRows(); renderSel(); } }, "Clear"),
    );
  };

  const search = h("input", { type: "search", placeholder: "Search questions", value: state.search,
    oninput: (e) => { state.search = e.target.value; renderRows(); } });
  const buttons = filters.map(([key, label]) =>
    h("button", { class: state.filter === key ? "on" : "", onclick: () => { state.filter = key; showOverview(); } }, label));

  renderRows();
  renderSel();
  return h("section", { class: "card" },
    h("h2", {}, `Questions (${state.questions.length})`),
    h("div", { class: "filters" }, ...buttons, search),
    h("table", { class: "ledger" },
      h("thead", {}, h("tr", {}, h("th", {}), h("th", {}, "ID"), h("th", {}, "Question"), h("th", {}, "Type"),
        h("th", {}, "Verdict"), h("th", {}, "Answer"))),
      body),
    selbar,
  );
}

function row(q, r, onSelect) {
  const box = h("input", { type: "checkbox", checked: state.selected.has(q.id) });
  box.onclick = (e) => {
    e.stopPropagation();
    box.checked ? state.selected.add(q.id) : state.selected.delete(q.id);
    onSelect();
  };
  return h("tr", { class: "q", onclick: () => (location.hash = `#/q/${encodeURIComponent(q.id)}`) },
    h("td", { class: "chk" }, box),
    h("td", { class: "id" }, q.id),
    h("td", {}, h("div", {}, q.title), h("div", { class: "small muted" }, q.prompt.slice(0, 140) + (q.prompt.length > 140 ? "…" : ""))),
    h("td", { class: "small" }, q.kind || "—"),
    h("td", {}, !q.graded ? pill("not graded", "") : r ? pill(r.verdict) : h("span", { class: "small muted" }, "not run")),
    h("td", {}, r ? (r.error ? pill("error", "bad") : r.answer_correct ? pill("✓ correct", "ok") : pill("✗ wrong", "bad")) : ""),
  );
}

// ---------- question page ----------
async function showQuestion(id) {
  const q = state.questions.find((x) => x.id === id);
  if (!q) { app.replaceChildren(h("p", {}, `No question ${id}. `, h("a", { href: "#/" }, "Back"))); return; }
  const r = results()[id];
  const idx = state.questions.indexOf(q);
  const prev = state.questions[idx - 1], next = state.questions[idx + 1];

  app.replaceChildren(
    h("div", { class: "row" },
      h("a", { href: "#/" }, "← All questions"),
      h("div", { class: "nav" },
        prev && h("a", { href: `#/q/${encodeURIComponent(prev.id)}` }, `← ${prev.id}`),
        next && h("a", { href: `#/q/${encodeURIComponent(next.id)}` }, `${next.id} →`))),
    verdictCard(q, r),
    h("section", { class: "card" },
      h("div", { class: "row" }, h("h1", {}, `${q.id}. ${q.title}`),
        h("div", {}, pill(q.source, ""), " ", pill(q.reviewed ? "reviewed" : "not reviewed", q.reviewed ? "ok" : "warn"))),
      q.split_from && h("p", { class: "small muted" }, `Split from question ${q.split_from}.`),
      h("p", { class: "prompt" }, q.prompt),
      h("h3", {}, "Files given to the agent"),
      h("ul", { class: "plain" }, ...q.files.map((f) =>
        h("li", {}, h("a", { href: fileUrl(f.path), target: "_blank" }, f.name), h("span", { class: "small muted" }, `  revision ${f.revision} · ${f.path.split("/").slice(-2, -1)[0]}`)))),
    ),
    h("div", { class: "two" }, citationsCard(r), answerKeyCard(q)),
    r?.explanation && h("section", { class: "card" }, h("h2", {}, "Agent explanation"), h("p", { class: "prompt" }, r.explanation)),
    h("section", { class: "card" }, h("h2", {}, "Trajectory"), h("div", { class: "steps", id: "traj" }, h("p", { class: "empty" }, r ? "Loading…" : "Not in this run."))),
  );
  if (r && state.run) {
    const traj = await api(`/api/runs/${encodeURIComponent(state.run)}/trajectory/${encodeURIComponent(id)}`);
    const el = document.getElementById("traj");
    if (el) el.replaceChildren(...(traj.length ? renderTrajectory(traj) : [h("p", { class: "empty" }, "No trajectory recorded.")]));
  }
}

function verdictCard(q, r) {
  if (!q.graded) return h("section", { class: "card verdict" }, h("div", { class: "big" }, "Not graded yet"),
    h("p", { class: "muted" }, "This question has no typed expected answer yet."));
  if (!r) return h("section", { class: "card verdict" }, h("div", { class: "big" }, "Not in this run"),
    h("p", { class: "muted" }, "Run it with ", h("code", {}, `uv run verdict run -q ${q.id}`)),
    h("div", { class: "answers" }, box("Expected", q.expected)));
  return h("section", { class: `card verdict ${r.verdict}` },
    h("div", { class: "row" },
      h("div", { class: "big" }, pill(r.verdict), " ", r.error ? "agent error" : r.answer_correct ? "answer correct" : "answer wrong"),
      h("span", { class: "small muted" }, r.reason)),
    h("div", { class: "answers" },
      box("Agent answer", r.answer, r.error ? "" : r.answer_correct ? "ok" : "bad"),
      box("Expected", q.expected),
      box("Answer type", q.kind + (q.choices.length ? `: ${q.choices.join(" | ")}` : ""))),
    r.error && h("pre", { class: "small" }, r.error),
    (r.audit || []).length > 0 && h("div", { class: "small" }, h("b", {}, "Audit flags: "), h("ul", {}, ...r.audit.map((a) => h("li", {}, a)))),
  );
}

function box(label, value, cls = "") {
  return h("div", { class: "box" }, h("div", { class: "small muted" }, label),
    h("div", { class: `v ${cls}`, style: cls ? `color:var(--${cls})` : "" }, fmt(value)));
}

function citationsCard(r) {
  const cites = r?.citations || [];
  return h("section", { class: "card" }, h("h2", {}, "Agent citations"),
    cites.length ? h("ul", { class: "plain" }, ...cites.map((c) =>
      h("li", { class: `quote ${c.location ? "found" : "missing"}` },
        h("div", { class: "small muted" }, c.location ? `${c.file} · ${c.location}` : `${c.file} · NOT FOUND`, c.controlling ? " · controlling" : ""),
        h("div", {}, `“${c.quote}”`))))
      : h("p", { class: "empty" }, r ? "No citations." : "Not in this run."));
}

function answerKeyCard(q) {
  const traps = q.traps || (q.trap ? [q.trap] : []);
  return h("section", { class: "card" }, h("h2", {}, "Answer key"),
    h("h3", {}, "Expert evidence"),
    q.evidence.length ? h("ul", { class: "plain" }, ...q.evidence.map((e) =>
      h("li", { class: "quote" }, h("div", { class: "small muted" }, e.name), h("div", {}, `“${e.quote}”`))))
      : h("p", { class: "empty" }, "None."),
    q.answer && h("details", {}, h("summary", {}, "Expert answer"), h("p", { class: "prompt" }, q.answer)),
    q.basis && h("details", {}, h("summary", {}, "Basis"), h("p", { class: "prompt" }, q.basis)),
    traps.length > 0 && h("details", {}, h("summary", {}, `Traps (${traps.length})`), h("ul", {}, ...traps.map((t) => h("li", {}, t)))),
    q.notes && h("details", {}, h("summary", {}, "Notes"), h("p", { class: "prompt" }, q.notes)),
  );
}

// ---------- trajectory ----------
// Normalizes both agents' trajectories into steps: {kind, title, body, pre}.
function renderTrajectory(traj) {
  const steps = [];
  for (const item of traj) {
    if (item.type === "command") steps.push({ kind: "", title: "Started Claude Code", body: `files: ${(item.files || []).join(", ")}` });
    else if (item.type === "files") steps.push({ kind: "", title: "Uploaded files", body: (item.files || []).map((f) => f.filename).join(", ") });
    else if (item.type === "request") steps.push({ kind: "", title: "Request", body: "system prompt + question + tools" });
    else if (item.type === "claude_code") steps.push(...claudeCodeEvent(item.event || {}));
    else if (item.type === "response") steps.push(...apiResponse(item.response || {}));
    else if (item.type === "user") steps.push({ kind: "text", title: "Nudge", body: fmt(item.message?.content) });
    else if (item.type === "audit") steps.push({ kind: "err", title: "Audit flags", pre: (item.flags || []).join("\n") });
    else if (item.type === "error") steps.push({ kind: "err", title: "Error", pre: fmt(item.error) });
    else if (item.type === "stderr") steps.push({ kind: "err", title: "stderr", pre: item.text });
  }
  return steps.map((s, i) => h("div", { class: `step ${s.kind}` },
    h("div", { class: "h" }, h("span", {}, `#${i + 1}`), h("b", {}, s.title), s.meta && h("span", {}, s.meta)),
    s.body && h("div", { class: "body" }, s.body),
    s.pre && h("pre", {}, truncate(s.pre))));
}

function claudeCodeEvent(e) {
  if (e.type === "system" && e.subtype === "init") return [{ kind: "", title: "Session", body: `model ${e.model} · tools ${(e.tools || []).join(", ")}` }];
  if (e.type === "system" && e.subtype === "permission_denied") return [{ kind: "err", title: "Permission denied", pre: fmt(e) }];
  if (e.type === "assistant") return contentBlocks(e.message?.content || []);
  if (e.type === "user") return (e.message?.content || []).filter((b) => b.type === "tool_result").map((b) => ({
    kind: "result", title: b.is_error ? "Tool error" : "Tool result", pre: toolResultText(b.content) }));
  if (e.type === "result") return [{ kind: e.is_error ? "err" : "", title: `Finished: ${e.subtype}`,
    meta: [e.num_turns && `${e.num_turns} turns`, e.duration_ms && `${(e.duration_ms / 1000).toFixed(0)}s`,
           e.total_cost_usd != null && `$${e.total_cost_usd.toFixed(3)}`].filter(Boolean).join(" · ") }];
  return []; // rate-limit, thinking-token and other bookkeeping events
}

function apiResponse(resp) {
  const steps = contentBlocks(resp.content || []);
  const u = resp.usage || {};
  if (resp.stop_reason) steps.push({ kind: "", title: `stop: ${resp.stop_reason}`, meta: u.output_tokens ? `${u.input_tokens} in · ${u.output_tokens} out` : "" });
  return steps;
}

function contentBlocks(blocks) {
  const out = [];
  for (const b of blocks) {
    if (b.type === "text" && b.text?.trim()) out.push({ kind: "text", title: "Claude", body: b.text });
    else if (b.type === "tool_use" || b.type === "server_tool_use") {
      const inp = b.input || {};
      const title = b.name === "StructuredOutput" || b.name === "submit_answer" ? "Final answer" : `Tool: ${b.name}`;
      out.push({ kind: "tool", title, pre: inp.command || inp.code || inp.file_path || JSON.stringify(inp, null, 2) });
    } else if (b.type?.endsWith("_tool_result")) {
      const c = b.content || {};
      out.push({ kind: "result", title: "Tool result", pre: [c.stdout, c.stderr].filter(Boolean).join("\n") || JSON.stringify(c, null, 2) });
    }
  }
  return out;
}

function toolResultText(content) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map((c) => (c.type === "text" ? c.text : `[${c.type}]`)).join("\n");
  return JSON.stringify(content, null, 2);
}

init().catch((e) => app.replaceChildren(h("p", {}, `Failed to load: ${e}`)));
