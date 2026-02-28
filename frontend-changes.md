# Frontend Changes

## Code Quality Tooling (quality_feature branch)

### What was added

**Prettier** — automatic code formatter (the frontend equivalent of Python's `black`):
- `frontend/.prettierrc` — configuration: 2-space indentation, single quotes, trailing commas (ES5), 100-char print width, LF line endings
- `frontend/.prettierignore` — excludes `node_modules/`

**ESLint** — JavaScript linter:
- `frontend/eslint.config.js` — flat config for ES2022; enforces `no-var`, `prefer-const`, `eqeqeq`, `curly`, and flags undefined globals

**`frontend/package.json`** — dev tooling manifest with scripts:
- `npm run format` — auto-format all files with Prettier
- `npm run format:check` — check formatting without writing (CI-friendly)
- `npm run lint` — lint `script.js` with ESLint
- `npm run lint:fix` — auto-fix lint issues
- `npm run check` — run both format check and lint (full quality gate)

**`scripts/check-frontend.sh`** — shell script for running quality checks:
- `./scripts/check-frontend.sh` — check mode (exits non-zero on failure)
- `./scripts/check-frontend.sh --fix` — fix mode (applies Prettier + ESLint auto-fixes)
- Auto-installs `node_modules` if missing on first run

### Files reformatted

All three frontend files were reformatted to match Prettier's output style:

- **`frontend/index.html`** — normalized to 2-space indentation; attributes on separate lines for long elements (buttons with `data-question`, SVG tags); `<!doctype html>` lowercased per HTML5 convention
- **`frontend/script.js`** — switched to 2-space indentation; removed extra blank lines; added curly braces around single-statement `if` bodies; trailing commas added in objects/arrays; arrow function params consistently parenthesized
- **`frontend/style.css`** — switched to 2-space indentation; expanded shorthand selector groups (h1–h6 font sizes on separate rules); multi-value `transition` properties formatted on separate lines per Prettier's CSS output

### How to use

```bash
# First-time setup (from repo root)
cd frontend && npm install

# Check formatting and lint
./scripts/check-frontend.sh

# Auto-fix all issues
./scripts/check-frontend.sh --fix

# Or use npm scripts directly from frontend/
cd frontend
npm run check        # format check + lint
npm run format       # auto-format
npm run lint:fix     # auto-fix lint
```
