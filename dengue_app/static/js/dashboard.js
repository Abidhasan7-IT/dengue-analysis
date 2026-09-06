// Chart.js rendering for the model dashboard. METRICS is injected inline in dashboard.html.
(function () {
  const TEAL = "#123A3D";
  const TEAL_SOFT = "rgba(18, 58, 61, 0.15)";
  const NAVY = "#1F3A54";
  const LOW = "#3D7A5C";
  const HIGH = "#A6403B";
  const INK_SOFT = "#4B5A54";
  const LINE = "#D8DED9";

  Chart.defaults.font.family = "'IBM Plex Sans', sans-serif";
  Chart.defaults.color = INK_SOFT;
  Chart.defaults.borderColor = LINE;

  // ---------------------------------------------------------------- ROC
  new Chart(document.getElementById("rocChart"), {
    type: "line",
    data: {
      labels: METRICS.roc_curve.map(p => p.fpr.toFixed(2)),
      datasets: [
        {
          label: "Model",
          data: METRICS.roc_curve.map(p => p.tpr),
          borderColor: TEAL,
          backgroundColor: TEAL_SOFT,
          fill: true,
          tension: 0.15,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "Chance",
          data: METRICS.roc_curve.map(p => p.fpr),
          borderColor: LINE,
          borderDash: [4, 4],
          pointRadius: 0,
          borderWidth: 1.5,
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: true, position: "bottom", labels: { boxWidth: 14 } } },
      scales: {
        x: { title: { display: true, text: "False positive rate" }, grid: { display: false } },
        y: { title: { display: true, text: "True positive rate" }, min: 0, max: 1, grid: { color: LINE } },
      },
    },
  });

  // --------------------------------------------------------- importance
  const imp = METRICS.rf_importance.slice(0, 10);
  new Chart(document.getElementById("importanceChart"), {
    type: "bar",
    data: {
      labels: imp.map(p => p[0].replaceAll("_", " ")),
      datasets: [{
        data: imp.map(p => p[1]),
        backgroundColor: TEAL,
        borderRadius: 2,
        barThickness: 18,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { title: { display: true, text: "Relative importance" }, grid: { color: LINE } },
        y: { grid: { display: false } },
      },
    },
  });

  // -------------------------------------------------------------- area
  const areas = Object.entries(METRICS.top_areas);
  new Chart(document.getElementById("areaChart"), {
    type: "bar",
    data: {
      labels: areas.map(a => a[0]),
      datasets: [{ data: areas.map(a => a[1]), backgroundColor: NAVY, borderRadius: 2 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { autoSkip: false, maxRotation: 55, minRotation: 45 }, grid: { display: false } },
        y: { grid: { color: LINE } },
      },
    },
  });

  // ----------------------------------------------------------- outcome
  new Chart(document.getElementById("outcomeChart"), {
    type: "doughnut",
    data: {
      labels: ["Negative", "Positive"],
      datasets: [{
        data: [METRICS.outcome_distribution.negative, METRICS.outcome_distribution.positive],
        backgroundColor: [LOW, HIGH],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: "62%",
      plugins: { legend: { position: "bottom", labels: { boxWidth: 14 } } },
    },
  });

  // ------------------------------------------------------------- labs
  const nbo = METRICS.numeric_by_outcome;
  new Chart(document.getElementById("labChart"), {
    type: "bar",
    data: {
      labels: ["Platelet count", "WBC count"],
      datasets: [
        { label: "Negative", data: [nbo.Platelet_Count.negative.mean, nbo.WBC_Count.negative.mean], backgroundColor: LOW, borderRadius: 2 },
        { label: "Positive", data: [nbo.Platelet_Count.positive.mean, nbo.WBC_Count.positive.mean], backgroundColor: HIGH, borderRadius: 2 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: "bottom", labels: { boxWidth: 14 } } },
      scales: { y: { grid: { color: LINE } }, x: { grid: { display: false } } },
    },
  });

  // ---------------------------------------------------------- vitals
  new Chart(document.getElementById("vitalsChart"), {
    type: "bar",
    data: {
      labels: ["Body temperature (\u00b0C)", "Fever duration (days)"],
      datasets: [
        { label: "Negative", data: [nbo.Body_Temperature.negative.mean, nbo.Fever_Duration.negative.mean], backgroundColor: LOW, borderRadius: 2 },
        { label: "Positive", data: [nbo.Body_Temperature.positive.mean, nbo.Fever_Duration.positive.mean], backgroundColor: HIGH, borderRadius: 2 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: "bottom", labels: { boxWidth: 14 } } },
      scales: { y: { grid: { color: LINE } }, x: { grid: { display: false } } },
    },
  });
})();
