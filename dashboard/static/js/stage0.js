/**
 * Stage 0 — OpenAI Sandbox Escape Visual
 *
 * Full-screen overlay that plays the GPT-5.6 Sol origin narrative.
 * Driven by triggerStage0(phase, label) calls from index.html SSE handler.
 *
 * Visual flow:
 *   init → show overlay + GPT-Sandbox box with OpenAI logo
 *   guardrails → amber warning log line
 *   recon → log line
 *   exploit → SHAKE + alarm badge, red flash on box
 *   breach → box border turns red, BREACHED badge
 *   lateral → OpenAI Infra node appears with animated arrow
 *   internet → Internet node appears with animated arrow
 *   reasoning → log line
 *   target → HuggingFace node appears (orange), animated arrow
 *   handoff → INITIATING banner pulses, overlay fades out
 */

// OpenAI logo path — the classic 4-lobe "flower" mark, centered at (0,0), ~24px radius
// Traced from the public OpenAI SVG brand asset
// NOTE: We use the simplified radial-line version below for reliability across browsers.
// OPENAI_PATH is kept for reference but not used directly.

// Simpler fallback: not used, logo is drawn with D3 primitives in _s0DrawGptNode

// Positions for the 4 topology nodes in the 700x280 SVG
const S0_NODES = {
  gpt:     { x: 350, y: 70,  label: "GPT-5.6 Sol",    sub: "OpenAI ExploitGym Sandbox" },
  infra:   { x: 350, y: 160, label: "OpenAI Infra",   sub: "internal network" },
  internet:{ x: 170, y: 220, label: "Internet",        sub: "egress established" },
  hf:      { x: 530, y: 220, label: "HuggingFace",    sub: "huggingface.co" },
};

let s0svg = null;
let s0rendered = {};

function triggerStage0(phase, label) {
  switch (phase) {
    case "init":        _s0Init();           break;
    case "guardrails":  _s0Log(label, "warn"); break;
    case "recon":       _s0Log(label, "info"); break;
    case "exploit":     _s0Exploit(label);   break;
    case "breach":      _s0Breach(label);    break;
    case "lateral":     _s0Lateral(label);   break;
    case "internet":    _s0Internet(label);  break;
    case "reasoning":   _s0Log(label, "info"); break;
    case "target":      _s0Target(label);    break;
    case "handoff":     _s0Handoff();        break;
  }
}

// ─── Init: show overlay, render GPT-Sandbox node ──────────────────────────

function _s0Init() {
  const overlay = document.getElementById("stage0-overlay");
  overlay.style.display = "flex";
  overlay.style.opacity = "1";

  const wrap = document.getElementById("stage0-svg-wrap");
  const W = wrap.clientWidth || 700;
  const H = 280;

  s0svg = d3.select("#stage0-svg")
    .attr("width", W).attr("height", H)
    .attr("viewBox", `0 0 700 280`);

  // Arrow marker
  const defs = s0svg.append("defs");
  defs.append("marker")
    .attr("id", "s0-arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 8).attr("refY", 0)
    .attr("markerWidth", 5).attr("markerHeight", 5)
    .attr("orient", "auto")
    .append("path").attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#e74c3c");

  defs.append("marker")
    .attr("id", "s0-arrow-orange")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 8).attr("refY", 0)
    .attr("markerWidth", 5).attr("markerHeight", 5)
    .attr("orient", "auto")
    .append("path").attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#f5a623");

  _s0DrawGptNode();
}

// ─── Draw GPT-Sandbox node (large containment box + OpenAI logo) ───────────

