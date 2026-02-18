# Personal Ebooks Build System
# Usage: just build <bookname> <format>
# Example: just build api-optimization pdf

# Default recipe - show available commands
default:
    @just --list

# Install all dependencies required for building ebooks
init:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "Installing ebook build dependencies..."
    echo ""
    
    # Install pandoc
    if ! command -v pandoc &> /dev/null; then
        echo "Installing pandoc..."
        sudo apt update
        sudo apt install -y pandoc
        echo "✓ pandoc installed"
    else
        echo "✓ pandoc already installed"
    fi
    
    # Install LaTeX for PDF generation
    if ! command -v pdflatex &> /dev/null; then
        echo "Installing LaTeX (for PDF generation)..."
        sudo apt install -y texlive-latex-base texlive-latex-extra
        echo "✓ LaTeX installed"
    else
        echo "✓ LaTeX already installed"
    fi
    
    # Install librsvg for SVG to PDF conversion
    if ! command -v rsvg-convert &> /dev/null; then
        echo "Installing librsvg2-bin (for SVG in PDFs)..."
        sudo apt install -y librsvg2-bin
        echo "✓ librsvg2-bin installed"
    else
        echo "✓ rsvg-convert already installed"
    fi

    # Install entr for watch mode (optional)
    if ! command -v entr &> /dev/null; then
        echo "Installing entr (for watch mode)..."
        sudo apt install -y entr
        echo "✓ entr installed"
    else
        echo "✓ entr already installed"
    fi

    echo ""
    echo "All dependencies installed!"
    echo "Run 'just check-deps' to verify installation."

# List available ebooks
list-books:
    #!/usr/bin/env bash
    echo "Available ebooks:"
    find ebooks -mindepth 1 -maxdepth 1 -type d ! -name '_template' -exec basename {} \;

# Build an ebook in specified format
build bookname format:
    #!/usr/bin/env bash
    set -euo pipefail

    BOOK_DIR="ebooks/{{bookname}}"
    BUILD_DIR="build/{{bookname}}"

    # Handle special format naming (pdf-mobile -> bookname-mobile.pdf)
    case "{{format}}" in
        pdf-mobile)
            OUTPUT_FILE="$BUILD_DIR/{{bookname}}-mobile.pdf"
            ;;
        *)
            OUTPUT_FILE="$BUILD_DIR/{{bookname}}.{{format}}"
            ;;
    esac

    # Check if book exists
    if [ ! -d "$BOOK_DIR" ]; then
        echo "Error: Book '$BOOK_DIR' does not exist"
        exit 1
    fi

    # Check if chapters directory exists
    if [ ! -d "$BOOK_DIR/chapters" ]; then
        echo "Error: No chapters directory found in $BOOK_DIR"
        exit 1
    fi

    # Create build directory
    mkdir -p "$BUILD_DIR"

    echo "Building {{bookname}} as {{format}}..."

    # Convert HTML diagrams to SVG
    if [ -d "$BOOK_DIR/assets" ]; then
        echo "Converting diagrams..."
        ./scripts/convert-diagrams.sh "$BOOK_DIR" "$BUILD_DIR"
    fi

    # Preprocess chapters (update asset references from .html to target format)
    echo "Preprocessing chapters..."
    ./scripts/preprocess-chapters.sh "$BOOK_DIR" "$BUILD_DIR" "{{format}}"

    # Collect preprocessed chapters in order (space-separated for pandoc)
    CHAPTERS=$(find "$BUILD_DIR/chapters" -name "*.md" | sort | tr '\n' ' ')

    if [ -z "$CHAPTERS" ]; then
        echo "Error: No chapters found after preprocessing"
        exit 1
    fi

    # Build based on format
    case "{{format}}" in
        pdf)
            just _build-pdf "$BOOK_DIR" "$BUILD_DIR" "$OUTPUT_FILE" "$CHAPTERS"
            ;;
        pdf-mobile)
            just _build-pdf-mobile "$BOOK_DIR" "$BUILD_DIR" "$OUTPUT_FILE" "$CHAPTERS"
            ;;
        epub)
            just _build-epub "$BOOK_DIR" "$BUILD_DIR" "$OUTPUT_FILE" "$CHAPTERS"
            ;;
        html)
            just _build-html "$BOOK_DIR" "$BUILD_DIR" "$OUTPUT_FILE" "$CHAPTERS"
            ;;
        outline)
            just _build-outline "$BOOK_DIR" "$BUILD_DIR" "$OUTPUT_FILE" "$CHAPTERS"
            ;;
        *)
            echo "Error: Unsupported format '{{format}}'. Supported: pdf, pdf-mobile, epub, html, outline"
            exit 1
            ;;
    esac

    echo "✓ Built: $OUTPUT_FILE"

