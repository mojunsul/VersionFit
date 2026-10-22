// 버전 인지형 Spring Boot 문서 Q&A 화면. 대화는 (항목, 버전)마다 브라우저에 따로 저장한다. (F2008~F2012)
"use strict";

const $ = (id) => document.getElementById(id);
const CITE = /\[근거\s*([\d,\s]+)\]/g;
const state = { items: [], byId: {}, itemId: null, version: null, busy: false };

// ---------- 저장 (F2009) ----------
const chatKey = () => `chat:${state.itemId}|${state.version}`;
function loadChat() {
  try { return JSON.parse(localStorage.getItem(chatKey())) || []; } catch { return []; }
}
function saveChat(messages) {
  try { localStorage.setItem(chatKey(), JSON.stringify(messages)); } catch { /* 저장 불가(사생활 보호 모드 등)면 이번 화면에서만 유지 */ }
}
function remember(key, value) {
  try { localStorage.setItem(key, value); } catch { /* 위와 같음 */ }
}
function recall(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

// ---------- 공통 ----------
function el(tag, attrs = {}, text) {
  const node = document.createElement(tag);
  Object.assign(node, attrs);
  if (text !== undefined) node.textContent = text;
  return node;
}
function safeUrl(url) {
  return /^https?:\/\//.test(url) ? url : "#";
}
function markdown(text) {
  return DOMPurify.sanitize(marked.parse(text)); // LLM 출력에 섞인 스크립트를 막는다
}
async function getJson(url, options) {
  const res = await fetch(url, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || "요청을 처리하지 못했습니다.");
  return body;
}

// ---------- 근거 표시 (F2008): 답변이 실제로 인용한 [근거 N]만 ----------
function citedSources(answer, sources) {
  const used = new Set();
  for (const m of answer.matchAll(CITE)) {
    m[1].split(",").map((n) => parseInt(n, 10)).filter(Number.isInteger).forEach((n) => used.add(n));
  }
  return sources.map((s, i) => [i + 1, s]).filter(([n]) => used.has(n));
}
function renderSources(answer, sources) {
  const used = citedSources(answer, sources);
  if (!used.length) return el("p", { className: "caption" }, "ⓘ 답변에 인용된 근거가 없습니다.");
  const box = el("details", { className: "sources" });
  box.append(el("summary", {}, `답변에 사용한 근거 ${used.length}건`));
  const list = el("ul");
  for (const [n, s] of used) {
    const li = el("li");
    li.append(el("strong", {}, `[근거 ${n}] `), `${s.title} · ${s.source_type} · `,
      el("a", { href: safeUrl(s.url), target: "_blank", rel: "noopener" }, "원문"));
    list.append(li);
  }
  box.append(list);
  return box;
}

// ---------- 대화 ----------
function renderMessage(m) {
  const box = el("div", { className: `msg ${m.role}` });
  if (m.role === "user") {
    box.textContent = m.content;
    return box;
  }
  box.innerHTML = markdown(m.content);
  if (m.notice) box.append(el("p", { className: "notice" }, m.notice));
  box.append(renderSources(m.content, m.sources || []));
  if (m.general) box.append(renderGeneral(m.general));
  else if (m.question && needsGeneral(m)) box.append(generalButton(m));
  return box;
}
function renderChat() {
  const list = $("messages");
  list.replaceChildren(...loadChat().map(renderMessage));
}

// ---------- 문서에 답이 없을 때 일반 지식 답변 (버튼을 눌렀을 때만) ----------
function needsGeneral(m) {
  return m.content.includes("확인되지 않") || !citedSources(m.content, m.sources || []).length;
}
function renderGeneral(text) {
  const box = el("div", { className: "general" });
  box.append(el("p", { className: "general-label" }, "⚠ 문서 근거 없음 · 일반 지식 답변 (버전과 맞지 않을 수 있습니다)"));
  const body = el("div");
  body.innerHTML = markdown(text);
  box.append(body);
  return box;
}
function generalButton(m) {
  const btn = el("button", { type: "button", className: "secondary general-btn" }, "💡 일반 지식으로 답변 보기");
  btn.addEventListener("click", async () => {
    const key = chatKey();
    btn.disabled = true;
    btn.textContent = "일반 지식 답변을 만드는 중...";
    try {
      const { answer } = await getJson("/api/general", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item_id: m.item_id, version: m.version, question: m.question }),
      });
      // 같은 대화에서 이 답변을 찾아 일반 지식 답변을 붙여 저장한다
      const saved = (() => { try { return JSON.parse(localStorage.getItem(key)) || []; } catch { return []; } })();
      const target = saved.find((s) => s.role === "assistant" && s.question === m.question && s.content === m.content);
      if (target) target.general = answer;
      try { localStorage.setItem(key, JSON.stringify(saved)); } catch { /* 저장 불가 */ }
      m.general = answer;
      const box = renderGeneral(answer);
      btn.replaceWith(box);
      box.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      btn.disabled = false;
      btn.textContent = "💡 일반 지식으로 답변 보기";
      btn.after(el("p", { className: "error" }, err.message));
    }
  });
  return btn;
}

