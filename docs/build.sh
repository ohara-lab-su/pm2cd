#!/usr/bin/env bash
set -euo pipefail

DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$DOCS_DIR/.." && pwd)"
OUT_DIR="$DOCS_DIR/_build/html"

rm -rf "$DOCS_DIR/en/api" "$DOCS_DIR/ja/api" "$OUT_DIR"
mkdir -p "$DOCS_DIR/en/api" "$DOCS_DIR/ja/api" "$OUT_DIR"

for LANG_CODE in en ja; do
  sphinx-apidoc --force --module-first --output-dir "$DOCS_DIR/$LANG_CODE/api" "$ROOT_DIR/src/pm2cd"
  cat > "$DOCS_DIR/$LANG_CODE/api/index.md" <<'EOF'
# API Reference

```{toctree}
:maxdepth: 2

modules
```
EOF
  DOC_LANGUAGE="$LANG_CODE" sphinx-build --builder html --config-dir "$DOCS_DIR" "$DOCS_DIR/$LANG_CODE" "$OUT_DIR/$LANG_CODE"
done
cp -a "$OUT_DIR/en/." "$OUT_DIR/"
touch "$OUT_DIR/.nojekyll"
