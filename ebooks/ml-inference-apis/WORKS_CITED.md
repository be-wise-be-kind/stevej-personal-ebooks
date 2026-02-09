# Works Cited

A comprehensive bibliography of all sources referenced in "Productionizing ML Inference APIs: A Serving Engineer's Guide to Real-Time Speech and Audio."

---

## Frequently Cited Works

The following works are referenced across multiple chapters and form the foundational literature for ML inference serving:

| Work | Chapters Referenced |
|------|---------------------|
| Google SRE Book (Beyer et al., 2016) | 1, 3, 12, 14 |
| AssemblyAI (2025). "The 300ms Rule: Why Latency Makes or Breaks Voice AI." | 1, 4, 5, 12 |
| BentoML (2025). "LLM Inference Handbook." | 1, 2, 3, 12 |
| Clarifai (2025). "Comparing SGLang, vLLM, and TensorRT-LLM with GPT-OSS-120B." | 1, 2, 3 |
| AIMultiple (2026). "LLM Inference Engines: vLLM vs LMDeploy vs SGLang." | 1, 2 |
| Stixor (2025). "The New LLM Inference Stack 2025: FA-3, FP8 & FP4." | 1, 3 |
| OpenAI Realtime API Documentation (2025). | 4, 5, 7 |
| Deepgram Compliance Docs (2025). "Standard Compliance Speech-to-Text: HIPAA, SOC 2, GDPR." | 10, 11 |

---

## Chapter 1: The Serving Problem

1. **AssemblyAI** (2025). "The 300ms Rule: Why Latency Makes or Breaks Voice AI." https://www.assemblyai.com/blog/the-300ms-rule

2. **BentoML** (2025). "LLM Inference Handbook: Choosing the Right Framework." https://www.bentoml.com/blog/llm-inference-handbook

3. **Clarifai** (2025). "Comparing SGLang, vLLM, and TensorRT-LLM with GPT-OSS-120B." https://www.clarifai.com/blog/comparing-sglang-vllm-tensorrt-llm

4. **Stixor** (2025). "The New LLM Inference Stack 2025: FA-3, FP8 & FP4." https://stixor.com/the-new-llm-inference-stack-2025

5. **NVIDIA** (2025). "Optimizing Inference for Long Context with NVFP4 KV Cache." https://developer.nvidia.com/blog/nvfp4-kv-cache

6. **OpenMeter** (2025). "Real-Time Usage Metering." https://openmeter.io/docs

7. **Deepgram** (2025). "Pricing: Pay-as-you-go." https://deepgram.com/pricing

8. **AssemblyAI** (2025). "Pricing and Feature Add-ons." https://assemblyai.com/pricing

9. **ElevenLabs** (2025). "Pricing: Per-character TTS." https://elevenlabs.io/pricing

10. **OpenAI** (2025). "Realtime API Documentation." https://platform.openai.com/docs/guides/realtime

11. **Google Cloud** (2025). "Cloud Speech-to-Text V2 API Reference." https://cloud.google.com/speech-to-text/v2/docs

12. **Google** (2024). "RAIL Performance Model." https://web.dev/rail

13. **MarkTechPost** (2025). "Comparing Top 6 Inference Runtimes for LLM Serving in 2025." https://www.marktechpost.com/

14. **Dao, T., et al.** (2024). "FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-precision." arXiv preprint.

15. **AWS** (2025). "EC2 On-Demand Instance Pricing." https://aws.amazon.com/ec2/pricing/on-demand

16. **Ankur's Newsletter** (2025). "The Real Price of AI: Pre-Training Vs. Inference Costs." https://ankursnewsletter.com

17. **CloudZero** (2025). "Your Guide To Inference Cost (And Turning It Into Margin Advantage)." https://cloudzero.com/blog/inference-cost

18. **NVIDIA** (2025). "LLM Inference Benchmarking: Performance Tuning with TensorRT-LLM." https://developer.nvidia.com/blog/llm-inference-benchmarking-performance-tuning-with-tensorrt-llm

19. **vLLM** (2025). "Inside vLLM: Anatomy of a High-Throughput LLM Inference System." https://blog.vllm.ai/2025/09/05/anatomy-of-vllm.html

20. **Chen, Y., et al.** (2024). "A Systematic Characterization of LLM Inference on GPUs." arXiv:2512.01644.