# Internal: Build PDF using pandoc
_build-pdf book_dir build_dir output_file chapters:
    #!/usr/bin/env bash
    set -euo pipefail
    
    # Check for pandoc
    if ! command -v pandoc &> /dev/null; then
        echo "Error: pandoc is required for PDF generation"
        echo "Install: sudo apt install pandoc texlive-latex-base texlive-latex-extra"
        exit 1
    fi
    
    # Read book title from README
    TITLE=$(grep -m1 "^# " "{{book_dir}}/README.md" | sed 's/^# //' || echo "Untitled")
    
    # Build with pandoc
    # -implicit_figures prevents images from floating
    pandoc {{chapters}} \
        --from markdown-implicit_figures \
        --to pdf \
        --output "{{output_file}}" \
        --metadata title="$TITLE" \
        --metadata author="Steve Jackson" \
        --toc \
        --toc-depth=2 \
        --number-sections \
        --top-level-division=chapter \
        -V classoption:openany \
        -V geometry:margin=1in \
        -H templates/header.tex \
        --resource-path="{{build_dir}}/assets:{{book_dir}}/assets" \
        --pdf-engine=xelatex

# Internal: Build PDF (mobile) using pandoc - larger text for tablet/phone reading
_build-pdf-mobile book_dir build_dir output_file chapters:
    #!/usr/bin/env bash
    set -euo pipefail

    # Check for pandoc
    if ! command -v pandoc &> /dev/null; then
        echo "Error: pandoc is required for PDF generation"
        echo "Install: sudo apt install pandoc texlive-latex-base texlive-latex-extra"
        exit 1
    fi

    # Read book title from README
    TITLE=$(grep -m1 "^# " "{{book_dir}}/README.md" | sed 's/^# //' || echo "Untitled")

    # Build with pandoc - using 14pt font for mobile readability
    # extbook class supports larger font sizes (14pt, 17pt, 20pt)
    # -implicit_figures prevents images from floating
    pandoc {{chapters}} \
        --from markdown-implicit_figures \
        --to pdf \
        --output "{{output_file}}" \
        --metadata title="$TITLE" \
        --metadata author="Steve Jackson" \
        --toc \
        --toc-depth=2 \
        --number-sections \
        --top-level-division=chapter \
        -V documentclass=extbook \
        -V classoption:openany \
        -V fontsize:14pt \
        -V geometry:margin=0.8in \
        -H templates/header-mobile.tex \
        --resource-path="{{build_dir}}/assets:{{book_dir}}/assets" \
        --pdf-engine=xelatex

# Internal: Build EPUB using pandoc
_build-epub book_dir build_dir output_file chapters:
    #!/usr/bin/env bash
    set -euo pipefail
    
    # Check for pandoc
    if ! command -v pandoc &> /dev/null; then
        echo "Error: pandoc is required for EPUB generation"
        echo "Install: sudo apt install pandoc"
        exit 1
    fi
    
    # Read book title from README
    TITLE=$(grep -m1 "^# " "{{book_dir}}/README.md" | sed 's/^# //' || echo "Untitled")
    
    # Build with pandoc
    pandoc {{chapters}} \
        --from markdown \
        --to epub3 \
        --output "{{output_file}}" \
        --metadata title="$TITLE" \
        --metadata author="Steve Jackson" \
        --toc \
        --toc-depth=2 \
        --number-sections \
        --top-level-division=chapter \
        --css=templates/epub.css \
        --resource-path="{{build_dir}}/assets:{{book_dir}}/assets"

