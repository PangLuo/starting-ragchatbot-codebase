# Frontend Changes

## Dark/Light Theme Toggle

### Files Modified
- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

### Changes

**index.html**
- Added inline `<script>` in `<head>` that reads `localStorage.getItem('theme')` and immediately sets `data-theme="light"` on `<html>` if saved, preventing a flash of unstyled content (FOUC) on page load.
- Added a fixed-position `<button id="themeToggle" class="theme-toggle">` before `</body>` with accessible `aria-label` and `title` attributes. Contains two SVG icons: a sun (shown in dark mode) and a moon (shown in light mode), toggled via CSS.

**style.css**
- Added `transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease` to the `*` reset rule for smooth theme transitions across all elements.
- Added `[data-theme="light"]` CSS variable block overriding all color tokens:
  - Background: `#f8fafc` (near-white)
  - Surface: `#ffffff` (white)
  - Surface hover: `#f1f5f9`
  - Text primary: `#0f172a` (near-black)
  - Text secondary: `#64748b`
  - Border color: `#e2e8f0`
  - Primary/user message colors unchanged (blue stays blue)
- Added `.theme-toggle` button styles: fixed top-right, 40×40px circle, uses `--surface`, `--border-color`, and `--text-primary` variables so it adapts to both themes automatically.
- Added icon visibility rules: `.icon-sun` shown in dark mode, `.icon-moon` shown in light mode via `[data-theme="light"]` selector overrides.
- Added light-mode overrides for hardcoded `rgba(0,0,0,0.2)` code block backgrounds, replacing with lower-opacity values suitable for light backgrounds.

**script.js**
- Added `toggleTheme()` function: toggles `data-theme` attribute on `document.documentElement` and persists the choice to `localStorage`.
- Added `initTheme()` stub (theme is applied by the inline `<head>` script; this function exists for future expansion).
- Wired up `themeToggle` click event listener in `setupEventListeners()`.
- Called `initTheme()` in the `DOMContentLoaded` handler.
