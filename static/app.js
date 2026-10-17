async function loadChart() {
  const res = await fetch("/api/board");
  if (!res.ok) return;
  const data = await res.json();
  const canvas = document.getElementById("chart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const keys = Object.keys(data.series || {}).slice(0, 4);
  const width = canvas.width = canvas.clientWidth * 2;
  const height = canvas.height = 440;
  ctx.clearRect(0, 0, width, height);
  if (!keys.length) return;
  const colors = ["#9a4a24", "#2f6b4f", "#1d4e89", "#8a6a2f"];
  const all = keys.flatMap(k => data.series[k].prices);
  const min = Math.min(...all) * 0.95;
  const max = Math.max(...all) * 1.05;
  keys.forEach((k, i) => {
    const s = data.series[k];
    ctx.beginPath();
    ctx.strokeStyle = colors[i % colors.length];
    ctx.lineWidth = 3;
    s.prices.forEach((p, idx) => {
      const x = 40 + (s.prices.length === 1 ? 0 : idx / (s.prices.length - 1)) * (width - 60);
      const y = 30 + (1 - (p - min) / Math.max(max - min, 1)) * (height - 60);
      if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });
}

document.getElementById("scrape").addEventListener("click", async () => {
  const btn = document.getElementById("scrape");
  btn.disabled = true;
  btn.textContent = "Scraping…";
  const res = await fetch("/api/scrape", { method: "POST" });
  const data = await res.json();
  const note = document.getElementById("note");
  note.textContent = data.alerts.length
    ? `Alerts: ${data.alerts.map(a => a.sku + " " + a.drop_pct + "%").join(", ")}`
    : `Scrape finished. Errors: ${data.errors.length}`;
  if (data.errors.length) note.textContent += " — " + data.errors.map(e => e.sku + ": " + e.error).join("; ");
  setTimeout(() => location.reload(), 900);
});

document.getElementById("test").addEventListener("click", async () => {
  const form = document.getElementById("add");
  const note = document.getElementById("form-note");
  const body = {
    source_url: form.source_url.value,
    price_selector: form.price_selector.value,
  };
  const res = await fetch("/api/test-scrape", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  note.textContent = data.price ? `Found ₹${data.price} via ${data.engine}` : (data.error || "Failed");
});

document.getElementById("add").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const body = Object.fromEntries(new FormData(form).entries());
  body.our_price = Number(body.our_price);
  const res = await fetch("/api/skus", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    document.getElementById("form-note").textContent = data.detail || "Could not save";
    return;
  }
  location.reload();
});

document.querySelectorAll(".del").forEach(btn => {
  btn.addEventListener("click", async () => {
    if (!confirm("Remove this SKU and its history?")) return;
    await fetch("/api/skus/" + btn.dataset.id, { method: "DELETE" });
    location.reload();
  });
});

loadChart();
