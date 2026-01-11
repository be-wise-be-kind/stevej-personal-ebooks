# How to Make HTML Diagrams (SVG)

Best practices and lessons learned from creating diagrams for technical ebooks.

---

## Getting Started

**Always start with the template:** Copy `.ai/templates/html-diagram.html` as your starting point. This ensures consistent styling and linter compliance.

```bash
cp .ai/templates/html-diagram.html ebooks/<book>/assets/ch01-my-diagram.html
```

**Run the linter before committing:**
```bash
just lint html <bookname>
```

---

## Linter Rules (Required)

The HTML diagram linter (`just lint html`) enforces these rules:

| Rule | Requirement |
|------|-------------|
| SVG Required | File must contain an `<svg>` element |
| No External Titles | No `<h1>`-`<h6>` tags outside SVG - use `<text>` inside SVG |
| No CSS Classes | No `class=` attributes on SVG child elements - use inline styles |
| ViewBox Required | SVG must have a `viewBox` attribute |

### Why These Rules?
- **No external titles**: SVG diagrams are embedded in PDFs/EPUBs - external HTML elements don't convert properly
- **No CSS classes**: Inline styles survive conversion to other formats; external CSS may be lost
- **ViewBox required**: Ensures diagrams scale correctly across different output sizes

### What the Linter Can't Check:
These require visual inspection (see checklist below):
- Panel content overflow (content exceeding panel bounds)
- Text overflow from containers (boxes, badges, legends)
- Text/line overlaps
- Annotations overlapping centered titles
- Element spacing and padding
- Font size legibility

---

## 1. ViewBox Sizing

The viewBox defines the coordinate system: `viewBox="0 0 WIDTH HEIGHT"`

### Rules:
- **Calculate total content height**: All elements must fit within viewBox dimensions
- **Add padding**: Leave 20-30px margin at edges for visual breathing room
- **Account for transforms**: Parent transforms add to child element positions

### Common Mistake:
```html
<!-- BAD: Content extends beyond viewBox -->
<svg viewBox="0 0 800 520">
  <g transform="translate(300, 330)">
    <rect y="165" height="60"/>  <!-- Bottom: 330 + 165 + 60 = 555 > 520! -->
  </g>
</svg>
```

### Fix:
```html
<!-- GOOD: Increase viewBox or reposition content -->
<svg viewBox="0 0 800 580">  <!-- Increased height -->
```

---

## 2. Transform Coordinate Math

When using nested transforms, calculate absolute positions:

```
Absolute Y = parent_transform_y + element_y + element_height
```

### Example Analysis:
```html
<svg viewBox="0 0 900 600">
  <g transform="translate(455, 320)">      <!-- Parent Y: 320 -->
    <rect height="240"/>                    <!-- Panel ends: 320 + 240 = 560 -->
    <g transform="translate(30, 60)">       <!-- Inner Y: 320 + 60 = 380 -->
      <g transform="translate(0, 165)">     <!-- Gauge Y: 380 + 165 = 545 -->
        <rect y="10" height="20"/>          <!-- Bottom: 545 + 10 + 20 = 575 -->
      </g>
    </g>
  </g>
</svg>
```

**Issue**: Content at y=575 overflows panel (ends at 560) and conflicts with legend at y=575.

---

## 3. Minimum Font Sizes

| Context | Minimum Size | Recommended |
|---------|--------------|-------------|
| Primary labels | 10px | 11-14px |
| Secondary labels | 9px | 10-12px |
| Axis tick labels | 9px | 10-11px |
| Annotation text | 10px | 11-12px |
| Titles | 14px | 16-24px |

### Never Use:
- 8px or smaller (illegible at normal zoom)
- Inconsistent sizes for same-level elements

---

## 4. Annotation Placement

Annotations (callout boxes, labels with leader lines) need careful positioning.

### Rules:
1. **No overlapping boxes**: Calculate bounding boxes and ensure separation
2. **Minimum separation**: 10-15px between annotation boxes
3. **Clear leader lines**: Lines should not cross other annotations
4. **Consistent positioning**: Similar annotations should follow patterns

### Overlap Detection Formula:
```
Box A: (x1, y1) to (x1 + width, y1 + height)
Box B: (x2, y2) to (x2 + width, y2 + height)

Overlap if:
  x1 < x2 + width2 AND x1 + width1 > x2 AND
  y1 < y2 + height2 AND y1 + height1 > y2
```

