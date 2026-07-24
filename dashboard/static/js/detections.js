/**
 * Detections Feed — Falcon alert display
 */

const SEVERITY_COLORS = {
  CRITICAL: "#e74c3c",
  HIGH:     "#e67e22",
  MEDIUM:   "#f1c40f",
  LOW:      "#3498db",
  UNKNOWN:  "#777",
};

function addDetection(event) {
  const container = document.getElementById("detections-feed");
  const color = SEVERITY_COLORS[event.severity] || SEVERITY_COLORS.UNKNOWN;
  const ts = new Date(event.ts * 1000).toLocaleTimeString();

  const card = document.createElement("div");
  card.className = "detection-card";
  card.style.borderLeftColor = color;
  card.innerHTML = `
    <div class="det-header">
      <span class="det-severity" style="color:${color}">${event.severity}</span>
      <span class="det-technique">${escapeHtml(event.technique || "")}</span>
      <span class="det-ts">${ts}</span>
    </div>
    <div class="det-desc">${escapeHtml(event.description || "")}</div>
    ${event.host ? `<div class="det-host">📍 ${escapeHtml(event.host)}</div>` : ""}
  `;

  // Flash animation
  card.style.animation = "flashIn 0.4s ease";
  container.prepend(card);

  // Cap feed at 20 items
  const cards = container.querySelectorAll(".detection-card");
  if (cards.length > 20) cards[cards.length - 1].remove();
}
