# AI Agent Guide for stevej-personal-ebooks

**Purpose**: Primary entry point for AI agents working on this project

**Quick Start**: Read `.ai/index.yaml` for navigation, then check `.ai/ai-context.md` for project context.

---

## MANDATORY: First Action for Every Task

**BEFORE working on ANY task, you MUST:**

1. **READ** `.ai/index.yaml` to understand available resources
2. **IDENTIFY** relevant documentation, howtos, and templates for your task
3. **READ** all applicable documents completely before proceeding
4. **INFORM** the user which documents you are using

**Process:**
```
1. Scan .ai/index.yaml sections:
   - documentation: (reference docs)
   - howto: (step-by-step guides)
   - templates: (file templates)

2. Read applicable documents in this order:
   - Rules first (.ai/rules.md)
   - How-to guides second
   - Templates third

3. Tell the user:
   "I will use these resources:
    - [document 1]: [why it's relevant]
    - [document 2]: [why it's relevant]"

4. Then proceed with the task following the guidance
```

**This is NOT optional.** Skipping this step leads to inconsistent work.

---

## Project Overview

A collection of technical ebooks on API engineering and ML infrastructure, built with `just` + `pandoc`.

**Current Ebooks**:
- **api-optimization** - "Before the 3 AM Alert: What Every Developer Should Know About API Performance" (In Progress, 14 chapters + 2 appendices)
- **ml-inference-apis** - "Productionizing ML Inference APIs: A Serving Engineer's Guide to Real-Time Speech and Audio" (Outline Phase, 13 chapters)

## Navigation

### Critical Documents
- **AI Context**: `.ai/ai-context.md` - Project overview and structure
- **AI Rules**: `.ai/rules.md` - Do's and don'ts for this repository
- **Index**: `.ai/index.yaml` - Complete resource navigation
- **Style Guide**: `.ai/docs/style-guide.md` - Writing conventions

### How-To Guides
- `.ai/howto/how-to-roadmap.md` - Creating and managing ebook roadmaps
- `.ai/howto/evaluating-diagram-quality.md` - Diagram quality standards
- `.ai/howto/writing-technical-books.md` - Technical book authoring practices

### Templates
- `.ai/templates/html-diagram.html` - HTML diagram template
- `.ai/templates/roadmap-progress-tracker.md.template` - Roadmap progress tracker
- `.ai/templates/roadmap-milestone-breakdown.md.template` - Milestone breakdown
- `.ai/templates/roadmap-ai-context.md.template` - Book architecture context

## Roadmap-Driven Development

### When User Requests Planning

If the user says "plan out...", "create a roadmap for...", or "plan the implementation of...":

**Your Actions**:
1. **Read** `.ai/howto/how-to-roadmap.md` for roadmap workflow guidance
2. **Use templates** from `.ai/templates/roadmap-*.md.template`
3. **Create roadmap** in `.roadmap/planning/[book-name]/`
4. **Follow** the three-document structure:
   - `PROGRESS_TRACKER.md` (required - primary handoff document)
   - `MILESTONE_BREAKDOWN.md` (required - detailed milestone/chapter plans)
   - `AI_CONTEXT.md` (recommended - book architecture and context)

### When User Requests Continuation

If the user says "continue with...", "what's next in...", or "resume work on...":

**Your Actions**:
1. **Check** `.roadmap/in-progress/` for active roadmaps
2. **Read** the roadmap's `PROGRESS_TRACKER.md` FIRST
3. **Follow** the "Next Milestone to Work On" section
4. **Update** PROGRESS_TRACKER.md after completing work

### Roadmap Lifecycle

```
planning/ -> in-progress/ -> complete/
   |              |              |
Created      Implementing    Archived
```

See `.ai/howto/how-to-roadmap.md` for detailed workflow instructions.

## Ebook Conventions

### Chapter Files
- **Naming**: `NN-slug.md` with zero-padded numbers (01-, 02-, etc.)
- **Heading**: `# Chapter N: Title` (preface uses `# Preface {-}`)
- **Opener diagram**: `![Chapter N Opener](../assets/chNN-opener.html)` followed by `\newpage`
- **Section hierarchy**: `##` > `###` > `####` (no deeper)

### Citations
- **Inline**: `[Source: Author, Year]`
- **Full details**: In `WORKS_CITED.md` per chapter
- **Format**: Follow existing entries in `ebooks/api-optimization/WORKS_CITED.md`

### Callouts
- **Format**: `> **Bold Title:** content`

### Code Examples
- **Style**: Pseudocode, language-agnostic
- **Format**: Triple backticks with language hint

### Cross-References
- **Format**: `Chapter N: Title` with markdown links between chapter files
- **Book-to-book**: Reference "Before the 3 AM Alert" by title when cross-referencing

### Chapter Endings
Each chapter ends with:
1. `## Summary` with key takeaways
2. `## What's Next` preview (optional)
3. `## References` with citation details
4. `**Next: [Chapter N+1: Title](link)**`

### Diagrams
- **Location**: `assets/` directory within each ebook
- **Format**: HTML with embedded SVG
- **Naming**: `chNN-name.html`
- **Reference**: `![Caption](../assets/chNN-name.html)`
- **Page break**: `\newpage` after major diagrams

## Build and Validate Commands

```bash
# Validate ebook structure
just validate <book-name>

# Check markdown formatting
just lint md <book-name>

# Build single format
just build <book-name> <format>    # format: pdf, epub, html

# Build all formats
just build-all <book-name>

# Watch and rebuild on changes
just watch <book-name> <format>

# List all available ebooks
just list-books
```

## Git Workflow

### Branch Strategy
- `main` - Published content
- Feature branches for new ebooks or major revisions
- Per `CLAUDE.md`: Never commit directly to main

### Commit Conventions
Follow conventional commits:
```
type(scope): Brief description

Detailed description if needed.

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `chore`

### Before Committing
- [ ] `just validate <book-name>` passes
- [ ] `just lint md <book-name>` passes
- [ ] All TOC links in README.md resolve to actual files
- [ ] No secrets or credentials committed
- [ ] WORKS_CITED.md updated for any new references

## Quality Checks

1. **Structure**: `just validate <book-name>` passes
2. **Markdown**: `just lint md <book-name>` passes
3. **Links**: All TOC links resolve to actual chapter files
4. **Citations**: All `[Source: Author, Year]` references have entries in WORKS_CITED.md
5. **Diagrams**: All `![Caption](../assets/chNN-name.html)` references point to existing files
6. **Cross-references**: Chapter-to-chapter links are accurate

## Common Tasks

### Creating a New Ebook
1. Run `./scripts/new-ebook.sh <book-name>`
2. Edit `ebooks/<book-name>/README.md` with book details
3. Create chapter files in `chapters/`
4. Add assets to `assets/`
5. Create a roadmap in `.roadmap/planning/<book-name>/`

### Adding a Chapter
1. Create `ebooks/<book-name>/chapters/NN-slug.md`
2. Follow chapter conventions above
3. Update `ebooks/<book-name>/README.md` TOC
4. Update WORKS_CITED.md with new references
5. Run `just validate <book-name>`

### Creating Diagrams
1. Read `.ai/howto/evaluating-diagram-quality.md` for quality standards
2. Use `.ai/templates/html-diagram.html` as starting template
3. Save as `ebooks/<book-name>/assets/chNN-name.html`
4. Reference in chapter: `![Caption](../assets/chNN-name.html)`

### Building an Ebook
1. Run `just validate <book-name>` first
2. Build desired format: `just build <book-name> pdf`
3. Output appears in `build/<book-name>/`
4. For all formats: `just build-all <book-name>`
