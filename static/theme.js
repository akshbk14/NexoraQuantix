/**
 * StockSense — Theme System (no-flash, 3 themes)
 * Runs in <head> before page render to prevent flash.
 * Themes: neon-dark | gold | cream
 */
(function () {
  var THEMES = ['neon-dark', 'gold', 'cream'];
  var saved = localStorage.getItem('ss-theme') || document.documentElement.getAttribute('data-theme') || 'neon-dark';
  if (THEMES.indexOf(saved) === -1) saved = 'neon-dark';
  document.documentElement.setAttribute('data-theme', saved);
  localStorage.setItem('ss-theme', saved);

  // Expose a global function for theme picker UI
  window.SS = window.SS || {};
  window.SS.setTheme = function(theme) {
    if (THEMES.indexOf(theme) === -1) return;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ss-theme', theme);

    // Sync active state on all swatches on page
    document.querySelectorAll('.theme-swatch,.theme-card').forEach(function(el) {
      el.classList.toggle('active', el.getAttribute('data-t') === theme);
    });

    // Re-apply Plotly charts if present
    if (window.SS.recolorPlotly) window.SS.recolorPlotly(theme);

    // Persist to server if user is authenticated (best-effort, non-blocking)
    fetch('/api/set-theme', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme: theme })
    }).catch(function() {});
  };
})();
