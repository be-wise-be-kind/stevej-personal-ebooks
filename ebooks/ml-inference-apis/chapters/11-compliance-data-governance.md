# Chapter 11: Compliance & Data Governance

<!-- DIAGRAM: ch11-opener.html - Chapter 11 Opener -->

\newpage

## Overview

- **Ground the reader**: briefly explain what compliance means in this context. Compliance refers to meeting the security, privacy, and governance standards that enterprise customers and regulators require before they will trust a service with their data. Standards like SOC 2 (a security audit framework), GDPR (European privacy law), and HIPAA (US healthcare data protection) each impose specific requirements on how data is stored, accessed, retained, and deleted. For ML inference APIs that process audio, compliance is not a checkbox exercise; it shapes architectural decisions from day one, because retrofitting data isolation, audit logging, and retention controls into a running system is far more expensive than building them in.
- Compliance for ML inference APIs is not optional; enterprise customers require SOC 2, HIPAA, and GDPR compliance before signing contracts
- Audio data carries heightened regulatory obligations because voice is classified as biometric and personal data under most privacy frameworks
- This chapter maps specific compliance requirements (SOC 2, GDPR, CCPA, HIPAA, EU AI Act) to concrete architectural decisions and implementation patterns

## SOC 2 for ML APIs

### Why SOC 2 Is Effectively Mandatory

- SOC 2 is not a law; it is an auditing standard from the AICPA (American Institute of Certified Public Accountants)
- In practice, B2B AI companies cannot sell to enterprise customers without SOC 2 Type II certification
- The sales cycle bottleneck: procurement and security review teams require SOC 2 reports before evaluating the product
- Type I (point-in-time) vs. Type II (sustained over 6-12 months); Type II is what enterprise buyers require

### Trust Service Criteria Applied to Inference Systems

- **Security**: network controls around GPU clusters, model access controls, encryption of audio data in transit and at rest
- **Availability**: SLOs for inference uptime, redundancy for model serving infrastructure, failover procedures
- **Processing Integrity**: model versioning audit trails, ensuring the correct model version processes each request
- **Confidentiality**: customer audio data isolation (multi-tenant separation), data classification policies for audio vs. transcripts vs. metadata
- **Privacy**: PII handling procedures (cross-reference Chapter 10), data retention and deletion policies, consent management

### SOC 2 Evidence for ML-Specific Controls

- Model deployment logs: who deployed which model version, when, and with what configuration
- Inference request audit trails: request metadata (not audio content) logged for every inference call
- GPU access controls: which engineers can access GPU nodes, SSH audit logs, privileged access management
- Automated evidence collection: integrate compliance logging into the inference pipeline rather than collecting evidence retroactively

## Audit Logging

### What to Log

- **Inference request metadata**: timestamp, API key (hashed), model version, audio duration, response latency, status code
- **Model lifecycle events**: model deployment, version swap, rollback, A/B test configuration changes
- **Access events**: API key creation/rotation/revocation, admin console access, configuration changes
- **Audio metadata (NOT content)**: codec, sample rate, channel count, duration; never log the audio content itself
- **PII redaction events**: what was detected, what was redacted, redaction method; without logging the PII itself

### What NOT to Log

- Raw audio data; logging audio creates a secondary copy that must be protected and retained/deleted separately
- Full transcript text; transcripts contain customer data and PII, log only metadata about the transcription
- API key values in plaintext; log hashed or truncated key identifiers (e.g., `sk_live_...a3f2`)
- Model weights or proprietary inference configurations; trade secret risk

### Retention Requirements

- Retention periods vary by regulation: SOC 2 (typically 1 year), HIPAA (6 years), GDPR (as short as possible)
- Conflict resolution: when multiple regulations apply, retain for the longest required period but restrict access to the minimum necessary
- Cost implications: audit log storage at scale is non-trivial; tiered storage (hot → warm → cold) with appropriate access controls at each tier

### Tamper-Proof Storage

- Append-only log stores: prevent modification or deletion of audit records
- Write-once storage: AWS S3 Object Lock, GCS retention policies, Azure immutable blob storage
- Cryptographic verification: hash chains or Merkle trees to detect tampering
- Third-party attestation: route audit logs to an independent aggregator that the auditor can verify directly

## Data Retention and Deletion

### Configurable Retention Policies

- Default to zero retention: process audio, return results, delete the audio; the Deepgram pattern
- Configurable retention tiers: zero (immediate deletion), short (24-72 hours for debugging), extended (30-90 days for model improvement), long-term (compliance-mandated)
- Per-customer retention: enterprise customers may require specific retention periods per their own compliance obligations
- Retention metadata: tag every stored artifact with its retention policy and scheduled deletion date

### Zero-Retention Architecture

- Process audio entirely in memory; never write to persistent storage
- Ephemeral compute: inference nodes with no persistent disk, data exists only in RAM during processing
- Verification: prove to auditors that zero-retention is actually zero; no hidden caches, no temporary files left behind
- Trade-offs: zero retention means no ability to debug issues after the fact, no training data collection, no replay for quality assurance

