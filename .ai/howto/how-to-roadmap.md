# How to Use Roadmaps for Ebook Development

**Purpose**: Guide for creating and managing roadmaps in the ebooks project

**Quick Start**: Roadmaps help plan and track complex ebook development through structured templates and lifecycle management.

---

## What Are Roadmaps?

Roadmaps are structured planning documents that break down ebook development into manageable, trackable milestones. They provide:

- **Comprehensive planning** before writing begins
- **Progress tracking** across chapters and milestones
- **AI agent coordination** through handoff documents
- **Context preservation** across writing sessions

## When to Use Roadmaps

Use roadmaps for:

- **New Ebooks** - Planning and tracking a full ebook from outline to publication
- **Major Revisions** - Significant rewrites spanning multiple chapters
- **Multi-Phase Projects** - Work spanning research, outlining, drafting, and review

Don't use roadmaps for:

- **Minor Edits** - Typo fixes or small chapter updates
- **Single Chapter Work** - Unless it requires extensive research

## Roadmap Structure

Every roadmap follows a **three-document structure**:

### 1. PROGRESS_TRACKER.md (Required)
**The primary AI agent handoff document**

- Current milestone and next action
- Overall progress dashboard
- Per-chapter progress matrix (Research | Outline | Draft | Review | Diagrams | Final)
- Word count and diagram tracking
- AI agent instructions

**This is the FIRST document AI agents read when continuing work.**

### 2. MILESTONE_BREAKDOWN.md (Required)
**Detailed milestone plans**

- Complete milestone breakdown with deliverables
- Chapter-by-chapter plans within each milestone
- Validation requirements
- Success criteria for each milestone

### 3. AI_CONTEXT.md (Optional but recommended)
**Book architecture context**

- Book vision and scope
- Relationship to other books
- Key design decisions
- Reference APIs and systems
- Research sources

## Roadmap Lifecycle

Roadmaps move through three phases:

```
PLANNING -> IN-PROGRESS -> COMPLETE
```

### 1. Planning Phase
**Location**: `.roadmap/planning/[book-name]/`

Activities:
- Create roadmap from templates
- Fill in all placeholders
- Break development into milestones
- Define success criteria
- Review and refine plan

### 2. In-Progress Phase
**Location**: `.roadmap/in-progress/[book-name]/`

Activities:
- Work through milestones sequentially
- Update PROGRESS_TRACKER.md after each milestone
- Track per-chapter progress
- Document blockers and notes
- Adjust plan if needed

### 3. Complete Phase
**Location**: `.roadmap/complete/[book-name]/`

Activities:
- Archive completed roadmap
- Preserve for future reference
- Extract learnings and patterns

## Creating a New Roadmap

### Step 1: Create Roadmap Directory

```bash
mkdir -p .roadmap/planning/[book-name]
```

### Step 2: Copy Templates

```bash
cp .ai/templates/roadmap-progress-tracker.md.template .roadmap/planning/[book-name]/PROGRESS_TRACKER.md
cp .ai/templates/roadmap-milestone-breakdown.md.template .roadmap/planning/[book-name]/MILESTONE_BREAKDOWN.md
cp .ai/templates/roadmap-ai-context.md.template .roadmap/planning/[book-name]/AI_CONTEXT.md
```

### Step 3: Fill in Placeholders

Edit each file and replace `{{PLACEHOLDER}}` values with book-specific details.

### Step 4: Define Milestones

Typical ebook milestones:

| Milestone | Description |
|-----------|-------------|
| M1: Outline Complete | Research done, chapter outlines finalized, bibliography skeleton |
| M2: First Draft | Full prose for all chapters, pseudocode examples |
| M3: Technical Review | Accuracy review, citation verification, gap analysis |
| M4: Diagrams & Polish | All diagrams finalized, formatting consistency |
| M5: Publication | Final proofread, build validation, release |

### Step 5: Move to In-Progress

When ready to start:

```bash
mv .roadmap/planning/[book-name] .roadmap/in-progress/
```

## Continuing an Existing Roadmap

### Step 1: Find Active Roadmaps

```bash
ls .roadmap/in-progress/
```

### Step 2: Read PROGRESS_TRACKER.md

**Always read this document FIRST:**

Key sections:
- **Current Status** - Where we are
- **Next Milestone to Work On** - What to do next
- **Chapter Progress Matrix** - Per-chapter status

### Step 3: Follow Milestone Instructions

Go to `MILESTONE_BREAKDOWN.md` and find the milestone from PROGRESS_TRACKER.md.

### Step 4: Update PROGRESS_TRACKER.md

After completing work, update:
1. Milestone status
2. Chapter progress matrix
3. Word count and diagram counts
4. "Next Milestone to Work On" section
5. Overall progress percentage

## Completing a Roadmap

When all milestones are done:

1. Final PROGRESS_TRACKER.md update (100%)
2. Move to complete: `mv .roadmap/in-progress/[book-name] .roadmap/complete/`
3. Update project documentation

## Validation

Always validate ebook structure during and after milestones:

```bash
just validate [book-name]
just lint md [book-name]
```

## Resources

- **Roadmap Templates**: `.ai/templates/roadmap-*.md.template`
- **Workflow Documentation**: `.ai/docs/ROADMAP_WORKFLOW.md`
- **Active Roadmaps**: `.roadmap/in-progress/`
- **Completed Roadmaps**: `.roadmap/complete/`
