#!/usr/bin/env python3
"""Fix HTML diagram lint violations.

Fixes:
1. CSS class attributes on SVG elements -> inline styles
2. h1-h6 titles outside SVG -> move into SVG as <text> element
"""
import sys
import re
import glob


def parse_css_rules(style_content: str) -> dict[str, str]:
    """Parse CSS rules from a style block into a dict of class -> properties."""
    rules = {}
    for match in re.finditer(r'\.([a-zA-Z0-9_-]+)\s*\{([^}]+)\}', style_content):
        class_name = match.group(1)
        properties = match.group(2).strip()
        properties = re.sub(r'\s+', ' ', properties)
        rules[class_name] = properties
    return rules


def inline_css_in_svg(content: str, css_rules: dict[str, str]) -> str:
    """Inline CSS classes on SVG elements."""

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

        combined_style = '; '.join(styles_to_add)

        existing_style_match = re.search(r'style="([^"]*)"', full_tag)
        if existing_style_match:
            existing_style = existing_style_match.group(1).rstrip(';')
            combined_style = existing_style + '; ' + combined_style
            full_tag = re.sub(r'style="[^"]*"', f'style="{combined_style}"', full_tag)
        else:
            full_tag = re.sub(r'(/?)>$', f' style="{combined_style}"\\1>', full_tag)

        full_tag = re.sub(r'\s*class="[^"]*"', '', full_tag)
        return full_tag

    # Find SVG content
    svg_match = re.search(r'(<svg[^>]*>)(.*?)(</svg>)', content, re.DOTALL)
    if not svg_match:
        return content

    svg_open = svg_match.group(1)
    svg_inner = svg_match.group(2)
    svg_close = svg_match.group(3)

    # Replace class attributes in SVG inner content
    svg_inner_fixed = re.sub(r'<([a-zA-Z][a-zA-Z0-9]*)[^>]*class="[^"]*"[^>]*/?>',
                              replace_class, svg_inner)

    # Reconstruct
    new_svg = svg_open + svg_inner_fixed + svg_close
    return content[:svg_match.start()] + new_svg + content[svg_match.end():]


def move_title_into_svg(content: str) -> str:
    """Move h1-h6 title from outside SVG into SVG as text element."""

    # Find h2 (or h1-h6) in diagram-container but outside SVG
    container_match = re.search(
        r'(<div[^>]*class="diagram-container"[^>]*>)(.*?)(</div>)',
        content, re.DOTALL
    )
    if not container_match:
        return content

    container_open = container_match.group(1)
    container_inner = container_match.group(2)
    container_close = container_match.group(3)

    # Find title element
    title_match = re.search(r'<h([1-6])[^>]*>(.*?)</h\1>', container_inner, re.DOTALL)
    if not title_match:
        return content

    title_text = title_match.group(2).strip()
    # Remove any HTML tags from title
    title_text = re.sub(r'<[^>]+>', '', title_text)

    # Find SVG
    svg_match = re.search(r'(<svg[^>]*>)(.*?)(</svg>)', container_inner, re.DOTALL)
    if not svg_match:
        return content

    svg_open = svg_match.group(1)
    svg_inner = svg_match.group(2)
    svg_close = svg_match.group(3)

    # Get viewBox to determine title position
    viewbox_match = re.search(r'viewBox="([^"]*)"', svg_open)
    if viewbox_match:
        viewbox = viewbox_match.group(1).split()
        if len(viewbox) >= 4:
            width = float(viewbox[2])
            x_center = width / 2
        else:
            x_center = 400
    else:
        x_center = 400

    # Create title text element
    title_svg = f'''
            <!-- Title -->
            <text x="{x_center}" y="30" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="600" fill="#1e293b">{title_text}</text>
'''

    # Check if SVG already has a title-like text at y="30" or similar
    if re.search(r'<text[^>]*y="3[0-5]"[^>]*>.*?</text>', svg_inner):
        # Already has a title, don't add another
        title_svg = ''

    # Insert title at beginning of SVG content
    new_svg_inner = title_svg + svg_inner
    new_svg = svg_open + new_svg_inner + svg_close

    # Remove the h1-h6 from container
    new_container_inner = container_inner[:title_match.start()] + container_inner[title_match.end():]
    # Update SVG in container
    new_container_inner = re.sub(r'<svg[^>]*>.*?</svg>', new_svg, new_container_inner, flags=re.DOTALL)

    new_container = container_open + new_container_inner + container_close

    return content[:container_match.start()] + new_container + content[container_match.end():]


def fix_file(path: str) -> tuple[bool, list[str]]:
    """Fix violations in a file. Returns (modified, fixes_applied)."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    fixes = []

    # Parse CSS rules
    css_rules = {}
    for style_match in re.finditer(r'<style[^>]*>(.*?)</style>', content, re.DOTALL):
        css_rules.update(parse_css_rules(style_match.group(1)))

    # Check for CSS class violations in SVG
    svg_match = re.search(r'<svg[^>]*>.*?</svg>', content, re.DOTALL)
    if svg_match:
        svg_content = svg_match.group(0)
        inner_svg = re.sub(r'^<svg[^>]*>', '', svg_content)
        if re.search(r'<[^>]+\sclass=', inner_svg) and css_rules:
            content = inline_css_in_svg(content, css_rules)
            fixes.append("Inlined CSS classes on SVG elements")

    # Check for title outside SVG
    container_match = re.search(
        r'<div[^>]*class="diagram-container"[^>]*>(.*?)</div>',
        content, re.DOTALL
    )
    if container_match:
        container = container_match.group(1)
        svg_in_container = re.search(r'<svg.*?</svg>', container, re.DOTALL)
        if svg_in_container:
            outside_svg = container.replace(svg_in_container.group(0), '')
            if re.search(r'<h[1-6][^>]*>', outside_svg):
                content = move_title_into_svg(content)
                fixes.append("Moved title into SVG")

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, fixes

    return False, []


def main():
    if len(sys.argv) < 2:
        print("Usage: fix-html-diagrams.py <path-or-glob>")
        sys.exit(1)

    pattern = sys.argv[1]
    files = glob.glob(pattern, recursive=True)

    if not files:
        print(f"No files found matching: {pattern}")
        sys.exit(1)

    total_fixed = 0
    for path in sorted(files):
        modified, fixes = fix_file(path)
        if modified:
            print(f"Fixed: {path}")
            for fix in fixes:
                print(f"  - {fix}")
            total_fixed += 1

    if total_fixed:
        print(f"\nFixed {total_fixed} file(s)")
    else:
        print("No files needed fixing")


if __name__ == '__main__':
    main()