# Internal: Build HTML using pandoc
_build-html book_dir build_dir output_file chapters:
    #!/usr/bin/env bash
    set -euo pipefail
    
    # Check for pandoc
    if ! command -v pandoc &> /dev/null; then
        echo "Error: pandoc is required for HTML generation"
        echo "Install: sudo apt install pandoc"
        exit 1
    fi
    
    # Read book title from README
    TITLE=$(grep -m1 "^# " "{{book_dir}}/README.md" | sed 's/^# //' || echo "Untitled")
    
    # Build with pandoc
    pandoc {{chapters}} \
        --from markdown \
        --to html5 \
        --output "{{output_file}}" \
        --metadata title="$TITLE" \
        --metadata author="Steve Jackson" \
        --toc \
        --toc-depth=2 \
        --number-sections \
        --standalone \
        --embed-resources \
        --resource-path="{{build_dir}}/assets:{{book_dir}}/assets" \
        --css=templates/html.css

# Internal: Build outline - extract document structure (headings only)
_build-outline book_dir build_dir output_file chapters:
    #!/usr/bin/env bash
    set -euo pipefail

    # Read book title from README
    TITLE=$(grep -m1 "^# " "{{book_dir}}/README.md" | sed 's/^# //' || echo "Untitled")

    {
        echo "# $TITLE - Outline"
        echo ""
        echo "Generated: $(date '+%Y-%m-%d %H:%M')"
        echo ""
        echo "---"
        echo ""

        # Extract headings from each chapter, preserving order
        for chapter in {{chapters}}; do
            # Get headings (lines starting with #)
            grep -E "^#{1,5} " "$chapter" || true
            echo ""
        done
    } > "{{output_file}}"

# Build all formats for a book
build-all bookname:
    just build {{bookname}} pdf
    just build {{bookname}} pdf-mobile
    just build {{bookname}} epub
    just build {{bookname}} html

# Clean build artifacts
clean:
    rm -rf build/

# Clean build artifacts for specific book
clean-book bookname:
    rm -rf build/{{bookname}}

# Validate that a book's chapters are properly numbered and complete
validate bookname:
    #!/usr/bin/env bash
    set -euo pipefail
    
    BOOK_DIR="ebooks/{{bookname}}"
    
    if [ ! -d "$BOOK_DIR" ]; then
        echo "Error: Book '$BOOK_DIR' does not exist"
        exit 1
    fi
    
    echo "Validating {{bookname}}..."
    
    # Check for README
    if [ ! -f "$BOOK_DIR/README.md" ]; then
        echo "⚠ Warning: No README.md found"
    else
        echo "✓ README.md exists"
    fi
    
    # Check for chapters directory
    if [ ! -d "$BOOK_DIR/chapters" ]; then
        echo "✗ Error: No chapters directory"
        exit 1
    fi
    
    # List chapters in order
    CHAPTERS=$(find "$BOOK_DIR/chapters" -name "*.md" | sort)
    CHAPTER_COUNT=$(echo "$CHAPTERS" | wc -l)
    
    echo "✓ Found $CHAPTER_COUNT chapters:"
    echo "$CHAPTERS" | xargs -n1 basename
    
    # Check for assets directory
    if [ -d "$BOOK_DIR/assets" ]; then
        ASSET_COUNT=$(find "$BOOK_DIR/assets" -type f | wc -l)
        echo "✓ Found $ASSET_COUNT assets"
    else
        echo "ℹ No assets directory"
    fi
    
    echo "Validation complete!"

# Lint assets by type (e.g., just lint html, just lint md api-optimization)
lint type *args:
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{type}}" in
        html)
            # Default to all books if no args, or specific book
            if [ -z "{{args}}" ]; then
                python3 scripts/lint-html-diagrams.py "ebooks/*/assets/*.html"
            else
                python3 scripts/lint-html-diagrams.py "ebooks/{{args}}/assets/*.html"
            fi
            ;;
        md|markdown)
            # Lint markdown chapters for formatting compliance
            if [ -z "{{args}}" ]; then
                python3 scripts/lint-markdown.py "ebooks/*/chapters/*.md"
            else
                python3 scripts/lint-markdown.py "ebooks/{{args}}/chapters/*.md"
            fi
            ;;
        *)
            echo "Unknown lint type: {{type}}"
            echo "Supported: html, md"
            exit 1
            ;;
    esac

