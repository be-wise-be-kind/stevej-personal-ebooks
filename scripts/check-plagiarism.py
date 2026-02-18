#!/usr/bin/env python3
"""Plagiarism spot-check for ebook chapters.

Extracts distinctive prose passages from each chapter, searches for them
on the web via DuckDuckGo, and reports any matches found. Cross-references
matches against WORKS_CITED.md to distinguish intentional citations from
potential issues.

Severity levels:
  CLEAN           - no matches found
  CITED MATCH     - match found but source is cited (likely intentional)
  POTENTIAL MATCH - match found against an uncited source (needs review)
"""

import argparse
import glob
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


# ---------------------------------------------------------------------------
# Passage Extraction
# ---------------------------------------------------------------------------

# Inline markdown to strip from extracted text
INLINE_BOLD = re.compile(r'\*\*(.+?)\*\*')
INLINE_ITALIC = re.compile(r'\*(.+?)\*')
INLINE_CODE = re.compile(r'`[^`]+`')
INLINE_LINK = re.compile(r'\[([^\]]*)\]\([^)]+\)')
INLINE_CITATION = re.compile(r'\[Source:\s*[^\]]+\]')
INLINE_IMAGE = re.compile(r'!\[[^\]]*\]\([^)]+\)')
HTML_COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)

# Lines to skip entirely
SKIP_LINE_PATTERNS = [
    re.compile(r'^#{1,6}\s'),            # headings
    re.compile(r'^\|'),                   # table rows
    re.compile(r'^```'),                  # code fences
    re.compile(r'^\\newpage'),            # page breaks
    re.compile(r'^\*\*Next:\s*\['),       # navigation links
    re.compile(r'^!\['),                  # image references
    re.compile(r'^<!--'),                 # HTML comments
    re.compile(r'^>\s*\*\*'),             # callout openers (> **Title:**)
]


