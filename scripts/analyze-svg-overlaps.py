#!/usr/bin/env python3
"""Analyze SVG files for potential visual issues like text overlap, clipping, etc."""

import sys
import re
import glob
from dataclasses import dataclass
from typing import List, Tuple, Optional
import xml.etree.ElementTree as ET

@dataclass
class BoundingBox:
    x: float
    y: float
    width: float
    height: float
    label: str

    def overlaps(self, other: 'BoundingBox') -> bool:
        """Check if two bounding boxes overlap."""
        return not (self.x + self.width < other.x or
                    other.x + other.width < self.x or
                    self.y + self.height < other.y or
                    other.y + other.height < self.y)

    def overlap_area(self, other: 'BoundingBox') -> float:
        """Calculate overlap area between two boxes."""
        if not self.overlaps(other):
            return 0
        x_overlap = max(0, min(self.x + self.width, other.x + other.width) - max(self.x, other.x))
        y_overlap = max(0, min(self.y + self.height, other.y + other.height) - max(self.y, other.y))
        return x_overlap * y_overlap

def parse_transform(transform: str) -> Tuple[float, float]:
    """Extract translate(x, y) values from transform attribute."""
    if not transform:
        return 0, 0
    match = re.search(r'translate\(([^,]+),?\s*([^)]*)\)', transform)
    if match:
        x = float(match.group(1))
        y = float(match.group(2)) if match.group(2) else 0
        return x, y
    return 0, 0

def get_text_bbox(elem, parent_transform: Tuple[float, float] = (0, 0)) -> Optional[BoundingBox]:
    """Estimate bounding box for a text element."""
    try:
        x = float(elem.get('x', 0)) + parent_transform[0]
        y = float(elem.get('y', 0)) + parent_transform[1]
        text = elem.text or ''

        # Estimate width based on font size and character count
        font_size = 12  # default
        fs_attr = elem.get('font-size', '')
        if fs_attr:
            try:
                font_size = float(fs_attr.replace('px', ''))
            except:
                pass

        # Rough estimate: each character is about 0.6 * font_size wide
        width = len(text) * font_size * 0.6
        height = font_size * 1.2

        # Adjust for text-anchor
        anchor = elem.get('text-anchor', 'start')
        if anchor == 'middle':
            x -= width / 2
        elif anchor == 'end':
            x -= width

        # Y is baseline, so adjust up
        y -= font_size * 0.8

        if width > 0 and text.strip():
            return BoundingBox(x, y, width, height, f"text: '{text[:30]}..'" if len(text) > 30 else f"text: '{text}'")
    except Exception as e:
        pass
    return None

def get_rect_bbox(elem, parent_transform: Tuple[float, float] = (0, 0)) -> Optional[BoundingBox]:
    """Get bounding box for a rect element."""
    try:
        x = float(elem.get('x', 0)) + parent_transform[0]
        y = float(elem.get('y', 0)) + parent_transform[1]
        width = float(elem.get('width', 0))
        height = float(elem.get('height', 0))
        if width > 0 and height > 0:
            return BoundingBox(x, y, width, height, f"rect({width}x{height})")
    except:
        pass
    return None

def analyze_svg(filepath: str) -> List[str]:
    """Analyze an SVG file for visual issues."""
    issues = []

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        return [f"XML parse error: {e}"]

    # Get viewBox dimensions
    viewbox = root.get('viewBox', '0 0 900 500')
    try:
        vb_parts = viewbox.split()
        vb_width = float(vb_parts[2])
        vb_height = float(vb_parts[3])
    except:
        vb_width, vb_height = 900, 500

    # Namespace handling
    ns = {'svg': 'http://www.w3.org/2000/svg'}

    # Collect all text elements with their bounding boxes
    text_boxes = []

    def process_element(elem, parent_transform=(0, 0)):
        # Get this element's transform
        transform = elem.get('transform', '')
        tx, ty = parse_transform(transform)
        current_transform = (parent_transform[0] + tx, parent_transform[1] + ty)

        # Handle text elements
        tag = elem.tag.replace('{http://www.w3.org/2000/svg}', '')
        if tag == 'text':
            bbox = get_text_bbox(elem, current_transform)
            if bbox:
                text_boxes.append(bbox)
                # Check if text is outside viewBox
                if bbox.x < -50 or bbox.x + bbox.width > vb_width + 50:
                    issues.append(f"Text possibly outside horizontal bounds: {bbox.label} at x={bbox.x:.0f}")
                if bbox.y < -50 or bbox.y + bbox.height > vb_height + 50:
                    issues.append(f"Text possibly outside vertical bounds: {bbox.label} at y={bbox.y:.0f}")

        # Recursively process children
        for child in elem:
            process_element(child, current_transform)

    process_element(root)

    # Check for text overlaps (only significant overlaps)
    for i, box1 in enumerate(text_boxes):
        for box2 in text_boxes[i+1:]:
            overlap = box1.overlap_area(box2)
            min_area = min(box1.width * box1.height, box2.width * box2.height)
            if min_area > 0 and overlap / min_area > 0.3:  # More than 30% overlap
                issues.append(f"Significant text overlap: {box1.label} and {box2.label}")

    return issues

def main():
    if len(sys.argv) < 2:
        print("Usage: analyze-svg-overlaps.py <glob-pattern>")
        print("Example: analyze-svg-overlaps.py 'build/api-optimization/assets/*.svg'")
        sys.exit(1)

    pattern = sys.argv[1]
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"No files found matching: {pattern}")
        sys.exit(1)

    print(f"Analyzing {len(files)} SVG files...\n")

    total_issues = 0
    for filepath in files:
        issues = analyze_svg(filepath)
        if issues:
            filename = filepath.split('/')[-1]
            print(f"=== {filename} ===")
            for issue in issues:
                print(f"  - {issue}")
            print()
            total_issues += len(issues)

    if total_issues == 0:
        print("No significant issues detected!")
    else:
        print(f"\nTotal issues found: {total_issues}")

if __name__ == '__main__':
    main()
