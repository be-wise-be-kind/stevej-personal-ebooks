#!/usr/bin/env python3
"""Lint markdown files for formatting compliance.

Rules checked:
1. Code blocks must be preceded by a blank line
2. Inline code must be preceded by whitespace or allowed punctuation
3. No em-dashes allowed (—, --, or ---) - rewrite sentences instead
"""

import sys
import re
import glob

# Pattern to find inline code spans (single backticks, not triple)
# Matches: `code` but not ```code```
INLINE_CODE_PATTERN = re.compile(r'(?<!`)(`[^`\n]+?`)(?!`)')

# Patterns for em-dash violations in prose
# Matches word---word or word--word (em-dash written as hyphens)
EM_DASH_WORD_PATTERN = re.compile(r'\w---?\w')
# Matches spaced em-dashes like " -- " or " --- "
EM_DASH_SPACED_PATTERN = re.compile(r' ---? ')
# Matches Unicode em-dash character (U+2014)
EM_DASH_UNICODE_PATTERN = re.compile(r'—')

# Pattern to detect table row separators (should not be flagged)
TABLE_SEPARATOR_PATTERN = re.compile(r'^\|[-:|]+\|$')

# Pattern to detect horizontal rules at start of line
HORIZONTAL_RULE_PATTERN = re.compile(r'^---+$')

# Characters allowed immediately before an opening backtick
# Includes: whitespace, apostrophe, opening brackets/parens, quotes,
# and markdown emphasis characters (* and _)
ALLOWED_BEFORE_BACKTICK = set(" \t'\"([{<*_")


def lint_file(path: str) -> list[str]:
    """Return list of violations for a file."""
    errors = []
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_code_block = False

    for i, line in enumerate(lines):
        line_num = i + 1
        stripped = line.rstrip('\n')

        # Check if this line is a code fence
        if stripped.startswith('```'):
            if not in_code_block:
                # Opening code fence - check if preceded by blank line
                if i > 0:
                    prev_line = lines[i - 1].rstrip('\n')
                    # Previous line should be blank (empty or whitespace only)
                    if prev_line.strip() != '':
                        errors.append(
                            f"Line {line_num}: Code block not preceded by blank line"
                        )
                in_code_block = True
            else:
                # Closing code fence
                in_code_block = False
            continue

        # Skip inline code checks inside code blocks
        if in_code_block:
            continue

        # Check for inline code spacing violations
        for match in INLINE_CODE_PATTERN.finditer(stripped):
            pos = match.start()
            if pos == 0:
                # Start of line is fine
                continue

            char_before = stripped[pos - 1]
            if char_before not in ALLOWED_BEFORE_BACKTICK:
                # Found a violation - letter/digit directly before backtick
                inline_code = match.group(1)
                # Truncate long inline code for readability
                if len(inline_code) > 20:
                    inline_code = inline_code[:17] + '...'
                errors.append(
                    f"Line {line_num}: Missing space before inline code {inline_code}"
                )

        # Check for em-dash violations (-- or --- used instead of —)
        # Skip horizontal rules (--- at start of line)
        if HORIZONTAL_RULE_PATTERN.match(stripped):
            continue

        # Skip table separator rows
        if TABLE_SEPARATOR_PATTERN.match(stripped):
            continue

        # Remove inline code spans before checking for em-dash violations
        # This prevents flagging -- inside backticks (e.g., `--help`)
        line_without_code = INLINE_CODE_PATTERN.sub('', stripped)

        # Check for word---word or word--word patterns
        for match in EM_DASH_WORD_PATTERN.finditer(line_without_code):
            # Extract context around the match
            start = max(0, match.start() - 10)
            end = min(len(line_without_code), match.end() + 10)
            context = line_without_code[start:end]
            errors.append(
                f"Line {line_num}: Em-dash not allowed (rewrite sentence): ...{context}..."
            )

        # Check for spaced em-dashes like " -- " or " --- "
        for match in EM_DASH_SPACED_PATTERN.finditer(line_without_code):
            start = max(0, match.start() - 10)
            end = min(len(line_without_code), match.end() + 10)
            context = line_without_code[start:end]
            errors.append(
                f"Line {line_num}: Em-dash not allowed (rewrite sentence): ...{context}..."
            )

        # Check for Unicode em-dash character
        for match in EM_DASH_UNICODE_PATTERN.finditer(line_without_code):
            start = max(0, match.start() - 15)
            end = min(len(line_without_code), match.end() + 15)
            context = line_without_code[start:end]
            errors.append(
                f"Line {line_num}: Em-dash not allowed (rewrite sentence): ...{context}..."
            )

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: lint-markdown.py <path-or-glob>")
        sys.exit(1)

    pattern = sys.argv[1]
    files = glob.glob(pattern, recursive=True)

    if not files:
        print(f"No files found matching: {pattern}")
        sys.exit(1)

    total_errors = 0
    files_with_errors = 0
    for path in sorted(files):
        errors = lint_file(path)
        if errors:
            files_with_errors += 1
            print(f"\n{path}:")
            for err in errors:
                print(f"  - {err}")
            total_errors += len(errors)

    if total_errors:
        print(f"\n{total_errors} violation(s) found in {files_with_errors} file(s)")
        sys.exit(1)
    else:
        print(f"All {len(files)} markdown file(s) pass lint checks")
        sys.exit(0)


if __name__ == '__main__':
    main()
