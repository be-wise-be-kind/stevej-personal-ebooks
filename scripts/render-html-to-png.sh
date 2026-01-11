#!/bin/bash
# Render an HTML diagram to PNG for visual inspection
# Usage: render-html-to-png.sh <input.html> <output.png>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_HTML="$1"
OUTPUT_PNG="$2"

# Create temp SVG
TEMP_SVG=$(mktemp --suffix=.svg)
trap "rm -f $TEMP_SVG" EXIT

# Extract SVG from HTML
python3 "$SCRIPT_DIR/extract-svg.py" "$INPUT_HTML" "$TEMP_SVG"

# Convert SVG to PNG (width 1000px, height auto)
rsvg-convert -w 1000 -o "$OUTPUT_PNG" "$TEMP_SVG"

echo "Rendered: $OUTPUT_PNG"
