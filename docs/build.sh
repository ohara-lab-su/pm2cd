#!/usr/bin/env bash
set -euo pipefail

DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$DOCS_DIR/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/src/pm2cd"
STAGE_DIR="$DOCS_DIR/_generated"
OUTPUT_DIR="$DOCS_DIR/_build/html"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "ERROR: pm2cd package not found: $SOURCE_DIR" >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR/src:${PYTHONPATH:-}"
rm -rf "$STAGE_DIR" "$DOCS_DIR/_build"
mkdir -p "$OUTPUT_DIR"

for lang in en ja; do
  mkdir -p "$STAGE_DIR/$lang"
  cp -R "$DOCS_DIR/$lang/." "$STAGE_DIR/$lang/"
  sphinx-apidoc --force --module-first -o "$STAGE_DIR/$lang/api" "$SOURCE_DIR"
  if [[ ! -s "$STAGE_DIR/$lang/api/modules.rst" ]]; then
    echo "ERROR: API reference was not generated for $lang" >&2
    exit 1
  fi
done

# Follow the same three-build layout used by the other multilingual projects.
# The root is built from the actual English Sphinx source, not copied HTML.
DOC_LANGUAGE=en sphinx-build -b html -c "$DOCS_DIR" -D language=en "$STAGE_DIR/en" "$OUTPUT_DIR"
DOC_LANGUAGE=en sphinx-build -b html -c "$DOCS_DIR" -D language=en "$STAGE_DIR/en" "$OUTPUT_DIR/en"
DOC_LANGUAGE=ja sphinx-build -b html -c "$DOCS_DIR" -D language=ja "$STAGE_DIR/ja" "$OUTPUT_DIR/ja"

for page in index.html en/index.html ja/index.html api/modules.html en/api/modules.html ja/api/modules.html; do
  if [[ ! -f "$OUTPUT_DIR/$page" ]]; then
    echo "ERROR: expected HTML file is missing: $page" >&2
    exit 1
  fi
done
touch "$OUTPUT_DIR/.nojekyll"
