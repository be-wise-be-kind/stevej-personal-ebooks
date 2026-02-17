# Productionizing ML Inference APIs - PR Breakdown

**Scope**: Complete ebook development from outline through publication, one PR per deliverable

---

## Overview
This document breaks down the ml-inference-apis ebook into 18 PRs. The approach is:
- **PR1**: Produce all outlines, submit for review
- **PR2-PR17**: Author one chapter at a time, submit each for review
- **PR18**: Write preface (last, since it references all chapters) + final polish

**Note**: Chapter 4 (Deployment Architecture Strategies) was inserted between Chapters 3 and 5, shifting all subsequent chapter and PR numbers by 1.

Each PR is designed to be:
- Self-contained and reviewable
- Builds incrementally toward the complete ebook
- Validated with `just validate ml-inference-apis`
- Includes research, authoring, diagrams, and citations for that chapter

---

## PR1: Outline Review

**Scope**: Produce the complete book skeleton for Steve's review before any authoring begins.

**Deliverables**:
1. `README.md` — Book metadata, overview, full TOC with links to all chapter files
2. `chapters/00-preface.md` — Section headings + bullet points (outline only)
3. `chapters/01-the-serving-problem.md` through `chapters/13-putting-it-all-together.md` — Each file contains:
   - `# Chapter N: Title` heading
   - `![Chapter N Opener](../assets/chNN-opener.html)` + `\newpage`
   - `## Overview` with 2-3 bullet points
   - Every `##` and `###` section heading planned
   - 2-5 bullet points under each heading describing planned content
   - Planned diagram references: `![Caption](../assets/chNN-name.html)`
   - Cross-references to other chapters and to Book 1
   - `## Summary` with planned key takeaways
   - `## References` placeholder
   - `**Next: [Chapter N+1: Title](link)**`
4. `WORKS_CITED.md` — One section per chapter with initial sources from research
5. `DIAGRAM_INVENTORY.md` — Complete inventory of planned diagram assets by chapter
6. `edits/CHAPTER_ASSIGNMENTS.md` — Per-chapter specs (key concepts, suggested diagrams, cross-refs, research topics)

**Research to consult**: All 8 topics in `research/RESEARCH_SUMMARY.md`

**Note on Chapter 1 (The Serving Problem)**: This is the most important outline. It's a comprehensive introduction (no narrative hook / fictional scenario — direct, informative exposition). The outline should be the most detailed of any chapter, with extensive section and subsection breakdowns. See PROPOSAL.md and AI_CONTEXT.md for guidance.

**Validation**:
- `just validate ml-inference-apis` passes
- All TOC links in README.md resolve to actual chapter files
- Every chapter file follows the conventions in AGENTS.md

**Review**: Steve reviews the complete outline before any authoring begins. May result in chapters being added, merged, split, or reordered.

---

## PR2: Chapter 1 — The Serving Problem

**Scope**: Author Chapter 1 in full prose. This is the most important chapter — it sets the tone and philosophy for the entire book.

**Content** (from outline, refined during authoring):
- The problem landscape: why ML inference serving is hard, what makes it different
- The industry context: LLM revolution, speech/audio AI renaissance, 2025-2026 state
- The difficulties: GPU costs, latency budgets, cold starts, model lifecycle, talent gap
- The innovations: continuous batching, PagedAttention, speculative decoding, streaming pipelines
- The business case: user experience, cost, competitive advantage
- The approach: measure-first methodology, serving not training, audio as running example
- Scope boundaries

**Research to consult**: Topics 1, 2, 3, 8 in RESEARCH_SUMMARY.md

**Diagrams to create**:
- ch01-opener.html
- ch01-latency-breakdown.html (inference request latency anatomy)
- ch01-serving-landscape.html (framework/ecosystem map)
- ch01-innovation-timeline.html (key innovations timeline)

**Cross-references**: Book 1 Ch 1 (The Empirical Discipline), Book 1 Ch 3 (Observability), Book 1 Ch 5 (Network)

**Validation**:
- Chapter follows conventions (heading, opener, sections, summary, next link)
- WORKS_CITED.md Chapter 1 section fully populated
- Diagrams created in assets/
- `just validate ml-inference-apis` passes

**Review**: Steve reviews full prose + diagrams before moving to PR3.

---

## PR3: Chapter 2 — Model Serving Frameworks

**Scope**: Author Chapter 2 in full prose.

**Content**:
- Framework landscape: 3 generations (TF Serving/TorchServe -> Triton/KServe/BentoML -> vLLM/TensorRT-LLM/SGLang)
- Selection criteria: model type, latency requirements, scaling model, operational complexity
- Model loading, versioning, hot-swapping
- Multi-model serving: GPU memory, MPS/MIG, ensemble pipelines
- When to build your own, the hybrid approach

