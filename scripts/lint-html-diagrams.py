#!/usr/bin/env python3
"""Lint HTML diagrams for rule compliance.

Rules checked:
1. Must have SVG element
2. No external titles (h1-h6 outside SVG in diagram-container)
3. No CSS class attributes on SVG child elements (use inline styles)
4. viewBox attribute required on SVG
5. No web fonts in SVG (use Liberation Sans, Arial, or sans-serif)
6. All text elements must have explicit font-family attribute
7. Minimum 50px gap between title and first content element
"""

# Minimum gap in pixels between title text and first content element
MIN_TITLE_GAP = 50

# Web fonts that don't render correctly in PDF extraction
DISALLOWED_FONTS = [
    '-apple-system',
    'BlinkMacSystemFont',
    'Segoe UI',
    'Roboto',
    'Oxygen',
    'Ubuntu',
    'Cantarell',
    'Fira Sans',
    'Droid Sans',
    'Helvetica Neue',
]
import sys
import re
import glob


def get_element_y(element_str: str) -> float | None:
    """Extract y coordinate from an SVG element string.

    Handles both direct y= attributes and transform="translate(x, y)" attributes.
    Returns None if no y coordinate can be determined.
    """
    # Try direct y attribute
    y_match = re.search(r'\by="([0-9.]+)"', element_str)
    if y_match:
        return float(y_match.group(1))

    # Try y1 attribute (for lines)
    y1_match = re.search(r'\by1="([0-9.]+)"', element_str)
    if y1_match:
        return float(y1_match.group(1))

    # Try cy attribute (for circles/ellipses)
    cy_match = re.search(r'\bcy="([0-9.]+)"', element_str)
    if cy_match:
        return float(cy_match.group(1))

    # Try transform translate
    translate_match = re.search(r'transform="translate\(([0-9.]+),?\s*([0-9.]+)\)"', element_str)
    if translate_match:
        return float(translate_match.group(2))

    return None


def check_title_spacing(svg_content: str) -> str | None:
    """Check that there's adequate spacing between title and content.

    Returns error message if spacing is insufficient, None otherwise.
    """
    # Find title text element (first text with font-size >= 17 and y < 60)
    text_elements = re.findall(r'<text\s+[^>]*>', svg_content)

    title_y = None
    for text_el in text_elements:
        y = get_element_y(text_el)
        if y is None or y > 60:  # Title should be near top
            continue

        # Check font-size
        size_match = re.search(r'font-size="?([0-9.]+)"?', text_el)
        if size_match:
            size = float(size_match.group(1))
            if size >= 17:  # Title font size threshold
                title_y = y
                break

    if title_y is None:
        return None  # No title found, skip check

    # Find first content element after title (excluding defs, text near title)
    # Look for rect, line, circle, ellipse, path, g with transform
    content_elements = re.findall(
        r'<(rect|line|circle|ellipse|path|polygon)\s+[^>]*>|<g\s+transform="translate[^>]*>',
        svg_content
    )

    first_content_y = None
    for el in content_elements:
        y = get_element_y(el)
        if y is None:
            continue
        # Must be below title area (y > 40) to be considered content
        if y > 40:
            if first_content_y is None or y < first_content_y:
                first_content_y = y

    if first_content_y is None:
        return None  # No content elements found

    gap = first_content_y - title_y
    if gap < MIN_TITLE_GAP:
        return (
            f"Insufficient spacing after title: {gap:.0f}px "
            f"(minimum {MIN_TITLE_GAP}px). Title at y={title_y:.0f}, "
            f"first content at y={first_content_y:.0f}"
        )

    return None


def lint_file(path: str) -> list[str]:
    """Return list of violations for a file."""
    errors = []
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Rule 1: Must have SVG element
    if not re.search(r'<svg[^>]*>', content):
        errors.append("Missing <svg> element")
        return errors  # Can't check other rules without SVG

    # Rule 2: No external titles (h1-h6 outside SVG)
    # Check for headings in diagram-container but outside svg
    container_match = re.search(
        r'<div[^>]*class="diagram-container"[^>]*>(.*?)</div>',
        content, re.DOTALL
    )
    if container_match:
        container = container_match.group(1)
        svg_match = re.search(r'<svg.*?</svg>', container, re.DOTALL)
        if svg_match:
            outside_svg = container.replace(svg_match.group(0), '')
            if re.search(r'<h[1-6][^>]*>', outside_svg):
                errors.append("Title element (h1-h6) found outside SVG - move into SVG as <text>")

    # Rule 3: Check for CSS class usage on SVG elements
    svg_match = re.search(r'<svg[^>]*>.*?</svg>', content, re.DOTALL)
    if svg_match:
        svg_content = svg_match.group(0)
        # Find elements with class= inside SVG (excluding the svg tag itself)
        inner_svg = re.sub(r'^<svg[^>]*>', '', svg_content)
        if re.search(r'<[^>]+\sclass=', inner_svg):
            errors.append("CSS class attribute found on SVG child element - use inline styles")

    # Rule 4: viewBox required
    if not re.search(r'<svg[^>]*viewBox=', content):
        errors.append("Missing viewBox attribute on <svg>")

    # Rule 5: No web fonts in SVG (they don't render correctly in PDF)
    svg_match = re.search(r'<svg[^>]*>.*?</svg>', content, re.DOTALL)
    if svg_match:
        svg_content = svg_match.group(0)
        for font in DISALLOWED_FONTS:
            if font.lower() in svg_content.lower():
                errors.append(
                    f"Web font '{font}' found in SVG - use 'Liberation Sans, Arial, sans-serif' instead"
                )
                break  # Only report once per file

    # Rule 6: All text elements must have explicit font-family
    svg_match = re.search(r'<svg[^>]*>.*?</svg>', content, re.DOTALL)
    if svg_match:
        svg_content = svg_match.group(0)
        # Find all text elements
        text_elements = re.findall(r'<text\s+[^>]*>', svg_content)
        missing_font = 0
        for text_el in text_elements:
            if 'font-family=' not in text_el:
                missing_font += 1
        if missing_font > 0:
            errors.append(
                f"{missing_font} <text> element(s) missing font-family attribute"
            )

    # Rule 7: Minimum title spacing
    svg_match = re.search(r'<svg[^>]*>.*?</svg>', content, re.DOTALL)
    if svg_match:
        svg_content = svg_match.group(0)
        spacing_error = check_title_spacing(svg_content)
        if spacing_error:
            errors.append(spacing_error)

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: lint-html-diagrams.py <path-or-glob>")
        sys.exit(1)

    pattern = sys.argv[1]
    files = glob.glob(pattern, recursive=True)

    if not files:
        print(f"No files found matching: {pattern}")
        sys.exit(1)

    total_errors = 0
    for path in sorted(files):
        errors = lint_file(path)
        if errors:
            print(f"\n{path}:")
            for err in errors:
                print(f"  - {err}")
            total_errors += len(errors)

    if total_errors:
        print(f"\n{total_errors} violation(s) found in {len(files)} file(s)")
        sys.exit(1)
    else:
        print(f"All {len(files)} HTML diagram(s) pass lint checks")
        sys.exit(0)


if __name__ == '__main__':
    main()
