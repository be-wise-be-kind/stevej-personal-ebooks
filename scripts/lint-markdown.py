#!/usr/bin/env python3
"""Lint markdown files for formatting compliance.

Rules checked:
1. Code blocks must be preceded by a blank line
2. Inline code must be preceded by whitespace or allowed punctuation
3. No em-dashes allowed (—, --, or ---) - rewrite sentences instead
4. Commas must be followed by a space in prose (fixable with --fix)
"""

import argparse
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

# Pattern for comma spacing violations in prose
# Matches: comma followed directly by a letter (no space)
COMMA_SPACING_PATTERN = re.compile(r',([a-zA-Z])')

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

        # Check for comma spacing violations (comma directly followed by letter)
        for match in COMMA_SPACING_PATTERN.finditer(line_without_code):
            start = max(0, match.start() - 15)
            end = min(len(line_without_code), match.end() + 15)
            context = line_without_code[start:end]
            errors.append(
                f"Line {line_num}: Missing space after comma: ...{context}..."
            )

    return errors


def fix_comma_spacing(path: str) -> int:
    """Fix comma spacing violations in a file. Returns number of fixes made."""
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    total_fixes = 0
    in_code_block = False

    for line in lines:
        stripped = line.rstrip('\n')

        # Track code blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            fixed_lines.append(line)
            continue

        # Don't modify lines inside code blocks
        if in_code_block:
            fixed_lines.append(line)
            continue

        # Skip horizontal rules and table separators
        if HORIZONTAL_RULE_PATTERN.match(stripped) or TABLE_SEPARATOR_PATTERN.match(stripped):
            fixed_lines.append(line)
            continue

        # Fix comma spacing while preserving inline code
        # Strategy: temporarily replace inline code with placeholders, fix, restore
        code_spans = []

        def save_code(match):
            code_spans.append(match.group(0))
            return f'\x00CODE{len(code_spans) - 1}\x00'

        # Save inline code spans
        line_with_placeholders = INLINE_CODE_PATTERN.sub(save_code, line)

        # Fix comma spacing: add space after comma before letters
        fixed_line, num_fixes = COMMA_SPACING_PATTERN.subn(r', \1', line_with_placeholders)
        total_fixes += num_fixes

        # Restore inline code spans
        for i, code in enumerate(code_spans):
            fixed_line = fixed_line.replace(f'\x00CODE{i}\x00', code)

        fixed_lines.append(fixed_line)

    if total_fixes > 0:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)

    return total_fixes


def main():
    parser = argparse.ArgumentParser(
        description='Lint markdown files for formatting compliance'
    )
    parser.add_argument('pattern', help='Glob pattern for files to lint')
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Auto-fix comma spacing violations'
    )
    args = parser.parse_args()

    files = glob.glob(args.pattern, recursive=True)

    if not files:
        print(f"No files found matching: {args.pattern}")
        sys.exit(1)

    if args.fix:
        # Fix mode: fix comma spacing violations
        total_fixes = 0
        files_fixed = 0
        for path in sorted(files):
            fixes = fix_comma_spacing(path)
            if fixes > 0:
                files_fixed += 1
                total_fixes += fixes
                print(f"Fixed {fixes} comma spacing violation(s) in {path}")

        if total_fixes:
            print(f"\nFixed {total_fixes} total violation(s) in {files_fixed} file(s)")
        else:
            print(f"No comma spacing violations found in {len(files)} file(s)")
        sys.exit(0)
    else:
        # Lint mode: report all violations
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
