const assert = require("node:assert/strict");
const test = require("node:test");
const compare = require("../static/subscriptions.js");

const tierCell = (names, status, verified = false) => ({
  tiers: Object.fromEntries(names.map(name => [name, status])), verified,
});
const aPlans = ["A Pro", "A Ultra"];
const aVerified = tierCell(aPlans, "verified", true);
const aStale = tierCell(aPlans, "verified");
const aConditional = tierCell(aPlans, "conditional");
const bVerified = tierCell(["B Pro"], "verified", true);
const cVerified = tierCell(["C Pro"], "verified", true);
const dConditional = tierCell(["D Legacy"], "conditional");
const unchecked = tierCell(["A Pro", "A Ultra", "B Pro", "C Pro"], "not checked");
const rows = [
  { id: "price", cells: { a: aVerified, b: bVerified, c: cVerified, d: tierCell(["D"], "verified", true) } },
  { id: "usage", cells: { a: aConditional, b: unchecked, c: cVerified, d: dConditional } },
  { id: "model", cells: { a: unchecked, b: unchecked, c: cVerified } },
  { id: "coding", cells: { a: aStale, b: unchecked, c: unchecked, d: dConditional } },
];
const plans = [
  { name: "A Pro", vendor: "a", selected: true },
  { name: "A Ultra", vendor: "a", selected: true },
  { name: "B Pro", vendor: "b", selected: true },
  { name: "C Pro", vendor: "c", selected: false },
  { name: "D Legacy", vendor: "d", selected: false },
];

test("three picked plans count a verified overlap once per row", () => {
  const { owned, overlap } = compare(rows, plans, new Set());
  assert.equal(overlap, 1);
  assert.equal(owned[0].verified.length, 3);
  assert.deepEqual(owned.slice(1).map(row => row.verified.length), [0, 0, 0]);
});

test("gaps are prioritized and only unpicked plans appear as alternatives", () => {
  const { gaps } = compare(rows, plans, new Set(["coding"]));
  assert.deepEqual(gaps.map(result => result.row.id), ["coding", "model"]);
  assert.deepEqual(gaps[0].verified, []);
  assert.deepEqual(gaps[0].conditional.map(plan => plan.name), ["D Legacy"]);
  assert.deepEqual(gaps[0].evidence.map(plan => plan.name), ["D Legacy"]);
  assert.deepEqual(gaps[1].verified.map(plan => plan.name), ["C Pro"]);
});

test("conditional picks cover a row without increasing verified overlap", () => {
  const { owned, gaps, overlap } = compare(rows, plans, new Set());
  const usage = owned.find(result => result.row.id === "usage");
  assert.deepEqual(usage.conditional.map(plan => plan.name), ["A Pro", "A Ultra"]);
  assert.equal(usage.verified.length, 0);
  assert.ok(!gaps.some(result => result.row.id === "usage"));
  assert.equal(overlap, 1);
});

test("a conditional cell does not grant coverage to Grok tiers explicitly excluded by the baseline", () => {
  const names = ["The X Subscription Plus", "SuperGrok Lite", "The X Subscription Premium"];
  const alwaysOn = [{ id: "always_on_agent", cells: { grok: {
    tiers: { [names[0]]: "not included", [names[1]]: "not included", [names[2]]: "conditional" },
  } } }];
  const grokPlans = names.map(name => ({ name, vendor: "grok", selected: true }));
  const { owned } = compare(alwaysOn, grokPlans, new Set());
  assert.deepEqual(owned[0].conditional.map(plan => plan.name), ["The X Subscription Premium"]);
});

test("picking only SuperGrok Lite leaves top model access and coding agent gaps", () => {
  const rows = ["top_model_access", "coding_agent"].map(id => ({
    id,
    cells: { grok: { tiers: { "SuperGrok Lite": "not checked", "The X Subscription Premium": "conditional" } } },
  }));
  const picks = [
    { name: "SuperGrok Lite", vendor: "grok", selected: true },
    { name: "The X Subscription Premium", vendor: "grok", selected: false },
  ];
  const { owned, gaps, overlap } = compare(rows, picks, new Set());
  assert.ok(owned.every(result => !result.verified.length && !result.conditional.length));
  assert.deepEqual(gaps.map(result => result.row.id), ["top_model_access", "coding_agent"]);
  assert.ok(gaps.every(result => result.conditional[0].name === "The X Subscription Premium"));
  assert.equal(overlap, 0);
});

test("unchecked and excluded plans retain the full vendor source card and flags", () => {
  const lite = { name: "SuperGrok Lite", vendor: "grok", selected: true };
  const vendorCard = {
    source: "https://docs.x.ai/",
    flags: ["New update, check", "Source changed, check"],
  };
  for (const status of ["not checked", "not included"]) {
    const row = { id: "grok", cells: { grok: {
      ...tierCell([lite.name], status),
      card: { cloneNode: deep => {
        assert.equal(deep, true);
        return vendorCard;
      } },
    } } };
    const { owned } = compare([row], [lite], new Set());
    assert.deepEqual(compare.evidenceCards(row, owned[0].evidence), [{ card: vendorCard, plans: [lite] }]);
  }
});

test("a vendor-level verified cell does not verify legacy entitlements", () => {
  const legacyOnly = [{ ...plans[4], selected: true }];
  const { verified } = compare(rows, legacyOnly, new Set()).owned[0];
  assert.deepEqual(verified, []);
});