async function refreshIndexStatus() {
  const total = state.itemsTotal == null ? "" : `항목 ${state.itemsTotal}건`;
  let docs = "";
  if (state.itemId) {
    try {
      const { count } = await getJson(`/api/docs-count?item_id=${encodeURIComponent(state.itemId)}&version=${state.version}`);
      docs = ` · 이 항목·버전 문서 청크 ${count}건`;
    } catch { /* 현황 표시는 부가 정보라 실패해도 넘어간다 */ }
  }
  $("index-status").textContent = `색인 현황 · ${total}${docs}`;
}

function selectTarget() {
  const item = state.byId[state.itemId];
  const ready = Boolean(item) && !state.blocked;
  $("chat-area").hidden = !ready;
  $("chat-title").hidden = !ready;
  $("pick-hint").hidden = Boolean(item);
  $("guide-btn").disabled = !ready || state.busy;
  $("clear-btn").disabled = !item || state.blocked;
  $("unpick-btn").disabled = !item || state.blocked;
  if (item) {
    $("chat-title").textContent = `${item.name} · Spring Boot ${state.version}`;
    $("ask-input").placeholder = `${item.name} (${state.version})에 대해 궁금한 점을 물어보세요`;
    $("item-select").value = state.itemId;
    remember("last-item", state.itemId);
    renderChat();
  }
  remember("last-version", state.version);
  showVersionWarning();
  refreshIndexStatus();
}

// ---------- SSE 요청 (F2012 진행 상태) ----------
async function streamRequest(url, payload, onStep) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "요청을 처리하지 못했습니다.");
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const event = /^event: (.*)$/m.exec(raw)?.[1];
      const data = JSON.parse(/^data: (.*)$/m.exec(raw)?.[1] ?? "null");
      if (event === "step") onStep(data);
      if (event === "error") throw new Error(data);
      if (event === "result") return data;
    }
  }
  throw new Error("응답이 중간에 끊겼습니다. 다시 시도해 주세요.");
}

async function send(kind, question) {
  if (state.busy) return;
  state.busy = true;
  const target = { item_id: state.itemId, version: state.version };
  const messages = loadChat();
  const user = { role: "user", content: question };
  messages.push(user);
  saveChat(messages);
  $("messages").append(renderMessage(user));

  const status = el("details", { className: "msg status", open: true });
  const label = el("summary", {}, kind === "guide" ? "가이드를 준비하고 있습니다..." : "관련 문서를 찾고 있습니다...");
  const steps = el("ul");
  status.append(label, steps);
  $("messages").append(status);
  setBusy(true);
  try {
    const url = kind === "guide" ? "/api/guide" : "/api/ask";
    const result = await streamRequest(url, kind === "guide" ? target : { ...target, question }, (step) => {
      label.textContent = step;
      steps.append(el("li", {}, step));
    });
    status.open = false;
    label.textContent = kind === "guide" ? "가이드 준비 완료" : "근거 준비 완료";
    const reply = { role: "assistant", content: result.answer, sources: result.sources, notice: result.notice };
    if (kind === "ask") Object.assign(reply, { question, ...target }); // 일반 지식 답변 버튼이 같은 질문을 다시 보낸다
    // 응답이 오는 동안 사용자가 항목·버전을 바꿨을 수 있어 원래 대화에 저장한다
    const key = `chat:${target.item_id}|${target.version}`;
    const saved = (() => { try { return JSON.parse(localStorage.getItem(key)) || messages; } catch { return messages; } })();
    saved.push(reply);
    try { localStorage.setItem(key, JSON.stringify(saved)); } catch { /* 저장 불가 */ }
    if (chatKey() === key) {
      const node = renderMessage(reply);
      $("messages").append(node);
      node.scrollIntoView({ behavior: "smooth", block: "start" }); // 긴 답변도 첫 줄부터 읽게 한다
    }
  } catch (err) {
    status.replaceWith(el("p", { className: "error" }, err.message));
  } finally {
    state.busy = false;
    setBusy(false);
  }
}
function setBusy(busy) {
  for (const id of ["guide-btn", "ask-input"]) $(id).disabled = busy || !state.itemId || state.blocked;
  $("ask-form").querySelector("button").disabled = busy;
}