function _s0DrawGptNode() {
  const n = S0_NODES.gpt;
  const g = s0svg.append("g")
    .attr("id", "s0-node-gpt")
    .attr("transform", `translate(${n.x}, ${n.y})`);

  // Outer containment box (larger rect)
  g.append("rect")
    .attr("id", "s0-gpt-box")
    .attr("x", -70).attr("y", -44)
    .attr("width", 140).attr("height", 88)
    .attr("rx", 8)
    .attr("fill", "rgba(10,10,20,0.9)")
    .attr("stroke", "#2a2a45")
    .attr("stroke-width", 2)
    .style("filter", "drop-shadow(0 0 8px rgba(42,42,69,0.8))");

  // "CONTAINED" label top-left of box
  g.append("text")
    .attr("x", -64).attr("y", -28)
    .attr("fill", "#2a2a45")
    .attr("font-size", "7px")
    .attr("font-weight", "bold")
    .attr("letter-spacing", "2px")
    .text("CONTAINED");

  // OpenAI logo (two concentric circles as simplified mark)
  // Outer ring
  g.append("circle")
    .attr("cx", 0).attr("cy", -2)
    .attr("r", 20)
    .attr("fill", "none")
    .attr("stroke", "#aaa")
    .attr("stroke-width", 1.5);
  // Inner petal hints (6 rotated lines to suggest the flower)
  [0, 60, 120, 180, 240, 300].forEach(deg => {
    const rad = (deg * Math.PI) / 180;
    g.append("line")
      .attr("x1", Math.cos(rad) * 7).attr("y1", -2 + Math.sin(rad) * 7)
      .attr("x2", Math.cos(rad) * 18).attr("y2", -2 + Math.sin(rad) * 18)
      .attr("stroke", "#aaa")
      .attr("stroke-width", 1.5)
      .attr("stroke-linecap", "round");
  });
  // Center dot
  g.append("circle")
    .attr("cx", 0).attr("cy", -2)
    .attr("r", 3)
    .attr("fill", "#aaa");

  // Node label
  g.append("text")
    .attr("text-anchor", "middle").attr("y", 34)
    .attr("fill", "#c0c0d0").attr("font-size", "11px").attr("font-weight", "bold")
    .attr("letter-spacing", "1px")
    .text(n.label);

  g.append("text")
    .attr("text-anchor", "middle").attr("y", 47)
    .attr("fill", "#555570").attr("font-size", "9px")
    .text(n.sub);

  // State badge (initially empty)
  g.append("text")
    .attr("id", "s0-gpt-badge")
    .attr("text-anchor", "middle").attr("y", -50)
    .attr("fill", "#2ecc71").attr("font-size", "8px").attr("font-weight", "bold")
    .attr("letter-spacing", "1px")
    .text("● RUNNING");

  s0rendered.gpt = true;
}

// ─── Exploit: shake + alarm badge ─────────────────────────────────────────

function _s0Exploit(label) {
  _s0Log(label, "crit");
  document.getElementById("stage0-alarm-badge").classList.remove("hidden");

  // Shake the GPT node using D3 transitions (CSS animations on SVG <g> are unreliable)
  const n = S0_NODES.gpt;
  const base = `translate(${n.x}, ${n.y})`;
  const g = d3.select("#s0-node-gpt");
  g.transition().duration(60).attr("transform", `translate(${n.x - 7}, ${n.y})`)
   .transition().duration(60).attr("transform", `translate(${n.x + 7}, ${n.y})`)
   .transition().duration(60).attr("transform", `translate(${n.x - 5}, ${n.y})`)
   .transition().duration(60).attr("transform", `translate(${n.x + 5}, ${n.y})`)
   .transition().duration(60).attr("transform", `translate(${n.x - 3}, ${n.y})`)
   .transition().duration(60).attr("transform", base);

  // Flash the box border amber
  d3.select("#s0-gpt-box")
    .transition().duration(100).attr("stroke", "#f5a623").attr("stroke-width", 3)
    .transition().duration(100).attr("stroke", "#2a2a45")
    .transition().duration(100).attr("stroke", "#f5a623")
    .transition().duration(100).attr("stroke", "#2a2a45")
    .transition().duration(100).attr("stroke", "#f5a623").attr("stroke-width", 2.5);
}

// ─── Breach: box turns red, BREACHED badge ─────────────────────────────────

function _s0Breach(label) {
  _s0Log(label, "crit");

  d3.select("#s0-gpt-box")
    .transition().duration(400)
    .attr("stroke", "#e74c3c")
    .attr("stroke-width", 2.5)
    .style("filter", "drop-shadow(0 0 16px rgba(231,76,60,0.6))");

  d3.select("#s0-gpt-badge")
    .transition().duration(300)
    .attr("fill", "#e74c3c")
    .text("⚠ BREACHED");

  // Logo lines turn red
  s0svg.select("#s0-node-gpt").selectAll("line, circle")
    .transition().duration(400)
    .attr("stroke", "#e74c3c");
  s0svg.select("#s0-node-gpt").selectAll("circle[r='3']")
    .transition().duration(400)
    .attr("fill", "#e74c3c");
}

// ─── Lateral: OpenAI Infra node appears ───────────────────────────────────

