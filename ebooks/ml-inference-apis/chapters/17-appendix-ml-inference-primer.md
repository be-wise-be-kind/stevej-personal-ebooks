# Appendix A: ML Inference for API Engineers {-}

This appendix provides the ML inference background you need to read this book. If you are an API engineer who has not worked with ML systems before, start here. Every concept in this appendix appears in the main chapters, and spending 30 to 45 minutes with this material will make the rest of the book significantly easier to follow. If you already have ML infrastructure experience, skip this appendix and proceed directly to Chapter 1.

![ML Inference Primer](../assets/ch17-opener.html)

\newpage

## The Restaurant Kitchen {-}

Every concept in this appendix maps to a single metaphor: a restaurant kitchen.

A restaurant is a request/response system. A customer (client) sends an order (request) to the kitchen (server). The kitchen processes the order using recipes and ingredients (model and weights), and delivers a finished dish (response). The kitchen has limited counter space (GPU memory), specialized equipment (GPUs), and a staff that works most efficiently when cooking multiple dishes at once (batching).

This is not a perfect metaphor, and we will note where it breaks down. But it provides a framework for understanding ML inference that builds on something API engineers already intuit: how systems process requests under resource constraints.

Each section below introduces one ML concept using the kitchen analog, then explains the technical reality and its implications for the systems you will build.

## What Is a Model? {-}

**The kitchen analog:** A model is the restaurant's recipe book combined with all its pre-measured, pre-prepared ingredients. The recipes describe the steps; the ingredients are what make the food taste the way it does. Without the ingredients, the recipes are useless instructions. Without the recipes, the ingredients are just raw material.

**The technical reality:** A machine learning model is a file (or collection of files) containing two things: an architecture that defines the computation graph (the recipe), and weights that encode learned patterns from training data (the ingredients). The weights are numerical parameters, often billions of them, that were adjusted during training to produce useful outputs from inputs.

The critical insight for API engineers is that a model is data, not code. Your Go binary is 50 to 200 MB of compiled instructions. A model file is 1 to 140 GB of floating-point numbers. Loading a model is not like starting a process; it is like loading an enormous dataset into memory before your service can handle its first request.

![Model Anatomy](../assets/ch17-model-anatomy.html)

\newpage

Size comparisons make this concrete:

| Artifact | Typical Size |
|---|---|
| Go/Rust API binary | 50–200 MB |
| Node.js application (with dependencies) | 200–500 MB |
| Whisper-large-v3 (speech recognition) | 3 GB |
| Llama 3 8B (language model) | 16 GB |
| Llama 3 70B (language model) | 140 GB |

When someone says "deploy a model," they mean: move this multi-gigabyte file from storage into GPU memory so the system can use it to process requests. The size of the model directly determines how long startup takes, how much GPU memory is required, and which GPU hardware can even fit it.

> **Where the metaphor breaks down:** A recipe book is readable and interpretable. Model weights are opaque. You cannot look at a model's billions of floating-point numbers and understand what it "knows." This opacity has real engineering implications: when a model produces unexpected output, you cannot debug it the way you debug code. You can only observe inputs and outputs.

**Referenced in:** Chapters 1, 2, 3, 8

## Inference: The Forward Pass {-}

**The kitchen analog:** Inference is cooking a dish. A customer sends an order, and the kitchen follows the recipe using its pre-prepared ingredients to produce the finished dish. Training, by contrast, is the months the head chef spent developing the recipe: testing ingredient combinations, adjusting proportions, iterating until the result was good enough to serve.

**The technical reality:** Inference (also called a forward pass) is the process of feeding input data through a model's weights to produce an output. Audio bytes go in; a transcript comes out. A text prompt goes in; generated tokens come out. The computation flows in one direction through the model's layers, hence "forward pass."

Training is the process that created those weights in the first place, using massive datasets and significant compute over days or weeks. But here is what matters for API engineers: training happens once (or periodically). Inference happens millions of times per day. Over a model's production lifetime, inference costs dwarf training costs [Source: Ankur's Newsletter, 2025].

![Training vs Inference](../assets/ch17-training-vs-inference.html)

\newpage

