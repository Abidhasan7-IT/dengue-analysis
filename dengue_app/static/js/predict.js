(function () {
  const form = document.getElementById("predict-form");
  const placeholder = document.getElementById("result-placeholder");
  const content = document.getElementById("result-content");
  const submitBtn = document.getElementById("submit-btn");

  const RISK_COLORS = { Low: "#3D7A5C", Moderate: "#B4791F", High: "#A6403B" };

  function gaugeSVG(prob, level) {
    const r = 46, cx = 60, cy = 60, circumference = 2 * Math.PI * r;
    const offset = circumference * (1 - prob);
    const color = RISK_COLORS[level] || "#123A3D";
    return `
      <svg class="risk-gauge" width="120" height="120" viewBox="0 0 120 120">
        <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#EAEDEB" stroke-width="10"/>
        <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="10"
                stroke-linecap="round" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
                transform="rotate(-90 ${cx} ${cy})"/>
        <text x="${cx}" y="${cy + 6}" text-anchor="middle" font-family="'IBM Plex Mono', monospace"
              font-size="22" font-weight="600" fill="${color}">${Math.round(prob * 100)}%</text>
      </svg>`;
  }

  function contributorRows(contributors) {
    const maxAbs = Math.max(...contributors.map(c => Math.abs(c.contribution)), 0.001);
    return contributors.map(c => {
      const pct = Math.min(100, (Math.abs(c.contribution) / maxAbs) * 100);
      const color = c.contribution > 0 ? "#A6403B" : "#3D7A5C";
      return `
        <div class="factor-row">
          <span>${c.label}</span>
          <div class="factor-bar-track"><div class="factor-bar-fill" style="width:${pct}%; background:${color};"></div></div>
          <span class="factor-value">${c.direction === "raises risk" ? "\u2191" : "\u2193"}</span>
        </div>`;
    }).join("");
  }

  function flagsBox(flags) {
    if (!flags.length) {
      return `<div class="flags-box empty"><h4>Clinical flags</h4><p style="margin:0;">No brief-defined thresholds are tripped.</p></div>`;
    }
    return `<div class="flags-box"><h4>Clinical flags tripped</h4><ul>${flags.map(f => `<li>${f}</li>`).join("")}</ul></div>`;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    submitBtn.disabled = true;
    submitBtn.textContent = "Assessing\u2026";

    const fd = new FormData(form);
    const payload = {};
    fd.forEach((v, k) => { payload[k] = v; });
    // unchecked checkboxes are simply absent from FormData -> default them to "0"
    ["Headache", "Myalgia", "Joint_Pain", "Retro_Orbital_Pain", "Rash"].forEach(s => {
      if (!(s in payload)) payload[s] = "0";
    });

    try {
      const res = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Prediction failed");

      const levelClass = data.risk_level.toLowerCase();
      content.innerHTML = `
        <div class="risk-readout">
          ${gaugeSVG(data.probability, data.risk_level)}
          <div>
            <p class="risk-level-label">Predicted risk</p>
            <p class="risk-level-value ${levelClass}">${data.risk_level}</p>
            <p class="risk-prob">${data.prediction === 1 ? "Model classifies as dengue-positive" : "Model classifies as dengue-negative"}</p>
          </div>
        </div>
        ${flagsBox(data.clinical_flags)}
        <p class="contrib-title">Top contributing factors</p>
        ${contributorRows(data.contributors)}
      `;
      placeholder.style.display = "none";
      content.style.display = "block";
    } catch (err) {
      content.innerHTML = `<div class="flags-box"><h4>Something went wrong</h4><p style="margin:0;">${err.message}</p></div>`;
      placeholder.style.display = "none";
      content.style.display = "block";
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Assess risk";
    }
  });
})();
