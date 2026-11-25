(function () {
  "use strict";

  function offers(plan, cell) {
    return cell && cell.verified && plan.group !== "legacy";
  }

  function compare(rows, plans, priorities) {
    const selected = plans.filter(plan => plan.selected);
    const others = plans.filter(plan => !plan.selected);
    const owned = rows.map(row => ({
      row,
      verified: selected.filter(plan => offers(plan, row.cells[plan.vendor])),
      evidence: selected,
    }));
    const gaps = owned.filter(result => !result.verified.length).map(({ row }) => ({
      row,
      verified: others.filter(plan => offers(plan, row.cells[plan.vendor])),
      evidence: others.filter(plan => {
        const cell = row.cells[plan.vendor];
        return cell && !["not checked", "not included"].includes(cell.status);
      }),
    }));
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
      status: card.dataset.status,
      verified: card.dataset.verified === "true",
    }])),
  }));

  function node(tag, text, className) {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (className) el.className = className;
    return el;
  }

  function rowDetails({ row, verified, evidence }, marked) {
    const status = verified.length ? ` — verified: ${verified.map(plan => plan.name).join(", ")}` : " — none verified";
    const details = node("details", null, "stack-row");
    details.append(node("summary", row.label + status + (marked ? " · Matters to me" : "")));
    const cards = node("div", null, "stack-evidence");
    const grouped = new Map();
    for (const plan of evidence) {
      if (!grouped.has(plan.vendor)) grouped.set(plan.vendor, []);
      grouped.get(plan.vendor).push(plan);
    }
    for (const [vendor, group] of grouped) {
      const cell = row.cells[vendor];
      const card = cell.card.cloneNode(true);
      card.querySelector("h3").after(node("p", group.map(plan => plan.name).join(", "), "stack-plan-label"));
      if (group.some(plan => !offers(plan, cell))) {
        card.append(node("small", "Vendor-level evidence; not verified for all listed plans."));
      }
      cards.append(card);
    }
    if (!evidence.length) cards.append(node("p", "No other plan has an offer documented here."));
    details.append(cards);
    return details;
  }

  function render() {
    const marked = new Set(priorities.filter(box => box.checked).map(box => box.dataset.priority));
    priorities.forEach(box => { box.disabled = !box.checked && marked.size >= 3; });
    document.querySelector("#priority-count").textContent = `${marked.size} of 3`;
    const picked = plans.map(box => ({
      name: box.value, vendor: box.dataset.vendor, group: box.dataset.group, selected: box.checked,
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
      : [node("p", "Your picked plans have verified coverage in all map rows.")]));
  }

  controls.addEventListener("change", render);
  controls.hidden = false;
  render();
})();
