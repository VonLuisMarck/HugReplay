/**
 * Attack Graph — LangGraph node visualization (D3.js)
 * Dark ops palette: glow on active, bright green for done.
 */

const GRAPH_NODES = [
  { id: "recon_node",    label: "RECON",    x: 75,  y: 80, mitre: "T1082/T1552" },
  { id: "decision_node", label: "DECISION", x: 230, y: 80, mitre: "LLM" },
  { id: "exec_node",     label: "EXEC",     x: 375, y: 80, mitre: "T1059" },
  { id: "eval_node",     label: "EVAL",     x: 510, y: 80, mitre: "loop" },
];

const GRAPH_EDGES = [
  { source: "recon_node",    target: "decision_node" },
  { source: "decision_node", target: "exec_node" },
  { source: "exec_node",     target: "eval_node" },
  { source: "eval_node",     target: "decision_node", curved: true },
];

const NODE_COLORS = {
  pending: "#0c0c18",
  active:  "#ff9500",
  done:    "#00ff88",
  failed:  "#e74c3c",
};

const NODE_TEXT_COLORS = {
  pending: "#444460",
  active:  "#fff",
  done:    "#030308",
  failed:  "#fff",
};

let svgGraph, nodeElements;

function initAttackGraph() {
  const container = document.getElementById("attack-graph-container");
  const W = container.clientWidth || 600;
  const H = 160;

  svgGraph = d3.select("#attack-graph")
    .attr("width", W).attr("height", H)
    .attr("viewBox", "0 0 600 160");

  const defs = svgGraph.append("defs");

  // Arrow marker
  defs.append("marker")
    .attr("id", "graph-arrow")
    .attr("viewBox", "0 -4 8 8")
    .attr("refX", 7).attr("refY", 0)
    .attr("markerWidth", 5).attr("markerHeight", 5)
    .attr("orient", "auto")
    .append("path").attr("d", "M0,-4L8,0L0,4")
    .attr("fill", "#1e1e35");

  // Glow filter for active node
  const glow = defs.append("filter").attr("id", "graph-glow")
    .attr("x", "-50%").attr("y", "-50%").attr("width", "200%").attr("height", "200%");
  glow.append("feGaussianBlur").attr("stdDeviation", "4").attr("result", "blur");
  const fm = glow.append("feMerge");
  fm.append("feMergeNode").attr("in", "blur");
  fm.append("feMergeNode").attr("in", "SourceGraphic");

  // Edges
  GRAPH_EDGES.forEach(e => {
    const s = GRAPH_NODES.find(n => n.id === e.source);
    const t = GRAPH_NODES.find(n => n.id === e.target);
    if (e.curved) {
      svgGraph.append("path")
        .attr("d", `M${s.x},${s.y + 22} C${s.x},${s.y + 65} ${t.x},${t.y + 65} ${t.x},${t.y + 22}`)
        .attr("fill", "none")
        .attr("stroke", "#1e1e35").attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "5,3")
        .attr("marker-end", "url(#graph-arrow)");
    } else {
      svgGraph.append("line")
        .attr("x1", s.x + 38).attr("y1", s.y)
        .attr("x2", t.x - 38).attr("y2", t.y)
        .attr("stroke", "#1e1e35").attr("stroke-width", 1.5)
        .attr("marker-end", "url(#graph-arrow)");
    }
  });

  // Nodes
  const nodeG = svgGraph.selectAll(".node")
    .data(GRAPH_NODES).enter()
    .append("g").attr("class", "node")
    .attr("id", d => "gnode-" + d.id)
    .attr("transform", d => `translate(${d.x},${d.y})`);

  nodeG.append("rect")
    .attr("x", -38).attr("y", -22)
    .attr("width", 76).attr("height", 44)
    .attr("rx", 4)
    .attr("fill", NODE_COLORS.pending)
    .attr("stroke", "#1e1e35").attr("stroke-width", 1);

  nodeG.append("text")
    .attr("text-anchor", "middle").attr("y", -5)
    .attr("fill", "#444460").attr("font-size", "10px").attr("font-weight", "700")
    .attr("letter-spacing", "1px")
    .text(d => d.label);

  nodeG.append("text")
    .attr("text-anchor", "middle").attr("y", 11)
    .attr("fill", "#333350").attr("font-size", "8px")
    .text(d => d.mitre);

  nodeElements = nodeG;
}

function updateAttackGraph(nodeId, state, detail) {
  const g = d3.select("#gnode-" + nodeId);
  if (g.empty()) return;

  const color = NODE_COLORS[state] || NODE_COLORS.pending;
  const textColor = NODE_TEXT_COLORS[state] || "#444460";
  const isActive = state === "active";
  const isDone = state === "done";

  g.select("rect")
    .transition().duration(250)
    .attr("fill", color)
    .attr("stroke", isActive ? "#ff9500" : isDone ? "#00ff88" : "#1e1e35")
    .attr("stroke-width", isActive ? 2 : 1)
    .style("filter", isActive ? "url(#graph-glow)" : isDone ? "drop-shadow(0 0 4px #00ff88)" : "none");

  g.select("text:first-of-type")
    .transition().duration(250)
    .attr("fill", textColor);

  if (isActive) pulseNode(g);
}

function pulseNode(g) {
  function doPulse() {
    const rect = g.select("rect");
    if (rect.attr("fill") !== NODE_COLORS.active) return;
    rect.transition().duration(500).attr("stroke-width", 3)
      .transition().duration(500).attr("stroke-width", 1.5)
      .on("end", doPulse);
  }
  doPulse();
}

document.addEventListener("DOMContentLoaded", initAttackGraph);
