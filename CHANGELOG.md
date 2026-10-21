# 📋 Changelog — AgentGreenHydrogen

All notable changes to the AgentGreenHydrogen autonomous clean energy escrow protocol and dApp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-21

### 🚀 Added
- **Intelligent Contract Core (`contracts/contract.py`):**
  - Built on `py-genlayer` pragma with GenLayer consensus support.
  - Implemented `HydrogenPolicy` storage with `TreeMap[str, HydrogenPolicy]` and `DynArray[str]`.
  - On-chain AI Clean Energy Jury using `gl.nondet.web.render`, `gl.nondet.exec_prompt`, and `gl.vm.run_nondet`.
  - Whitelist filter `_is_accredited_hydrogen_auditor` for TÜV SÜD, DNV, Bureau Veritas, NREL, CertifHy, Fraunhofer, and ISO.
  - Anti-hallucination security canary (`CANARY_AGENT_GREEN_HYDROGEN_V1`).
  - 24-block (~72 seconds) cooling-off challenge window with 10% staked dispute bond.
  - Double-payout prevention and Pull-Payment safety pattern (`claim_payout`).
- **Comprehensive Pytest Suite (`tests/`):**
  - `test_green_hydrogen_certified_full_payout`: Validates 100% subsidy release for ISO 14687 compliant hydrogen.
  - `test_green_hydrogen_unaccredited_source_rejected`: Verifies on-chain rejection of unauthenticated sources.
  - `test_partial_carbon_penalty`: Asserts 50% subsidy penalty for moderate fossil peaking grid mix.
  - `test_gray_hydrogen_rejection`: Asserts 100% refund to climate fund when steam methane reforming or low purity is detected.
  - `test_cooling_off_dispute_and_appeal`: Tests 10% staked appellate review with bound laboratory logs.
  - `test_sponsor_cannot_self_designate_electrolyzer`: Asserts role separation enforcement.
- **Frontend Command Console (`frontend/`):**
  - Industrial Hydrogen Command Console with teal, graphite, cryogenic cyan, and solar lime branding.
  - Live Web3 connector for GenLayer StudioNet (Chain ID: `61999` / Hex `0xF22F`).
  - DePIN Parametric Electrolyzer Command Matrix with gas chromatography peak spectrum, hourly renewable attribution breakdown, and PEM fuel cell diagnostics.
  - Interactive modals: Create Escrow, Submit Telemetry, Inspect Adjudication Evidence, and File Appeal.
  - Pull-payment withdrawal interface for buffered balances.
- **Deployment & Tooling:**
  - `scripts/deploy_studionet.py`: Automated contract deployment to GenLayer StudioNet with transaction receipt confirmation.
  - `scripts/generate_logo.py`: High-resolution vector/raster branding logo generator.
  - Verified deployment on StudioNet at `0xb2e60946c7c54007B04A66300378f13702FcF150`.
