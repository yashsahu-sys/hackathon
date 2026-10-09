"use strict";
const API = "/api/v1";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const S = { mode: "offline", glid: null, persona: null, session: null, busy: false, audio: null, trio: [],
            voice: "female", cmpVoice: "female", cmp: null };

// Seller lines for quick testing (Roman Hinglish, how real VANI sellers talk)
const QUICK = [
  "Haan ji, main bol raha hoon", "Abhi busy hoon, baad mein call karna", "Matlab? Samjha nahi", "Thoda dheere boliye",
  "Aap baar baar call kyun karte ho?", "Sorry, can you speak in English please", "Aap AI ho?",
  "Kitne der ki meeting hogi?", "Main already TradeIndia pe hoon", "Haan theek hai, kal 11 baje aa jaiye",
];
const LABELS = {
  "language.style": "Language", "language.formality": "Formality", "language.english_mix": "English mix",
  "voice.pace": "Pace", "voice.gender": "Voice gender", "voice.speaker": "Voice", "voice.pitch": "Pitch",
  "tone.empathy": "Empathy", "tone.warmth": "Warmth", "tone.max_words_per_turn": "Max words / turn",
  "plan.opening": "Opening", "plan.objection_playbook": "Objection order", "plan.greeting": "Greeting",
  "voice.temperature": "Expressiveness", "language.seller_gender": "Seller gender", "language.address_as": "Address as",
};

function segmented(id, onPick) {
  $(id).querySelectorAll("button").forEach((b) => b.onclick = () => {
    $(id).querySelectorAll("button").forEach((x) => { x.classList.toggle("on", x === b); x.setAttribute("aria-checked", x === b); });
    onPick(b.dataset.g);
  });
}
segmented("voice", (g) => { S.voice = g; if (S.glid && !S.session) loadSeller(S.glid); });
segmented("cmp-voice", (g) => { S.cmpVoice = g; loadCompare(); });

async function api(path, opts = {}) {
  const res = await fetch(API + path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || res.statusText);
  return body;
}
const post = (path, data) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
const status = (m) => { $("status").textContent = m || ""; };

// ------------------------------------------------------------------ views
document.querySelectorAll(".tab").forEach((t) => t.onclick = () => {
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === t));
  ["call", "compare", "evidence"].forEach((v) => $("view-" + v).classList.toggle("hidden", v !== t.dataset.view));
  if (t.dataset.view === "evidence") loadEvidence();
});

async function init() {
  const h = await api("/health");
  S.mode = h.mode;
  $("mode").textContent = h.mode === "live" ? `LIVE · ${h.models.tts} · ${h.models.llm}` : "OFFLINE · browser voice";
  $("mode").className = "badge " + h.mode;
  if (h.evidence_baseline?.n) $("baseline").textContent =
    `${h.evidence_baseline.n.toLocaleString()} past calls · ${(h.evidence_baseline.meeting_rate * 100).toFixed(1)}% meetings`;
  $("quick").innerHTML = QUICK.map((q) => `<button disabled data-t="${esc(q)}">${esc(q)}</button>`).join("");
  $("quick").querySelectorAll("button").forEach((b) => b.onclick = () => sellerSays(b.dataset.t));
  try {
    const d = await api("/demo-sellers?k=3");
    S.trio = d.sellers;
    S.cmp = d;
    $("trio").innerHTML = d.sellers.map((s, i) =>
      `<button data-g="${s.glid}">${i + 1}. ${esc(s.state || "?")} · ${esc(s.business_kind)}</button>`).join("");
    $("trio").querySelectorAll("button").forEach((b) => b.onclick = () => loadSeller(b.dataset.g));
    await loadCompare();
  } catch (e) { $("trio").textContent = "Demo trio unavailable: " + e.message; }
}

// ---------------------------------------------------------------- sellers
$("load").onclick = () => $("glid").value.trim() && loadSeller($("glid").value.trim());
$("glid").onkeydown = (e) => { if (e.key === "Enter") $("load").onclick(); };