This distinction shapes the entire infrastructure. Training optimizes for throughput: process as much data as possible, time is secondary. Inference optimizes for latency: each individual request must be fast. The engineering challenges are fundamentally different, and this book is entirely about the inference side.

> **Where the metaphor breaks down:** In a real kitchen, the chef improvises and adjusts. A model's forward pass is deterministic given the same input and the same random seed. There is no creativity in the computation, only the illusion of it produced by very large matrix multiplications.

**Referenced in:** Chapters 1, 3, 6

## GPUs: The Industrial Kitchen {-}

**The kitchen analog:** A GPU is an industrial kitchen with 10,000 line cooks who each perform one simple task extremely fast. A CPU is a home kitchen with one master chef who can do anything but only one dish at a time. The industrial kitchen is dramatically faster when you need 500 identical dishes, but it costs far more to rent and sits expensively idle when there are no orders.

**The technical reality:** GPUs (Graphics Processing Units) excel at ML inference because inference is fundamentally matrix multiplication, and GPUs contain thousands of cores optimized for parallel arithmetic. A modern CPU has 8 to 64 cores. A modern inference GPU has over 10,000 CUDA cores. For the kind of computation that inference requires, a GPU is 10 to 100 times faster than a CPU.

![CPU vs GPU](../assets/ch17-cpu-vs-gpu.html)

\newpage

But this performance comes at a cost:

| Resource | CPU Instance | GPU Instance |
|---|---|---|
| Cores | 8–64 general-purpose | 10,000+ specialized |
| Memory | 64–256 GB system RAM | 16–192 GB VRAM |
| Hourly cost | $0.10–0.50 | $1.50–7.00+ |
| Cost per idle hour | Negligible | Painful |

**VRAM (Video RAM)** is the GPU's local memory. It is fast but finite, and everything the GPU needs must fit in VRAM: the model weights, the intermediate computation state, and the per-request caches. VRAM is the single most constraining resource in inference serving, analogous to counter space in the kitchen. You can have the fastest line cooks in the world, but if there is no counter space to prep, they stand idle.

This cost asymmetry drives nearly every optimization in this book. An idle GPU is money on fire. An idle CPU is a rounding error. The relentless focus on GPU utilization, batching, memory management, and scaling policies all stem from this economic reality.

> **Where the metaphor breaks down:** Line cooks can do different things simultaneously. GPU cores execute the same instruction on different data (SIMD architecture). This uniformity is what makes GPUs fast at matrix math and slow at branching logic. You cannot assign one CUDA core to "make salad" and another to "grill steak"; they all execute the same operation in lockstep.

**Referenced in:** Chapters 1, 3, 12, 14

## Tokens: How ML Sees Your Data {-}

**The kitchen analog:** Tokens are pre-portioned ingredients. The kitchen does not work with "some flour" and "a bit of butter." It works with precisely measured portions: 200g of flour, 50g of butter. Similarly, ML models do not process raw text or audio. They process sequences of tokens: standardized, numbered units that the model's vocabulary defines.

**The technical reality:** Tokenization is the process of converting raw input into the discrete units a model understands. For text, a tokenizer splits strings into subword pieces: "tokenization" might become ["token", "ization"]. For audio, the input is split into fixed-duration frames, typically 10 to 30 milliseconds each. Different models use different tokenizers with different vocabularies, so the same text produces different token sequences depending on the model.

![Tokenization](../assets/ch17-tokenization.html)

\newpage

Tokens matter to API engineers for three reasons:

**Tokens are the unit of cost.** Providers charge per token. OpenAI charges per input and output token. Deepgram charges per second of audio (which maps to a fixed number of audio frames). Understanding tokenization is understanding your cost model.

**Tokens are the unit of latency.** Generating each output token takes time. A 200-token response takes roughly 200 times longer than a 1-token response. Time-to-first-token (TTFT) and time-per-output-token (TPOT) are the latency metrics that matter, and both are denominated in tokens.

**Tokens are the unit of memory.** Each token in the model's context consumes GPU memory (via the KV cache, covered later). More tokens in context means more memory consumed, which means fewer concurrent requests the GPU can handle.

> **Where the metaphor breaks down:** Pre-portioned ingredients are interchangeable across recipes. Tokens are model-specific. A token ID of 42 means completely different things to different models. You cannot take tokens from one model and feed them to another.