# Watch for changes and rebuild (requires entr)
watch bookname format:
    #!/usr/bin/env bash
    if ! command -v entr &> /dev/null; then
        echo "Error: entr is required for watch mode"
        echo "Install: sudo apt install entr"
        exit 1
    fi
    
    echo "Watching ebooks/{{bookname}} for changes..."
    echo "Press Ctrl+C to stop"
    
    find ebooks/{{bookname}} -name "*.md" | entr -c just build {{bookname}} {{format}}

# Check dependencies
check-deps:
    #!/usr/bin/env bash
    echo "Checking build dependencies..."
    
    deps_missing=0
    
    if command -v pandoc &> /dev/null; then
        echo "✓ pandoc $(pandoc --version | head -n1)"
    else
        echo "✗ pandoc not found"
        deps_missing=1
    fi
    
    if command -v pdflatex &> /dev/null; then
        echo "✓ pdflatex (for PDF generation)"
    else
        echo "⚠ pdflatex not found (PDF generation will fail)"
        echo "  Install: sudo apt install texlive-latex-base texlive-latex-extra"
    fi

    if command -v rsvg-convert &> /dev/null; then
        echo "✓ rsvg-convert (for SVG in PDFs)"
    else
        echo "⚠ rsvg-convert not found (PDF generation with SVG diagrams will fail)"
        echo "  Install: sudo apt install librsvg2-bin"
    fi

    if command -v entr &> /dev/null; then
        echo "✓ entr (for watch mode)"
    else
        echo "ℹ entr not found (watch mode unavailable)"
        echo "  Install: sudo apt install entr"
    fi
    
    if [ $deps_missing -eq 0 ]; then
        echo ""
        echo "All required dependencies installed!"
    else
        echo ""
        echo "Some dependencies missing. Install them to enable all features."
        exit 1
    fi

# Publish all ebooks to a GitHub release
release version="":
    #!/usr/bin/env bash
    set -euo pipefail

    VERSION="{{ version }}"

    # Prompt for version if not provided
    if [[ -z "$VERSION" ]]; then
        read -p "Enter release version (e.g., v1.0.0): " VERSION
    fi

    # Validate version format
    if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "Error: Version must be in format v1.0.0"
        exit 1
    fi

    # Check gh CLI is available
    if ! command -v gh &> /dev/null; then
        echo "Error: GitHub CLI (gh) is required. Install with: sudo apt install gh"
        exit 1
    fi

    # Build all ebooks
    echo "Building all ebooks..."
    for book in ebooks/*/; do
        bookname=$(basename "$book")
        if [[ "$bookname" == "_template" ]]; then
            continue
        fi
        echo "Building $bookname..."
        just build-all "$bookname"
    done

    # Collect artifacts
    ARTIFACTS=""
    for book in ebooks/*/; do
        bookname=$(basename "$book")
        if [[ "$bookname" == "_template" ]]; then
            continue
        fi
        builddir="build/$bookname"
        if [[ -d "$builddir" ]]; then
            for file in "$builddir"/*.pdf "$builddir"/*.epub "$builddir"/*.html; do
                [[ -f "$file" ]] && ARTIFACTS="$ARTIFACTS $file"
            done
        fi
    done

    # Create git tag
    echo "Creating git tag $VERSION..."
    git tag -a "$VERSION" -m "Release $VERSION"
    git push origin "$VERSION"

    # Create GitHub release (unset GITHUB_TOKEN to use gh's own auth)
    echo "Creating GitHub release..."
    unset GITHUB_TOKEN
    gh release create "$VERSION" $ARTIFACTS \
        --title "Release $VERSION" \
        --generate-notes

    echo "Release $VERSION published successfully!"

# Dry-run: show extracted passages without searching
plagiarism-dry-run bookname:
    python3 scripts/check-plagiarism.py {{bookname}} --dry-run

# Run plagiarism spot-check via web search
plagiarism-check bookname *args:
    python3 scripts/check-plagiarism.py {{bookname}} {{args}}
