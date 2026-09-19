/* ResearchMind frontend: plain JavaScript, no build step. */

const STEPS = [
  { id: "search", label: "Search agent", desc: "Looks for recent sources on the web" },
  { id: "reader", label: "Reader agent", desc: "Opens the best pages and takes notes" },
  { id: "writer", label: "Writer", desc: "Drafts the report from the notes" },
  { id: "critic", label: "Critic", desc: "Scores the report and lists fixes" },
  { id: "revise", label: "Reviser", desc: "Rewrites the report using the critic's fixes" },
];
const EXAMPLES = ["Fusion energy progress", "CRISPR gene editing", "How LLM agents use tools"];
const STATUS_TEXT = { waiting: "Waiting", running: "Working", done: "Done" };

const $ = (id) => document.getElementById(id);
const el = {
  form: $("form"), topic: $("topic"), revise: $("revise"), run: $("run"), cancel: $("cancel"),
  trace: $("trace"), error: $("error"), banner: $("banner"),
  empty: $("empty"), emptyTitle: $("empty-title"), emptyBody: $("empty-body"), examples: $("examples"),
  result: $("result"), reportBody: $("report-body"), reportNote: $("report-note"), download: $("download"),
  critic: $("critic"), score: $("score"), scoreValue: $("score-value"), criticText: $("critic-text"),
};

let state = { status: "idle", steps: {}, error: null };
let source = null;
let currentTopic = "";

const escapeHtml = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/** Markdown -> sanitised HTML (model output can contain text scraped from the web). */
const markdown = (text) => DOMPurify.sanitize(marked.parse(text ?? ""));

// ---------- state ----------

function applyEvent(e) {
  const steps = state.steps;
  if (e.type === "step_start") steps[e.step] = { status: "running", tools: [] };
  if (e.type === "tool") {
    const s = (steps[e.step] ??= { status: "running", tools: [] });
    s.tools.push({ name: e.name, arg: e.arg });
  }
  if (e.type === "step_done") steps[e.step] = { ...steps[e.step], status: "done", output: e.output, score: e.score ?? null };
  if (e.type === "done") state.status = "done";
  if (e.type === "error") { state.status = "error"; state.error = e.message; }
}

function stopStream() {
  if (source) { source.close(); source = null; }
}

function startRun(topic) {
  const clean = topic.trim();
  if (!clean || state.status === "running") return;
  stopStream();
  el.topic.value = clean;
  currentTopic = clean;
  state = { status: "running", steps: {}, error: null };
  render();

  source = new EventSource(`/api/research?topic=${encodeURIComponent(clean)}&revise=${el.revise.checked}`);
  source.onmessage = (msg) => {
    const event = JSON.parse(msg.data);
    applyEvent(event);
    if (event.type === "done" || event.type === "error") stopStream(); // stop EventSource auto-reconnecting
    render();
  };
  source.onerror = () => {
    // Network failure, or the server rejected the request (empty topic / busy).
    stopStream();
    state.status = "error";
    state.error = "Could not reach the server. Check that it is running, then try again.";
    render();
  };
}

// ---------- rendering ----------

function renderTrace() {
  const started = state.status !== "idle";
  el.trace.hidden = !started;
  if (!started) return;
  const visible = STEPS.filter((s) => s.id !== "revise" || state.steps.revise);
  el.trace.innerHTML = visible.map((s, i) => {
    const st = state.steps[s.id];
    const status = st?.status ?? "waiting";
    const tools = (st?.tools ?? []).map((t) =>
      `<li>${t.name === "web_search" ? `Searching “${escapeHtml(t.arg)}”` : `Reading ${escapeHtml(t.arg)}`}</li>`).join("");
    const raw = status === "done" && (s.id === "search" || s.id === "reader")
      ? `<details class="trace-raw"><summary>Show what it found</summary><pre>${escapeHtml(st.output)}</pre></details>` : "";
    return `
      <li class="trace-step is-${status}">
        <span class="trace-marker" aria-hidden="true">${status === "done" ? "✓" : i + 1}</span>
        <div class="trace-body">
          <div class="trace-head">
            <span class="trace-label">${s.label}</span>
            <span class="trace-status">${STATUS_TEXT[status]}</span>
          </div>
          <p class="trace-desc">${s.desc}</p>
          ${tools ? `<ul class="trace-tools">${tools}</ul>` : ""}
          ${raw}
        </div>
      </li>`;
  }).join("");
}

function renderReport() {
  const { steps } = state;
  const revised = steps.revise?.status === "done";
  const text = revised ? steps.revise.output : steps.writer?.status === "done" ? steps.writer.output : null;

  el.result.hidden = !text;
  el.empty.hidden = Boolean(text);
  if (!text) {
    const running = state.status === "running";
    el.emptyTitle.textContent = running ? "The report appears here when the writer finishes" : "No report yet";
    el.emptyBody.hidden = running;
    return;
  }
  el.reportBody.innerHTML = markdown(text);
  el.reportNote.hidden = !revised;

  const critic = steps.critic?.status === "done" ? steps.critic : null;
  el.critic.hidden = !critic;
  if (critic) {
    el.score.hidden = critic.score == null;
    el.scoreValue.textContent = critic.score ?? "";
    el.criticText.innerHTML = markdown(critic.output.replace(/^Score:.*\n?/i, ""));
  }
}

function render() {
  const running = state.status === "running";
  el.topic.disabled = running;
  el.revise.disabled = running;
  el.run.hidden = running;
  el.cancel.hidden = !running;
  el.run.disabled = !el.topic.value.trim();
  el.error.hidden = state.status !== "error";
  el.error.textContent = state.error ?? "";
  renderTrace();
  renderReport();
}

// ---------- wiring ----------

el.form.addEventListener("submit", (e) => { e.preventDefault(); startRun(el.topic.value); });
el.topic.addEventListener("input", render);
el.cancel.addEventListener("click", () => {
  stopStream();
  state.status = "error";
  state.error = "Cancelled.";
  render();
});
el.download.addEventListener("click", () => {
  const revised = state.steps.revise?.status === "done";
  const text = revised ? state.steps.revise.output : state.steps.writer?.output;
  if (!text) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "text/markdown" }));
  a.download = `${currentTopic.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40) || "report"}.md`;
  a.click();
  URL.revokeObjectURL(a.href);
});

el.examples.innerHTML = EXAMPLES.map((ex) => `<button type="button" class="chip">${escapeHtml(ex)}</button>`).join("");
el.examples.addEventListener("click", (e) => {
  if (e.target.classList.contains("chip")) startRun(e.target.textContent);
});

// Warn early if the server or the API keys are not set up.
fetch("/api/health")
  .then((r) => r.json())
  .then((h) => {
    const missing = [!h.openai && "OPENAI_API_KEY", !h.tavily && "TAVILY_API_KEY"].filter(Boolean);
    if (missing.length) {
      el.banner.innerHTML = `Add ${missing.map((m) => `<code>${m}</code>`).join(" and ")} to the <code>.env</code> file, then restart the server.`;
      el.banner.hidden = false;
    }
  })
  .catch(() => {
    el.banner.textContent = "Can’t reach the server. Make sure it is running.";
    el.banner.hidden = false;
  });

render();
