# Repository Rules

## Do

- Follow the STYLE_GUIDE.md within each ebook for writing conventions
- Use kebab-case for directory and file names
- Number chapters with two-digit prefixes (01-, 02-, 03-)
- Store images and diagrams in the `assets/` directory
- Maintain WORKS_CITED.md with proper citations for external sources
- Use the `ebooks/_template/` when creating new ebooks
- Run `just validate <book>` before building to check structure
- Run `just lint md <book>` to check markdown formatting (blank lines before code blocks, spacing before inline code)
- Test all output formats after making build system changes

## Don't

- Don't commit directly to main without approval
- Don't create ebooks outside the `ebooks/` directory
- Don't modify `justfile` or build scripts without testing all formats
- Don't add new dependencies without updating BUILD.md
- Don't remove or rename chapters without updating the book's README.md
- Don't commit generated build artifacts (the `build/` directory is gitignored)