21. **AIMultiple** (2026). "LLM Inference Engines: vLLM vs LMDeploy vs SGLang." https://research.aimultiple.com/inference-engines/

22. **Red Hat** (2025). "How PagedAttention Resolves Memory Waste in LLM Systems." https://developers.redhat.com/articles/2025/07/24/how-pagedattention-resolves-memory-waste-llm-systems

23. **Anyscale** (2023). "Continuous Batching in LLM Inference." https://www.anyscale.com/blog/continuous-batching-llm-inference

24. **Kwon, W., et al.** (2023). "Efficient Memory Management for Large Language Model Serving with PagedAttention." *Proceedings of the ACM SOSP '23*. arXiv:2309.06180

25. **GitHub** (2025). "TorchServe Repository Archived." https://github.com/pytorch/serve/issues/3396

---

## Chapter 2: Model Serving Frameworks

1. **Google** (2016). "Running Your Models in Production with TensorFlow Serving." https://opensource.googleblog.com/2016/02/running-your-models-in-production-with.html

2. **GitHub** (2025). "TorchServe Repository Archived." https://github.com/pytorch/serve/issues/3396

3. **Hugging Face** (2025). "Text Generation Inference Documentation." https://huggingface.co/docs/inference-endpoints/en/engines/tgi

4. **NVIDIA** (2025). "Triton Inference Server Ensemble Models." https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/ensemble_models.html

5. **KServe** (2025). "KServe Documentation." https://kserve.github.io/website/

6. **BentoML** (2025). "Choosing the Right Inference Framework." https://bentoml.com/llm/getting-started/choosing-the-right-inference-framework

7. **Anyscale** (2025). "Ray Serve: Faster First Token with Custom Routing." https://www.anyscale.com/blog/ray-serve-faster-first-token-custom-routing

8. **Clarifai** (2025). "Comparing SGLang, vLLM, and TensorRT-LLM with GPT-OSS-120B." https://www.clarifai.com/blog/comparing-sglang-vllm-and-tensorrt-llm-with-gpt-oss-120b

9. **AIMultiple** (2026). "LLM Inference Engines: vLLM vs LMDeploy vs SGLang." https://research.aimultiple.com/inference-engines/

10. **Clarifai** (2025). "Benchmarking GPT-OSS Across H100s and B200s." https://www.clarifai.com/blog/benchmarking-gpt-oss-across-h100s-and-b200s

11. **NVIDIA** (2025). "NVIDIA Blackwell Leads on New SemiAnalysis InferenceMAX Benchmarks." https://developer.nvidia.com/blog/nvidia-blackwell-leads-on-new-semianalysis-inferencemax-benchmarks/

12. **Red Hat** (2025). "How PagedAttention Resolves Memory Waste in LLM Systems." https://developers.redhat.com/articles/2025/07/24/how-pagedattention-resolves-memory-waste-llm-systems

13. **Kwon, W., et al.** (2023). "Efficient Memory Management for Large Language Model Serving with PagedAttention." *Proceedings of the ACM SOSP '23*. arXiv:2309.06180

14. **LMSYS** (2024). "SGLang: Efficient Execution of Structured Language Model Programs." https://lmsys.org/blog/2024-01-17-sglang/

15. **AWS** (2025). "How Amazon Scaled Rufus by Building Multi-Node Inference Using AWS Trainium Chips and vLLM." https://aws.amazon.com/blogs/machine-learning/how-amazon-scaled-rufus-by-building-multi-node-inference-using-aws-trainium-chips-and-vllm/

16. **LinkedIn/The Stack** (2025). "LinkedIn Touts vLLM Brilliance for 50+ AI Use Cases." https://www.thestack.technology/linkedin-touts-vllm-brilliance-for-50-ai-use-cases/

17. **Red Hat** (2025). "How vLLM Accelerates AI Inference: 3 Enterprise Use Cases." https://www.redhat.com/en/topics/ai/how-vllm-accelerates-ai-inference-3-enterprise-use-cases

18. **Towards Data Science** (2024). "Deploying LLMs into Production Using TensorRT-LLM." https://towardsdatascience.com/deploying-llms-into-production-using-tensorrt-llm-ed36e620dac4/

19. **Baseten** (2025). "Automatic LLM Optimization with TensorRT-LLM Engine Builder." https://www.baseten.co/blog/automatic-llm-optimization-with-tensorrt-llm-engine-builder/