**Research to consult**: Topic 1 in RESEARCH_SUMMARY.md

**Diagrams**:
- ch02-opener.html
- ch02-framework-decision-tree.html
- ch02-multi-model-architecture.html
- ch02-framework-generations.html

**Cross-references**: Forward to Ch 3 (GPU optimization), Ch 6 (inference pipelines)

---

## PR4: Chapter 3 — GPU Optimization & Cold Starts

**Scope**: Author Chapter 3 in full prose.

**Content**:
- GPU utilization: why GPUs sit idle, how to fix it
- Dynamic/continuous batching: collect requests, maximize throughput within latency budgets
- KV cache as the central bottleneck: PagedAttention, paging, quantization, reuse, offload
- Cold start anatomy: model loading, runtime init, container spin-up
- Mitigation: pre-warming, model caching, persistent GPU pools, snapshot/restore
- Quantization: FP16 -> FP8 -> FP4 -> INT4, quality tradeoffs
- Right-sizing GPU instances: cost vs latency

**Research to consult**: Topic 2 in RESEARCH_SUMMARY.md

**Diagrams**:
- ch03-opener.html
- ch03-batching-comparison.html (static vs dynamic vs continuous)
- ch03-kv-cache-paging.html (PagedAttention visualization)
- ch03-cold-start-anatomy.html
- ch03-quantization-tradeoffs.html

**Cross-references**: Book 1 Ch 9 (Compute & Scaling), forward to Ch 12 (Scaling)

---

## PR5: Chapter 4 — Deployment Architecture Strategies

**Scope**: Author Chapter 4 in full prose. NEW chapter inserted between GPU Optimization (Ch 3) and Streaming Audio Architecture (Ch 5).

**Status**: 🟢 Complete

**Content**:
- Three deployment patterns: shared cluster, container-per-model, platform template
- Infrastructure-as-code for ML deployments (Terraform module design, Helm charts)
- CI/CD for model deployments (4 key differences from code CI/CD)
- Namespace and tenant isolation (RBAC, network policies, resource quotas, GPU partitioning)
- The noisy neighbor problem (GPU interference patterns, detection, mitigation)
- Maturity evolution and migration signals

**Diagrams**:
- ch04-opener.html
- ch04-three-patterns.html
- ch04-platform-template.html
- ch04-cicd-pipeline.html
- ch04-noisy-neighbor.html
- ch04-maturity-evolution.html

**Cross-references**: Ch 2 (frameworks), Ch 3 (GPU optimization), Ch 15 (scaling), Book 1 Ch 9 (infrastructure scaling)

---

## PR6: Chapter 5 — Streaming Audio Architecture

**Scope**: Author Chapter 5 in full prose.

**Content**:
- End-to-end architecture: client -> audio capture -> transport -> inference -> response -> client
- Audio fundamentals for serving engineers: sample rates, bit depth, channels, codecs
- Chunk size selection: latency vs accuracy tradeoff (100ms vs 200ms vs 250ms)
- Voice Activity Detection (VAD): intelligent segmentation
- Buffering strategies: when to buffer, drop, or interpolate
- Reference architectures: how Deepgram, AssemblyAI, Google, Amazon, OpenAI architect streaming

**Research to consult**: Topics 3, 4 in RESEARCH_SUMMARY.md

**Diagrams**:
- ch05-opener.html
- ch05-e2e-architecture.html
- ch05-chunk-size-tradeoff.html
- ch05-provider-comparison.html

**Cross-references**: Book 1 Ch 5 (Network), forward to Ch 6 (protocols), Ch 7 (pipelines)

---

## PR7: Chapter 6 — Protocol Selection for Audio

**Scope**: Author Chapter 6 in full prose.

**Content**:
- WebSocket for audio: binary framing, backpressure, 33% bandwidth savings over base64
- gRPC bidirectional: protobuf for audio chunks, deadline propagation, Google's approach
- WebRTC: jitter buffers, NAT traversal, OpenAI's browser approach
- WebTransport: unreliable datagrams, head-of-line blocking elimination (future)
- Media over QUIC: not production-ready yet, timeline
- Decision framework: client constraints, latency targets, browser requirements

**Research to consult**: Topic 4 in RESEARCH_SUMMARY.md

**Diagrams**:
- ch06-opener.html
- ch06-protocol-decision-tree.html
- ch06-binary-vs-base64.html
- ch06-protocol-comparison-table.html

**Cross-references**: Book 1 Ch 5 (protocol fundamentals — recap + cross-ref)

---

