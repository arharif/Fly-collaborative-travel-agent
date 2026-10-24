/* Accessible FLY Academy theme switcher. Uses only localStorage, no tracking. */
(() => {
  'use strict';
  const valid = new Set(['rose','black','king-green']);
  const storageKey = 'fly-academy-theme-v2';
  const buttons = [...document.querySelectorAll('[data-theme-option]')];
  function loadTheme() {
    try { const stored = localStorage.getItem(storageKey); return valid.has(stored) ? stored : 'rose'; }
    catch (_) { return 'rose'; }
  }
  function setTheme(theme) {
    const selected = valid.has(theme) ? theme : 'rose';
    document.documentElement.setAttribute('data-theme', selected);
    document.documentElement.style.colorScheme = selected === 'rose' ? 'light' : 'dark';
    buttons.forEach(button => {
      const active = button.dataset.themeOption === selected;
      button.setAttribute('aria-pressed', String(active));
      button.title = `${button.dataset.themeLabel || selected} theme${active ? ' (selected)' : ''}`;
    });
    const meta = document.querySelector('meta[name="theme-color"]');
    if(meta) meta.content = selected === 'black' ? '#101013' : selected === 'king-green' ? '#091e15' : '#f6e5ed';
    try { localStorage.setItem(storageKey, selected); } catch (_) {}
  }
  buttons.forEach(button => button.addEventListener('click', () => setTheme(button.dataset.themeOption)));
  setTheme(loadTheme());
})();