**Referenced in:** Chapters 1, 3, 6, 7, 12, 13

## Latency in ML: Where the Milliseconds Go {-}

**The kitchen analog:** When a customer orders a dish, the wait time includes: the waiter walking to the kitchen (network transit), waiting for an available station (queue wait), prepping the ingredients (preprocessing), the actual cooking (GPU inference), plating (postprocessing), and the waiter bringing it back (network return). In a traditional restaurant, cooking dominates. In a fast-food kitchen, everything else dominates. ML inference latency works the same way: the dominant phase shifts depending on the workload.

**The technical reality:** Inference latency is not a single number. It is a pipeline with distinct phases, and different phases dominate depending on whether you are doing text generation, speech recognition, or text-to-speech.

![Latency Comparison](../assets/ch17-latency-comparison.html)

\newpage

For text generation (LLMs), two metrics matter most:

- **Time to First Token (TTFT)**: How long until the first output token appears. This is the "prefill" phase where the model processes all input tokens at once. TTFT determines perceived responsiveness.
- **Time Per Output Token (TPOT)**: How long each subsequent token takes. This is the "decode" phase where the model generates one token at a time. TPOT determines streaming speed.

For a traditional API, latency is typically 10 to 200 ms end-to-end, dominated by database queries and network hops. For ML inference, latency ranges from 50 ms to several seconds, dominated by GPU computation. The 300ms threshold for voice AI [Source: AssemblyAI, 2025] is extremely tight when your GPU computation alone may consume 50 to 200 ms.

The takeaway for API engineers: the latency optimization toolkit is different. You cannot cache inference results the way you cache database queries (every input is unique). You cannot add read replicas (GPUs are expensive). The optimization levers are batching, quantization, caching intermediate state, and choosing the right model size, all covered in later sections and chapters.

**Referenced in:** Chapters 1, 3, 5, 6, 12

## Batching: The Bus, Not the Taxi {-}

**The kitchen analog:** If every customer's order goes to a dedicated cook who makes only that dish, most cooks are idle most of the time. But if the kitchen collects orders that arrive within a short window and cooks them together, sharing heat, oil, and prep work, throughput increases dramatically with minimal latency impact. This is batching: the bus, not the taxi.

**The technical reality:** The model weights are already in GPU memory (loaded once at startup, as covered in the Model Loading section). So why not process one request at a time? Because the bottleneck is not the weights sitting in VRAM — it is moving them from VRAM into the GPU's compute cores. Every inference pass reads the entire model (7 GB for a 7B model at FP8) through the memory bus. For a single request, you move 7 GB of weights, do a small amount of math, and produce one output. For a batch of 8 requests, you move the same 7 GB once and produce 8 outputs. The weight transfer — not the compute — is the bottleneck, and batching amortizes it.

On top of the memory bandwidth issue, a GPU has over 10,000 cores. A single request does not saturate them; most cores sit idle while a few do the work. Batching fills those idle cores with useful work at near-zero additional latency cost. A GPU processing a batch of 8 finishes in barely more time than it takes to process 1. Sending one request at a time to a GPU is like sending a taxi for every passenger. Batching is the bus.

![Batching Strategies](../assets/ch17-batching-strategies.html)

\newpage

Three generations of batching have evolved:

**Static batching** collects a fixed number of requests, processes them together, and returns all results at once. Simple but wasteful: short requests wait for long ones to finish, and the GPU idles while collecting enough requests to fill the batch.

**Dynamic batching** collects requests within a time window (say, 50 ms) and processes whatever has arrived. Better than static, but the GPU still processes the entire batch as a unit, meaning short requests are held hostage by long ones.

**Continuous batching** (also called iteration-level batching) is the breakthrough. The GPU processes one iteration (one token) at a time across all active requests. When a request finishes, a new request immediately takes its slot. No request waits for others to complete; no GPU cycles are wasted. This is the technique that makes high-throughput, low-latency serving practical [Source: Yu et al., 2022].

For API engineers, continuous batching is the most important GPU optimization to understand. It is the reason modern inference servers can serve hundreds of concurrent requests on a single GPU. It is analogous to how an event loop handles concurrent connections without threads: by interleaving work at a fine granularity.

