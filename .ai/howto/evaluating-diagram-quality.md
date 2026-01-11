# How to Evaluate Diagram Quality

When reviewing SVG/HTML diagrams rendered as images, systematically check for these visual issues.

## 1. Spacing and Breathing Room

### Container Margins
- **Edge padding**: All content should have at least 20-30px padding from container edges
- **Bottom margin**: Especially important - elements touching the bottom edge look cramped
- **Side margins**: Text and boxes should not touch left/right edges

### Object Spacing
- **Between boxes**: Minimum 15-20px gap between adjacent elements
- **Text to box edges**: Text inside boxes needs 15-20px padding from box borders (especially left edge for bulleted lists)
- **Labels to objects**: Annotation labels should have clear separation from the objects they describe
- **Leading characters**: Bullet points, +/- symbols, numbers at start of lines need extra left padding to not get clipped

## 2. Text Issues

### Overlap Problems
- **Text crossing other text**: Any text overlapping other text is a critical issue
- **Text crossing lines/shapes**: Lines or shapes should not cross through text (like a strikethrough effect)
- **Labels overlapping boxes**: Annotation boxes should not overlap each other

### Truncation/Cutoff
- **Partial words**: Look for words cut off mid-word ("Cascading failu" instead of "Cascading failure")
- **Clipped characters**: Characters partially visible at edges
- **Missing text**: Compare against expected content

### Readability
- **Font size**: Text should be readable at normal viewing size
- **Contrast**: Text color should contrast sufficiently with background
- **Crowded text**: Multiple lines of text shouldn't be cramped together

## 3. Layout Problems

### Crowding
- **Stacked elements**: Elements piled on top of each other
- **Tight clusters**: Too many elements in a small area
- **No visual hierarchy**: Everything competing for attention equally

### Alignment
- **Misaligned elements**: Items that should line up but don't
- **Inconsistent spacing**: Uneven gaps between similar elements
- **Off-center text**: Text that should be centered but isn't

## 4. SVG Layering / Z-Order

### Critical: SVG Render Order
- **Elements render in document order**: Later elements appear ON TOP of earlier elements
- **Lines crossing through text**: Usually caused by connection lines drawn AFTER boxes
- **Fix**: Move all connection/arrow definitions BEFORE box definitions in the SVG

### Correct SVG Structure
```xml
<!-- 1. Definitions (markers, gradients, filters) -->
<defs>...</defs>

<!-- 2. Background elements -->
<rect class="background"/>

<!-- 3. CONNECTION LINES (drawn first, render underneath) -->
<line class="connection"/>
<path class="arrow"/>

<!-- 4. BOXES AND TEXT (drawn last, render on top) -->
<rect class="box"/>
<text class="label"/>
```

### Common Mistake
```xml
<!-- WRONG: Lines drawn after boxes = lines ON TOP of boxes -->
<rect>Box</rect>
<line>Connection</line>  <!-- This crosses through the box! -->
```

## 5. Visual Artifacts

### Rendering Issues
- **Black fills**: Unexpected black areas (often from missing `fill="none"` on paths)
- **Missing elements**: Expected content not appearing
- **Wrong colors**: Elements appearing in unexpected colors
- **Broken gradients**: Gradients not rendering properly

### Path Problems
- **Disconnected lines**: Arrow paths not connecting properly
- **Overlapping paths**: Lines crossing when they shouldn't
- **Arrow direction**: Arrows pointing wrong direction

## 5. Boundary Checks

### ViewBox Issues
- **Content outside viewBox**: Elements positioned outside visible area
- **Too small viewBox**: Content cramped because viewBox is too restrictive
- **Aspect ratio**: ViewBox dimensions appropriate for content

### Clipping
- **Elements at edges**: Anything touching or crossing container boundaries
- **Partial visibility**: Elements only partially visible

## CRITICAL: Commonly Missed Issues

These issues are frequently overlooked during audits. Pay special attention:

### 1. Internal Legend Padding
- Legend boxes must have **30px minimum internal padding** from all edges
- Text and colored squares inside legends should NOT touch the legend box border
- Common mistake: placing legend items at x=10-15 when they need x=25-30

### 2. Stacked Element Spacing
- When boxes/bars are stacked vertically, there must be **40-50px minimum gap** between them
- This applies to: timeline bars below process boxes, legends below diagrams, info boxes below flowcharts
- The gap should be visually obvious - if elements look "close" they ARE too close
- Common mistake: grace period bars, timeline indicators placed too close to content above

### 3. Text Overlap in Sequence Diagrams
- When multiple labels appear on parallel paths, verify EACH label for overlap
- Check labels at: branch points, merge points, annotation positions
- Render at multiple zoom levels - overlaps may only be visible at certain scales
- Common mistake: "Hedge sent" labels overlapping "Primary Request (slow)" labels

### 4. Box-Internal Text Centering
- Text inside circular/rounded elements is often clipped or off-center
- Circle text: verify the FULL text fits within the circle radius
- Round-rect text: ensure text doesn't touch any edge
- Common mistake: timeline circles with text like "Implementation" getting cut off

### 5. PDF vs PNG Rendering Differences
- Always check BOTH the PNG render AND the final PDF
- PDF scaling can reveal issues not visible in PNG
- Tight spacing that "looks ok" in PNG may collide in PDF
- Common mistake: assuming PNG render is sufficient

### 6. Double/Parallel Line Effects
- When forward arrows and return arrows are close together, they create a "double line" visual
- This is especially problematic in sequence diagrams and flow charts showing request/response
- **Minimum separation**: 20px between parallel forward and return arrows
- **Better approach**: Use distinctly different arrow styles (solid vs dashed) AND spatial separation
- Common mistake: forward arrow at y=110, return arrow at y=118 (only 8px apart)