## PR8: Chapter 7 — Streaming Inference Pipelines

**Scope**: Author Chapter 7 in full prose.

**Content**:
- Connecting transport layer to inference layer
- Request queuing and scheduling for streaming workloads
- Partial results and incremental decoding (word-by-word transcription)
- Handling multiple concurrent streams per server instance
- Graceful degradation under load: quality reduction vs rejection
- End-to-end latency tracing through the streaming pipeline

**Research to consult**: Topics 1, 3, 4 in RESEARCH_SUMMARY.md

**Diagrams**:
- ch07-opener.html
- ch07-streaming-pipeline.html
- ch07-concurrent-streams.html
- ch07-degradation-strategies.html

**Cross-references**: Book 1 Ch 3 (distributed tracing), Ch 2 (frameworks), Ch 5 (audio arch)

---

## PR9: Chapter 8 — Designing ML-Facing APIs

**Scope**: Author Chapter 8 in full prose.

**Content**:
- Resource-oriented design for inference (Google AIPs)
- Sync vs async patterns: short inference vs long-running operations (AIP-151)
- Streaming response design: SSE events (OpenAI pattern), WebSocket messages, gRPC streams
- Error handling for ML-specific failures: model not loaded, GPU OOM, inference timeout
- API versioning: URL path vs header vs content negotiation + model version mapping
- SDK and developer experience

**Research to consult**: Topic 5 in RESEARCH_SUMMARY.md

**Diagrams**:
- ch08-opener.html
- ch08-sync-vs-async-decision.html
- ch08-error-handling-taxonomy.html

**Cross-references**: Forward to Ch 9 (streaming response contracts), Book 1 Ch 10 (rate limiting)

---

## PR10: Chapter 9 — Streaming Response Contracts

**Scope**: Author Chapter 9 in full prose.

**Content**:
- Streaming response design patterns (SSE, WebSocket, gRPC)
- Connection lifecycle management
- Interim vs final results flow
- Backpressure and reconnection strategies

**Diagrams**:
- ch09-opener.html
- ch09-streaming-response-patterns.html
- ch09-connection-lifecycle.html
- ch09-interim-final-results.html

**Cross-references**: Ch 6 (Protocol Selection), Ch 8 (ML API Design)

---

## PR11: Chapter 10 — API Versioning & Developer Experience

**Scope**: Author Chapter 10 in full prose.

**Content**:
- API versioning strategies for ML APIs
- Two-axis versioning (API version vs model version)
- Developer journey and experience optimization

**Diagrams**:
- ch10-opener.html
- ch10-versioning-strategies.html
- ch10-two-axis-versioning.html
- ch10-developer-journey.html

---

## PR12: Chapter 11 — Security for Audio ML APIs

**Scope**: Author Chapter 11 in full prose.

**Content**:
- Auth for streaming connections: token-based WebSocket auth, per-stream gRPC auth
- API key management: generation, rotation, scoping, revocation
- OAuth2 flows for ML API access
- Rate limiting and abuse prevention for inference endpoints
- Securing audio data: encryption at rest and in transit
- PII in transcripts: detection, redaction, handling (Deepgram/AssemblyAI patterns)

**Research to consult**: Topic 7 in RESEARCH_SUMMARY.md

**Diagrams**:
- ch11-opener.html
- ch11-streaming-auth-flow.html
- ch11-api-key-lifecycle.html
- ch11-pii-redaction-pipeline.html

**Cross-references**: Book 1 Ch 11 (auth performance), Book 1 Appendix A (auth fundamentals)

---

## PR13: Chapter 12 — Compliance & Data Governance

**Scope**: Author Chapter 12 in full prose.

**Content**:
- SOC 2 for ML APIs: Trust Service Criteria applied to inference systems
- Audit logging: what to log, retention requirements
- Data retention and deletion for audio data
- GDPR/CCPA for stored audio and transcripts (voice = personal data)
- EU AI Act: timeline (Aug 2026 high-risk rules), requirements, penalties
- HIPAA for healthcare speech AI: encryption, BAAs, PHI redaction
- Data residency: keeping audio in the right geography
- Building compliance into architecture vs bolting on

**Research to consult**: Topic 7 in RESEARCH_SUMMARY.md

**Diagrams**:
- ch12-opener.html
- ch12-eu-ai-act-timeline.html
- ch12-compliance-matrix.html
- ch12-data-lifecycle.html

**Cross-references**: Ch 11 (security), forward to Ch 13 (SLOs for monitoring)

---

## PR14: Chapter 13 — SLOs for Streaming ML Systems

**Scope**: Author Chapter 13 in full prose.

