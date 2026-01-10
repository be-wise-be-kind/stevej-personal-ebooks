# Contributing Guide

## Creating a New Ebook

### Quick Start

Use the helper script:

```bash
./scripts/new-ebook.sh your-topic-name
```

This will create a new ebook directory with the proper structure.

### Manual Setup

1. Create a directory: `ebooks/your-topic-name/`
2. Copy the template structure from `ebooks/_template/`
3. Update the README.md with your ebook details

## Writing Content

### Markdown Guidelines

- Use standard Markdown syntax
- Keep chapters focused and concise
- Use code blocks with language specifications
- Number chapters with two-digit prefixes (01-, 02-, etc.)

### Chapter Structure

Each chapter should include:
- Overview section
- Main content with clear headings
- Code examples where applicable
- Summary of key points
- Link to next chapter

### Assets

- Store images as PNG or SVG
- Use descriptive filenames
- Reference assets with relative paths
- Keep file sizes reasonable

## Building for Distribution

### PDF Generation (Pandoc)

```bash
cd ebooks/your-topic-name
pandoc chapters/*.md -o book.pdf --toc
```

### EPUB Generation

```bash
pandoc chapters/*.md -o book.epub --toc --metadata title="Your Title"
```

## Best Practices

- Commit frequently with descriptive messages
- Keep one topic per ebook
- Update the main README when adding new ebooks
- Review and proofread before marking as "Complete"
- Add references and citations where appropriate
