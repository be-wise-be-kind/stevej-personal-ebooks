#!/usr/bin/env python3
"""Extract SVG from HTML diagram file with CSS inlining.

Handles diagrams that use CSS classes by inlining the styles directly
onto SVG elements for standalone rendering.
"""
import sys
import re


def parse_css_rules(style_content: str) -> dict[str, str]:
    """Parse CSS rules from a style block into a dict of class -> properties."""
    rules = {}
    # Match .classname { properties }
    for match in re.finditer(r'\.([a-zA-Z0-9_-]+)\s*\{([^}]+)\}', style_content):
        class_name = match.group(1)
        properties = match.group(2).strip()
        # Clean up the properties (remove extra whitespace)
        properties = re.sub(r'\s+', ' ', properties)
        rules[class_name] = properties
    return rules


def inline_css_classes(svg_content: str, css_rules: dict[str, str]) -> str:
    """Replace class attributes with inline styles on SVG elements."""

    def replace_class(match):
        full_tag = match.group(0)
        class_attr_match = re.search(r'class="([^"]*)"', full_tag)
        if not class_attr_match:
            return full_tag

        class_names = class_attr_match.group(1).split()
        styles_to_add = []

        for class_name in class_names:
            if class_name in css_rules:
                styles_to_add.append(css_rules[class_name])

        if not styles_to_add:
            return full_tag

        # Combine all styles
        combined_style = '; '.join(styles_to_add)

        # Check if there's an existing style attribute
        existing_style_match = re.search(r'style="([^"]*)"', full_tag)
        if existing_style_match:
            existing_style = existing_style_match.group(1).rstrip(';')
            combined_style = existing_style + '; ' + combined_style
            # Replace existing style with combined
            full_tag = re.sub(r'style="[^"]*"', f'style="{combined_style}"', full_tag)
        else:
            # Add style attribute before the closing >
            full_tag = re.sub(r'(/?)>$', f' style="{combined_style}"\\1>', full_tag)

        # Remove class attribute
        full_tag = re.sub(r'\s*class="[^"]*"', '', full_tag)

        return full_tag

    # Match opening tags with class attribute (not self-closing for now, handle both)
    result = re.sub(r'<([a-zA-Z][a-zA-Z0-9]*)[^>]*class="[^"]*"[^>]*/?>',
                    replace_class, svg_content)
    return result


def extract_svg(html_path: str, output_path: str) -> None:
    """Extract SVG from HTML file, inlining CSS classes."""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract CSS rules from <style> tags
    css_rules = {}
    for style_match in re.finditer(r'<style[^>]*>(.*?)</style>', content, re.DOTALL):
        css_rules.update(parse_css_rules(style_match.group(1)))

    # Extract SVG element (including all content)
    svg_match = re.search(r'(<svg[^>]*>.*?</svg>)', content, re.DOTALL)
    if not svg_match:
        raise ValueError(f"No SVG found in {html_path}")

    svg = svg_match.group(1)

    # Inline CSS classes if there are any rules
    if css_rules:
        svg = inline_css_classes(svg, css_rules)

    # Ensure xmlns is present
    if 'xmlns=' not in svg:
        svg = svg.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"', 1)

    # Escape unescaped ampersands for valid XML
    # Match & not followed by amp; lt; gt; quot; apos; or #
    svg = re.sub(r'&(?!(amp|lt|gt|quot|apos|#);)', '&amp;', svg)

    # Replace web font stacks with standard fonts for rsvg-convert compatibility
    # This ensures text renders as vectors, not rasterized bitmaps
    # Handle font-family in attributes - need to match until closing quote of same type
    def replace_font_attr(match):
        return 'font-family="Liberation Sans, Arial, sans-serif"'

    # Match font-family="..." with double quotes (handles embedded single quotes)
    svg = re.sub(r'font-family="-apple-system[^"]*"', replace_font_attr, svg)
    # Match font-family='...' with single quotes (handles embedded double quotes)
    svg = re.sub(r"font-family='-apple-system[^']*'", replace_font_attr, svg)

    # Also handle font-family in style attributes
    svg = re.sub(
        r"font-family:\s*-apple-system[^;\"']*",
        'font-family: Liberation Sans, Arial, sans-serif',
        svg
    )

    # Add font-family to text elements that don't have one (they inherit from CSS which doesn't work in extracted SVG)
    def add_font_to_text(match):
        tag = match.group(0)
        if 'font-family=' not in tag:
            # Add font-family before the closing >
            return tag[:-1] + ' font-family="Liberation Sans, Arial, sans-serif">'
        return tag

    svg = re.sub(r'<text[^>]*>', add_font_to_text, svg)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(svg)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: extract-svg.py <input.html> <output.svg>", file=sys.stderr)
        sys.exit(1)

    try:
        extract_svg(sys.argv[1], sys.argv[2])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