**Referenced in:** Chapters 1, 3, 14

## The KV Cache: Your Inference Scratchpad {-}

**The kitchen analog:** Mise en place: the prepped, portioned ingredients arranged at each station. When a chef is making a complex dish and reaches step 7, they do not go back and re-chop every vegetable from step 1. The prep work is right there on the counter. The KV cache is the inference equivalent: previously computed state kept in GPU memory so the model does not recompute it for every new token.

**The technical reality:** When a transformer model generates text, it produces key and value vectors at each layer for every token in the sequence. These vectors are needed for the attention mechanism (covered in a later section). Without caching, the model would recompute these vectors for all previous tokens every time it generates a new token. With the KV cache, the model stores these vectors and only computes new ones for each new token.

![KV Cache Memory](../assets/ch17-kv-cache-memory.html)

\newpage

The KV cache is the central memory bottleneck in inference serving. Here is why:

- Model weights are fixed. A 7B parameter model always uses the same amount of VRAM for its weights.
- KV caches are per-request and grow with context length. Each concurrent user's conversation consumes VRAM proportional to how many tokens have been generated so far.
- At high concurrency, KV cache memory can exceed model weight memory. A model using 14 GB for weights might need 30+ GB for KV caches across 50 concurrent users.

This is why GPU memory management is the defining challenge of inference serving. **PagedAttention** [Source: Kwon et al., 2023] addressed this by borrowing virtual memory concepts from operating systems: instead of allocating contiguous memory blocks for each request's KV cache, it allocates fixed-size pages and maps them dynamically. This reduced memory waste from fragmentation by up to 55% and enabled significantly higher concurrency.

For API engineers, the KV cache explains several behaviors you will observe: why longer conversations use more GPU memory, why concurrent user limits exist, why context window limits are enforced, and why "memory pressure" is the most common cause of inference quality degradation.

> **Where the metaphor breaks down:** Mise en place on a counter is visible and manageable. KV caches are invisible, growing, and can silently crowd out other work. A chef sees when counter space is running out. A GPU silently degrades performance or crashes with an out-of-memory error.

**Referenced in:** Chapters 1, 3, 6, 12, 14

## Model Loading: Why Startup Takes Minutes {-}

**The kitchen analog:** Opening a restaurant in the morning takes time. You unlock the doors, turn on the ovens, light the burners, wait for them to reach temperature, pull ingredients from the walk-in, portion them into station containers, and run a test dish to make sure everything works. You cannot serve customers the moment you walk in. Model loading is opening the kitchen, and it takes far longer than you expect.

**The technical reality:** When an inference server starts, it goes through a sequence of steps that collectively take 30 seconds to several minutes:

![Cold Start Timeline](../assets/ch17-cold-start-timeline.html)

\newpage

1. **Container startup** (1–5 seconds): The container runtime pulls the image and starts the process. Standard for any containerized service.
2. **CUDA initialization** (2–5 seconds): The GPU driver initializes the CUDA context, allocates GPU resources, and establishes communication with the GPU hardware.
3. **Model weight loading** (10 seconds to several minutes): The multi-gigabyte model file is read from storage and loaded into GPU VRAM. This is the dominant phase. Loading 14 GB of model weights from network-attached storage at 1 GB/s takes 14 seconds minimum.
4. **Warmup inference** (2–10 seconds): The first inference pass compiles CUDA kernels and warms up caches. Without this, the first real request would experience 5 to 10 times normal latency.

Compare this to a Go web server: compile, start, ready to serve in 50 to 200 ms. The difference is 100 to 1,000 times slower startup.

A critical detail: once the weights are in GPU memory, they stay there. The model is loaded once and then serves every subsequent request — thousands or millions of them — without reloading. This is why batching works: the recipe and ingredients are already on the counter, and the kitchen just cooks multiple dishes simultaneously using what is already laid out. The cold start cost is enormous but you pay it only once per server instance. Everything after that first load is fast inference.

