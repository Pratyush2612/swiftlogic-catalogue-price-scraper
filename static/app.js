async function loadChart() {
  const res = await fetch("/api/board");
  const data = await res.json();
  const canvas = document.getElementById("chart");
  const ctx = canvas.getContext("2d");
  const keys = Object.keys(data.series).slice(0, 4);
  const width = canvas.width = canvas.clientWidth * 2;
  const height = canvas.height = 440;
  ctx.clearRect(0, 0, width, height);
  const colors = ["#9a4a24", "#2f6b4f", "#1d4e89", "#8a6a2f"];
  const all = keys.flatMap(k => data.series[k].prices);
  if (!all.length) return;
  const min = Math.min(...all) * 0.95;
  const max = Math.max(...all) * 1.05;
  keys.forEach((k, i) => {
    const s = data.series[k];
    ctx.beginPath();
    ctx.strokeStyle = colors[i % colors.length];
    ctx.lineWidth = 3;
    s.prices.forEach((p, idx) => {
      const x = 40 + (idx / (s.prices.length - 1)) * (width - 60);
      const y = 30 + (1 - (p - min) / (max - min)) * (height - 60);
      if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });
  ctx.font = "22px Segoe UI";
  ctx.fillStyle = "#6e675e";
  keys.forEach((k, i) => {
    ctx.fillStyle = colors[i % colors.length];
    ctx.fillText(k, 40 + i * 180, height - 12);
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
    ? `Alerts fired: ${data.alerts.map(a => a.sku + " " + a.drop_pct + "% via " + a.channel).join(", ")}`
    : "Scrape finished. No drop past the threshold.";
  if (data.errors.length) note.textContent += " Errors: " + data.errors.map(e => e.sku).join(", ");
  setTimeout(() => location.reload(), 700);
});

loadChart();
