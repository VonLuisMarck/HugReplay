/**
 * Network Map — fixed-position topology visualization
 * Dark ops aesthetic: glow nodes, animated dashed links, FA icons.
 */

let svgMap, mapNodes, mapLinks;
const nodeStates = {};

// FontAwesome 6 codepoints
const NODE_ICONS = {
  attacker: "\uf54c",   // skull-crossbones (solid)
  victim1:  "\uf233",   // server (solid)
  victim2:  "\uf233",   // server (solid)
  gist:     "\uf09b",   // github (brands)
  aws:      "\uf0c2",   // cloud (solid)
  cloud:    "\uf0c2",   // cloud (solid)
};
const NODE_ICON_FAMILY = { gist: "'Font Awesome 6 Brands'" };

const NODE_STATE_COLORS = {
  active:      "#e74c3c",
  clean:       "#00ff88",
  compromised: "#e74c3c",
  external:    "#00b4ff",
  unknown:     "#444460",
};

// Fixed hub-and-spoke positions (viewBox 620x290)
const FIXED_POSITIONS = {
  attacker: { x: 310, y:  52 },
  victim1:  { x: 310, y: 148 },
  gist:     { x: 520, y:  95 },
  victim2:  { x: 115, y: 240 },
  cloud:    { x: 490, y: 240 },
  aws:      { x: 310, y: 248 },
};

const LINK_COLORS = {
  c2:       "#e74c3c",
  ssh:      "#ff9500",
  api:      "#00b4ff",
  internal: "#444460",
  attack:   "#e74c3c",
};

let topologyNodes = [];
let topologyLinks = [];

function initNetworkMap(nodes) {
  topologyNodes = nodes.map(n => ({
    ...n,
    x: (FIXED_POSITIONS[n.id] || { x: 310, y: 148 }).x,
    y: (FIXED_POSITIONS[n.id] || { x: 310, y: 148 }).y,
  }));

  topologyLinks = [
    { source: "attacker", target: "victim1",  type: "c2" },
    { source: "victim1",  target: "gist",     type: "c2" },
    { source: "victim1",  target: "aws",      type: "internal" },
    { source: "victim1",  target: "victim2",  type: "ssh" },
    { source: "victim1",  target: "cloud",    type: "api" },
  ];

  renderMap();
}

