# Repository Context

## Purpose

This is a personal ebooks collection repository for creating, organizing, and building technical mini-ebooks. Each ebook is self-contained and can be built into multiple output formats.

## Directory Structure

```
stevej-personal-ebooks/
├── ebooks/                    # All ebook content lives here
│   ├── <book-name>/           # Individual ebook directories
│   │   ├── README.md          # Book overview and table of contents
│   │   ├── chapters/          # Numbered chapter files (01-, 02-, etc.)
│   │   ├── assets/            # Images, diagrams, and visual content
│   │   ├── edits/             # Editorial tracking documents
│   │   ├── STYLE_GUIDE.md     # Book-specific writing conventions
│   │   └── WORKS_CITED.md     # References and citations
│   └── _template/             # Template for creating new ebooks
├── scripts/                   # Helper scripts
│   └── new-ebook.sh           # Creates new ebook from template
├── build/                     # Generated output (gitignored)
├── justfile                   # Build automation commands
├── BUILD.md                   # Build system documentation
├── AGENTS.md                  # Primary AI agent entry point
└── CONTRIBUTING.md            # Contribution guidelines
```

## Build System

**Tool**: `just` (command runner) with `pandoc` (document converter)

**Output Formats**:
- PDF (via LaTeX/pdflatex)
- EPUB (e-reader format)
- HTML (single-page with embedded styles)

**Key Commands**:
```bash
just build <book-name> <format>    # Build single format (pdf/epub/html)
just build-all <book-name>         # Build all formats
just validate <book-name>          # Check ebook structure
just watch <book-name> <format>    # Watch and rebuild on changes
just list-books                    # List all available ebooks
just lint md <book-name>           # Check markdown formatting
```

**Output Location**: `build/<book-name>/`

## Ebook Conventions

- **Directory naming**: Use kebab-case (e.g., `api-optimization`)
- **Chapter numbering**: Two-digit prefixes (01-introduction.md, 02-fundamentals.md)
- **Assets**: Store in `assets/` directory within each ebook
- **Style guide**: Each ebook should have its own STYLE_GUIDE.md
- **Citations**: Maintain WORKS_CITED.md for references
- **Diagrams**: HTML with embedded SVG in `assets/`, named `chNN-name.html`

## Current Ebooks

### api-optimization
**Title**: "Before the 3 AM Alert: What Every Developer Should Know About API Performance"
**Status**: In Progress
A practical guide to API performance optimization covering observability, caching, database patterns, async processing, scaling, and traffic management. Contains 14 chapters with comprehensive diagrams and two appendices.

### ml-inference-apis
**Title**: "Productionizing ML Inference APIs: A Serving Engineer's Guide to Real-Time Speech and Audio"
**Status**: Outline Phase
A companion to "Before the 3 AM Alert" focused on the ML inference serving side. Covers model serving frameworks, GPU optimization, real-time audio streaming, API design for ML services, usage metering, enterprise compliance, and SLOs for streaming systems. 13 chapters organized in 5 parts.

## Roadmap Workflow

Ebook development is tracked through roadmaps in `.roadmap/`. See:
- **AGENTS.md** at project root for AI agent entry point
- `.ai/howto/how-to-roadmap.md` for roadmap usage guide
- `.ai/docs/ROADMAP_WORKFLOW.md` for workflow documentation
- `.roadmap/in-progress/` for active ebook development roadmaps
