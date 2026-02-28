#!/usr/bin/env bash
# Frontend quality checks: formatting (Prettier) and linting (ESLint)
# Usage: ./scripts/check-frontend.sh [--fix]

set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"
FIX_MODE=false

for arg in "$@"; do
  if [[ "$arg" == "--fix" ]]; then
    FIX_MODE=true
  fi
done

echo "==> Checking frontend quality in: $FRONTEND_DIR"

cd "$FRONTEND_DIR"

# Install deps if node_modules is missing
if [[ ! -d node_modules ]]; then
  echo "==> Installing dev dependencies..."
  npm install --silent
fi

if [[ "$FIX_MODE" == true ]]; then
  echo "==> Running Prettier (fix mode)..."
  npx prettier --write .

  echo "==> Running ESLint (fix mode)..."
  npx eslint --fix script.js

  echo "==> All fixes applied."
else
  PASS=true

  echo "==> Running Prettier check..."
  if ! npx prettier --check .; then
    PASS=false
    echo "    FAIL: run './scripts/check-frontend.sh --fix' to auto-format."
  else
    echo "    OK"
  fi

  echo "==> Running ESLint..."
  if ! npx eslint script.js; then
    PASS=false
  else
    echo "    OK"
  fi

  if [[ "$PASS" == false ]]; then
    echo ""
    echo "==> Quality checks FAILED. Run './scripts/check-frontend.sh --fix' to auto-fix formatting."
    exit 1
  fi

  echo ""
  echo "==> All frontend quality checks passed."
fi