This cold start penalty fundamentally changes how you think about auto-scaling. In traditional API infrastructure, scaling up means spinning up a new container in seconds. In ML inference, scaling up means waiting 30 seconds to several minutes before the new instance can serve traffic. You cannot react to a traffic spike; you must predict it or maintain warm capacity. Chapter 3 covers cold start mitigation in depth, and Chapter 14 covers the scaling policies that account for it.

> **Where the metaphor breaks down:** A restaurant opens once per day. Inference servers may cold-start many times: on deployments, scale-up events, hardware failures, and spot instance preemptions. The "morning" can happen at any time, and your users experience the delay.

**Referenced in:** Chapters 1, 3, 14

## Quantization: Smaller Numbers, Faster Math {-}

**The kitchen analog:** A recipe calls for 2.3847 grams of salt. The head chef says: "Just use about 2.5 grams. Nobody will taste the difference." By rounding to fewer decimal places, the measurement is faster, the scale can be cheaper, and the dish is nearly identical. Quantization applies this principle to model weights: use lower-precision numbers that take less memory and compute faster, with minimal quality loss.

**The technical reality:** Model weights are stored as floating-point numbers. The precision of those numbers determines memory usage and compute speed:

![Precision Spectrum](../assets/ch17-precision-spectrum.html)

\newpage

| Precision | Bits per Weight | Memory for 7B Model | GPU Tier |
|---|---|---|---|
| FP32 | 32 bits | 28 GB | Multi-GPU required |
| FP16 / BF16 | 16 bits | 14 GB | High-end consumer or data center |
| FP8 | 8 bits | 7 GB | Current production standard |
| INT4 | 4 bits | 3.5 GB | Consumer GPUs, mobile |

Each halving of precision roughly halves memory usage and increases throughput. FP8 has emerged as the production standard in 2025–2026, offering 4x memory reduction from FP32 with quality that is indistinguishable for most inference tasks [Source: NVIDIA, 2024].

The quality impact of quantization is task-specific. For speech recognition, FP8 quantization has negligible impact on word error rate. For nuanced text generation where subtle word choice matters, aggressive quantization (INT4) can degrade quality noticeably. The right precision depends on your task, your quality requirements, and your hardware budget.

For API engineers, quantization explains why the same model can run on vastly different hardware depending on how it is quantized, why you might offer different quality tiers at different price points, and why "model size" is not a fixed number but a range depending on precision.

**Referenced in:** Chapters 1, 3, 14

## The Attention Mechanism: What Transformers Actually Do {-}

**The kitchen analog:** Imagine a translator interpreting a long speech. For every new sentence the speaker says, the translator glances back at everything the speaker has said so far to ensure the translation is coherent. The longer the speech, the more the translator must look back, and the slower translation gets. This "looking back at everything" is the attention mechanism.

**The technical reality:** The attention mechanism is the core innovation of the transformer architecture that powers modern language and speech models [Source: Vaswani et al., 2017]. For each new token the model processes, it computes how much "attention" to pay to every previous token in the sequence. This is what allows the model to understand context: it can relate a word at position 500 to a word at position 3.

![Attention Simplified](../assets/ch17-attention-simplified.html)

\newpage

The computation is essentially a weighted lookup across all previous tokens. For each new token, the model:

1. Creates a query vector ("what am I looking for?")
2. Compares it against key vectors from all previous tokens ("what does each previous token offer?")
3. Uses the similarity scores to weight the value vectors from all previous tokens
4. Combines the weighted values into a context-aware representation

This is why the KV cache exists: the key and value vectors are stored so they are not recomputed for every new token.

The cost implications are significant. Attention is quadratic with sequence length in the simplest formulation: doubling the context length quadruples the attention computation. Optimizations like FlashAttention [Source: Dao et al., 2022] reduce the memory overhead, but the fundamental scaling relationship means that longer contexts are more expensive to serve.

For API engineers, attention explains three things you will encounter repeatedly: why longer conversations cost more, why context window limits exist, and why the KV cache is the dominant memory consumer. When you see "context length" in an API specification, it is describing how far back the attention mechanism can look.

> **Where the metaphor breaks down:** The translator metaphor suggests sequential processing. In practice, attention over previous tokens happens in parallel across all attention heads and layers, which is precisely why GPUs are effective at it.

**Referenced in:** Chapters 1, 3, 6

## Audio Fundamentals: Sample Rates, Codecs, and PCM {-}