### Common Fix Strategies:
1. Move one annotation to opposite side of the data point
2. Stack annotations vertically with clear separation
3. Use shorter leader lines
4. Reduce annotation box size

---

## 5. Title Spacing (Critical)

Titles MUST have adequate space between them and the diagram content below.

### Rules:
- **Title position**: y=30-35 (from top of viewBox)
- **Content start**: y=80 minimum (main diagram content)
- **Minimum gap**: 25-30px between title bottom and first diagram element

### Template Pattern:
```html
<!-- Title at y=35 -->
<text x="450" y="35" text-anchor="middle" font-size="20">Diagram Title</text>

<!-- Optional subtitle at y=55 -->
<text x="450" y="55" font-size="12">Subtitle here</text>

<!-- Content starts at y=80, giving 25px gap from subtitle or 45px from title -->
<g transform="translate(50, 80)">
    <!-- Main diagram content here -->
</g>
```

### Common Mistake:
```html
<!-- BAD: Title at y=28, content at y=60 = only 14px gap -->
<text y="28">Title</text>
<g transform="translate(50, 60)">  <!-- Too close to title! -->
```

### Fix:
```html
<!-- GOOD: Title at y=35, content at y=80 = proper spacing -->
<text y="35">Title</text>
<g transform="translate(50, 80)">  <!-- 25px+ gap -->
```

---

## 6. Border and Edge Padding

Content near viewBox edges looks cramped and may clip on some renderers.

### Rules:
- **Minimum edge padding**: 15-20px from viewBox boundaries
- **Legend/footer padding**: 25-30px from bottom edge
- **Title padding**: 20px from top edge

### Example:
```html
<!-- BAD: Box too close to bottom -->
<svg viewBox="0 0 900 600">
  <rect y="570" height="40"/>  <!-- Only 590-600, clips at edge -->
</svg>

<!-- GOOD: Adequate padding -->
<svg viewBox="0 0 900 620">    <!-- Increase viewBox -->
  <rect y="570" height="40"/>  <!-- Now 10px padding at bottom -->
</svg>
```

---

## 6. Panel Content Overflow

When using panel containers with inner content, ensure content fits.

### Calculation:
```
Panel top = panel_transform_y
Panel bottom = panel_transform_y + panel_height

Content must satisfy:
  content_transform_y + content_element_y + content_height <= Panel bottom
```

### Fix Options:
1. Increase panel height
2. Move inner content up (reduce transform Y)
3. Reduce content element sizes
4. Restructure content layout

---

## 7. Lines and Text Overlap

Dashed lines, grid lines, and marker lines can inadvertently cross over text labels.

### Rules:
- **Calculate text bounding box**: Text with `text-anchor="middle"` extends ~half its width in each direction
- **Position lines away from text**: Ensure vertical/horizontal lines don't pass through label areas
- **Consider text width**: A label like "99 requests @ 10ms" at x=45 might span x=15 to x=75

### Example Problem:
```html
<!-- BAD: Line at x=60 passes through text centered at x=45 -->
<text x="45" text-anchor="middle">99 requests @ 10ms</text>
<line x1="60" y1="0" x2="60" y2="100"/>  <!-- Crosses the text! -->
```

### Fix:
```html
<!-- GOOD: Move line further right to clear the text -->
<text x="45" text-anchor="middle">99 requests @ 10ms</text>
<line x1="125" y1="0" x2="125" y2="100"/>  <!-- Clear of text -->
```

---

## 8. Labels vs Titles Overlap

When placing labels above chart elements (like percentile markers), ensure they don't overlap with section titles.

### The Problem:
```html
<g transform="translate(50, 310)">
  <!-- Title at y=30 → absolute y=340 -->
  <text y="30">Chart Title</text>

  <g transform="translate(70, 50)">
    <!-- Label at y=-15 → absolute y=310+50-15=345 -->
    <text y="-15">210ms</text>  <!-- Overlaps with title! -->
  </g>
</g>
```

### Solution:
Move labels down (increase y value) or move the chart area down to create clearance:

