# Roadmap Workflow Documentation

**Purpose**: Documentation of the roadmap-driven development workflow for ebook projects

**Scope**: Roadmap lifecycle, document structure, AI agent coordination, and workflow patterns

---

## Overview

The roadmap workflow is a systematic approach to planning, writing, and tracking ebooks that require sustained multi-session effort. It provides:

1. **Structured Planning** - Templates for comprehensive ebook development breakdown
2. **Progress Tracking** - Clear visibility into per-chapter and per-milestone status
3. **AI Agent Coordination** - Handoff documents for seamless continuation across sessions
4. **Lifecycle Management** - Organized progression from planning to completion

## Core Concepts

### Three-Document Structure

Every roadmap consists of three documents:

#### 1. PROGRESS_TRACKER.md
**Role**: Primary AI agent handoff document

**Contains**:
- Current milestone and next action
- Overall progress dashboard
- Per-chapter progress matrix (Research | Outline | Draft | Review | Diagrams | Final)
- Word count targets and actuals
- Diagram inventory tracking
- Update protocol

**Usage**: FIRST document AI agents read. Answers "Where are we?" and "What's next?"

#### 2. MILESTONE_BREAKDOWN.md
**Role**: Detailed milestone plans

**Contains**:
- Complete milestone breakdown with deliverables
- Chapter-by-chapter plans within each milestone
- Validation requirements per milestone
- Success criteria
- Dependencies between milestones

**Usage**: AI agents reference for detailed work plans after consulting PROGRESS_TRACKER.md.

#### 3. AI_CONTEXT.md
**Role**: Book architecture and context

**Contains**:
- Book vision and scope boundaries
- Relationship to other books in the collection
- Key design decisions and rationale
- Reference APIs, systems, and sources
- Writing conventions specific to this book

**Usage**: Provides deep context. AI agents read to understand "why" decisions were made.

### Why Three Documents?

**Separation of Concerns**:
- **PROGRESS_TRACKER.md** - Current state (changes after each work session)
- **MILESTONE_BREAKDOWN.md** - Development plan (stable after planning phase)
- **AI_CONTEXT.md** - Architecture context (stable, deep knowledge)

**AI Agent Efficiency**:
- Quick status check: Read PROGRESS_TRACKER.md only
- Detailed work guidance: Add MILESTONE_BREAKDOWN.md
- Architectural understanding: Add AI_CONTEXT.md

## Roadmap Lifecycle

### Phase 1: Planning
**Location**: `.roadmap/planning/[book-name]/`

**Activities**:
1. Create roadmap directory
2. Copy templates
3. Replace placeholders with book details
4. Define milestones and chapter plans
5. Set success criteria
6. Review and refine

**Completion Criteria**:
- All placeholders replaced
- Milestones defined with clear deliverables
- Success criteria measurable
- Ready to start writing

**Transition**: Move to `.roadmap/in-progress/`

### Phase 2: In-Progress
**Location**: `.roadmap/in-progress/[book-name]/`

**Activities**:
1. Read PROGRESS_TRACKER.md to identify next milestone
2. Reference MILESTONE_BREAKDOWN.md for detailed plans
3. Work through chapters within the milestone
4. Update PROGRESS_TRACKER.md after each session
5. Run `just validate` and `just lint md` regularly

**Update Protocol** (after each work session):
- Update chapter progress matrix
- Update word count actuals
- Update diagram counts
- Note any blockers or changes
- Commit changes

**Transition**: Move to `.roadmap/complete/` when done

### Phase 3: Complete
**Location**: `.roadmap/complete/[book-name]/`

**Activities**:
1. Final PROGRESS_TRACKER.md update
2. Document learnings
3. Archive for future reference

## AI Agent Coordination

### Handoff Protocol

**Starting Work**:
1. Check `.roadmap/in-progress/` for active roadmaps
2. Read PROGRESS_TRACKER.md FIRST
3. Note "Next Milestone to Work On"
4. Read MILESTONE_BREAKDOWN.md for that milestone
5. Reference AI_CONTEXT.md for architectural context

**During Work**:
1. Follow MILESTONE_BREAKDOWN.md plans
2. Track deviations in PROGRESS_TRACKER.md
3. Document blockers immediately
4. Validate with `just validate` regularly

**After Work**:
1. Update PROGRESS_TRACKER.md immediately
2. Update chapter progress matrix
3. Set next milestone/chapter to work on
4. Commit roadmap updates

## Workflow Patterns

### Pattern 1: Sequential Chapter Writing
**Use Case**: Writing chapters in order (most common for ebooks)

1. Complete chapter research
2. Write chapter outline
3. Write full draft
4. Self-review
5. Create diagrams
6. Move to next chapter

### Pattern 2: Research-First
**Use Case**: New ebook requiring significant research before writing

1. Complete all research for all chapters
2. Produce all chapter outlines
3. Write chapters with research as reference
4. Review and polish

### Pattern 3: Iterative Refinement
**Use Case**: Content evolves during writing

1. Write initial chapters
2. Discover new insights
3. Update AI_CONTEXT.md with decisions
4. Adjust remaining chapter plans
5. Continue with refined plan

## Integration Points

### With AGENTS.md
AGENTS.md contains a "Roadmap-Driven Development" section pointing to:
- This workflow document
- How-to guide (`.ai/howto/how-to-roadmap.md`)
- Templates (`.ai/templates/roadmap-*.md.template`)

### With Build System
Validate ebook structure during milestones:
```bash
just validate [book-name]    # Check structure
just lint md [book-name]     # Check markdown formatting
just build [book-name] pdf   # Test PDF build
```

### With Templates
Roadmap templates in `.ai/templates/`:
- `roadmap-progress-tracker.md.template`
- `roadmap-milestone-breakdown.md.template`
- `roadmap-ai-context.md.template`

## Common Scenarios

### Scenario 1: New Ebook
1. Create roadmap in planning/
2. Define milestones (Outline -> Draft -> Review -> Polish -> Publish)
3. Move to in-progress/
4. Work through milestones
5. Archive to complete/

### Scenario 2: Resuming Work After Break
1. Read PROGRESS_TRACKER.md
2. Find "Next Milestone to Work On"
3. Check chapter progress matrix
4. Continue from where you left off
5. Update PROGRESS_TRACKER.md after session

### Scenario 3: Chapter Needs Major Revision
1. Document in PROGRESS_TRACKER.md notes
2. Reset chapter status in progress matrix
3. Update MILESTONE_BREAKDOWN.md if scope changes
4. Continue with revised plan

## Quality Metrics

### Planning Quality
- All milestones have clear deliverables
- Success criteria are measurable (`just validate` passes)
- Chapter plans are detailed enough for AI agent continuation

### Writing Quality
- `just validate [book-name]` passes
- `just lint md [book-name]` passes
- All TOC links resolve to actual files
- Citations are properly formatted
- Cross-references are accurate

### Completion Quality
- All milestones achieved
- All output formats build successfully
- PROGRESS_TRACKER.md shows 100%
- Roadmap archived to complete/
