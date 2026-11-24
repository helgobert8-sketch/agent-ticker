(function () {
  var state = { agent: null, cat: null };
  var chips = document.querySelectorAll(".filters .chip");
  function apply() {
    document.querySelectorAll("#timeline .item").forEach(function (el) {
      var ok = (!state.agent || el.dataset.agent === state.agent) && (!state.cat || el.dataset.cat === state.cat);
      el.classList.toggle("hidden", !ok);
    });
    document.querySelectorAll("#timeline .day").forEach(function (d) {
      d.classList.toggle("hidden", !d.querySelector(".item:not(.hidden)"));
    });
    chips.forEach(function (c) {
      var on = c.hasAttribute("data-all") ? !state.agent && !state.cat : c.dataset.agent ? c.dataset.agent === state.agent : c.dataset.cat === state.cat;
      c.classList.toggle("on", on);
    });
  }
  chips.forEach(function (c) {
    c.addEventListener("click", function () {
      if (c.hasAttribute("data-all")) state = { agent: null, cat: null };
      else if (c.dataset.agent) state.agent = state.agent === c.dataset.agent ? null : c.dataset.agent;
      else state.cat = state.cat === c.dataset.cat ? null : c.dataset.cat;
      apply();
    });
  });
  document.querySelectorAll("[data-jump]").forEach(function (a) {
    a.addEventListener("click", function (ev) {
      ev.preventDefault();
      state = { agent: a.dataset.jump, cat: null };
      apply();
      document.querySelector(".filters").scrollIntoView({ behavior: "smooth" });
    });
  });
})();