20. **BentoML** (2024). "Benchmarking LLM Inference Backends." https://bentoml.com/blog/benchmarking-llm-inference-backends

21. **NVIDIA** (2025). "Reducing Cold Start Latency for LLM Inference with NVIDIA Run:ai Model Streamer." https://developer.nvidia.com/blog/reducing-cold-start-latency-for-llm-inference-with-nvidia-runai-model-streamer/

22. **NVIDIA** (2025). "Cut Model Deployment Costs While Keeping Performance with GPU Memory Swap." https://developer.nvidia.com/blog/cut-model-deployment-costs-while-keeping-performance-with-gpu-memory-swap/

23. **NVIDIA** (2025). "Triton Model Management." https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/model_management.html

24. **NVIDIA** (2025). "Multi-Instance GPU User Guide." https://docs.nvidia.com/datacenter/tesla/mig-user-guide/

25. **Pebble** (2025). "NVIDIA MPS vs Dedicated GPU Allocation for LLM Inference." https://www.gopebble.com/case-studies/nvidia-mps-vs-dedicated-gpu-allocation-for-llm-inference

26. **TensorFusion** (2025). "MIG vs MPS Comparison." https://tensor-fusion.ai/guide/comparison/compare-with-mig-mps

27. **Nebius** (2025). "Serving LLMs with vLLM: A Practical Inference Guide." https://nebius.com/blog/serving-llms-with-vllm

28. **Anyscale** (2023). "Continuous Batching in LLM Inference." https://www.anyscale.com/blog/continuous-batching-llm-inference

---

## Chapter 3: GPU Optimization & Cold Starts

1. **NVIDIA** (2025). "Optimizing Inference for Long Context with NVFP4 KV Cache." NVIDIA Blog. https://developer.nvidia.com/blog/

2. **Stixor** (2025). "The New LLM Inference Stack 2025: FA-3, FP8 & FP4." https://stixor.com/the-new-llm-inference-stack-2025

3. **Nebius** (2025). "Serving LLMs with vLLM: A Practical Inference Guide." https://nebius.com/blog/serving-llms-with-vllm

4. **Dao, T., et al.** (2024). "FlashAttention-3: Fast and Exact Attention with Asynchrony and Low-Precision." arXiv preprint.