### Right to Deletion

- GDPR Article 17 (Right to Erasure) and CCPA deletion requests apply to all stored audio and derived data
- Deletion scope: the original audio, all transcripts, any derived data (speaker embeddings, sentiment scores), and all copies (backups, replicas)
- Deletion verification: technical proof that data was actually deleted, not just dereferenced; important for audit
- Cascading deletion: if audio was used to fine-tune a model, the model itself may need to be retrained without that data (machine unlearning)

## GDPR and CCPA for Audio and Transcripts

### Voice as Personal Data

- Under GDPR, voice recordings are personal data; they identify a natural person
- Voice is also biometric data under GDPR Article 9 (special category) when processed for identification purposes
- CCPA classifies voice recordings as personal information and biometric information
- Consent requirements: GDPR requires explicit consent for biometric processing; CCPA requires opt-out rights for sale/sharing

### Data Subject Rights for Audio

- **Right of Access**: provide a copy of all stored audio and transcripts associated with the data subject
- **Right to Erasure**: delete all audio, transcripts, and derived data on request; within 30 days under GDPR
- **Right to Portability**: export audio and transcripts in a machine-readable format (e.g., WAV + JSON)
- **Right to Restriction**: stop processing a subject's audio while a dispute is resolved, but retain the data
- Implementation challenge: identifying which audio recordings belong to a specific data subject requires speaker identification capabilities

### Cross-Border Data Transfers

- EU-US Data Privacy Framework: current mechanism for transferring personal data from EU to US; but legal landscape is unstable
- Standard Contractual Clauses (SCCs) as a fallback mechanism
- Data localization: process and store EU audio data exclusively within EU regions; see Data Residency section below
- Transfer impact assessments: required under GDPR for transfers to countries without adequacy decisions

## EU AI Act

### Timeline and Key Dates

- **February 2, 2025**: Prohibited AI practices take effect (social scoring, real-time biometric identification in public spaces with exceptions)
- **August 2, 2025**: GPAI (General Purpose AI) model obligations; transparency, copyright compliance, model documentation
- **August 2, 2026**: High-risk AI system requirements and transparency obligations for AI systems that interact with natural persons
- **August 2, 2027**: Requirements for AI systems embedded in regulated products (medical devices, vehicles, etc.)

<!-- DIAGRAM: ch11-eu-ai-act-timeline.html - EU AI Act Timeline -->

\newpage

### Implications for Speech AI Systems

- Speech AI interacting with humans triggers **transparency obligations**: users must be informed they are interacting with an AI system
- Emotion recognition in workplace or educational settings is **prohibited** (effective Feb 2025)
- Real-time speech-to-text for law enforcement may qualify as **high-risk**; requires conformity assessment, risk management, data governance
- GPAI obligations (Aug 2025): if your speech models are general-purpose, you must provide model documentation, training data summaries, and copyright compliance

### Fines and Enforcement

- Prohibited practices: up to EUR 35 million or 7% of global annual turnover (whichever is higher)
- High-risk non-compliance: up to EUR 15 million or 3% of global annual turnover
- Supplying incorrect information: up to EUR 7.5 million or 1% of global annual turnover
- Enforcement: national market surveillance authorities in each EU member state, with coordination by the AI Office
- The financial risk is significant enough that compliance must be built into architecture from the start, not bolted on

## HIPAA for Healthcare Speech AI

### Why HIPAA Applies to Speech AI

- Telehealth sessions transcribed by speech AI contain Protected Health Information (PHI); patient names, conditions, medications, treatment plans
- Clinical dictation: physicians using speech-to-text for medical notes creates PHI in the transcript
- Patient call centers: automated call handling with speech AI processes caller health information
- Any entity processing PHI must comply with HIPAA, regardless of whether they are a healthcare provider themselves

### Technical Requirements

- **Encryption**: AES-256 at rest and TLS 1.3 in transit; mandatory, not optional
- **Access controls**: role-based access to audio and transcripts, minimum necessary standard (only access what your role requires)
- **Audit logging**: granular logs of all access to PHI; who accessed what, when, and why; retained for 6 years
- **Automatic logoff**: idle session termination for systems with access to PHI
- **Integrity controls**: ensure transcripts are not altered after generation; checksums or digital signatures

### Business Associate Agreements (BAAs)

- Any ML inference provider processing PHI on behalf of a covered entity must sign a BAA
- The BAA defines: permitted uses of PHI, safeguard requirements, breach notification obligations, return/destruction of PHI on termination
- BAA chain: if your inference service uses a cloud provider (AWS, GCP, Azure), you need BAAs at every level; cloud provider, inference platform, and any sub-processors
- Provider support: Deepgram, AssemblyAI, and Google Cloud Speech all offer BAAs; verify before selecting a provider

## Data Residency

### Regional Processing Requirements

- Many regulations (GDPR, data localization laws in Russia, China, India, etc.) require data to be processed and stored within specific geographies
- Audio data residency: ensure audio is transcribed in the same region it was recorded; no cross-region transfer for inference
- Model deployment per region: deploy identical model replicas in each required region, with independent scaling
- Metadata residency: even inference metadata (request logs, timestamps) may be subject to residency requirements

