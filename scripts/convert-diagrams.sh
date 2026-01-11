#!/bin/bash
# Convert all HTML diagrams in a book's assets/ to SVG and PDF in build/bookname/assets/
set -euo pipefail

BOOK_DIR="$1"
BUILD_DIR="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ASSETS_DIR="$BOOK_DIR/assets"
BUILD_ASSETS="$BUILD_DIR/assets"

# Check if assets directory exists
if [ ! -d "$ASSETS_DIR" ]; then
    echo "No assets directory found in $BOOK_DIR"
    exit 0
fi

mkdir -p "$BUILD_ASSETS"

# Convert each HTML diagram to SVG, then to PDF for high-quality embedding
converted=0
for html_file in "$ASSETS_DIR"/*.html; do
    [ -e "$html_file" ] || continue

    filename=$(basename "$html_file" .html)
    svg_file="$BUILD_ASSETS/${filename}.svg"
    pdf_file="$BUILD_ASSETS/${filename}.pdf"

    echo "  Converting: $filename.html -> $filename.svg"

    if ! python3 "$SCRIPT_DIR/extract-svg.py" "$html_file" "$svg_file"; then
        echo "  Error: Failed to convert $filename.html" >&2
        exit 1
    fi

    # Convert SVG to PDF for crisp rendering in pdflatex (vector, not rasterized)
    if command -v rsvg-convert &> /dev/null; then
        rsvg-convert -f pdf -o "$pdf_file" "$svg_file" 2>/dev/null || true
    fi

    converted=$((converted + 1))
done

# Copy non-HTML assets as-is (images, etc.)
for asset in "$ASSETS_DIR"/*; do
    [ -e "$asset" ] || continue
    if [[ ! "$asset" =~ \.html$ ]]; then
        cp "$asset" "$BUILD_ASSETS/"
    fi
done

echo "  Converted $converted HTML diagram(s) to SVG"
