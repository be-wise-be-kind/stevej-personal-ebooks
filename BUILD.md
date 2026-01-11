# Building Ebooks

This repository uses [just](https://github.com/casey/just) as a command runner and [pandoc](https://pandoc.org/) for document conversion.

## Prerequisites

Install required dependencies:

```bash
# Install just (command runner)
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/bin

# Install pandoc (document converter)
sudo apt install pandoc

# For PDF generation
sudo apt install texlive-latex-base texlive-latex-extra

# Optional: for watch mode
sudo apt install entr
```

Check if dependencies are installed:

```bash
just check-deps
```

## Building an Ebook

### Basic Usage

Build a single format:

```bash
just build <bookname> <format>
```

Example:

```bash
just build api-optimization pdf
just build api-optimization epub
just build api-optimization html
```

### Build All Formats

```bash
just build-all api-optimization
```

This generates PDF, EPUB, and HTML versions.

## Available Commands

```bash
just                      # Show all available commands
just list-books           # List all ebooks in the repository
just validate <bookname>  # Check that a book structure is valid
just clean                # Remove all build artifacts
just clean-book <name>    # Remove build artifacts for one book
just watch <name> <fmt>   # Watch for changes and rebuild automatically
```

## Output Location

Built files are placed in `build/<bookname>/`:

```
build/
└── api-optimization/
    ├── api-optimization.pdf
    ├── api-optimization.epub
    └── api-optimization.html
```

## Supported Formats

- **PDF**: Suitable for printing or reading on any device
- **EPUB**: Standard ebook format for e-readers (Kindle, Kobo, etc.)
- **HTML**: Single-page HTML with embedded styles

## Watch Mode

Automatically rebuild when files change:

```bash
just watch api-optimization pdf
```

This watches all markdown files in the ebook directory and rebuilds on save.

## Book Structure

Each ebook must have this structure:

```
ebooks/your-book-name/
├── README.md           # Book overview (title extracted from here)
├── chapters/           # Required: all chapters
│   ├── 01-intro.md
│   ├── 02-chapter.md
│   └── ...
└── assets/             # Optional: images, diagrams, etc.
    └── ...
```

Chapters are automatically included in numerical/alphabetical order based on filename.

## Pandoc Configuration

The build system uses pandoc with these options:

- Table of contents (TOC) included
- Numbered sections
- Assets automatically included from `assets/` directory
- Metadata (title, author) extracted from README

## Troubleshooting

### "pandoc: command not found"

Install pandoc: `sudo apt install pandoc`

### PDF generation fails

Install LaTeX: `sudo apt install texlive-latex-base texlive-latex-extra`

### Images not showing up

Ensure images are in the `assets/` directory and referenced with relative paths in markdown:

```markdown
![Description](../assets/image.png)
```

### Chapters in wrong order

Rename chapters with zero-padded numbers: `01-`, `02-`, etc.

## Advanced Usage

### Custom Pandoc Options

To modify pandoc options, edit the `_build-pdf`, `_build-epub`, or `_build-html` recipes in the `justfile`.

### Adding New Output Formats

Add a new `_build-<format>` recipe in the justfile and update the `build` recipe's case statement.