function renderMap() {
  const container = document.getElementById("network-map-container");
  const W = container.clientWidth || 620;
  const H = 300;
  const VW = 620, VH = 290;

  d3.select("#network-map").selectAll("*").remove();

  svgMap = d3.select("#network-map")
    .attr("width", W).attr("height", H)
    .attr("viewBox", `0 0 ${VW} ${VH}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const defs = svgMap.append("defs");

  // Glow filter for nodes
  const glow = defs.append("filter").attr("id", "node-glow")
    .attr("x", "-40%").attr("y", "-40%").attr("width", "180%").attr("height", "180%");
  glow.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "blur");
  const feMerge = glow.append("feMerge");
  feMerge.append("feMergeNode").attr("in", "blur");
  feMerge.append("feMergeNode").attr("in", "SourceGraphic");

  // Red glow for compromised
  const redGlow = defs.append("filter").attr("id", "node-glow-red")
    .attr("x", "-50%").attr("y", "-50%").attr("width", "200%").attr("height", "200%");
  redGlow.append("feGaussianBlur").attr("stdDeviation", "5").attr("result", "blur");
  const feMerge2 = redGlow.append("feMerge");
  feMerge2.append("feMergeNode").attr("in", "blur");
  feMerge2.append("feMergeNode").attr("in", "SourceGraphic");

  // Arrow markers
  Object.entries(LINK_COLORS).forEach(([t, col]) => {
    defs.append("marker")
      .attr("id", "arrow-" + t)
      .attr("viewBox", "0 -4 8 8")
      .attr("refX", 7).attr("refY", 0)
      .attr("markerWidth", 4).attr("markerHeight", 4)
      .attr("orient", "auto")
      .append("path").attr("d", "M0,-4L8,0L0,4")
      .attr("fill", col);
  });

  // Subtle grid background
  const gridG = svgMap.append("g").attr("class", "grid-bg");
  for (let x = 0; x <= VW; x += 40) {
    gridG.append("line")
      .attr("x1", x).attr("y1", 0).attr("x2", x).attr("y2", VH)
      .attr("stroke", "#0f0f20").attr("stroke-width", 0.5);
  }
  for (let y = 0; y <= VH; y += 40) {
    gridG.append("line")
      .attr("x1", 0).attr("y1", y).attr("x2", VW).attr("y2", y)
      .attr("stroke", "#0f0f20").attr("stroke-width", 0.5);
  }

  // Resolve source/target to node objects
  const nodeById = {};
  topologyNodes.forEach(n => nodeById[n.id] = n);

  // Links
  topologyLinks.forEach(link => {
    const s = nodeById[link.source];
    const t = nodeById[link.target];
    if (!s || !t) return;

    const col = LINK_COLORS[link.type] || "#333";
    const dashArr = link.type === "internal" ? "6,4" : link.type === "ssh" ? "4,3" : "none";

    const line = svgMap.append("line")
      .attr("class", "map-link map-link-animated")
      .attr("x1", s.x).attr("y1", s.y)
      .attr("x2", t.x).attr("y2", t.y)
      .attr("stroke", col)
      .attr("stroke-width", link.type === "c2" ? 1.5 : 1)
      .attr("stroke-opacity", 0.5)
      .attr("stroke-dasharray", dashArr !== "none" ? dashArr : "none")
      .attr("marker-end", `url(#arrow-${link.type})`);

    if (dashArr !== "none") line.classed("map-link-animated", true);

    // Link type label
    const mx = (s.x + t.x) / 2, my = (s.y + t.y) / 2 - 8;
    svgMap.append("text")
      .attr("x", mx).attr("y", my)
      .attr("text-anchor", "middle")
      .attr("fill", col)
      .attr("font-size", "7px")
      .attr("opacity", 0.6)
      .attr("letter-spacing", "1px")
      .text(link.type.toUpperCase());
  });

  // Nodes
  const nodeG = svgMap.append("g").selectAll(".mapnode")
    .data(topologyNodes)
    .enter().append("g")
    .attr("class", "mapnode")
    .attr("id", d => "mapnode-" + d.id)
    .attr("transform", d => `translate(${d.x},${d.y})`);

  // Node background rect
  nodeG.append("rect")
    .attr("x", -42).attr("y", -26)
    .attr("width", 84).attr("height", 52)
    .attr("rx", 4)
    .attr("fill", "#080812")
    .attr("stroke", d => NODE_STATE_COLORS[d.state] || NODE_STATE_COLORS.unknown)
    .attr("stroke-width", 1)
    .attr("filter", "url(#node-glow)");

  // FA icon
  nodeG.append("text")
    .attr("text-anchor", "middle")
    .attr("y", -6)
    .attr("font-family", d => NODE_ICON_FAMILY[d.id] || "'Font Awesome 6 Free'")
    .attr("font-weight", "900")
    .attr("font-size", "14px")
    .attr("fill", d => NODE_STATE_COLORS[d.state] || NODE_STATE_COLORS.unknown)
    .text(d => NODE_ICONS[d.id] || "\uf233");

  // Label
  nodeG.append("text")
    .attr("text-anchor", "middle").attr("y", 8)
    .attr("fill", "#c8c8e0").attr("font-size", "9px").attr("font-weight", "700")
    .attr("letter-spacing", "0.5px")
    .text(d => d.label);

  // IP
  nodeG.append("text")
    .attr("text-anchor", "middle").attr("y", 19)
    .attr("fill", "#444460").attr("font-size", "8px")
    .text(d => d.ip);

  // State badge
  nodeG.append("text")
    .attr("class", "state-badge")
    .attr("text-anchor", "middle").attr("y", -32)
    .attr("font-size", "7px").attr("font-weight", "700")
    .attr("letter-spacing", "1px")
    .attr("fill", "#444460")
    .text("");
}

function animateNetworkFlow(sourceIp, targetId, technique, label, color) {
  const source = topologyNodes.find(n => n.ip === sourceIp);
  const target = topologyNodes.find(n => n.id === targetId || n.ip === targetId);
  if (!source || !target) return;

  const flowColor = color || "#e74c3c";

  const path = svgMap.append("line")
    .attr("x1", source.x).attr("y1", source.y)
    .attr("x2", source.x).attr("y2", source.y)
    .attr("stroke", flowColor)
    .attr("stroke-width", 2.5)
    .attr("opacity", 0.9)
    .attr("stroke-dasharray", "none")
    .attr("marker-end", "url(#arrow-attack)");

  path.transition().duration(1000)
    .attr("x2", target.x).attr("y2", target.y)
    .on("end", () => {
      markNodeCompromised(target.ip || target.id);
      path.transition().delay(3000).duration(600).attr("opacity", 0).remove();
    });

  const midX = (source.x + target.x) / 2;
  const midY = (source.y + target.y) / 2 - 12;
  const lbl = svgMap.append("text")
    .attr("x", midX).attr("y", midY)
    .attr("text-anchor", "middle")
    .attr("fill", flowColor)
    .attr("font-size", "8px").attr("font-weight", "700")
    .attr("letter-spacing", "1px")
    .text(technique + (label ? ` — ${label}` : ""));

  lbl.transition().delay(3500).duration(400).attr("opacity", 0).remove();
}

function markNodeCompromised(ipOrId) {
  const node = topologyNodes.find(n => n.ip === ipOrId || n.id === ipOrId);
  if (!node) return;

  const g = d3.select("#mapnode-" + node.id);

  g.select("rect")
    .transition().duration(350)
    .attr("stroke", "#e74c3c")
    .attr("stroke-width", 2)
    .attr("filter", "url(#node-glow-red)");

  g.select("text:first-of-type")  // icon
    .transition().duration(350)
    .attr("fill", "#e74c3c");

  g.select(".state-badge")
    .text("COMPROMISED")
    .attr("fill", "#e74c3c");
}
