/**
 * Network Map — D3.js force-directed topology visualization
 *
 * Shows lab nodes and animates attack flows between them.
 * Icons use FontAwesome 6 Free unicode codepoints (requires FA loaded in page).
 */

let svgMap, simulation, mapNodes, mapLinks;
const nodeStates = {};   // id → state
const nodeElements2 = {}; // id → D3 selection

// FontAwesome 6 Free (solid / brands) unicode codepoints
const NODE_ICONS = {
  attacker: "\uf54c",  // fa-skull-crossbones  (solid)
  victim1:  "\uf233",  // fa-server            (solid)
  victim2:  "\uf233",  // fa-server            (solid)
  gist:     "\uf09b",  // fa-github            (brands)
  aws:      "\uf0c2",  // fa-cloud             (solid)
  cloud:    "\uf0c2",  // fa-cloud             (solid)
  k8s:      "\uf3e2",  // fa-dharmachakra (wheel) — closest to k8s (solid)
};

// FontAwesome font-family per node (brands vs solid)
const NODE_ICON_FAMILY = {
  gist: "'Font Awesome 6 Brands'",
};

const NODE_STATE_COLORS = {
  active:      "#e74c3c",
  clean:       "#2ecc71",
  compromised: "#e74c3c",
  external:    "#4aa3df",
  unknown:     "#555570",
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
  const H = 300;

  d3.select("#network-map").selectAll("*").remove();

  svgMap = d3.select("#network-map")
    .attr("width", W).attr("height", H)
    .attr("viewBox", `0 0 ${W} ${H}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const defs = svgMap.append("defs");

  // Drop shadow filter for nodes
  const filter = defs.append("filter")
    .attr("id", "node-shadow")
    .attr("x", "-30%").attr("y", "-30%")
    .attr("width", "160%").attr("height", "160%");
  filter.append("feDropShadow")
    .attr("dx", 0).attr("dy", 0)
    .attr("stdDeviation", 4)
    .attr("flood-color", "#000")
    .attr("flood-opacity", 0.5);

  // Arrow markers for different link types
  const LINK_COLORS = { c2: "#e74c3c", ssh: "#f5a623", api: "#4aa3df", internal: "#555570", attack: "#e74c3c" };
  ["c2", "ssh", "api", "internal", "attack"].forEach(t => {
    defs.append("marker")
      .attr("id", "arrow-" + t)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 34).attr("refY", 0)
      .attr("markerWidth", 5).attr("markerHeight", 5)
      .attr("orient", "auto")
      .append("path").attr("d", "M0,-5L10,0L0,5")
      .attr("fill", LINK_COLORS[t] || "#555570");
  });

  // Force simulation
  simulation = d3.forceSimulation(topologyNodes)
    .force("link", d3.forceLink(topologyLinks).id(d => d.id).distance(160))
    .force("charge", d3.forceManyBody().strength(-320))
    .force("center", d3.forceCenter(W / 2, H / 2))
    .force("collision", d3.forceCollide(52));

  // Links
  const link = svgMap.append("g").selectAll("line")
    .data(topologyLinks)
    .enter().append("line")
    .attr("stroke", d => LINK_COLORS[d.type] || "#333")
    .attr("stroke-width", d => d.type === "c2" ? 2 : 1.5)
    .attr("stroke-opacity", 0.6)
    .attr("stroke-dasharray", d => d.type === "internal" ? "4,3" : "none")
    .attr("marker-end", d => `url(#arrow-${d.type})`);

  // Node groups
  const nodeG = svgMap.append("g").selectAll(".mapnode")
    .data(topologyNodes)
    .enter().append("g")
    .attr("class", "mapnode")
    .attr("id", d => "mapnode-" + d.id);

  // Outer glow ring
  nodeG.append("circle")
    .attr("r", 36)
    .attr("fill", "none")
    .attr("stroke", d => NODE_STATE_COLORS[d.state] || NODE_STATE_COLORS.unknown)
    .attr("stroke-width", 0.5)
    .attr("stroke-opacity", 0.25);

  // Main node circle
  nodeG.append("circle")
    .attr("r", 28)
    .attr("fill", d => NODE_STATE_COLORS[d.state] || NODE_STATE_COLORS.unknown)
    .attr("fill-opacity", 0.12)
    .attr("stroke", d => NODE_STATE_COLORS[d.state] || NODE_STATE_COLORS.unknown)
    .attr("stroke-width", 1.5)
    .attr("filter", "url(#node-shadow)");

  // FontAwesome icon
  nodeG.append("text")
    .attr("text-anchor", "middle")
    .attr("dominant-baseline", "central")
    .attr("y", 1)
    .attr("font-family", d => NODE_ICON_FAMILY[d.id] || "'Font Awesome 6 Free'")
    .attr("font-weight", "900")
    .attr("font-size", "18px")
    .attr("fill", d => NODE_STATE_COLORS[d.state] || NODE_STATE_COLORS.unknown)
    .text(d => NODE_ICONS[d.id] || "\uf233");

  // Node label
  nodeG.append("text")
    .attr("text-anchor", "middle").attr("y", 44)
    .attr("fill", "#a0a0c0").attr("font-size", "10px").attr("font-weight", "bold")
    .attr("letter-spacing", "0.5px")
    .text(d => d.label);

  // IP address
  nodeG.append("text")
    .attr("text-anchor", "middle").attr("y", 57)
    .attr("fill", "#555570").attr("font-size", "9px")
    .text(d => d.ip);

  // State badge
  nodeG.append("text")
    .attr("class", "state-badge")
    .attr("text-anchor", "middle").attr("y", -36)
    .attr("fill", "#e74c3c").attr("font-size", "8px").attr("font-weight", "bold")
    .attr("letter-spacing", "1px")
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

  const flowColor = color || "#e74c3c";

  // Draw animated flow arrow
  const path = svgMap.append("line")
    .attr("x1", source.x).attr("y1", source.y)
    .attr("x2", source.x).attr("y2", source.y)
    .attr("stroke", flowColor)
    .attr("stroke-width", 3)
    .attr("opacity", 0.85)
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
  const midY = (source.y + target.y) / 2 - 14;
  const lbl = svgMap.append("text")
    .attr("x", midX).attr("y", midY)
    .attr("text-anchor", "middle")
    .attr("fill", flowColor)
    .attr("font-size", "9px")
    .attr("font-weight", "bold")
    .attr("letter-spacing", "0.5px")
    .text(technique + (label ? ` — ${label}` : ""));

  lbl.transition().delay(4000).duration(500).attr("opacity", 0).remove();
}

function markNodeCompromised(ipOrId) {
  const node = topologyNodes.find(n => n.ip === ipOrId || n.id === ipOrId);
  if (!node) return;

  const g = d3.select("#mapnode-" + node.id);

  g.selectAll("circle")
    .transition().duration(400)
    .attr("stroke", "#e74c3c");

  g.select("circle:nth-child(2)")
    .transition().duration(400)
    .attr("fill-opacity", 0.25);

  g.select("text.state-badge")
    .text("COMPROMISED")
    .attr("fill", "#e74c3c");

  g.select("text:nth-child(4)")  // icon text
    .transition().duration(400)
    .attr("fill", "#e74c3c");
}
