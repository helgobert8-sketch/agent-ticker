const assert = require("node:assert/strict");
const test = require("node:test");
const compare = require("../static/subscriptions.js");

const verified = { status: "verified", verified: true };
const stale = { status: "verified", verified: false };
const conditional = { status: "conditional", verified: false };
const unchecked = { status: "not checked", verified: false };
const rows = [
  { id: "price", cells: { a: verified, b: verified, c: verified, d: verified } },
  { id: "usage", cells: { a: conditional, b: unchecked, c: verified, d: conditional } },
  { id: "model", cells: { a: unchecked, b: unchecked, c: verified } },
  { id: "coding", cells: { a: stale, b: unchecked, c: unchecked, d: conditional } },
];
const plans = [
  { name: "A Pro", vendor: "a", selected: true },
  { name: "A Ultra", vendor: "a", selected: true },
  { name: "B Pro", vendor: "b", selected: true },
  { name: "C Pro", vendor: "c", selected: false },
  { name: "D Legacy", vendor: "d", group: "legacy", selected: false },
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
  const alwaysOn = [{ id: "always_on_agent", cells: { grok: conditional } }];
  const grokPlans = ["The X Subscription Plus", "SuperGrok Lite", "The X Subscription Premium"].map(name => ({
    name, vendor: "grok", selected: true,
  }));
  const { owned } = compare(alwaysOn, grokPlans, new Set());
  assert.deepEqual(owned[0].conditional.map(plan => plan.name), ["The X Subscription Premium"]);
});

test("a vendor-level verified cell does not verify legacy entitlements", () => {
  const legacyOnly = [{ ...plans[4], selected: true }];
  const { verified } = compare(rows, legacyOnly, new Set()).owned[0];
  assert.deepEqual(verified, []);
});
