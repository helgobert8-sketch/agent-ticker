(function () {
  "use strict";

  function planStatus(plan, row) {
    const cell = row.cells[plan.vendor];
    const status = cell?.tiers[plan.name] ?? "not checked";
    return status === "verified" && !cell.verified ? "review needed" : status;
  }

  function coverage(row, plans) {
    return {
      row,
      verified: plans.filter(plan => planStatus(plan, row) === "verified"),
      conditional: plans.filter(plan => planStatus(plan, row) === "conditional"),
    };
  }

  function compare(rows, plans, priorities) {
    const selected = plans.filter(plan => plan.selected);
    const others = plans.filter(plan => !plan.selected);
    const owned = rows.map(row => ({ ...coverage(row, selected), evidence: selected }));
    const gaps = owned.filter(result => !result.verified.length && !result.conditional.length).map(({ row }) => {
      const result = coverage(row, others);
      return { ...result, evidence: [...result.verified, ...result.conditional] };
    });
    gaps.sort((a, b) => Number(priorities.has(b.row.id)) - Number(priorities.has(a.row.id)));
    return { owned, gaps, overlap: owned.filter(result => result.verified.length >= 2).length };
  }

  function evidenceCards(row, evidence) {
    const grouped = new Map();
    for (const plan of evidence) {
      if (!grouped.has(plan.vendor)) grouped.set(plan.vendor, []);
      grouped.get(plan.vendor).push(plan);
    }
    return Array.from(grouped, ([vendor, plans]) => ({
      card: row.cells[vendor].card.cloneNode(true),
      plans,
    }));
  }

  function agentExport(rows, plans, marked, format) {
    const { owned, gaps } = compare(rows, plans, marked);
    const entries = (row, evidence) => evidence.map(plan => {
      const { sources, checked } = row.cells[plan.vendor];
      return { plan: plan.name, status: planStatus(plan, row), sources, checked };
    });
    const data = {
      pickedPlans: plans.filter(plan => plan.selected).map(plan => plan.name),
      mustHaves: rows.filter(row => marked.has(row.id)).map(row => row.label),
      coverage: owned.filter(result => result.verified.length || result.conditional.length).map(result => ({
        row: result.row.label,
        plans: entries(result.row, [...result.verified, ...result.conditional]),
      })),
      gaps: gaps.map(({ row, evidence }) => ({
        row: row.label,
        mustHave: marked.has(row.id),
        picked: entries(row, plans.filter(plan => plan.selected)),
        alternatives: entries(row, evidence),
      })),
    };
    if (format === "json") return JSON.stringify(data, null, 2);
    const reference = entry => {
      const links = entry.sources.map((url, index) => `[official source${index ? " " + (index + 1) : ""}](<${url}>)`);
      return `${entry.plan} — ${entry.status}, ${links.join(", ")}, checked ${entry.checked}`;
    };
    const coverage = data.coverage.map(item =>
      `- ${item.row}: ${item.plans.map(reference).join("; ")}`);
    const missing = data.gaps.flatMap(item => [
      `- ${item.row}${item.mustHave ? " (must-have)" : ""}`,
      ...item.picked.map(entry => `  - Picked: ${reference(entry)}`),
      ...item.alternatives.map(entry => `  - Other plan: ${reference(entry)}`),
    ]);
    return [
      "# Agent-Ticker stack check",
      "",
      `**Picked plans:** ${data.pickedPlans.join(", ")}`,
      `**Must-haves:** ${data.mustHaves.join(", ") || "None marked"}`,
      "",
      "## Coverage",
      ...(coverage.length ? coverage : ["- None documented for these plans."]),
      "",
      "## Gaps",
      ...(missing.length ? missing : ["- None: verified or conditional coverage in every row."]),
      "",
      `**Suggested prompt:** ${marked.size ? "Check my marked gaps first, then the others" : "Check the gaps listed"}. Cite current original sources and distinguish documented product feature, plan entitlement and unknown usage.`,
    ].join("\n");
  }

  if (typeof module !== "undefined") {
    module.exports = compare;
    module.exports.evidenceCards = evidenceCards;
    module.exports.agentExport = agentExport;
    return;
  }

  const controls = document.querySelector("#stack-controls");
  const plans = [...controls.querySelectorAll("[data-plan]")];
  const priorities = [...controls.querySelectorAll("[data-priority]")];
  const results = document.querySelector("#stack-results");
  const summary = document.querySelector("#stack-summary");
  const copy = document.querySelector("#stack-copy");
  const format = document.querySelector("#stack-format");
  const copyStatus = document.querySelector("#stack-copy-status");
  const output = document.querySelector("#stack-copy-output");
  const preview = document.querySelector("#stack-copy-preview");
  const rows = [...document.querySelectorAll(".map-row")].map(el => ({
    id: el.id,
    label: el.dataset.label,
    cells: Object.fromEntries([...el.querySelectorAll(".map-cell")].map(card => [card.dataset.vendor, {
      card,
      tiers: JSON.parse(card.dataset.tierEvidence),
      verified: card.dataset.verified === "true",
      sources: [...card.querySelectorAll("[data-map-source]")].map(link => link.getAttribute("href")),
      checked: card.querySelector("[data-map-checked]").textContent,
    }])),
  }));

  function node(tag, text, className) {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (className) el.className = className;
    return el;
  }

  function rowDetails({ row, verified, conditional, evidence }, marked) {
    const labels = [
      verified.length && `verified: ${verified.map(plan => plan.name).join(", ")}`,
      conditional.length && `conditional: ${conditional.map(plan => plan.name).join(", ")}`,
      ...["not checked", "not included", "review needed"].map(status => {
        const names = evidence.filter(plan => planStatus(plan, row) === status).map(plan => plan.name);
        return names.length && `${status}: ${names.join(", ")}`;
      }),
    ].filter(Boolean);
    const status = " — " + (labels.join(" · ") || "no verified or conditional coverage");
    const details = node("details", null, "stack-row");
    details.append(node("summary", row.label + status + (marked ? " · Matters to me" : "")));
    const cards = node("div", null, "stack-evidence");
    for (const { card, plans } of evidenceCards(row, evidence)) {
      card.querySelector("h3").after(node("p", plans.map(plan => plan.name).join(", "), "stack-plan-label"));
      if (plans.some(plan => planStatus(plan, row) !== "verified")) {
        card.append(node("small", "Vendor-level source and notes; see the status for your tier above."));
      }
      cards.append(card);
    }
    if (!evidence.length) cards.append(node("p", "No other plan has an offer documented here."));
    details.append(cards);
    return details;
  }

  function inputs() {
    const marked = new Set(priorities.filter(box => box.checked).map(box => box.dataset.priority));
    const picked = plans.map(box => ({
      name: box.value, vendor: box.dataset.vendor, selected: box.checked,
    }));
    return { marked, picked };
  }

  function resetExport() {
    preview.hidden = true;
    output.value = "";
    copyStatus.textContent = "";
  }

  function render() {
    const { marked, picked } = inputs();
    priorities.forEach(box => { box.disabled = !box.checked && marked.size >= 3; });
    document.querySelector("#priority-count").textContent = `${marked.size} of 3`;
    const count = picked.filter(plan => plan.selected).length;
    results.hidden = !count;
    copy.disabled = !count;
    resetExport();
    if (!count) {
      summary.textContent = "Pick at least one plan to see your stack.";
      return;
    }
    const { owned, gaps, overlap } = compare(rows, picked, marked);
    summary.textContent = `${count} picked · Rows where both offer verified coverage: ${overlap} of ${rows.length}`;
    document.querySelector("#stack-owned").replaceChildren(...owned.map(result => rowDetails(result, false)));
    document.querySelector("#stack-gaps").replaceChildren(...(gaps.length
      ? gaps.map(result => rowDetails(result, marked.has(result.row.id)))
      : [node("p", "Your picked plans have verified or conditional coverage in every row.")]));
  }

  copy.addEventListener("click", async () => {
    const { picked, marked } = inputs();
    const text = agentExport(rows, picked, marked, format.value);
    output.value = text;
    preview.hidden = false;
    try {
      await navigator.clipboard.writeText(text);
      if (output.value === text) copyStatus.textContent = "Copied.";
    } catch {
      if (output.value !== text) return;
      copyStatus.textContent = "Clipboard unavailable. Copy the selected text below.";
      output.focus();
      output.select();
    }
  });
  controls.addEventListener("change", render);
  controls.hidden = false;
  render();
})();