async function loadSeller(glid) {
  try {
    status("Generating persona…");
    const [s, p] = await Promise.all([api(`/sellers/${glid}`), api(`/sellers/${glid}/persona?voice_gender=${S.voice}`)]);
    S.session = null;
    S.glid = glid;
    $("trio").querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.g === glid));
    const pr = s.profile, h = pr.bot_history;
    $("seller").innerHTML = `<b>${esc(pr.company_name || glid)}</b> · ${esc(pr.city || "")}, ${esc(pr.state || "?")}<br>
      ${esc(pr.business_kind)} · ${esc(pr.turnover_raw || "turnover n/a")} · ${pr.business_age_years ?? "?"} yrs ·
      ${esc((pr.categories || []).slice(0, 2).join(", "))}<br>
      VANI history: ${h.answered}/${h.attempts} answered · ${h.meetings_fixed} meeting(s) ·
      ${Object.entries(h.dispositions).map(([k, v]) => `${esc(k)} ×${v}`).join(", ") || "no dispositions"}
      ${pr.missing_fields.length ? `<br><span class="badge default">missing: ${esc(pr.missing_fields.join(", "))}</span>` : ""}`;
    renderPersona(p.persona);
    $("start").disabled = false;
    status("");
  } catch (e) { status("⚠ " + e.message); }
}

function badge(d) {
  const conf = d.confidence === "live" ? "live-c" : d.confidence;
  return `<span class="badge ${esc(d.source)}">${esc(d.source.replace("_", " "))}</span>
          <span class="badge ${esc(conf)}">${esc(d.confidence.replace("_", " "))}</span>`;
}

function renderPersona(p, changed = []) {
  S.persona = p;
  $("pver").textContent = "v" + p.version;
  const decs = Object.entries(p.decisions).map(([k, d]) => `
    <div class="dec" data-k="${esc(k)}">
      <div class="k">${esc(LABELS[k] || k)} ${badge(d)}</div>
      <div class="v">${esc(Array.isArray(d.value) ? d.value.join(", ") : d.value)}</div>
      <div class="why">${esc(d.reason)}</div>
      ${d.evidence_ids.map((id) => `<span class="ev-link" data-id="${esc(id)}">${esc(id)}</span>`).join("")}
    </div>`).join("");
  $("persona").innerHTML = `
    <div class="persona-label">${esc(p.label)}</div>
    <dl class="facts">
      <dt>Language</dt><dd>${esc(p.language.code)} · ${esc(p.language.style)} · ${Math.round(p.language.english_mix * 100)}% English</dd>
      <dt>Voice</dt><dd>${esc(p.voice.speaker)} (${esc(p.voice.gender)}) · ${p.voice.pace}x · expressiveness ${p.voice.temperature} · ${esc(p.voice.accent)}</dd>
      <dt>Seller</dt><dd>${p.language.seller_gender === "unknown" ? "gender unknown → neutral" : esc(p.language.seller_gender)} · address as “${esc(p.language.address_as)}”</dd>
      <dt>Tone</dt><dd>${esc(p.language.formality)} · warmth ${esc(p.tone.warmth)} · empathy ${esc(p.tone.empathy)}</dd>
      <dt>Strategy</dt><dd>${esc(p.tone.strategy)} · ≤${p.tone.max_words_per_turn} words</dd>
    </dl>
    <div class="opening">“${esc(p.plan.opening)}”</div>
    ${decs}`;
  document.querySelectorAll(".ev-link").forEach((a) => a.onclick = () => showFinding(a.dataset.id));
  changed.forEach((f) => {
    const el = document.querySelector(`.dec[data-k="${CSS.escape(f)}"]`);
    if (el) { el.classList.add("flash"); setTimeout(() => el.classList.remove("flash"), 2500); }
  });
}

async function showFinding(id) {
  try {
    const f = await api(`/evidence/${encodeURIComponent(id)}`);
    $("finding-body").innerHTML = `<h3>${esc(f.title)}</h3><p>${esc(f.statement)}</p>
      <p><span class="badge ${esc(f.strength)}">${esc(f.strength)}</span> ${f.causal ? '<span class="badge seller_data">side-by-side variant</span>' : '<span class="badge default">correlational</span>'}
      95% CI ${(f.ci95[0] * 100).toFixed(1)}–${(f.ci95[1] * 100).toFixed(1)}% · p ${f.p_value ?? "n/a"}</p>
      <p>${esc(f.implication)}</p><pre>${esc(JSON.stringify(f, null, 2))}</pre>`;
    $("finding-dlg").showModal();
  } catch (e) { status("⚠ " + e.message); }
}