## Evaluation Checklist

When reviewing each diagram, check:

```
[ ] All text fully visible (no truncation)
[ ] No text overlapping other text
[ ] No lines crossing through text (SVG z-order issue)
[ ] Adequate padding from all edges (especially bottom)
[ ] Annotation boxes don't overlap each other
[ ] Clear spacing between all elements (40-50px between stacked sections)
[ ] Text has breathing room inside boxes
[ ] No unexpected black fills or artifacts
[ ] Arrows/lines connect properly
[ ] Overall layout is balanced and uncluttered
[ ] Diagram content matches chapter/section topic
[ ] SVG structure: connections before boxes (for proper layering)
[ ] Legends have adequate clearance from content above (25-30px)
[ ] Legend internal padding from box edges (30px minimum)
[ ] All arrows have visible line bodies (not just arrowheads, min 15-20px)
[ ] No empty boxes that should have labels
[ ] No duplicate/double lines
[ ] Labels clearly associated with their elements (proper spacing)
[ ] Stacked timeline/bar elements have 40-50px gap from content above
[ ] Text in circles/rounded boxes fits completely within bounds
[ ] Forward/return arrow pairs separated by at least 20px (no double-line effect)
```

## Common Fixes

| Issue | Solution |
|-------|----------|
| Content touching edge | Increase viewBox dimensions, add padding |
| Text cutoff | Widen viewBox or move element inward |
| Overlapping labels | Reposition labels, increase spacing |
| Lines crossing through boxes | Move connection lines BEFORE boxes in SVG document order |
| Text through line | Move line or text, adjust path |
| Crowded layout | Increase viewBox, spread elements out |
| Black fill artifact | Add `fill="none"` to path elements |
| Legend too close to content | Shift legend down, increase viewBox height if needed |
| Arrow too short | Extend arrow path, ensure min 15-20px line before arrowhead |
| Empty box | Add missing label text or remove box if unneeded |
| Double/duplicate lines | Remove duplicate path/line elements from SVG |
| Label too close to wrong element | Reposition label closer to its intended element |

## 6. Legend and Connection Issues

### Legend Positioning
- **Legend collision**: Legends must not touch or overlap diagram content above them
- **Minimum clearance**: 25-30px between legend and nearest element above
- **Bottom padding**: Legends need adequate space below them to the viewBox edge (15-20px)
- **Fix**: Shift legend down, increase viewBox height if needed

### Malformed Arrows
- **Arrow too short**: Arrows must have a visible line body, not just an arrowhead
- **Minimum line length**: 15-20px of visible line before the arrowhead
- **Connection clarity**: Arrows should clearly connect source to destination
- **Fix**: Extend arrow path, ensure marker-end is positioned after adequate line length

### Empty/Missing Text
- **Placeholder boxes**: Boxes that appear in the diagram must have a purpose
- **Missing labels**: Every visible box/shape should contain text or be clearly decorative
- **Fix**: Add missing label text or remove unnecessary placeholder elements

### Duplicate Lines
- **Double rendering**: Lines appearing twice (visible doubling/ghosting)
- **Overlapping paths**: Identical paths layered on top of each other
- **Check source**: Look for duplicate `<line>` or `<path>` elements with same coordinates
- **Fix**: Remove duplicate path/line elements from SVG source

### Element Proximity
- **Label association**: Labels should be clearly associated with their elements
- **Minimum spacing**: 15px between unrelated elements (labels shouldn't appear to belong to wrong box)
- **Floating labels**: Text that appears disconnected or associated with wrong elements
- **Fix**: Reposition labels closer to their intended elements, increase spacing from unrelated elements

## 7. Content Matching

### Verify Diagram Matches Context
- **Chapter opener**: Does the diagram title match the chapter title/theme?
- **Section relevance**: Does the diagram illustrate the concept being discussed?
- **Correct file**: Is this the right diagram file for this location?
- **Title accuracy**: Does the diagram title match what the diagram shows?

### Common Mismatches
- Wrong opener image for a chapter
- Diagram copied from another chapter without updating title
- Generic diagram that doesn't match specific section content

## Testing Process

### Single Diagram Testing
1. Render HTML to SVG: `python3 scripts/extract-svg.py input.html output.svg`
2. Convert to PNG: `rsvg-convert -w 1000 -o output.png output.svg`
3. View PNG and evaluate against checklist
4. Fix issues in source HTML
5. Re-render and verify fix
6. Repeat until all issues resolved

### Bulk Diagram Auditing (Use Parallel Agents)

For reviewing many diagrams efficiently, use parallel Task agents:

```
Launch multiple agents in parallel:
- Agent 1: Review ch01-ch04 diagrams
- Agent 2: Review ch05-ch08 diagrams
- Agent 3: Review ch09-ch12 diagrams
- Agent 4: Review ch13-ch16 diagrams
```

Each agent should:
1. Render all diagrams in their assigned range to PNG
2. Visually inspect each PNG against the evaluation checklist
3. Report ONLY diagrams with issues (file path + specific problem)
4. Be thorough - check spacing, text, overlaps, edges, content matching

For fixes, also use parallel agents:
```
Launch fix agents in parallel:
- Agent 1: Fix diagram-a.html (specific issue description)
- Agent 2: Fix diagram-b.html (specific issue description)
- Agent 3: Fix diagram-c.html (specific issue description)
```

Each fix agent should:
1. Read the source HTML
2. Make the fix
3. Render to PNG
4. Verify the fix visually
5. Report completion or remaining issues