**The kitchen analog:** This section does not map cleanly to the kitchen metaphor, so we will use a direct analogy instead. Audio encoding is like image encoding: raw, uncompressed data is huge, and different compression formats offer different tradeoffs between size and quality.

**The technical reality:** Digital audio is a sequence of amplitude samples taken at regular intervals. The two parameters that define audio quality are:

- **Sample rate**: How many samples per second. 16 kHz (16,000 samples/second) is standard for speech recognition. 44.1 kHz is CD quality. 48 kHz is professional audio.
- **Bit depth**: How many bits per sample. 16-bit is standard for speech. This gives 65,536 possible amplitude values per sample.

At 16 kHz / 16-bit (the standard for speech recognition), raw PCM audio consumes 256 kilobits per second (32 KB/s). One minute of audio is approximately 1.9 MB.

![Audio Encoding](../assets/ch17-audio-encoding.html)

\newpage

**Codec** is short for coder-decoder. It compresses and decompresses audio. The codecs you will encounter in inference APIs:

| Codec | 1 Second at 16 kHz | Use Case |
|---|---|---|
| PCM (raw) | 32 KB | Server-to-server, low latency |
| FLAC (lossless) | ~16 KB | Archival, quality-sensitive |
| Opus | ~2 KB | Browser/mobile, bandwidth-constrained |
| MP3 | ~4 KB | Legacy compatibility |

**PCM** is uncompressed audio. It requires no decoding on the server side (zero added latency) but uses the most bandwidth. Most inference providers accept PCM for lowest-latency paths.

**Opus** is the modern standard for compressed streaming audio. It achieves excellent quality at very low bitrates and is natively supported in web browsers. The tradeoff is that the server must decode Opus before inference, adding a small processing step.

The codec choice affects the entire pipeline. If your API accepts Opus, you reduce client bandwidth but add server-side decoding. If your API requires PCM, you simplify the server but require clients to send 16 times more data. Chapters 4 and 5 cover these tradeoffs in detail.

**Referenced in:** Chapters 4, 5, 6

## VAD and Endpointing: Finding the Speech {-}

**The kitchen analog:** A noise gate on a microphone. When nobody is speaking, the gate stays closed and nothing passes through to the expensive recording equipment. When speech is detected, the gate opens and audio flows to the recorder. The noise gate is cheap; the recording and processing equipment is expensive. VAD (Voice Activity Detection) works the same way: a lightweight model that decides what audio is worth sending to the expensive GPU inference pipeline.

**The technical reality:** In any real-time speech application, the audio stream contains both speech and silence (or background noise). Sending everything to the GPU inference model wastes compute: the model spends GPU cycles processing silence and returns empty results.

![VAD Pipeline](../assets/ch17-vad-pipeline.html)

\newpage

VAD is a small, fast model that runs on the CPU (not the GPU) and classifies each audio frame as speech or non-speech. Silero VAD [Source: Silero, 2024], one of the most widely deployed implementations, processes audio in approximately 1 millisecond per frame on a single CPU core.

The cost impact is substantial. In typical voice conversations, 40 to 60% of audio frames contain silence or background noise. By filtering these out before they reach the GPU, VAD can reduce inference costs by 40 to 60% while actually improving transcription quality (the model is not confused by noise).

**Endpointing** is the related problem of determining when a speaker has finished a thought. This is harder than detecting silence: a brief pause might be mid-sentence, or it might signal the end of a turn. Endpointing algorithms use a combination of silence duration, prosodic features, and context to make this determination. The endpointing decision controls when the system generates a final result versus an interim result, which directly affects the API's streaming response contract.

For API engineers, VAD and endpointing are the components that bridge the audio input stream and the inference pipeline. They determine what gets processed, when final results are emitted, and how the system behaves during pauses. Understanding them is essential for designing streaming API contracts, which Chapters 6 and 8 cover in depth.

> **Where the metaphor breaks down:** A noise gate is a simple threshold. Modern VAD models are neural networks that distinguish speech from background noise, music, and other non-speech audio with high accuracy. They are "smart gates," not simple amplitude thresholds.

**Referenced in:** Chapters 4, 6, 8

## What You Can Skip {-}