**Content**:
- Streaming-specific SLIs: TTFT, TPOT, inter-token latency, jitter, connection drops, RTF
- Target numbers: TTFT <= 100ms (interactive), <= 300ms (speech), P95 Final <= 800ms
- Goodput: percentage of requests meeting SLOs (quality of throughput)
- Setting SLO targets: user experience vs infrastructure cost
- Error budgets for ML: model accuracy interacting with infrastructure reliability
- The 300ms rule for voice AI
- Monitoring and alerting on SLO burn rate

**Research to consult**: Topic 8 in RESEARCH_SUMMARY.md

**Diagrams**:
- ch13-opener.html
- ch13-streaming-sli-taxonomy.html
- ch13-slo-target-framework.html
- ch13-burn-rate-alerting.html

**Cross-references**: Book 1 Ch 3-4 (observability, monitoring), Book 1 Ch 2 (SLO fundamentals)

---

## PR15: Chapter 14 — Usage Metering & Billing

**Scope**: Author Chapter 14 in full prose.

**Content**:
- What to meter: audio seconds, API calls, compute time, tokens, characters
- Billing models: per-second vs per-block vs per-character (provider comparison)
- Metering architecture: idempotent events, aggregation pipelines
- Stripe Meters API integration (the new standard, legacy removed)
- OpenMeter as open-source alternative
- Rate limiting tied to billing tiers
- Feature-based pricing stacking
- Audit trail for usage disputes

**Research to consult**: Topic 6 in RESEARCH_SUMMARY.md

**Diagrams**:
- ch14-opener.html
- ch14-metering-architecture.html
- ch14-billing-model-comparison.html
- ch14-stripe-integration.html

**Cross-references**: Book 1 Ch 10 (rate limiting), forward to Ch 15 (scaling)

---

## PR16: Chapter 15 — Scaling Inference Globally

**Scope**: Author Chapter 15 in full prose.

**Content**:
- Horizontal scaling: adding GPU instances, load balancing inference requests
- Auto-scaling for inference: GPU utilization, queue depth, latency signals
- Multi-region deployment: model replication, request routing, data sovereignty
- Edge inference vs centralized: when to push models closer to users
- Cost optimization: spot/preemptible GPUs, right-sizing, scheduled scaling

**Research to consult**: Topics 1, 2 in RESEARCH_SUMMARY.md

**Diagrams**:
- ch15-opener.html
- ch15-autoscaling-signals.html
- ch15-multi-region-architecture.html
- ch15-cost-optimization-strategies.html

**Cross-references**: Book 1 Ch 9 (compute scaling), Book 1 Ch 12 (geographic optimization)

---

## PR17: Chapter 16 — Putting It All Together

**Scope**: Author Chapter 16 in full prose.

**Content**:
- Case study: building a production streaming speech API from scratch
- Architecture walkthrough: from audio input to transcription output
- Decision points: framework, protocol, API design, security, metering, compliance
- What goes wrong and how to recover
- Operational runbook patterns for ML inference systems

**Research to consult**: All topics in RESEARCH_SUMMARY.md (synthesis chapter)

**Diagrams**:
- ch16-opener.html
- ch16-complete-architecture.html
- ch16-decision-flowchart.html
- ch16-runbook-patterns.html

**Cross-references**: All previous chapters, Book 1 Ch 14 (Putting It All Together)

---

## PR18: Preface & Final Polish

**Scope**: Write the preface (last, since it references all chapters) and do final polish.

**Deliverables**:
1. `chapters/00-preface.md` — Full prose (Why This Book, Who For, How to Read, Relationship to Book 1, What Not Covered)
2. Final `WORKS_CITED.md` — Verify all citations, fill any gaps
3. Final `DIAGRAM_INVENTORY.md` — Update with actual diagram counts
4. Cross-reference audit: verify all chapter-to-chapter and book-to-book references
5. `just validate ml-inference-apis` passes
6. `just lint md ml-inference-apis` passes
7. Test build: `just build-all ml-inference-apis`

**Review**: Final review by Steve before publication.

---

## Implementation Guidelines

### Writing Standards
- Follow `.ai/docs/style-guide.md` for writing conventions
- Follow chapter conventions in AGENTS.md (headings, citations, callouts, code examples)
- Pseudocode, not production code
- `[Source: Author, Year]` inline citations

### Validation Requirements
- `just validate ml-inference-apis` must pass after every PR
- `just lint md ml-inference-apis` should pass
- All TOC links must resolve

### Quality Targets
- Each chapter: ~4000-6000 words of prose
- Each chapter: ~4 diagrams (HTML with embedded SVG)
- Total book: ~55,000-75,000 words
- Total diagrams: ~55-60