### Architecture for Data Residency

- Regional API gateways that route requests to region-local inference clusters
- DNS-based routing: use geographic DNS to direct clients to the nearest compliant region
- No cross-region replication of audio data; each region is a self-contained processing boundary
- Centralized configuration with regional execution: model versions and configs pushed from a central control plane, but all data processing happens locally

### Compliance Verification

- Prove to auditors that audio data never leaves the designated region; network flow logs, VPC configurations, data transfer monitoring
- Regular testing: simulate data residency violations to verify that controls are effective
- Monitoring: alert on any cross-region data transfer events

## Building Compliance into Architecture

### Compliance-by-Design Patterns

- Feature flags for regional requirements: enable/disable PII redaction, data retention, consent management per region
- Policy-as-code: encode compliance rules as executable policies (e.g., Open Policy Agent) rather than as documentation
- Compliance middleware: intercept inference requests to enforce retention, redaction, and consent policies before reaching the model
- Immutable infrastructure: infrastructure-as-code ensures that compliance configurations are versioned, reviewed, and reproducible

### Key Compliance Features to Implement

- **Zero-retention defaults**: process and delete; require explicit opt-in for any data retention
- **Configurable redaction**: allow customers to specify which PII categories to redact; different industries need different redaction profiles
- **Regional processing**: route audio to region-local inference clusters based on customer configuration
- **BAA support**: operational and legal infrastructure to sign and manage BAAs with healthcare customers
- **Audit logging**: comprehensive, tamper-proof logging of all inference operations and data access events
- **Consent management**: record and enforce user consent for audio processing, biometric analysis, and data retention

<!-- DIAGRAM: ch11-compliance-matrix.html - Compliance Matrix -->

\newpage

### Bolt-On vs. Built-In Compliance

- Bolt-on compliance: adding compliance controls after the system is built; fragile, expensive, and often incomplete
- Built-in compliance: designing the system with compliance as a first-class architectural concern from day one
- Example: retrofitting zero-retention into a system that was designed with persistent storage is a major rewrite; designing for zero-retention from the start is a configuration choice
- The cost of bolt-on is 5-10x higher than built-in; both in engineering time and in audit remediation

<!-- DIAGRAM: ch11-data-lifecycle.html - Data Lifecycle -->

\newpage

## Common Pitfalls

- **Treating compliance as a checkbox exercise**: compliance is an ongoing operational practice, not a one-time certification; controls must be continuously monitored and evidenced
- **Assuming SOC 2 covers everything**: SOC 2 is a baseline; HIPAA, GDPR, and EU AI Act each add specific requirements that SOC 2 does not address
- **Logging too much**: audit logging of audio content or full transcripts creates new compliance obligations for the logs themselves; log metadata, not content
- **Ignoring the EU AI Act timeline**: the Aug 2026 high-risk and transparency obligations will affect most production speech AI systems; start preparing now
- **BAA gaps in the processor chain**: a single sub-processor without a BAA breaks HIPAA compliance for the entire chain
- **Conflating data residency with data sovereignty**: residency means data is stored in a region; sovereignty means the region's laws govern the data; they are related but distinct
- **Building for one regulation and assuming it covers others**: GDPR compliance does not automatically satisfy HIPAA, and neither satisfies the EU AI Act; map each regulation independently

## Summary

- SOC 2 Type II is effectively mandatory for B2B ML API providers; the Trust Service Criteria map directly to inference system controls
- Audit logging must capture inference metadata, model lifecycle events, and access events; never log audio content or full transcripts
- Zero-retention is the safest default: process and delete, with configurable opt-in retention for customers who need it
- GDPR and CCPA classify voice as personal/biometric data; all data subject rights (access, erasure, portability) apply to audio and transcripts
- The EU AI Act introduces obligations on a staggered timeline through Aug 2027, with fines up to EUR 35M or 7% of global turnover
- HIPAA requires encryption, granular access logs, and BAAs at every level of the processor chain for healthcare speech AI
- Data residency requires region-local processing with no cross-region transfer; build regional routing into the architecture from day one
- Compliance-by-design is 5-10x cheaper than bolt-on compliance; encode rules as executable policies and feature flags

## References

*To be populated during chapter authoring. Initial sources:*

1. European Commission (2024). "EU AI Act; Regulation (EU) 2024/1689." Official Journal of the European Union.
2. EU AI Act Service Desk (2025). "Implementation Timeline and Key Dates."
3. DLA Piper (2025). "Latest Wave of Obligations Under the EU AI Act."
4. Wiz (2026). "AI Compliance in 2026: A Practical Guide."
5. Deepgram (2025). "Standard Compliance Speech-to-Text: HIPAA, SOC 2, GDPR."
6. AICPA (2025). "SOC 2 Trust Service Criteria."
7. U.S. Department of Health and Human Services (2025). "HIPAA Security Rule Guidance."

---

**Next: [Chapter 12: SLOs for Streaming ML Systems](./12-slos-streaming-ml.md)**
