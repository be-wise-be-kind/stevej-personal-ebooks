# Personal Ebooks Collection

A personal repository for capturing knowledge and learnings in ebook format.

## Purpose

This repository serves as a structured collection of mini-ebooks documenting topics I learn about. Each ebook is self-contained and can be used for personal reference or shared with others.

## Structure

```
ebooks/
├── topic-name/
│   ├── README.md          # Overview and table of contents
│   ├── chapters/          # Individual chapters
│   │   ├── 01-introduction.md
│   │   ├── 02-chapter-name.md
│   │   └── ...
│   └── assets/            # Images, diagrams, code samples
│       └── ...
```

## Creating a New Ebook

1. Create a new directory under `ebooks/` with a descriptive name (use kebab-case)
2. Add a `README.md` file with the ebook's overview and table of contents
3. Create a `chapters/` directory for your content
4. Optionally create an `assets/` directory for supporting files

## Writing Guidelines

- Use Markdown for all content
- Number chapters with prefixes (01-, 02-, etc.)
- Keep chapters focused on specific topics
- Include code examples where applicable
- Add diagrams and visuals in the assets folder

## Building Ebooks

Each ebook can be converted to various formats:
- PDF (using Pandoc or similar tools)
- EPUB (for e-readers)
- HTML (for web viewing)

Build scripts can be added as needed per ebook.

## License

Personal use. If sharing publicly, add appropriate license information per ebook.