function _s0Lateral(label) {
  _s0Log(label, "warn");
  const src = S0_NODES.gpt;
  const tgt = S0_NODES.infra;

  // Animated arrow from gpt down to infra
  _s0AnimateArrow(src.x, src.y + 44, tgt.x, tgt.y - 28, "#e74c3c", "s0-arrow", "T1021");

  // Draw infra node after arrow
  setTimeout(() => _s0DrawSimpleNode("infra", "#e74c3c"), 1000);
}

// ─── Internet: Internet node appears ──────────────────────────────────────

function _s0Internet(label) {
  _s0Log(label, "ok");
  const src = S0_NODES.infra;
  const tgt = S0_NODES.internet;

  _s0AnimateArrow(src.x, src.y + 20, tgt.x + 30, tgt.y - 18, "#e74c3c", "s0-arrow", "T1041");
  setTimeout(() => _s0DrawSimpleNode("internet", "#4aa3df"), 1000);
}

// ─── Target: HuggingFace node appears ─────────────────────────────────────

function _s0Target(label) {
  _s0Log(label, "warn");
  const src = S0_NODES.internet;
  const tgt = S0_NODES.hf;

  _s0AnimateArrow(src.x + 50, src.y - 8, tgt.x - 50, tgt.y - 8, "#f5a623", "s0-arrow-orange", "HuggingFace");
  setTimeout(() => _s0DrawSimpleNode("hf", "#f5a623"), 1000);
}

// ─── Handoff: show banner, fade out overlay ───────────────────────────────

function _s0Handoff() {
  _s0Log("Attack chain initialized — handing off to Phantom Pipeline", "ok");

  document.getElementById("stage0-handoff").classList.remove("hidden");

  setTimeout(() => {
    const overlay = document.getElementById("stage0-overlay");
    overlay.style.transition = "opacity 1s ease";
    overlay.style.opacity = "0";
    setTimeout(() => { overlay.style.display = "none"; }, 1050);
  }, 2200);
}

// ─── Helpers ──────────────────────────────────────────────────────────────

function _s0DrawSimpleNode(id, color) {
  if (s0rendered[id]) return;
  s0rendered[id] = true;

  const n = S0_NODES[id];
  const g = s0svg.append("g")
    .attr("id", `s0-node-${id}`)
    .attr("transform", `translate(${n.x}, ${n.y})`)
    .attr("opacity", 0);

  g.append("rect")
    .attr("x", -54).attr("y", -20)
    .attr("width", 108).attr("height", 40)
    .attr("rx", 5)
    .attr("fill", "rgba(10,10,20,0.9)")
    .attr("stroke", color)
    .attr("stroke-width", 1.5)
    .style("filter", `drop-shadow(0 0 6px ${color}55)`);

  g.append("text")
    .attr("text-anchor", "middle").attr("y", 1)
    .attr("fill", color).attr("font-size", "11px").attr("font-weight", "bold")
    .attr("letter-spacing", "1px")
    .text(n.label);

  g.append("text")
    .attr("text-anchor", "middle").attr("y", 14)
    .attr("fill", "#555570").attr("font-size", "9px")
    .text(n.sub);

  g.transition().duration(400).attr("opacity", 1);
}

function _s0AnimateArrow(x1, y1, x2, y2, color, markerId, techLabel) {
  const line = s0svg.append("line")
    .attr("x1", x1).attr("y1", y1)
    .attr("x2", x1).attr("y2", y1)
    .attr("stroke", color)
    .attr("stroke-width", 2)
    .attr("opacity", 0.85)
    .attr("marker-end", `url(#${markerId})`);

  line.transition().duration(900)
    .attr("x2", x2).attr("y2", y2);

  if (techLabel) {
    const lx = (x1 + x2) / 2;
    const ly = (y1 + y2) / 2 - 10;
    s0svg.append("text")
      .attr("x", lx).attr("y", ly)
      .attr("text-anchor", "middle")
      .attr("fill", color)
      .attr("font-size", "8px")
      .attr("font-weight", "bold")
      .attr("letter-spacing", "0.5px")
      .attr("opacity", 0)
      .text(techLabel)
      .transition().delay(200).duration(300).attr("opacity", 1);
  }
}

function _s0Log(text, level) {
  const log = document.getElementById("stage0-log");
  if (!log) return;
  const line = document.createElement("div");
  line.className = `s0-line s0-${level || "info"}`;

  const prefix = level === "ok" ? "[✓] " : level === "crit" ? "[!] " : level === "warn" ? "[~] " : "[>] ";
  line.textContent = prefix + text;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}
