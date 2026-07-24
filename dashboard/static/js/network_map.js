/**
 * Network Map — D3.js force-directed topology visualization
 *
 * Shows lab nodes and animates attack flows between them.
 */

let svgMap, simulation, mapNodes, mapLinks;
const nodeStates = {};   // id → state
const nodeElements2 = {}; // id → D3 selection

const NODE_ICONS = {
  attacker: "⚔",
  victim1:  "🖥",
  victim2:  "🖥",
  gist:     "☁",
  k8s:      "⎈",
  cloud:    "☁",
};

const NODE_STATE_COLORS = {
  active:      "#e74c3c",
  clean:       "#2ecc71",
  compromised: "#e74c3c",
  external:    "#3498db",
  unknown:     "#555",
};

let topologyNodes = [];
let topologyLinks = [];

function initNetworkMap(nodes) {
  topologyNodes = nodes.map((n, i) => ({
    ...n,
    index: i,
    x: 100 + (i % 3) * 200,
    y: 80 + Math.floor(i / 3) * 160,
  }));

  // Default links (lab topology)
  topologyLinks = [
    { source: "attacker", target: "victim1",  type: "c2" },
    { source: "victim1",  target: "gist",     type: "c2" },
    { source: "victim1",  target: "k8s",      type: "internal" },
    { source: "victim1",  target: "victim2",  type: "ssh" },
    { source: "victim1",  target: "cloud",    type: "api" },
  ];

  renderMap();
}

function renderMap() {
  const container = document.getElementById("network-map-container");
  const W = container.clientWidth || 600;
  const H = 340;

  d3.select("#network-map").selectAll("*").remove();

  svgMap = d3.select("#network-map")
    .attr("width", W).attr("height", H)
    .attr("viewBox", `0 0 ${W} ${H}`);

  // Arrow markers for different link types
  const defs = svgMap.append("defs");
  ["c2", "ssh", "api", "internal", "attack"].forEach(t => {
    defs.append("marker")
      .attr("id", "arrow-" + t)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 30).attr("refY", 0)
      .attr("markerWidth", 5).attr("markerHeight", 5)
      .attr("orient", "auto")
      .append("path").attr("d", "M0,-5L10,0L0,5")
      .attr("fill", t === "attack" ? "#e74c3c" : "#555");
  });

  // Force simulation
  simulation = d3.forceSimulation(topologyNodes)
    .force("link", d3.forceLink(topologyLinks).id(d => d.id).distance(160))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(W / 2, H / 2))
    .force("collision", d3.forceCollide(50));

  // Links
  const link = svgMap.append("g").selectAll("line")
    .data(topologyLinks)
    .enter().append("line")
    .attr("stroke", d => d.type === "attack" ? "#e74c3c" : "#333")
    .attr("stroke-width", 1.5)
    .attr("stroke-dasharray", d => d.type === "internal" ? "4,3" : "none")
    .attr("marker-end", d => `url(#arrow-${d.type})`);

  // Node groups
  const nodeG = svgMap.append("g").selectAll(".mapnode")
    .data(topologyNodes)
    .enter().append("g")
    .attr("class", "mapnode")
    .attr("id", d => "mapnode-" + d.id);

  nodeG.append("circle")
    .attr("r", 28)
    .attr("fill", d => NODE_STATE_COLORS[d.state] || NODE_STATE_COLORS.unknown)
    .attr("fill-opacity", 0.15)
    .attr("stroke", d => NODE_STATE_COLORS[d.state] || NODE_STATE_COLORS.unknown)
    .attr("stroke-width", 2);

  nodeG.append("text")
    .attr("text-anchor", "middle").attr("y", 5)
    .attr("font-size", "18px")
    .text(d => NODE_ICONS[d.id] || "🖥");

  nodeG.append("text")
    .attr("text-anchor", "middle").attr("y", 44)
    .attr("fill", "#aaa").attr("font-size", "10px").attr("font-weight", "bold")
    .text(d => d.label);

  nodeG.append("text")
    .attr("text-anchor", "middle").attr("y", 56)
    .attr("fill", "#666").attr("font-size", "9px")
    .text(d => d.ip);

  // State badge
  nodeG.append("text")
    .attr("class", "state-badge")
    .attr("text-anchor", "middle").attr("y", -32)
    .attr("fill", "#e74c3c").attr("font-size", "8px").attr("font-weight", "bold")
    .text("");

  simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
    nodeG.attr("transform", d => `translate(${d.x},${d.y})`);
  });
}

function animateNetworkFlow(sourceIp, targetId, technique, label, color) {
  // Find source node by IP
  const source = topologyNodes.find(n => n.ip === sourceIp);
  const target = topologyNodes.find(n => n.id === targetId || n.ip === targetId);

  if (!source || !target) return;

  // Draw animated flow arrow
  const path = svgMap.append("line")
    .attr("x1", source.x).attr("y1", source.y)
    .attr("x2", source.x).attr("y2", source.y)
    .attr("stroke", color || "#e74c3c")
    .attr("stroke-width", 3)
    .attr("opacity", 0.8)
    .attr("marker-end", "url(#arrow-attack)");

  path.transition().duration(1200)
    .attr("x2", target.x).attr("y2", target.y)
    .on("end", () => {
      // Mark target as compromised
      markNodeCompromised(target.ip || target.id);
      // Fade out arrow after 3s
      path.transition().delay(3000).duration(800).attr("opacity", 0).remove();
    });

  // Add technique label
  const midX = (source.x + target.x) / 2;
  const midY = (source.y + target.y) / 2 - 12;
  const lbl = svgMap.append("text")
    .attr("x", midX).attr("y", midY)
    .attr("text-anchor", "middle")
    .attr("fill", color || "#e74c3c")
    .attr("font-size", "9px")
    .attr("font-weight", "bold")
    .text(technique + (label ? ` — ${label}` : ""));

  lbl.transition().delay(4000).duration(500).attr("opacity", 0).remove();
}

function markNodeCompromised(ipOrId) {
  const node = topologyNodes.find(n => n.ip === ipOrId || n.id === ipOrId);
  if (!node) return;

  d3.select("#mapnode-" + node.id).select("circle")
    .transition().duration(400)
    .attr("stroke", "#e74c3c")
    .attr("fill-opacity", 0.3);

  d3.select("#mapnode-" + node.id).select(".state-badge")
    .text("COMPROMISED")
    .attr("fill", "#e74c3c");
}