// ------------------------------------------------------------------ calls
$("start").onclick = async () => {
  stopAudio();
  try {
    status("Dialling…");
    const r = await post("/calls", { seller_glid: S.glid, voice_gender: S.voice });
    S.session = r.session_id;
    renderPersona(r.persona);
    $("chat").innerHTML = "";
    $("log").innerHTML = `<p class="empty">No switches yet: persona v1 is live.</p>`;
    $("stage").textContent = "opening";
    setCallControls(true);
    bubble("bot", r.bot.text, metaOf(r.bot, r.persona.version));
    await speak(r.bot);
    status("Your turn: hold the mic or type as the seller.");
  } catch (e) { status("⚠ " + e.message); }
};

$("end").onclick = async () => {
  if (!S.session) return;
  const r = await post(`/calls/${S.session}/end`, {});
  outcome(r.outcome);
  setCallControls(false);
  stopAudio();
};

function setCallControls(on) {
  ["mic", "say", "send", "end", "export"].forEach((id) => $(id).disabled = !on && id !== "export");
  $("quick").querySelectorAll("button").forEach((b) => b.disabled = !on);
}

const metaOf = (bot, v) => `v${v} · ${bot.speaker} · ${bot.pace}x · expr ${bot.temperature} · ${bot.language_code}${bot.source === "llm" ? " · LLM" : ""}`;

function bubble(role, text, meta, signals = []) {
  const el = document.createElement("div");
  el.className = "bubble " + role;
  const flow = new Set(["agreement", "refusal", "identity"]);
  const chips = signals.filter((s) => s.confidence >= 0.6)
    .map((s) => `<span class="sig ${flow.has(s.type) ? "flow" : ""}">${esc(s.type.replace("_", " "))}</span>`).join("");
  el.innerHTML = `${esc(text)}${chips ? `<div>${chips}</div>` : ""}${meta ? `<div class="meta">${esc(meta)}</div>` : ""}`;
  $("chat").appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "end" });
}

function switchCard(e) {
  $("log").querySelector(".empty")?.remove();
  const rows = e.changes.map((c) => `<tr><td>${esc(c.field)}</td><td>${esc(c.old)} → <b>${esc(c.new)}</b></td></tr>`).join("");
  const el = document.createElement("div");
  el.className = "event";
  el.innerHTML = `<div class="top"><span class="sigtype">${esc(e.signal.replace("_", " "))}</span>
      <span>turn ${e.turn} · ${(e.at_ms / 1000).toFixed(1)}s · conf ${e.confidence} · v${e.from_version}→v${e.to_version}</span></div>
    <div class="trigger">“${esc(e.trigger)}”</div><table>${rows}</table><div>${esc(e.reason)}</div>`;
  $("log").prepend(el);
}

function outcome(o) {
  const el = document.createElement("div");
  el.className = "outcome " + (o === "meeting_fixed" ? "ok" : "no");
  el.textContent = { meeting_fixed: "✅ Meeting fixed: tomorrow 11:00", declined: "Call closed politely: seller declined",
                     callback: "Callback requested", dropped: "Call ended" }[o] || o;
  $("log").prepend(el);
}

