/**
 * Attack Graph — LangGraph node visualization (D3.js)
 *
 * Renders the 4-node attack loop: RECON → DECISION → EXEC → EVAL
 * Animates node state changes via SSE events.
 */

const GRAPH_NODES = [
  { id: "recon_node",    label: "RECON",    x: 80,  y: 80,  mitre: "T1082/T1552" },
  { id: "decision_node", label: "DECISION", x: 240, y: 80,  mitre: "LLM" },
  { id: "exec_node",     label: "EXEC",     x: 380, y: 80,  mitre: "T1059" },
  { id: "eval_node",     label: "EVAL",     x: 510, y: 80,  mitre: "loop" },
];

const GRAPH_EDGES = [
  { source: "recon_node",    target: "decision_node" },
  { source: "decision_node", target: "exec_node" },
  { source: "exec_node",     target: "eval_node" },
  { source: "eval_node",     target: "decision_node", curved: true },  // loop back
];

const NODE_COLORS = {
  pending: "#2a2a3a",
  active:  "#f5a623",
  done:    "#27ae60",
  failed:  "#e74c3c",
};

let svgGraph, nodeElements;

function initAttackGraph() {
  const container = document.getElementById("attack-graph-container");
  const W = container.clientWidth || 600;
  const H = 160;

  svgGraph = d3.select("#attack-graph")
    .attr("width", W)
    .attr("height", H)
    .attr("viewBox", `0 0 600 160`);

  // Arrow marker
  svgGraph.append("defs").append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 32)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#666");

  // Draw edges
  GRAPH_EDGES.forEach(e => {
    const s = GRAPH_NODES.find(n => n.id === e.source);
    const t = GRAPH_NODES.find(n => n.id === e.target);
    if (e.curved) {
      svgGraph.append("path")
        .attr("d", `M${s.x},${s.y + 28} C${s.x},${s.y + 70} ${t.x},${t.y + 70} ${t.x},${t.y + 28}`)
        .attr("fill", "none")
        .attr("stroke", "#444")
        .attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "4,3")
        .attr("marker-end", "url(#arrow)");
    } else {
      svgGraph.append("line")
        .attr("x1", s.x + 40).attr("y1", s.y)
        .attr("x2", t.x - 40).attr("y2", t.y)
        .attr("stroke", "#444").attr("stroke-width", 1.5)
        .attr("marker-end", "url(#arrow)");
    }
  });

  // Draw nodes
  const nodeG = svgGraph.selectAll(".node")
    .data(GRAPH_NODES)
    .enter()
    .append("g")
    .attr("class", "node")
    .attr("id", d => "gnode-" + d.id)
    .attr("transform", d => `translate(${d.x}, ${d.y})`);

  nodeG.append("rect")
    .attr("x", -38).attr("y", -22)
    .attr("width", 76).attr("height", 44)
    .attr("rx", 6)
    .attr("fill", NODE_COLORS.pending)
    .attr("stroke", "#555").attr("stroke-width", 1.5);

  nodeG.append("text")
    .attr("text-anchor", "middle").attr("y", -4)
    .attr("fill", "#ccc").attr("font-size", "11px").attr("font-weight", "bold")
    .text(d => d.label);

  nodeG.append("text")
    .attr("text-anchor", "middle").attr("y", 12)
    .attr("fill", "#666").attr("font-size", "9px")
    .text(d => d.mitre);

  nodeElements = nodeG;
}

function updateAttackGraph(nodeId, state, detail) {
  const g = d3.select("#gnode-" + nodeId);
  if (g.empty()) return;

  const color = NODE_COLORS[state] || NODE_COLORS.pending;

  g.select("rect")
    .transition().duration(300)
    .attr("fill", color)
    .attr("stroke", state === "active" ? "#f5a623" : "#555")
    .attr("stroke-width", state === "active" ? 2.5 : 1.5);

  // Pulsing animation for active state
  if (state === "active") {
    pulseNode(g);
  }
}

function pulseNode(g) {
  function doPulse() {
    g.select("rect")
      .transition().duration(600)
      .attr("stroke-width", 3.5)
      .transition().duration(600)
      .attr("stroke-width", 2)
      .on("end", () => {
        // Only continue if still active
        if (g.select("rect").attr("fill") === NODE_COLORS.active) doPulse();
      });
  }
  doPulse();
}

// Initialize on load
document.addEventListener("DOMContentLoaded", initAttackGraph);
