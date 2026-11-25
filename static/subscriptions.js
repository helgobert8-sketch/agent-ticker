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

  if (typeof module !== "undefined") {
    module.exports = compare;
    return;
  }

  const controls = document.querySelector("#stack-controls");
  const plans = [...controls.querySelectorAll("[data-plan]")];
  const priorities = [...controls.querySelectorAll("[data-priority]")];
  const results = document.querySelector("#stack-results");
  const summary = document.querySelector("#stack-summary");
  const rows = [...document.querySelectorAll(".map-row")].map(el => ({
    id: el.id,
    label: el.dataset.label,
    cells: Object.fromEntries([...el.querySelectorAll(".map-cell")].map(card => [card.dataset.vendor, {
      card,
      tiers: JSON.parse(card.dataset.tierEvidence),
      verified: card.dataset.verified === "true",
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
    const grouped = new Map();
    for (const plan of evidence) {
      if (["not checked", "not included"].includes(planStatus(plan, row))) continue;
      if (!grouped.has(plan.vendor)) grouped.set(plan.vendor, []);
      grouped.get(plan.vendor).push(plan);
    }
    for (const [vendor, group] of grouped) {
      const cell = row.cells[vendor];
      const card = cell.card.cloneNode(true);
      card.querySelector("h3").after(node("p", group.map(plan => plan.name).join(", "), "stack-plan-label"));
      if (group.some(plan => planStatus(plan, row) !== "verified")) {
        card.append(node("small", "Vendor-level evidence; check the terms for your tier."));
      }
      cards.append(card);
    }
    if (!evidence.length) cards.append(node("p", "No other plan has an offer documented here."));
    else if (!grouped.size) cards.append(node("p", "See the map for the vendor sources and notes."));
    details.append(cards);
    return details;
  }

  function render() {
    const marked = new Set(priorities.filter(box => box.checked).map(box => box.dataset.priority));
    priorities.forEach(box => { box.disabled = !box.checked && marked.size >= 3; });
    document.querySelector("#priority-count").textContent = `${marked.size} of 3`;
    const picked = plans.map(box => ({
      name: box.value, vendor: box.dataset.vendor, selected: box.checked,
    }));
    const count = picked.filter(plan => plan.selected).length;
    results.hidden = !count;
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

  controls.addEventListener("change", render);
  controls.hidden = false;
  render();
})();