5. **Kwon, W., et al.** (2023). "Efficient Memory Management for Large Language Model Serving with PagedAttention." *Proceedings of the ACM Symposium on Operating Systems Principles (SOSP '23)*.

6. **BentoML** (2025). "LLM Inference Handbook — Continuous Batching and Beyond." https://www.bentoml.com/blog/llm-inference-handbook

7. **Clarifai** (2025). "Comparing SGLang, vLLM, and TensorRT-LLM with GPT-OSS-120B." https://www.clarifai.com/blog/comparing-sglang-vllm-tensorrt-llm

---

## Chapter 4: Streaming Audio Architecture

1. **AssemblyAI** (2026). "Top APIs and Models for Real-Time Speech Recognition 2026." https://www.assemblyai.com/blog/

2. **Deepgram** (2026). "Best Speech-to-Text APIs 2026." https://deepgram.com/learn/best-speech-to-text-apis

3. **OpenAI** (2025). "Realtime API Documentation." https://platform.openai.com/docs/guides/realtime

4. **Google Cloud** (2025). "Speech-to-Text Documentation." https://cloud.google.com/speech-to-text/docs

5. **Amazon Web Services** (2025). "Amazon Transcribe Streaming Documentation." https://docs.aws.amazon.com/transcribe/

6. **AssemblyAI** (2025). "The 300ms Rule: Why Latency Makes or Breaks Voice AI." https://www.assemblyai.com/blog/the-300ms-rule

---

## Chapter 5: Protocol Selection for Audio

1. **GetStream** (2025). "WebRTC vs WebSocket: Which Keeps Audio in Sync for AI?" https://getstream.io/blog/

2. **VideoSDK** (2025). "What is Replacing WebSockets? Deep Dive into WebTransport, HTTP/3." https://www.videosdk.live/blog/

3. **Red5** (2025). "MOQ vs WebRTC: Why Both Can and Should Exist." https://www.red5.net/blog/

4. **WINK** (2025). "Media over QUIC Implementation — Technical Analysis 2025." https://wink.cloud/blog/

5. **OpenAI** (2025). "Realtime API Documentation." https://platform.openai.com/docs/guides/realtime [WebRTC, WebSocket, and SIP protocol support]

---

## Chapter 6: Streaming Inference Pipelines

*Combines sources from Chapters 1, 3, and 4. Additional sources to be identified during authoring.*

1. **BentoML** (2025). "LLM Inference Handbook." https://www.bentoml.com/blog/llm-inference-handbook [Streaming inference patterns]

2. **Stixor** (2025). "The New LLM Inference Stack 2025." https://stixor.com/the-new-llm-inference-stack-2025 [Pipeline architecture]

3. **AssemblyAI** (2026). "Top APIs and Models for Real-Time Speech Recognition 2026." https://www.assemblyai.com/blog/ [Streaming pipeline reference architectures]

4. **Deepgram** (2026). "Best Speech-to-Text APIs 2026." https://deepgram.com/learn/best-speech-to-text-apis [Concurrent stream handling]

---

## Chapter 7: Designing ML-Facing APIs

1. **Google** (2025). "API Improvement Proposals." https://aip.dev [AIP-121: Resource-oriented design, AIP-133: Standard methods, AIP-136: Custom methods, AIP-151: Long-running operations]

2. **OpenAI** (2025). "API Reference." https://platform.openai.com/docs/api-reference [Chat Completions, Responses API, streaming patterns]

3. **OpenAI** (2025). "OpenAI for Developers in 2025." https://openai.com/blog/openai-for-developers-2025 [Responses API, agent patterns, multimodality]

---

## Chapter 8: Streaming Response Contracts

1. **OpenAI** (2025). "API Reference — Chat Completions." https://platform.openai.com/docs/api-reference/chat [SSE streaming with `data:` prefix and `[DONE]` signal]

2. **OpenAI** (2025). "Streaming Events — Responses API." https://platform.openai.com/docs/api-reference/streaming [Structured event types: response.created, response.output_text.delta, response.completed]

3. **Deepgram** (2025). "WebSocket API Reference." https://developers.deepgram.com/docs/streaming [Binary WebSocket frames, interim/final results, keep-alive, close codes]

4. **AssemblyAI** (2025). "Real-Time Streaming API." https://www.assemblyai.com/docs/speech-to-text/streaming [WebSocket streaming, partial transcripts, session lifecycle]

5. **Google Cloud** (2025). "Speech-to-Text Streaming Recognition." https://cloud.google.com/speech-to-text/docs/streaming-recognize [gRPC bidirectional streaming, StreamingRecognizeRequest/Response, interim results]

---

## Chapter 9: API Versioning & Developer Experience

1. **Google** (2025). "API Improvement Proposals." https://aip.dev [AIP-181: Stability levels, AIP-180: Versioning, AIP-182: Deprecation]

2. **OpenAI** (2025). "API Reference." https://platform.openai.com/docs/api-reference [URL path versioning (/v1/), model version pinning, dated model snapshots]

3. **Microsoft Azure** (2025). "Azure OpenAI Service REST API Reference — v1." https://learn.microsoft.com/en-us/azure/ai-services/openai/reference [api-version query parameter, preview vs GA versioning]

---

## Chapter 10: Security for Audio ML APIs

1. **Deepgram** (2025). "Standard Compliance Speech-to-Text: HIPAA, SOC 2, GDPR." https://deepgram.com/compliance [Zero-retention defaults, configurable redaction, sub-300ms]

2. **OWASP** (2023). "API Security Top 10." https://owasp.org/API-Security/ [API-specific vulnerability categories]

3. **AssemblyAI** (2025). Security and compliance documentation. [HIPAA + BAA, auto PHI redaction]

---

## Chapter 11: Compliance & Data Governance

1. **EU AI Act Service Desk** (2025). "Implementation Timeline." [Prohibited practices Feb 2025, GPAI Aug 2025, High-risk Aug 2026, Regulated products Aug 2027]

2. **Deepgram** (2025). "Standard Compliance Speech-to-Text: HIPAA, SOC 2, GDPR." https://deepgram.com/compliance

3. **Wiz** (2026). "AI Compliance in 2026: Definition, Standards, and Frameworks." https://www.wiz.io/blog/ai-compliance

4. **DLA Piper** (2025). "Latest Wave of Obligations Under the EU AI Act." https://www.dlapiper.com/ [High-risk and transparency rule analysis]

---

## Chapter 12: SLOs for Streaming ML Systems

1. **Gladia** (2025). "How to Measure Latency in STT: TTFB, Partials, Finals, RTF." https://www.gladia.io/blog/ [Speech-to-text latency taxonomy]

2. **Anyscale** (2025). "Understand LLM Latency and Throughput Metrics." https://www.anyscale.com/blog/ [TTFT, TPOT, inter-token latency]

3. **AssemblyAI** (2025). "The 300ms Rule: Why Latency Makes or Breaks Voice AI." https://www.assemblyai.com/blog/the-300ms-rule

4. **BentoML** (2025). "Key Metrics for LLM Inference." https://www.bentoml.com/blog/ [Goodput, throughput, latency metrics]

5. **Beyer, Betsy, et al.** (2016). *Site Reliability Engineering: How Google Runs Production Systems.* O'Reilly Media. [SLI/SLO/SLA framework, error budgets]

---

## Chapter 13: Usage Metering & Billing

1. **Stripe** (2025). "Meters API Reference." https://docs.stripe.com/api/billing/meter [Aggregation, billing periods, event ingestion]

2. **Stripe** (2025). "Token Billing Documentation." https://docs.stripe.com/billing/subscriptions/usage-based/token-billing [LLM token metering]

3. **OpenMeter** (2025). Open-source real-time metering. https://openmeter.io [Native Stripe integration, real-time aggregation]

4. **BrasTranscripts** (2025). Deepgram and AssemblyAI pricing breakdowns. [Per-second vs per-block billing comparison]

---

## Chapter 14: Scaling Inference Globally

*Combines sources from Chapters 1 and 2. Additional sources to be identified during authoring.*

1. **BentoML** (2025). "LLM Inference Handbook." https://www.bentoml.com/blog/llm-inference-handbook [Scaling strategies]

2. **Clarifai** (2025). "Comparing SGLang, vLLM, and TensorRT-LLM." https://www.clarifai.com/blog/ [Performance at scale benchmarks]

3. **MarkTechPost** (2025). "Comparing Top 6 Inference Runtimes." https://www.marktechpost.com/ [Auto-scaling considerations]

4. **Beyer, Betsy, et al.** (2016). *Site Reliability Engineering: How Google Runs Production Systems.* O'Reilly Media. [Capacity planning, multi-region patterns]

---

## Chapter 15: Putting It All Together

*Synthesis chapter referencing all previous chapters. Sources drawn from across the full bibliography.*

*No unique sources — this chapter integrates findings from Chapters 1-14.*

---

## Verification Notes

This bibliography was initialized during the outline phase from research conducted in February 2026 across 8 topic areas. Full raw search results are stored in `.roadmap/in-progress/ml-inference-apis/research/raw-web-search-results.md`.

### Citation Standards Applied

All statistics and factual claims in the text use the `[Source: Author/Org, Year]` inline citation format. Each chapter concludes with a References section listing full bibliographic details.

### Source Categories

**Academic Papers** (to be verified via standard academic citations):
- Dao et al., "FlashAttention-3" (2024) - arXiv
- Kwon et al., "PagedAttention" (2023) - SOSP

**Industry Standards**:
- Google API Improvement Proposals (aip.dev)
- OWASP API Security Top 10
- EU AI Act

**Published Books**:
- Site Reliability Engineering (Google SRE Book, O'Reilly, 2016)

**Vendor Documentation** (current as of February 2026):
- OpenAI Realtime API, Deepgram, AssemblyAI, Google Cloud Speech, Amazon Transcribe
- Stripe Meters API, OpenMeter
- vLLM, SGLang, TensorRT-LLM, Triton, KServe, BentoML

**Industry Research and Blog Posts** (URLs to be verified during authoring):
- AssemblyAI "The 300ms Rule" (2025)
- BentoML "LLM Inference Handbook" (2025)
- Clarifai framework comparison (2025)
- MarkTechPost inference runtime comparison (2025)
- Stixor inference stack overview (2025)

### Recommendations for Future Verification

When authoring each chapter, the following should be completed:
1. Verify all URLs are active and point to the correct content
2. Add exact URLs where placeholder URLs are listed
3. Add publication dates where only years are listed
4. Add page numbers for book references where applicable
5. Verify all benchmark numbers against the original sources

---

*Last updated: February 2026*
*Status: Skeleton — to be populated fully during chapter authoring PRs*