```html
<g transform="translate(70, 50)">
  <!-- Label at y=0 → absolute y=360, clear of title at y=340 -->
  <text y="0">210ms</text>
  <!-- Also move the marker badge down -->
  <rect y="10" height="20"/>
  <line y1="15" y2="200"/>
</g>
```

### Rule of Thumb:
- Chart titles need 25-30px clearance below them
- Labels above data points should not extend into title space
- Calculate: `title_y + title_font_size + 10 < label_absolute_y`

---

## 9. Inner Panel Padding

Content within bordered panels needs adequate padding from panel edges.

### Rules:
- **Minimum inner padding**: 20px from panel edges
- **Right-side content**: Ensure rightmost elements have 15-20px from panel right edge
- **When widening**: If panel feels cramped, increase both panel width AND viewBox width

### Example:
```html
<!-- Panel width 380, content ending at x=330 = only 50px padding -->
<rect width="380"/>
<g transform="translate(30, 55)">
  <rect x="255" width="75"/>  <!-- Ends at 30+255+75=360, cramped -->
</g>

<!-- Better: Widen panel to 400 -->
<rect width="400"/>  <!-- Now 70px padding on right -->
```

---

## 10. Text Width and Container Sizing

SVG text does not automatically wrap or clip - it will overflow containers. You must manually ensure text fits.

### Text Width Estimation

Use these approximate character widths:

| Font Size | Approx Width per Character |
|-----------|---------------------------|
| 10px | 5-6px |
| 11px | 6-7px |
| 12px | 7-8px |
| 14px | 8-9px |
| 16px | 9-10px |

### Calculation Example:
```
Text: "Total Request: 2,405ms (97% in Order Service)"
Characters: 46
Font size: 12px
Estimated width: 46 × 7.5 = 345px

Container rect width must be: 345 + padding (20px each side) = 385px minimum
```

### Common Text Overflow Scenarios:

**1. Text in badge/label boxes:**
```html
<!-- BAD: Box too narrow -->
<rect x="-90" width="180"/>  <!-- 180px wide -->
<text text-anchor="middle">Total: 2,405ms (97% in Order Service)</text>  <!-- ~345px needed -->

<!-- GOOD: Size box to fit text -->
<rect x="-175" width="350"/>  <!-- Fits with padding -->
```

**2. Annotations overlapping titles:**
```html
<!-- BAD: Annotation extends into title area -->
<text x="450" y="35" text-anchor="middle">Centered Title Here</text>
<text x="155" y="24">HOTSPOT: network_io() - 22% time</text>  <!-- Extends to ~350px, overlaps title -->

<!-- GOOD: Position annotation to avoid title -->
<text x="450" y="35" text-anchor="middle">Centered Title Here</text>
<text x="30" y="24">HOTSPOT</text>  <!-- Left side, clear of title -->
```

**3. Legend items cramped:**
```html
<!-- BAD: Not enough vertical space -->
<rect height="100"/>
<text y="70">Line 1</text>
<text y="85">Line 2</text>
<text y="100">Line 3</text>  <!-- At edge, may clip -->

<!-- GOOD: Add breathing room -->
<rect height="130"/>
<text y="70">Line 1</text>
<text y="90">Line 2</text>  <!-- 20px spacing -->
<text y="110">Line 3</text>  <!-- 20px from bottom -->
```

### Rule of Thumb:
- **Always overestimate** text width by 10-20%
- **Minimum container padding**: 10px on each side of text
- **Check centered titles**: Calculate full span (x - width/2 to x + width/2)
- **Test with actual render** - estimation is imprecise

---

## 11. SVG Z-Ordering (Render Order)

SVG has no z-index property. Elements are painted in document order - **elements that appear later in the SVG source are rendered on top**.

### The Rule:
```
First in source = rendered first = appears BEHIND
Last in source = rendered last = appears IN FRONT
```

### Example Problem:
```html
<!-- BAD: ACK line renders first, Data line covers it -->
<line x1="155" y1="270" x2="545" y2="340" stroke="#8b5cf6"/>  <!-- ACK -->
<line x1="155" y1="275" x2="545" y2="345" stroke="#f59e0b"/>  <!-- Data - covers ACK -->
```

### Fix:
```html
<!-- GOOD: Data renders first (behind), ACK renders last (in front) -->
<!-- Step 4: Data - rendered first so it appears BEHIND -->
<line x1="155" y1="275" x2="545" y2="345" stroke="#f59e0b"/>

<!-- Step 3: ACK - rendered last so it appears IN FRONT -->
<line x1="155" y1="270" x2="545" y2="340" stroke="#8b5cf6"/>
```