async function sellerSays(text, audioBlob) {
  if (S.busy || !S.session) return;
  S.busy = true;
  stopAudio();
  status(audioBlob ? "Transcribing…" : "VANI is thinking…");
  const fd = new FormData();
  if (audioBlob) fd.append("audio", audioBlob, "turn.wav"); else fd.append("text", text);
  try {
    const r = await api(`/calls/${S.session}/turns`, { method: "POST", body: fd });
    bubble("seller", r.seller_text, "", r.signals);
    r.switches.forEach(switchCard);
    if (r.switches.length) renderPersona(r.persona, r.switches.flatMap((s) => s.changes.map((c) => c.field)));
    else S.persona = r.persona;
    bubble("bot", r.bot.text, metaOf(r.bot, r.persona.version));
    $("stage").textContent = r.stage;
    r.warnings.forEach((w) => console.warn(w));
    if (r.status === "ended") { outcome(r.outcome); setCallControls(false); }
    status(r.status === "ended" ? "Call ended." : "Your turn.");
    await speak(r.bot);
  } catch (e) { status("⚠ " + e.message); }
  finally { S.busy = false; }
}
$("send").onclick = () => { const t = $("say").value.trim(); if (t) { $("say").value = ""; sellerSays(t); } };
$("say").onkeydown = (e) => { if (e.key === "Enter") $("send").onclick(); };

$("export").onclick = async () => {
  const r = await api(`/calls/${S.session}`);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(r, null, 2)], { type: "application/json" }));
  a.download = `call_${r.seller_glid}_${r.session_id}.json`;
  a.click();
};

// ---------------------------------------------------------------- speaking
function stopAudio() { if (S.audio) { S.audio.pause(); S.audio = null; } window.speechSynthesis?.cancel(); }

function speak(bot) {
  return new Promise((resolve) => {
    if (bot.audio_b64) {
      const a = new Audio("data:audio/wav;base64," + bot.audio_b64);
      S.audio = a; a.onended = resolve; a.onerror = resolve; a.play().catch(resolve);
      return;
    }
    if (!window.speechSynthesis) return resolve();
    const u = new SpeechSynthesisUtterance(bot.text.replace(/।/g, "."));
    u.lang = bot.language_code; u.rate = bot.pace;
    const voices = speechSynthesis.getVoices();
    u.voice = voices.find((v) => v.lang === bot.language_code) || voices.find((v) => v.lang?.startsWith(bot.language_code.slice(0, 2))) || null;
    u.onend = resolve; u.onerror = resolve;
    speechSynthesis.speak(u);
  });
}

// --------------------------------------------------------------- listening
// Live: 16 kHz mono WAV to Saaras. Offline: the browser's own speech recognition.
const rec = { ctx: null, node: null, src: null, stream: null, chunks: [], recog: null };
async function startRec() {
  stopAudio();
  if (S.mode !== "live") {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { status("Browser speech recognition unavailable: type instead."); return; }
    rec.recog = new SR();
    rec.recog.lang = S.persona?.language?.code || "hi-IN";
    rec.recog.onresult = (e) => sellerSays(e.results[0][0].transcript);
    rec.recog.onerror = (e) => status("Mic: " + e.error);
    rec.recog.start();
    $("mic").classList.add("rec"); status("Listening…");
    return;
  }
  rec.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
  rec.ctx = new AudioContext({ sampleRate: 16000 });
  rec.src = rec.ctx.createMediaStreamSource(rec.stream);
  rec.node = rec.ctx.createScriptProcessor(4096, 1, 1);
  rec.chunks = [];
  rec.node.onaudioprocess = (e) => rec.chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
  rec.src.connect(rec.node); rec.node.connect(rec.ctx.destination);
  $("mic").classList.add("rec"); status("Listening… release to send");
}
function stopRec() {
  $("mic").classList.remove("rec");
  if (rec.recog) { rec.recog.stop(); rec.recog = null; return; }
  if (!rec.ctx) return;
  rec.node.disconnect(); rec.src.disconnect(); rec.stream.getTracks().forEach((t) => t.stop());
  const rate = rec.ctx.sampleRate; rec.ctx.close(); rec.ctx = null;
  const len = rec.chunks.reduce((n, c) => n + c.length, 0);
  if (len < rate * 0.3) { status("Too short: hold the button while you speak."); return; }
  sellerSays(null, wav(rec.chunks, len, rate));
}
function wav(chunks, len, rate) {
  const buf = new ArrayBuffer(44 + len * 2), v = new DataView(buf);
  const w = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  w(0, "RIFF"); v.setUint32(4, 36 + len * 2, true); w(8, "WAVE"); w(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, "data"); v.setUint32(40, len * 2, true);
  let o = 44;
  for (const c of chunks) for (let i = 0; i < c.length; i++, o += 2) {
    const s = Math.max(-1, Math.min(1, c[i])); v.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: "audio/wav" });
}
$("mic").onpointerdown = (e) => { e.preventDefault(); startRec().catch((err) => status("Mic: " + err.message)); };
$("mic").onpointerup = $("mic").onpointerleave = () => stopRec();