// ---------- 조건 탐색 (F2011) ----------
async function runExplore(condition) {
  const status = $("explore-status");
  status.textContent = "조건에 맞는 의존성을 고르는 중...";
  $("explore-cards").replaceChildren();
  try {
    const { results } = await getJson("/api/explore", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ condition }),
    });
    status.textContent = results.length ? `'${condition}'에 맞는 의존성 ${results.length}개` : `'${condition}'에 맞는 의존성을 찾지 못했습니다. 조건을 바꿔 보세요.`;
    $("explore-cards").replaceChildren(...results.map((r) => {
      const card = el("div", { className: "card" });
      const title = el("div");
      title.append(el("strong", {}, r.name), ` · ${r.group}`);
      const open = el("button", { type: "button" }, "이 의존성으로 대화하기");
      open.addEventListener("click", () => {
        state.itemId = r.item_id;
        $("item-filter").value = "";
        renderItemOptions("");
        $("explore").open = false; // 고른 뒤에는 접어서 상단 고정 영역을 줄인다
        selectTarget();
        $("chat-area").scrollIntoView({ behavior: "smooth" });
      });
      card.append(title, el("div", { className: "reason" }, r.reason), open);
      return card;
    }));
  } catch (err) {
    status.textContent = "";
    $("explore-cards").replaceChildren(el("p", { className: "error" }, err.message));
  }
}

// ---------- 사이드바 ----------
function renderItemOptions(filter) {
  const q = filter.trim().toLowerCase();
  const shown = state.items.filter((i) => !q || `${i.name} ${i.id} ${i.group}`.toLowerCase().includes(q));
  $("item-select").replaceChildren(...shown.map((i) => el("option", { value: i.id, title: `${i.name} (${i.group})` }, `${i.name} (${i.group})`)));
  if (state.itemId) $("item-select").value = state.itemId;
}
function showVersionWarning() {
  const missing = (state.missingDocs || []).includes(state.version);
  if (state.blocked) return;
  $("banner").hidden = !missing;
  $("banner").textContent = missing ? `${state.version} 문서 원문이 없습니다. 먼저 python -m scripts.fetch_docs 를 실행해 주세요.` : "";
}

async function init() {
  let status;
  try {
    status = await getJson("/api/status");
  } catch {
    $("banner").hidden = false;
    $("banner").textContent = "서버에 연결하지 못했습니다. 서버가 실행 중인지 확인해 주세요.";
    return;
  }
  state.itemsTotal = status.items_total;
  state.missingDocs = status.missing_docs;
  if (!status.gms_key || !status.items_total) {
    state.blocked = true;
    $("banner").hidden = false;
    $("banner").textContent = !status.gms_key
      ? "GMS_KEY가 설정되지 않았습니다. .env.example을 복사해 .env에 키를 넣고 서버를 다시 시작해 주세요."
      : "항목 색인이 비어 있습니다. 먼저 python -m scripts.build_items 를 실행해 주세요.";
    $("explore").hidden = true;
  }

  state.items = await getJson("/api/items");
  state.byId = Object.fromEntries(state.items.map((i) => [i.id, i]));
  $("version-select").replaceChildren(...status.versions.map((v) => el("option", { value: v }, v)));
  const lastVersion = recall("last-version");
  state.version = status.versions.includes(lastVersion) ? lastVersion : status.versions[0];
  $("version-select").value = state.version;
  const lastItem = recall("last-item");
  state.itemId = state.byId[lastItem] ? lastItem : null;
  renderItemOptions("");

  $("item-filter").addEventListener("input", (e) => renderItemOptions(e.target.value));
  $("item-select").addEventListener("change", (e) => { state.itemId = e.target.value; selectTarget(); });
  $("version-select").addEventListener("change", (e) => { state.version = e.target.value; selectTarget(); });
  $("clear-btn").addEventListener("click", () => { saveChat([]); renderChat(); });
  $("unpick-btn").addEventListener("click", () => {
    // 대화 기록은 남기고 선택만 비운다. 새로고침해도 빈 상태로 시작하게 저장된 마지막 항목도 지운다
    state.itemId = null;
    try { localStorage.removeItem("last-item"); } catch { /* 저장 불가 */ }
    $("item-select").value = "";
    $("explore").open = true;
    selectTarget();
  });
  $("guide-btn").addEventListener("click", () => send("guide", "📘 버전 맞춤 사용 가이드 (의존성 선언 · 핵심 설정 · import)"));
  $("ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = $("ask-input").value.trim();
    if (!q) return;
    $("ask-input").value = "";
    send("ask", q);
  });
  $("ask-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("ask-form").requestSubmit(); }
  });
  $("explore-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const c = $("explore-input").value.trim();
    if (c) runExplore(c);
  });
  selectTarget();
  setBusy(false);
}

// 상단 고정 영역의 높이만큼 답변 스크롤 위치를 내려, 답변 첫 줄이 고정 영역에 가리지 않게 한다
new ResizeObserver(([e]) => document.documentElement.style.setProperty("--topbar-h", `${e.target.offsetHeight}px`))
  .observe($("topbar"));

init();
