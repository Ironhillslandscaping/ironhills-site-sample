// Mobile menu + dropdown toggles for the static sample (replaces Wix's menu script).
document.addEventListener('DOMContentLoaded', function () {
  var t = document.querySelector('.nav-toggle'), n = document.querySelector('.site-nav');
  if (t && n) t.addEventListener('click', function () { var o = n.classList.toggle('open'); t.setAttribute('aria-expanded', o); });
  document.querySelectorAll('.sub-toggle').forEach(function (b) {
    b.addEventListener('click', function (e) { e.preventDefault(); b.parentElement.classList.toggle('open'); });
  });
});