// ----------------------------------------------------------------- compare
async function loadCompare() {
  if (!S.cmp) return;
  // Same trio, personas regenerated with the chosen bot voice.
  const sellers = await Promise.all(S.cmp.sellers.map(async (s) =>
    ({ ...s, persona: (await api(`/sellers/${s.glid}/persona?voice_gender=${S.cmpVoice}`)).persona })));
  S.trio = sellers;
  renderCompare({ ...S.cmp, sellers });
}

function renderCompare(d) {
  $("cmp-dist").textContent = `min distance ${d.min_pairwise_distance}`;
  $("compare").innerHTML = d.sellers.map((s, i) => {
    const p = s.persona, dec = p.decisions;
    const row = (k) => dec[k] ? `<div class="dec"><div class="k">${esc(LABELS[k] || k)} ${badge(dec[k])}</div>
      <div class="v">${esc(Array.isArray(dec[k].value) ? dec[k].value.join(", ") : dec[k].value)}</div>
      <div class="why">${esc(dec[k].reason)}</div></div>` : "";
    return `<div class="cmp-card">
      <h3>${i + 1}. ${esc(s.company_name || s.glid)}</h3>
      <div class="muted small">${esc(s.business_kind)} · ${esc(s.city || "")}, ${esc(s.state || "")} · ${esc(s.turnover || "n/a")}</div>
      <div class="persona-label">${esc(p.label)}</div>
      <div class="muted small">${esc(p.voice.speaker)} · ${p.voice.pace}x · ${esc(p.language.code)} · ${esc(p.language.formality)}</div>
      <div class="opening">“${esc(p.plan.opening)}”</div>
      <button class="play" data-i="${i}">▶ Play opening</button>
      ${["language.style", "voice.pace", "language.formality", "plan.opening", "tone.empathy"].map(row).join("")}
    </div>`;
  }).join("");
  $("compare").querySelectorAll(".play").forEach((b) => b.onclick = () => playOpening(S.trio[+b.dataset.i]));
}

async function playOpening(s) {
  const p = s.persona;
  stopAudio();
  const r = await post("/tts", { text: p.plan.opening, language_code: p.language.code, speaker: p.voice.speaker,
                                pace: p.voice.pace, temperature: p.voice.temperature });
  await speak({ audio_b64: r.audio_b64, text: p.plan.opening, language_code: p.language.code, pace: p.voice.pace });
}
$("play-all").onclick = async () => { for (const s of S.trio) await playOpening(s); };

// ---------------------------------------------------------------- evidence
async function loadEvidence() {
  const kind = $("ev-kind").value;
  const r = await api(`/evidence?min_strength=${$("ev-strength").value}${kind ? "&kind=" + kind : ""}`);
  $("caveats").innerHTML = r.caveats.map((c) => `<li>${esc(c)}</li>`).join("");
  const pct = (x) => (x * 100).toFixed(1) + "%";
  $("ev-body").innerHTML = r.findings.map((f) => `<tr data-id="${esc(f.id)}">
      <td><span class="badge ${esc(f.strength)}">${esc(f.strength)}</span>${f.causal ? ' <span class="badge seller_data">A/B</span>' : ""}</td>
      <td>${esc(f.statement)}</td><td class="num">${pct(f.rate)}</td><td class="num">${pct(f.base_rate)}</td>
      <td class="num">${f.n.toLocaleString()}</td><td class="small">${esc(f.implication)}</td></tr>`).join("")
    || `<tr><td colspan="6" class="empty">No findings at this strength.</td></tr>`;
  $("ev-body").querySelectorAll("tr[data-id]").forEach((tr) => tr.onclick = () => showFinding(tr.dataset.id));
}
$("ev-strength").onchange = loadEvidence;
$("ev-kind").onchange = loadEvidence;

init().catch((e) => status("⚠ " + e.message));
