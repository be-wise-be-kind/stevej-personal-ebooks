#!/bin/bash
# Preprocess chapters: copy to build dir and update .html references
set -euo pipefail

BOOK_DIR="$1"
BUILD_DIR="$2"
FORMAT="${3:-pdf}"  # Default to pdf if not specified

CHAPTERS_DIR="$BOOK_DIR/chapters"
BUILD_CHAPTERS="$BUILD_DIR/chapters"

# Check if chapters directory exists
if [ ! -d "$CHAPTERS_DIR" ]; then
    echo "Error: No chapters directory found in $BOOK_DIR" >&2
    exit 1
fi

# Clean old chapters to prevent stale files from accumulating
rm -rf "$BUILD_CHAPTERS"
mkdir -p "$BUILD_CHAPTERS"

# Determine target extension based on format
case "$FORMAT" in
    pdf)
        TARGET_EXT="pdf"
        ;;
    html|epub)
        TARGET_EXT="svg"
        ;;
    *)
        TARGET_EXT="svg"
        ;;
esac

processed=0
for chapter in "$CHAPTERS_DIR"/*.md; do
    [ -e "$chapter" ] || continue

    filename=$(basename "$chapter")
    output="$BUILD_CHAPTERS/$filename"

    # Preprocess chapter content:
    # 1. Replace .html references with target format (.pdf for PDF, .svg for HTML/EPUB)
    # 2. Strip "Chapter N: " prefix from H1 (pandoc adds chapter numbers)
    sed -e "s|\(!\[.*\](\.\./assets/[^)]*\)\.html)|\1.${TARGET_EXT})|g" \
        -e 's|^# Chapter [0-9]*: |# |' \
        "$chapter" > "$output"

    processed=$((processed + 1))
done

echo "  Preprocessed $processed chapter(s)"