This book is about serving models, not building them. The following ML topics are the head chef's domain and are explicitly out of scope:

- **Training and fine-tuning**: How models learn from data. We start where training ends: with a model artifact ready to serve.
- **Backpropagation and gradient descent**: The optimization algorithms used during training. Irrelevant to inference.
- **Loss functions and evaluation metrics**: How model quality is measured during training. We care about inference quality metrics like word error rate and latency, not training loss curves.
- **Hyperparameter tuning**: Adjusting training parameters for better model quality. Not a serving concern.
- **Model architecture design**: Choosing the number of layers, attention heads, and embedding dimensions. We take the architecture as given and focus on serving it efficiently.
- **Dataset curation and labeling**: Building the training data. Entirely upstream of serving.

If you encounter these terms in other resources, you can safely skip them. Nothing in this book requires understanding how models are trained, only how they are served.

## Summary {-}

- A **model** is a large file of numerical weights (1–140 GB), not executable code. Loading it into GPU memory is a prerequisite for serving any request.

- **Inference** (the forward pass) converts input to output through the model. Training creates the model; inference uses it. Inference costs dominate over a model's lifetime.

- **GPUs** are 10–100x faster than CPUs for inference but cost 10–100x more per hour. Idle GPU time is expensive, driving every optimization in this book.

- **Tokens** are the discrete units models process. They are the unit of cost, latency, and memory consumption.

- **Inference latency** has distinct phases (prefill, decode) with different optimization strategies. The 300ms voice AI threshold is the anchor target throughout this book.

- **Continuous batching** is the key throughput optimization: process one token at a time across all active requests so the GPU is never idle and no request waits for others.

- The **KV cache** stores previously computed attention state per request. It is the central memory bottleneck, often consuming more VRAM than the model weights themselves.

- **Cold starts** take 30 seconds to several minutes for ML inference servers, fundamentally changing how auto-scaling works compared to traditional API infrastructure.

- **Quantization** reduces model precision (FP32 to FP8 to INT4), halving memory with each step. FP8 is the current production standard.

- The **attention mechanism** lets models relate any token to any previous token. It is why longer contexts cost more and why the KV cache exists.

- Audio at 16 kHz / 16-bit PCM consumes 32 KB/s. **Codec choice** (PCM vs Opus) trades bandwidth for server-side decoding latency.

- **VAD** filters silence on the CPU before audio reaches the GPU, saving 40–60% of inference costs and improving quality.

## What's Next {-}

You now have the vocabulary and mental models to read this book with confidence. Every concept introduced here is explored in depth across the main chapters, with production patterns, benchmark data, and real-world provider examples.

Proceed to [Chapter 1: The Serving Problem](./01-the-serving-problem.md), which introduces the serving engineer's role and establishes why ML inference is a distinct engineering discipline.

## References {-}

1. **Ankur's Newsletter** (2025). "The Inference Economy." Analysis of inference vs training cost distribution in production ML systems.

2. **AssemblyAI** (2025). "Real-Time Speech Recognition." Documentation on latency requirements for voice AI applications. https://www.assemblyai.com/docs/

3. **Dao, T., Fu, D., Ermon, S., Rudra, A., & Re, C.** (2022). "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness." Advances in Neural Information Processing Systems.

4. **Kwon, W., Li, Z., Zhuang, S., et al.** (2023). "Efficient Memory Management for Large Language Model Serving with PagedAttention." Proceedings of the 29th Symposium on Operating Systems Principles.

5. **NVIDIA** (2024). "FP8 Formats for Deep Learning." Technical report on FP8 quantization for production inference. https://developer.nvidia.com/

6. **Silero** (2024). "Silero VAD: Pre-trained Voice Activity Detection." https://github.com/snakers4/silero-vad

7. **Vaswani, A., Shazeer, N., Parmar, N., et al.** (2017). "Attention Is All You Need." Advances in Neural Information Processing Systems.

8. **Yu, G-I., Jeong, J. S., Kim, G-W., Kim, S., & Chun, B-G.** (2022). "Orca: A Distributed Serving System for Transformer-Based Generative Models." Proceedings of the 16th USENIX Symposium on Operating Systems Design and Implementation.