### Common Scenarios:

**1. Overlapping lines (timeline diagrams):**
- Primary/important lines should be rendered LAST
- Background/secondary lines should be rendered FIRST

**2. Labels over shapes:**
- Draw the shape first, then the label text
- Text should always come after the element it labels

**3. Highlight effects:**
- Draw background highlight/glow first
- Draw the main element on top

**4. Layered elements:**
- Work from back to front when writing SVG
- Comment each layer to clarify intent

### Debugging Z-Order Issues:
1. Identify which element should be "in front"
2. Find both elements in the SVG source
3. Move the "front" element AFTER the "back" element
4. Add comments explaining the render order choice

### Rule of Thumb:
When two elements overlap, ask: "Which should the user see?" That element goes LAST in the source.

---

## 12. Pre-Publication Checklist

Before finalizing any diagram:

### Linter Check (Required):
```bash
just lint html <bookname>
```
All diagrams must pass before committing.

### Visual Checks:
- [ ] All text readable at 100% zoom
- [ ] No text clipped or truncated
- [ ] No overlapping elements (boxes, labels, lines)
- [ ] No lines crossing through text
- [ ] Labels don't overlap with titles
- [ ] Annotations don't overlap with centered titles
- [ ] Text fits within container boxes (badges, labels, legends)
- [ ] Consistent visual styling
- [ ] Colors have sufficient contrast
- [ ] Adequate padding within panels
- [ ] Panel content fits within panel bounds (no overflow)
- [ ] Z-ordering correct (important elements rendered last, visible on top)

### Mathematical Checks:
- [ ] Calculate absolute Y position of all bottom elements
- [ ] Verify: max_content_y + max_content_height < viewBox_height - 15
- [ ] Check all nested transforms accumulate correctly
- [ ] Verify annotation boxes don't overlap
- [ ] Check vertical lines don't pass through centered text
- [ ] Verify labels above markers clear section titles
- [ ] For panels: content_y + content_height <= panel_y + panel_height
- [ ] Estimate text width: chars × width_per_char < container_width - 20

### Rendering Test:
- [ ] Open in browser at various zoom levels (75%, 100%, 150%)
- [ ] Check on both light and dark system themes
- [ ] Verify no horizontal scrollbar appears

---

## 13. Common Issues Reference

| Symptom | Cause | Fix |
|---------|-------|-----|
| Content cut off at bottom | ViewBox too small | Increase viewBox height |
| Elements overlap | Transform math error | Recalculate positions |
| Text illegible | Font too small | Increase to 10px minimum |
| Annotations crowd together | Poor placement | Stagger positions, add separation |
| Cramped appearance | No edge padding | Add 15-20px margins |
| Panel content overflows | Inner content exceeds panel bounds | Increase panel or reduce content |
| Line crosses through text | Line position within text bounding box | Move line away from text center |
| Label hidden by title | Negative Y puts label in title space | Move label down, increase clearance |
| Right side feels cramped | Insufficient inner panel padding | Widen panel and viewBox |
| Text extends past box edge | Container too narrow for text | Widen container or shorten text |
| Annotation overlaps title | Annotation extends into title space | Reposition annotation to avoid title area |
| Legend text cramped | Insufficient vertical spacing | Increase legend height, spread items |
| Wrong element on top | SVG z-order issue | Move "front" element AFTER "back" element in source |

---

## 14. Tools for Verification

### Manual Coordinate Check:
1. Find all elements with transforms
2. Sum up nested transform values
3. Add element y position and height
4. Compare to viewBox height

### Browser DevTools:
1. Open diagram in browser
2. Right-click element → Inspect
3. Check computed bounding box
4. Look for any clipping or overflow

---

## Quick Reference

```bash
# Start a new diagram
cp .ai/templates/html-diagram.html ebooks/<book>/assets/ch01-my-diagram.html

# Lint all diagrams in a book
just lint html <bookname>

# Lint all diagrams across all books
just lint html
```

---

*Document created from lessons learned during API Optimization ebook diagram development.*
*Template: `.ai/templates/html-diagram.html`*
*Linter: `just lint html`*