def strip_inline_markdown(text):
    """Remove inline markdown formatting from text."""
    text = INLINE_CITATION.sub('', text)
    text = INLINE_IMAGE.sub('', text)
    text = INLINE_LINK.sub(r'\1', text)
    text = INLINE_BOLD.sub(r'\1', text)
    text = INLINE_ITALIC.sub(r'\1', text)
    text = INLINE_CODE.sub('', text)
    text = HTML_COMMENT.sub('', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_prose_paragraphs(filepath):
    """Extract prose paragraphs from a markdown file, skipping non-prose."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    paragraphs = []
    current_paragraph = []
    in_code_block = False

    for line in content.split('\n'):
        stripped = line.strip()

        # Track code blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
            continue

        if in_code_block:
            continue

        # Skip non-prose lines
        if any(pat.match(stripped) for pat in SKIP_LINE_PATTERNS):
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
            continue

        # Blank line ends paragraph
        if not stripped:
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
            continue

        current_paragraph.append(stripped)

    if current_paragraph:
        paragraphs.append(' '.join(current_paragraph))

    # Clean up inline markdown and filter short paragraphs
    cleaned = []
    for p in paragraphs:
        text = strip_inline_markdown(p)
        # Keep paragraphs with at least 20 words of actual prose
        if len(text.split()) >= 20:
            cleaned.append(text)

    return cleaned


def score_passage(text):
    """Score a passage for distinctiveness. Higher = more distinctive."""
    words = text.split()
    word_count = len(words)

    # Prefer passages around the target length
    length_score = word_count

    # Prefer sentences with narrative flow (longer average word length)
    avg_word_len = sum(len(w) for w in words) / max(word_count, 1)
    vocabulary_score = avg_word_len * 10

    # Prefer passages with fewer very common technical words
    common_words = {'the', 'is', 'are', 'was', 'were', 'be', 'to', 'of',
                    'and', 'a', 'in', 'that', 'it', 'for', 'on', 'with'}
    common_ratio = sum(1 for w in words if w.lower() in common_words) / max(word_count, 1)
    uniqueness_score = (1 - common_ratio) * 50

    return length_score + vocabulary_score + uniqueness_score


def extract_passage(text, target_words):
    """Extract a ~target_words passage from a paragraph.

    Takes from the beginning of the paragraph, trimming to sentence
    boundaries when possible.
    """
    words = text.split()
    if len(words) <= target_words:
        return text

    # Take roughly target_words, then trim to last sentence boundary
    candidate = ' '.join(words[:target_words + 15])
    sentences = re.split(r'(?<=[.!?])\s+', candidate)

    # Accumulate sentences until we're near the target
    result = []
    word_count = 0
    for sentence in sentences:
        sentence_words = len(sentence.split())
        if word_count + sentence_words > target_words + 10 and word_count >= target_words // 2:
            break
        result.append(sentence)
        word_count += sentence_words

    if result:
        return ' '.join(result)
    return ' '.join(words[:target_words])


def select_passages(paragraphs, num_passages, target_words):
    """Select representative passages spread across the chapter."""
    if not paragraphs:
        return []

    if len(paragraphs) <= num_passages:
        return [extract_passage(p, target_words) for p in paragraphs]

    # Divide paragraphs into equal segments
    segment_size = len(paragraphs) / num_passages
    passages = []

    for i in range(num_passages):
        start = int(i * segment_size)
        end = int((i + 1) * segment_size)
        segment = paragraphs[start:end]

        if not segment:
            continue

        # Pick the most distinctive paragraph from this segment
        best = max(segment, key=score_passage)
        passages.append(extract_passage(best, target_words))

    return passages


# ---------------------------------------------------------------------------
# Web Search
# ---------------------------------------------------------------------------

def extract_search_phrase(passage, min_words=8, max_words=12):
    """Extract a distinctive phrase from a passage for web search.

    Picks a phrase from the middle of the passage (less likely to be
    generic opening/closing), preferring phrases with distinctive words.
    """
    sentences = re.split(r'(?<=[.!?])\s+', passage)

    # Prefer longer sentences from the middle of the passage
    if len(sentences) >= 3:
        candidates = sentences[1:-1]
    elif len(sentences) >= 2:
        candidates = sentences[1:]
    else:
        candidates = sentences

    # Find the most distinctive sentence
    best_sentence = max(candidates, key=lambda s: len(s.split()))
    words = best_sentence.split()

    if len(words) <= max_words:
        return best_sentence

    # Take words from the middle of the sentence
    mid = len(words) // 2
    half_target = (min_words + max_words) // 4
    start = max(0, mid - half_target)
    end = min(len(words), start + max_words)
    start = max(0, end - max_words)

    return ' '.join(words[start:end])


def search_duckduckgo(phrase, max_retries=2):
    """Search DuckDuckGo for an exact phrase match.

    Returns dict with 'error' (str or None) and 'results' (list of dicts).
    Retries with exponential backoff on 403 rate-limit responses.
    """
    quoted = f'"{phrase}"'
    params = urllib.parse.urlencode({'q': quoted})
    url = f'https://html.duckduckgo.com/html/?{params}'

    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; PlagiarismChecker/1.0)',
    })

    last_error = None
    for attempt in range(1 + max_retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode('utf-8', errors='replace')
            return {'error': None, 'results': parse_duckduckgo_results(body)}
        except urllib.error.HTTPError as e:
            last_error = str(e)
            if e.code == 403 and attempt < max_retries:
                backoff = 10 * (attempt + 1)
                print(f'    Rate limited, waiting {backoff}s before retry...',
                      file=sys.stderr)
                time.sleep(backoff)
                continue
            return {'error': last_error, 'results': []}
        except (urllib.error.URLError, TimeoutError) as e:
            return {'error': str(e), 'results': []}


def parse_duckduckgo_results(html_body):
    """Parse search results from DuckDuckGo HTML response."""
    results = []

    # DuckDuckGo HTML results are in <div class="result..."> blocks
    # with <a class="result__a"> for title and <a class="result__snippet"> for snippet
    title_pattern = re.compile(
        r'class="result__a"[^>]*>(.*?)</a>', re.DOTALL
    )
    snippet_pattern = re.compile(
        r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)>', re.DOTALL
    )

    titles = title_pattern.findall(html_body)
    snippets = snippet_pattern.findall(html_body)

    for i in range(min(len(titles), len(snippets))):
        title = re.sub(r'<[^>]+>', '', titles[i]).strip()
        snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
        title = html.unescape(title)
        snippet = html.unescape(snippet)
        if title or snippet:
            results.append({'title': title, 'snippet': snippet})

    return results


# ---------------------------------------------------------------------------
# Citation Cross-Reference
# ---------------------------------------------------------------------------

def load_works_cited(book_dir):
    """Load author names and keywords from WORKS_CITED.md for matching."""
    works_cited_path = os.path.join(book_dir, 'WORKS_CITED.md')
    if not os.path.exists(works_cited_path):
        return []

    with open(works_cited_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract author names, book titles, and organization names
    cited_terms = []

    # Author names from bold entries: **Name, First.**
    for match in re.finditer(r'\*\*([^*]+?)\.\*\*', content):
        name = match.group(1).strip()
        # Extract last name (first part before comma)
        parts = name.split(',')
        if parts:
            cited_terms.append(parts[0].strip().lower())

    # Organization/tool names from bold entries
    for match in re.finditer(r'\*\*([^*]+?)\.\*\*', content):
        term = match.group(1).split(',')[0].strip()
        if term:
            cited_terms.append(term.lower())

    # Italic book titles: *Title*
    for match in re.finditer(r'\*([^*]{5,}?)\*', content):
        title = match.group(1).strip()
        if not title.startswith('Last updated'):
            cited_terms.append(title.lower())

    # Website/org names
    for match in re.finditer(r'\b(\w+\.(?:com|org|io|net))\b', content):
        cited_terms.append(match.group(1).lower())

    return list(set(cited_terms))


def is_cited_match(result, cited_terms):
    """Check if a search result matches a known citation."""
    text = (result.get('title', '') + ' ' + result.get('snippet', '')).lower()
    for term in cited_terms:
        if term in text:
            return True
    return False


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def format_text_report(all_results):
    """Format results as human-readable text."""
    lines = []
    lines.append('=' * 70)
    lines.append('PLAGIARISM SPOT-CHECK REPORT')
    lines.append('=' * 70)

    summary_counts = {
        'CLEAN': 0, 'CITED MATCH': 0, 'POTENTIAL MATCH': 0, 'SEARCH ERROR': 0,
    }

    for chapter_result in all_results:
        chapter = chapter_result['chapter']
        lines.append(f'\n--- {chapter} ---')

        for passage_result in chapter_result['passages']:
            phrase = passage_result['search_phrase']
            severity = passage_result['severity']
            summary_counts[severity] += 1

            if severity == 'CLEAN':
                lines.append(f'  [{severity}] "{phrase}"')
            elif severity == 'SEARCH ERROR':
                error = passage_result.get('error', 'unknown')
                lines.append(f'  [{severity}] "{phrase}"')
                lines.append(f'    -> {error}')
            elif severity == 'CITED MATCH':
                lines.append(f'  [{severity}] "{phrase}"')
                for r in passage_result['results'][:2]:
                    lines.append(f'    -> {r["title"][:80]}')
            else:
                lines.append(f'  [{severity}] "{phrase}"')
                for r in passage_result['results'][:3]:
                    lines.append(f'    -> {r["title"][:80]}')
                    if r['snippet']:
                        lines.append(f'       {r["snippet"][:100]}')

    lines.append('\n' + '=' * 70)
    lines.append('SUMMARY')
    lines.append(f'  Clean passages:     {summary_counts["CLEAN"]}')
    lines.append(f'  Cited matches:      {summary_counts["CITED MATCH"]}')
    lines.append(f'  Potential matches:  {summary_counts["POTENTIAL MATCH"]}')
    lines.append(f'  Search errors:      {summary_counts["SEARCH ERROR"]}')

    total = sum(summary_counts.values())
    lines.append(f'  Total checked:      {total}')
    lines.append('=' * 70)

    return '\n'.join(lines)


def format_json_report(all_results):
    """Format results as JSON."""
    return json.dumps(all_results, indent=2)


def format_dry_run(all_results):
    """Format dry-run output showing extracted passages."""
    lines = []
    for chapter_result in all_results:
        chapter = chapter_result['chapter']
        lines.append(f'\n=== {chapter} ===')
        lines.append(f'    Prose paragraphs found: {chapter_result["paragraph_count"]}')

        for i, passage_result in enumerate(chapter_result['passages'], 1):
            passage = passage_result['passage']
            phrase = passage_result['search_phrase']
            word_count = len(passage.split())
            lines.append(f'\n  Passage {i} ({word_count} words):')
            # Wrap passage text at ~76 chars
            words = passage.split()
            current_line = '    '
            for word in words:
                if len(current_line) + len(word) + 1 > 76:
                    lines.append(current_line)
                    current_line = '    ' + word
                else:
                    current_line += (' ' if current_line.strip() else '') + word
            if current_line.strip():
                lines.append(current_line)

            lines.append(f'  Search phrase: "{phrase}"')

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_chapters(book_dir, chapter_glob=None):
    """Find chapter markdown files, optionally filtered by glob pattern."""
    chapters_dir = os.path.join(book_dir, 'chapters')
    if not os.path.isdir(chapters_dir):
        print(f'Error: chapters directory not found: {chapters_dir}',
              file=sys.stderr)
        sys.exit(1)

    if chapter_glob:
        pattern = os.path.join(chapters_dir, chapter_glob)
        if not pattern.endswith('.md'):
            pattern += '.md'
        files = glob.glob(pattern)
    else:
        files = glob.glob(os.path.join(chapters_dir, '*.md'))

    return sorted(files)


def main():
    parser = argparse.ArgumentParser(
        description='Plagiarism spot-check for ebook chapters'
    )
    parser.add_argument('bookname', help='Name of the ebook to check')
    parser.add_argument(
        '--chapters',
        help='Glob pattern for specific chapters (e.g., "06-*")',
        default=None,
    )
    parser.add_argument(
        '--passages-per-chapter',
        type=int, default=5,
        help='Number of passages to check per chapter (default: 5)',
    )
    parser.add_argument(
        '--target-words',
        type=int, default=75,
        help='Target words per passage (default: 75)',
    )
    parser.add_argument(
        '--delay',
        type=float, default=5,
        help='Delay between web searches in seconds (default: 5)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show extracted passages without searching',
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json'], default='text',
        help='Output format (default: text)',
    )
    args = parser.parse_args()

    book_dir = os.path.join('ebooks', args.bookname)
    if not os.path.isdir(book_dir):
        print(f'Error: book directory not found: {book_dir}', file=sys.stderr)
        sys.exit(1)

    chapters = find_chapters(book_dir, args.chapters)
    if not chapters:
        print(f'Error: no chapters found', file=sys.stderr)
        sys.exit(1)

    cited_terms = load_works_cited(book_dir)

    all_results = []

    for chapter_path in chapters:
        chapter_name = os.path.basename(chapter_path)
        paragraphs = extract_prose_paragraphs(chapter_path)
        passages = select_passages(
            paragraphs, args.passages_per_chapter, args.target_words
        )

        chapter_result = {
            'chapter': chapter_name,
            'paragraph_count': len(paragraphs),
            'passages': [],
        }

        for passage in passages:
            phrase = extract_search_phrase(passage)
            passage_result = {
                'passage': passage,
                'search_phrase': phrase,
                'severity': 'CLEAN',
                'results': [],
            }

            if not args.dry_run:
                search = search_duckduckgo(phrase)
                results = search['results']
                passage_result['results'] = results

                if search['error']:
                    passage_result['severity'] = 'SEARCH ERROR'
                    passage_result['error'] = search['error']
                elif results:
                    if all(is_cited_match(r, cited_terms) for r in results):
                        passage_result['severity'] = 'CITED MATCH'
                    else:
                        passage_result['severity'] = 'POTENTIAL MATCH'

                # Rate limit
                time.sleep(args.delay)

            chapter_result['passages'].append(passage_result)

        all_results.append(chapter_result)

        if not args.dry_run:
            # Progress indicator
            print(f'  Checked {chapter_name} '
                  f'({len(passages)} passages)',
                  file=sys.stderr)

    # Output
    if args.dry_run:
        print(format_dry_run(all_results))
    elif args.format == 'json':
        print(format_json_report(all_results))
    else:
        print(format_text_report(all_results))


if __name__ == '__main__':
    main()
