# 🛡️ Security Policy — AgentGreenHydrogen

## 1. Supported Versions

| Version | Supported          | Target Network |
| ------- | ------------------ | -------------- |
| 1.0.x   | :white_check_mark: | GenLayer StudioNet (Chain ID: 61999) |

---

## 2. Security Architecture & Threat Vectors

The AgentGreenHydrogen protocol is designed to operate autonomously in adversarial decentralized environments where substantial financial subsidies are escrowed.

### 2.1 Prompt Injection & LLM Jailbreak Defense
- All prompts evaluated by `gl.nondet.exec_prompt` encapsulate telemetry payloads in XML tag boundaries (`<chromatography_audit_payload>...</chromatography_audit_payload>`).
- Strict schema parsing mandates the exact presence of the protocol security canary token:
  ```python
  CANARY_TOKEN = "CANARY_AGENT_GREEN_HYDROGEN_V1"
  ```
- If an LLM output fails to echo the canary or returns non-standard keys, the contract transitions to `STATUS_UNRESOLVED` rather than misallocating funds.

### 2.2 Unauthenticated Telemetry Injection
- Only endpoints originating from pre-approved, accredited testing laboratories (`ACCREDITED_HYDROGEN_AUDITORS`) are accepted by `submit_production_telemetry` and `appeal_verdict`.
- The domain parser verifies host suffix boundaries to prevent spoofing (e.g. `malicious-tuvsud.com` is rejected).

### 2.3 Pull-Payment Reentrancy Safeguard
- In compliance with smart contract best practices, `_safe_transfer` catches downstream failures and buffers balances into `claimable_balances[recipient]`.
- Beneficiaries claim their funds via `claim_payout()`, preventing locked escrows caused by recipient contract gas exhaustion.

### 2.4 Double-Payout Prevention
- When payouts or refunds are executed, `p.escrow_amount` and `p.dispute_bond` are zeroed out before transferring tokens.

---

## 3. Reporting a Vulnerability

If you discover a security vulnerability within the AgentGreenHydrogen protocol or frontend, please report it privately:
- Email: `security@agentgreenhydrogen.org`
- GPG Key / Encrypted communications available upon request.

Please do not open public GitHub issues for security vulnerabilities.
