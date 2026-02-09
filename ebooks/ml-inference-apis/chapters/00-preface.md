# Preface {-}

## Why This Book {-}

- The gap between training a model and serving it in production is where most organizations struggle
- No single resource synthesizes the serving engineer's perspective -- knowledge is scattered across vendor docs, conference talks, and tribal knowledge
- This book bridges ML infrastructure and API engineering for the serving use case

## Who This Book Is For {-}

- Backend engineers moving into ML infrastructure
- Platform engineers building inference platforms
- SREs responsible for ML system SLOs
- Technical leaders evaluating inference infrastructure decisions
- API engineers working on speech/audio/real-time ML products

## What You'll Learn {-}

- How to deploy trained ML models behind production-grade inference APIs
- How to build real-time audio streaming pipelines with sub-second latency
- How to select protocols, design APIs, implement metering, and meet compliance requirements for ML services
- How to set meaningful SLOs and scale inference globally

## How to Read This Book {-}

- Five parts, each building on the previous: Foundations → Audio Streaming → API Design → Enterprise → Scale
- Part I (Chapters 1-3) is essential for all readers -- establishes the problem, frameworks, and GPU fundamentals
- Parts II-IV can be read selectively based on your role and immediate needs
- Part V synthesizes everything into a complete system
- Each chapter is self-contained enough to be a useful reference on its own

## Relationship to "Before the 3 AM Alert" {-}

- This is a companion book, not a replacement
- Book 1 covers foundational API performance: observability, caching, protocols, scaling, auth
- This book builds on that foundation for ML inference serving
- Where we need Book 1 concepts, we provide a brief recap and explicit cross-reference
- You'll benefit from having read Book 1, but this book stands alone

## What This Book Does Not Cover {-}

- Model training, hyperparameter tuning, or experiment tracking
- Data pipelines, feature stores, or data labeling
- ML model architecture design
- Frontend/client SDK implementation (beyond the API contract)
- Comprehensive security beyond ML/audio-specific concerns

## Conventions Used {-}

- Pseudocode over production code -- AI has commoditized code generation; the concepts matter more
- `[Source: Author, Year]` citations for all factual claims, with full details in References sections
- Cross-references to Book 1 formatted as: "For a deep dive on [topic], see 'Before the 3 AM Alert' Chapter N"
- Real-world provider examples (Deepgram, AssemblyAI, Google, OpenAI, Amazon, ElevenLabs) throughout
- The 300ms rule for voice AI referenced as a recurring threshold
