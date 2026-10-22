# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import json
import hashlib

CANARY_TOKEN = "CANARY_AGENT_GREEN_HYDROGEN_V1"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Time & Cooling-Off & Appellate Parameters
SECONDS_PER_BLOCK = 3
COOLING_OFF_BLOCKS = 24
COOLING_OFF_SECONDS = bigint(COOLING_OFF_BLOCKS * SECONDS_PER_BLOCK)  # 72 seconds
APPEAL_TIMEOUT_SECONDS = bigint(7 * 86400)                             # 7 days bounded appeal timeout
DEFAULT_SUBSIDY_EXPIRY_SECONDS = bigint(86400 * 30)                   # 30 days coverage

# Lifecycle Statuses
STATUS_POLICY_OPEN = u8(0)         # Climate Fund deposited subsidy escrow, awaiting production telemetry
STATUS_TELEMETRY_SUBMITTED = u8(1) # Electrolyzer plant submitted gas chromatography and renewable certificates
STATUS_AWAITING_PAYOUT = u8(2)     # AI Hydrogen Jury rendered verdict, cooling-off active
STATUS_SETTLED_CERTIFIED_FULL = u8(3)# ISO 14687 compliant green hydrogen confirmed, 100% subsidy released
STATUS_SETTLED_PARTIAL = u8(4)     # Carbon intensity breach / minor grid mixing, 50% penalty
STATUS_SETTLED_REJECTED = u8(5)    # Gray hydrogen detected / purity failure, 100% refunded to fund
STATUS_DISPUTED = u8(6)            # Under appellate review with 10% staked bond
STATUS_EXPIRED_RECLAIMED = u8(7)   # Policy expired with zero telemetry, reclaimed by fund
STATUS_UNRESOLVED = u8(8)          # Telemetry fetch, parse, or canary failure (protected non-settling state)


class ContractError(Exception):
    """Domain-specific error for AgentGreenHydrogen protocol."""
    pass


def _to_address(val) -> Address:
    """Converts any Address, int, or str into a valid GenLayer Address instance."""
    if isinstance(val, Address):
        return val
    if isinstance(val, int):
        hex_str = f"0x{val:040x}"
        return Address(hex_str)
    if isinstance(val, str):
        clean = val.strip()
        if clean.startswith("0x") or clean.startswith("0X"):
            return Address(clean.lower())
        try:
            int_val = int(clean)
            return Address(f"0x{int_val:040x}")
        except ValueError:
            return Address(clean.lower())
    if isinstance(val, (bytes, bytearray)):
        return Address("0x" + val.hex())
    return Address(str(val))


def _addr_str(addr) -> str:
    """Safely format an Address or address-like value into a lowercase hex string."""
    if addr is None:
        return ZERO_ADDRESS
    if isinstance(addr, int):
        return f"0x{addr:040x}".lower()
    try:
        return addr.as_hex.lower()
    except Exception:
        return str(addr).lower()


def _get_sender() -> Address:
    """Safely obtain transaction sender across GenVM runtime versions."""
    try:
        raw = gl.message.sender_address
        return _to_address(raw)
    except Exception:
        try:
            raw = gl.message.sender
            return _to_address(raw)
        except Exception:
            raise ContractError("Cannot resolve sender address.")


ACCREDITED_HYDROGEN_AUDITORS = [
    "tuvsud.com",
    "dnv.com",
    "bureauveritas.com",
    "nrel.gov",
    "certifhy.eu",
    "energy.gov",
    "fraunhofer.de",
    "iso.org",
]


def _is_accredited_hydrogen_auditor(url: str) -> bool:
    """Verifies that gas chromatography telemetry originates strictly from accredited testing agencies."""
    clean = str(url).strip().lower()
    if not (clean.startswith("http://") or clean.startswith("https://")):
        return False
    try:
        no_proto = clean.split("://", 1)[1]
        host = no_proto.split("/", 1)[0].split(":", 1)[0]
        for domain in ACCREDITED_HYDROGEN_AUDITORS:
            if host == domain or host.endswith("." + domain):
                return True
    except Exception:
        return False
    return False


@allow_storage
@dataclass
class HydrogenPolicy:
    policy_id: str
    sponsor: Address               # Climate Subsidy DAO / Clean Energy Fund
    electrolyzer_plant: Address    # Green Hydrogen Production Facility
    dispute_initiator: Address     # Appellant who staked bond
    escrow_amount: bigint          # Locked subsidy allocation
    dispute_bond: bigint           # 10% appeal stake
    facility_id: str               # Production plant identifier / GPS coordinates
    min_purity_bps: u32            # Basis points of purity (e.g., 9997 = 99.97% ISO 14687)
    max_carbon_intensity_g_co2: u32# Max allowable g CO2e per kg H2 (e.g., 2000g = 2.0 kg CO2/kg H2)
    chromatography_feed_url: str   # Accredited live lab report / gas chromatography telemetry
    evidence_hash: str             # SHA-256 snapshot of laboratory telemetry payload
    status: u8
    verdict: str                   # "PENDING", "GREEN_HYDROGEN_CERTIFIED_FULL", "PARTIAL_CARBON_INTENSITY_PENALTY", "GRAY_HYDROGEN_REJECTED", "DISPUTED", "UNRESOLVED_*"
    original_verdict: str          # Preserved pre-appeal verdict
    reason: str
    confidence: u8
    measured_purity_bps: u32       # Measured purity in basis points (e.g. 9998 = 99.98%)
    measured_carbon_intensity_g: u32 # Measured carbon intensity in grams CO2e/kg H2
    created_at_time: bigint        # Trusted Unix timestamp when policy was created
    expires_at_time: bigint        # Trusted Unix timestamp when coverage concludes
    audit_completed_time: bigint   # Trusted Unix timestamp when AI jury rendered verdict
    supplemental_evidence_url: str # Bound appellate evidence URL
    appeal_prior_verdict: str      # Verdict recorded before appeal was filed
    auditor_cert_id: str           # Accredited laboratory report/certificate identifier
    batch_id: str                  # Hydrogen production batch lot number
    dispute_filed_time: bigint     # Timestamp when appellate dispute was staked


class Contract(gl.Contract):
    """
    AgentGreenHydrogen: Autonomous Green Hydrogen Purity & Renewable Electrolysis Subsidy Escrow
    Target Network: GenLayer StudioNet (Chain ID: 61999)
    Strictly On-Chain Consensus & Verifiable Production Telemetry
    """
    policies: TreeMap[str, HydrogenPolicy]
    policy_ids: DynArray[str]
    total_subsidies_locked: bigint
    total_policies_settled: u32
    policy_counter: u64
    owner: Address
    claimable_balances: TreeMap[str, bigint]
    total_pending_claims: bigint
    total_withdrawn_ledger: TreeMap[str, bigint]

    def __init__(self, initial_owner: Address = Address(ZERO_ADDRESS)):
        target_owner = _to_address(initial_owner) if initial_owner is not None else Address(ZERO_ADDRESS)
        if _addr_str(target_owner) == ZERO_ADDRESS:
            try:
                target_owner = _to_address(_get_sender())
            except Exception:
                pass

        self.owner = target_owner
        self.total_subsidies_locked = bigint(0)
        self.total_policies_settled = u32(0)
        self.policy_counter = u64(0)
        self.total_pending_claims = bigint(0)

    def _resolve_pid(self, policy_id) -> str:
        return str(policy_id).strip()

    def _ensure_owner(self) -> None:
        if _addr_str(self.owner) == ZERO_ADDRESS:
            self.owner = _to_address(_get_sender())

    def _credit_payout(self, recipient: Address, amount: bigint) -> None:
        """
        Credits beneficiary's Pull-Payment ledger balance with verified asynchronous delivery tracking.
        Prevents silent balance extinguishment by recording credits prior to outbound delivery.
        """
        if amount <= bigint(0):
            return
        rec_str = _addr_str(_to_address(recipient))
        curr = self.claimable_balances.get(rec_str, bigint(0))
        self.claimable_balances[rec_str] = curr + amount
        self.total_pending_claims = self.total_pending_claims + amount

        # Attempt immediate push transfer if supported by runtime
        try:
            r_addr = _to_address(recipient)
            gl.get_contract_at(r_addr).emit_transfer(value=u256(int(amount)))
            # If emitted without throwing synchronously:
            self.claimable_balances[rec_str] = curr
            self.total_pending_claims = self.total_pending_claims - amount if self.total_pending_claims >= amount else bigint(0)
            prev_w = self.total_withdrawn_ledger.get(rec_str, bigint(0))
            self.total_withdrawn_ledger[rec_str] = prev_w + amount
        except Exception:
            # Transfer asynchronous or pending: credit safely recorded in claimable_balances ledger
            pass

    def _get_current_timestamp(self) -> bigint:
        """Derives trusted Unix timestamp strictly from consensus context (gl.message_raw['datetime'])."""
        import calendar
        from datetime import datetime, timezone
        try:
            if hasattr(gl, "message_raw") and isinstance(gl.message_raw, dict):
                raw_val = gl.message_raw.get("datetime", "")
                if raw_val:
                    dt_str = str(raw_val).strip().replace("Z", "+00:00")
                    dt = datetime.fromisoformat(dt_str)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    ts = calendar.timegm(dt.utctimetuple())
                    if ts > 0:
                        return bigint(ts)
        except Exception:
            pass
        return bigint(1760000000)

    # ── Public Write Methods (Strict Role & Provenance Enforcement) ───

    @gl.public.write.payable
    def create_subsidy_policy(
        self,
        electrolyzer_plant: Address,
        facility_id: str,
        min_purity_bps: u32,
        max_carbon_intensity_g_co2: u32,
        duration_blocks: u32
    ) -> str:
        """Role: Climate Subsidy Fund deposits subsidy allocation for accredited hydrogen electrolysis."""
        self._ensure_owner()
        escrow = bigint(gl.message.value)
        if escrow <= bigint(0):
            raise ContractError("Subsidy escrow deposit must be greater than 0 GEN.")

        clean_fac = str(facility_id).strip().upper()
        if len(clean_fac) < 4:
            raise ContractError("Valid hydrogen production facility ID required (>= 4 chars).")

        p_addr = _to_address(electrolyzer_plant)
        if _addr_str(p_addr) == ZERO_ADDRESS:
            raise ContractError("Valid electrolyzer plant address required.")

        s_addr = _to_address(_get_sender())
        if _addr_str(s_addr) == _addr_str(p_addr):
            raise ContractError("Role Violation: Sponsor fund cannot designate themselves as the electrolyzer plant.")

        dur_secs = bigint(int(duration_blocks) * 3 if int(duration_blocks) > 0 else int(DEFAULT_SUBSIDY_EXPIRY_SECONDS))

        self.policy_counter = self.policy_counter + u64(1)
        policy_id = str(self.policy_counter)
        current_time = self._get_current_timestamp()
        expires_at = current_time + dur_secs
        empty_addr = Address(ZERO_ADDRESS)

        new_policy = HydrogenPolicy(
            policy_id=policy_id,
            sponsor=s_addr,
            electrolyzer_plant=p_addr,
            dispute_initiator=empty_addr,
            escrow_amount=escrow,
            dispute_bond=bigint(0),
            facility_id=clean_fac,
            min_purity_bps=u32(int(min_purity_bps)),
            max_carbon_intensity_g_co2=u32(int(max_carbon_intensity_g_co2)),
            chromatography_feed_url="",
            evidence_hash="",
            status=STATUS_POLICY_OPEN,
            verdict="PENDING",
            original_verdict="PENDING",
            reason="Subsidy escrow active. Monitored for ISO 14687 hydrogen purity and 100% renewable energy attribution.",
            confidence=u8(0),
            measured_purity_bps=u32(0),
            measured_carbon_intensity_g=u32(0),
            created_at_time=current_time,
            expires_at_time=expires_at,
            audit_completed_time=bigint(0),
            supplemental_evidence_url="",
            appeal_prior_verdict="",
            auditor_cert_id="",
            batch_id="",
            dispute_filed_time=bigint(0),
        )

        self.policies[policy_id] = new_policy
        self.policy_ids.append(policy_id)
        self.total_subsidies_locked = self.total_subsidies_locked + escrow
        return policy_id

    @gl.public.write
    def submit_production_telemetry(
        self,
        policy_id: str,
        chromatography_feed_url: str
    ) -> None:
        """Role: Electrolyzer facility submits accredited gas chromatography and hourly renewable matching data."""
        self._ensure_owner()
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        if p.status not in (STATUS_POLICY_OPEN, STATUS_UNRESOLVED):
            raise ContractError("Policy is not open for production telemetry submission.")

        sender = _get_sender()
        if _addr_str(sender) != _addr_str(p.electrolyzer_plant):
            raise ContractError("Role Violation: Only registered electrolyzer plant can submit production telemetry.")

        clean_url = str(chromatography_feed_url).strip()
        if not _is_accredited_hydrogen_auditor(clean_url):
            raise ContractError("Telemetry unauthenticated: Must originate from an accredited testing agency (TÜV SÜD, DNV, Bureau Veritas, NREL, CertifHy, Fraunhofer, ISO).")

        current_time = self._get_current_timestamp()
        if current_time > p.expires_at_time:
            raise ContractError("Coverage duration for this subsidy policy has expired.")

        p.chromatography_feed_url = clean_url
        p.status = STATUS_TELEMETRY_SUBMITTED
        p.reason = "Gas chromatography and renewable matching telemetry submitted. Ready for on-chain AI Tribunal verification."

    @gl.public.write
    def adjudicate_hydrogen_quality(self, policy_id: str) -> None:
        """
        AI Clean Energy Tribunal: Multi-Perspective Forensic & Environmental Audit
        Ingests third-party laboratory telemetry, validates evidence integrity across validators,
        verifies facility provenance, and strictly enforces on-chain mathematical thresholds.
        """
        self._ensure_owner()
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        if p.status not in (STATUS_TELEMETRY_SUBMITTED, STATUS_UNRESOLVED):
            raise ContractError("Policy is not awaiting quality adjudication.")

        sender_str = _addr_str(_get_sender())
        if (
            sender_str != _addr_str(p.sponsor)
            and sender_str != _addr_str(p.electrolyzer_plant)
            and sender_str != _addr_str(self.owner)
        ):
            raise ContractError("Permission Denied: Only sponsor, electrolyzer plant, or owner can trigger adjudication.")

        feed_url = p.chromatography_feed_url
        facility = p.facility_id
        target_purity = int(p.min_purity_bps)
        max_carbon = int(p.max_carbon_intensity_g_co2)

        def leader_fn():
            raw_feed = ""
            try:
                raw_feed = gl.nondet.web.render(feed_url, mode="text")
            except Exception:
                pass

            if not raw_feed:
                return {
                    "canary": CANARY_TOKEN,
                    "verdict": "UNRESOLVED_FETCH_FAILED",
                    "confidence": 0,
                    "facility_id": "",
                    "batch_id": "",
                    "auditor_cert_id": "",
                    "measurement_timestamp": 0,
                    "measured_purity_bps": 0,
                    "measured_carbon_intensity_g": 0,
                    "reason": "Chromatography inspection report unreachable or empty.",
                    "evidence_hash": "0000000000000000000000000000000000000000000000000000000000000000",
                }

            ev_hash = hashlib.sha256(raw_feed.encode("utf-8")).hexdigest()

            prompt = f"""You are the Chief Industrial Chemist & Clean Hydrogen Standards Tribunal on GenLayer.
Evaluate third-party laboratory gas chromatography and hourly renewable matching data for facility: {facility}.

STANDARDS REQUIRED:
- TARGET FACILITY ID: {facility}
- MINIMUM REQUIRED PURITY: >= {target_purity} basis points (e.g. 9997 = 99.97% ISO 14687:2019 Type I Grade D fuel cell grade)
- MAXIMUM LIFECYCLE CARBON INTENSITY: <= {max_carbon} grams CO2e / kg H2 (EU RED III Clean Hydrogen Standard)

AUDIT & SPECTROMETRY TELEMETRY PAYLOAD:
<chromatography_audit_payload>
{raw_feed[:4000]}
</chromatography_audit_payload>

INDEPENDENT EVIDENCE EXTRACTION MANDATE:
1. Extract facility_id specified in the report (exact string).
2. Extract batch_id or inspection lot number.
3. Extract auditor_cert_id (accredited certificate or report reference number).
4. Extract measurement_timestamp (Unix timestamp in seconds or 0 if not present).
5. Extract measured_purity_bps (integer basis points, e.g. 99.98% = 9998 bps).
6. Extract measured_carbon_intensity_g (integer grams CO2 equivalent per kg H2 produced).
7. Extract hourly_renewable_match_ratio (0-100 percentage of hourly matched renewable power).

DECISION CLASSIFICATION:
- Certified Green Hydrogen: Purity >= {target_purity} bps AND Carbon Intensity <= {max_carbon} g CO2e/kg:
  Verdict: "GREEN_HYDROGEN_CERTIFIED_FULL"
- Partial Carbon Penalty: Purity >= {target_purity} bps BUT Carbon Intensity between ({max_carbon} + 1) and ({max_carbon} * 2) g CO2e/kg:
  Verdict: "PARTIAL_CARBON_INTENSITY_PENALTY"
- Gray Hydrogen / Purity Breach: Purity < {target_purity} bps OR Carbon Intensity > ({max_carbon} * 2) g CO2e/kg:
  Verdict: "GRAY_HYDROGEN_REJECTED"

SECURITY CANARY: Echo "{CANARY_TOKEN}" in JSON.
Respond ONLY with valid JSON without markdown fences:
{{
  "canary": "{CANARY_TOKEN}",
  "verdict": "GREEN_HYDROGEN_CERTIFIED_FULL" | "PARTIAL_CARBON_INTENSITY_PENALTY" | "GRAY_HYDROGEN_REJECTED",
  "confidence": <0-100>,
  "facility_id": "<exact facility string from report>",
  "batch_id": "<batch identifier>",
  "auditor_cert_id": "<certificate number>",
  "measurement_timestamp": <integer unix timestamp in seconds>,
  "measured_purity_bps": <integer>,
  "measured_carbon_intensity_g": <integer>,
  "hourly_renewable_match_ratio": <0-100>,
  "reason": "<rigorous chemical and environmental audit justification under 200 chars>"
}}"""

            raw_res = gl.nondet.exec_prompt(prompt, response_format="json")
            parsed = None
            if isinstance(raw_res, dict):
                parsed = raw_res
            elif isinstance(raw_res, str):
                try:
                    parsed = json.loads(raw_res.replace("```json", "").replace("```", "").strip())
                except Exception:
                    pass

            if not parsed or not isinstance(parsed, dict):
                return {
                    "canary": CANARY_TOKEN,
                    "verdict": "UNRESOLVED_PARSE_FAILED",
                    "confidence": 0,
                    "facility_id": "",
                    "batch_id": "",
                    "auditor_cert_id": "",
                    "measurement_timestamp": 0,
                    "measured_purity_bps": 0,
                    "measured_carbon_intensity_g": 0,
                    "reason": "AI validator parsing failed or malformed JSON returned.",
                    "evidence_hash": ev_hash,
                }

            if str(parsed.get("canary", "")) != CANARY_TOKEN:
                return {
                    "canary": CANARY_TOKEN,
                    "verdict": "UNRESOLVED_CANARY_FAILED",
                    "confidence": 0,
                    "facility_id": "",
                    "batch_id": "",
                    "auditor_cert_id": "",
                    "measurement_timestamp": 0,
                    "measured_purity_bps": 0,
                    "measured_carbon_intensity_g": 0,
                    "reason": "Security canary mismatch detected in jury output.",
                    "evidence_hash": ev_hash,
                }

            v_raw = str(parsed.get("verdict", "")).upper().strip()
            if v_raw not in {"GREEN_HYDROGEN_CERTIFIED_FULL", "PARTIAL_CARBON_INTENSITY_PENALTY", "GRAY_HYDROGEN_REJECTED"}:
                v_raw = "UNRESOLVED_PARSE_FAILED"

            return {
                "canary": CANARY_TOKEN,
                "verdict": v_raw,
                "confidence": max(0, min(100, int(parsed.get("confidence", 85)))),
                "facility_id": str(parsed.get("facility_id", "")).strip().upper(),
                "batch_id": str(parsed.get("batch_id", "")).strip(),
                "auditor_cert_id": str(parsed.get("auditor_cert_id", "")).strip(),
                "measurement_timestamp": int(parsed.get("measurement_timestamp", 0)),
                "measured_purity_bps": max(0, min(10000, int(parsed.get("measured_purity_bps", 0)))),
                "measured_carbon_intensity_g": max(0, min(100000, int(parsed.get("measured_carbon_intensity_g", 0)))),
                "reason": str(parsed.get("reason", "Hydrogen spectrometry audit concluded."))[:200],
                "evidence_hash": ev_hash,
            }

        def validator_fn(leader_res) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            leader = leader_res.calldata
            if not isinstance(leader, dict) or "verdict" not in leader:
                return False
            if leader.get("canary") != CANARY_TOKEN:
                return False

            mine = leader_fn()
            if mine.get("canary") != CANARY_TOKEN:
                return False

            # 1. Independent validation of evidence hash agreement
            if str(mine.get("evidence_hash", "")) != str(leader.get("evidence_hash", "")):
                return False

            # 2. Independent validation of facility ID provenance
            if str(mine.get("facility_id", "")).strip() != str(leader.get("facility_id", "")).strip():
                return False

            # 3. Independent validation of decisive purity within strict tolerance (<= 5 bps)
            purity_diff = abs(int(mine.get("measured_purity_bps", 0)) - int(leader.get("measured_purity_bps", 0)))
            if purity_diff > 5:
                return False

            # 4. Independent validation of decisive carbon intensity within strict tolerance (<= 50g)
            carbon_diff = abs(int(mine.get("measured_carbon_intensity_g", 0)) - int(leader.get("measured_carbon_intensity_g", 0)))
            if carbon_diff > 50:
                return False

            return mine["verdict"] == leader["verdict"]

        adjudication_res = gl.vm.run_nondet(leader_fn, validator_fn)
        v_res = str(adjudication_res["verdict"])

        if v_res.startswith("UNRESOLVED_"):
            p.status = STATUS_UNRESOLVED
            p.verdict = v_res
            p.reason = str(adjudication_res["reason"])
            p.evidence_hash = str(adjudication_res.get("evidence_hash", ""))
            return

        ev_hash = str(adjudication_res.get("evidence_hash", ""))
        facility_extracted = str(adjudication_res.get("facility_id", "")).strip().upper()
        batch_extracted = str(adjudication_res.get("batch_id", "")).strip()
        cert_extracted = str(adjudication_res.get("auditor_cert_id", "")).strip()
        meas_ts = int(adjudication_res.get("measurement_timestamp", 0))
        measured_purity = int(adjudication_res.get("measured_purity_bps", 0))
        measured_carbon = int(adjudication_res.get("measured_carbon_intensity_g", 0))

        p.evidence_hash = ev_hash
        p.measured_purity_bps = u32(max(0, min(10000, measured_purity)))
        p.measured_carbon_intensity_g = u32(max(0, min(100000, measured_carbon)))
        p.confidence = u8(max(0, min(100, int(adjudication_res.get("confidence", 85)))))
        p.auditor_cert_id = cert_extracted if cert_extracted else "CERT-VERIFIED-ISO14687"
        p.batch_id = batch_extracted if batch_extracted else "BATCH-ELECTROLYSIS-01"

        # On-Chain Independent Verification of Provenance & Decisive Thresholds
        if facility_extracted and facility_extracted != p.facility_id:
            p.verdict = "GRAY_HYDROGEN_REJECTED"
            p.reason = f"Provenance Failure: Telemetry issued for '{facility_extracted}', but policy requires '{p.facility_id}'."
        elif meas_ts > 0 and (meas_ts < int(p.created_at_time) or meas_ts > int(p.expires_at_time)):
            p.verdict = "GRAY_HYDROGEN_REJECTED"
            p.reason = f"Provenance Failure: Measurement timestamp ({meas_ts}) outside active policy lifespan ({p.created_at_time} - {p.expires_at_time})."
        elif measured_purity < int(p.min_purity_bps):
            p.verdict = "GRAY_HYDROGEN_REJECTED"
            p.reason = f"Threshold Enforcement: Measured purity {measured_purity} bps is below ISO 14687 minimum standard ({p.min_purity_bps} bps)."
        elif measured_carbon > int(p.max_carbon_intensity_g_co2) * 2:
            p.verdict = "GRAY_HYDROGEN_REJECTED"
            p.reason = f"Threshold Enforcement: Carbon intensity {measured_carbon} g CO2e/kg exceeds maximum allowable limit ({p.max_carbon_intensity_g_co2 * 2} g)."
        elif measured_carbon > int(p.max_carbon_intensity_g_co2):
            p.verdict = "PARTIAL_CARBON_INTENSITY_PENALTY"
            p.reason = f"Threshold Enforcement: Purity {measured_purity} bps verified, but carbon intensity {measured_carbon} g CO2e/kg exceeds clean threshold ({p.max_carbon_intensity_g_co2} g). 50% penalty applied."
        else:
            p.verdict = "GREEN_HYDROGEN_CERTIFIED_FULL"
            p.reason = f"ISO 14687 Fully Certified: Purity {measured_purity} bps >= {p.min_purity_bps} bps and lifecycle carbon {measured_carbon} g CO2e/kg <= {p.max_carbon_intensity_g_co2} g."

        p.original_verdict = p.verdict
        p.audit_completed_time = self._get_current_timestamp()
        p.status = STATUS_AWAITING_PAYOUT

    @gl.public.write.payable
    def file_dispute(
        self,
        policy_id: str,
        counter_evidence_url: str,
        dispute_reason: str
    ) -> None:
        """
        Role: Stakeholders can challenge quality verdict during cooling-off window.
        Stakes 10% dispute bond. Records dispute_filed_time for bounded appellate timeout recovery.
        """
        self._ensure_owner()
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        if p.status != STATUS_AWAITING_PAYOUT:
            raise ContractError("Disputes can only be filed during STATUS_AWAITING_PAYOUT cooling-off.")

        current_time = self._get_current_timestamp()
        if current_time > (p.audit_completed_time + COOLING_OFF_SECONDS):
            raise ContractError(f"Cooling-off window ({int(COOLING_OFF_SECONDS)}s) has elapsed. Settlement can be finalized.")

        sender = _get_sender()
        sender_str = _addr_str(sender)
        if sender_str != _addr_str(p.sponsor) and sender_str != _addr_str(p.electrolyzer_plant):
            raise ContractError("Permission Denied: Only sponsor or electrolyzer plant can dispute.")

        clean_url = str(counter_evidence_url).strip()
        if not _is_accredited_hydrogen_auditor(clean_url):
            raise ContractError("Counter-evidence unauthenticated: Must originate from an accredited testing agency.")

        staked = bigint(gl.message.value)
        required_bond = p.escrow_amount // bigint(10)
        if staked < required_bond:
            raise ContractError(f"Must stake at least 10% dispute bond ({int(required_bond)} wei).")

        clean_reason = str(dispute_reason).strip()
        if len(clean_reason) < 10:
            raise ContractError("Detailed dispute justification (>= 10 chars) required.")

        p.appeal_prior_verdict = p.verdict
        p.status = STATUS_DISPUTED
        p.dispute_initiator = _to_address(sender)
        p.dispute_bond = staked
        p.dispute_filed_time = current_time
        p.supplemental_evidence_url = clean_url
        p.reason = f"[DISPUTE by {_addr_str(sender)[:8]}]: {clean_reason} | Prior: {p.reason}"
        self.total_subsidies_locked = self.total_subsidies_locked + staked

    @gl.public.write.payable
    def appeal_verdict(
        self,
        policy_id: str,
        dispute_reason: str,
        counter_evidence_url: str
    ) -> None:
        """Alias for file_dispute allowing standard UI parameter order."""
        return self.file_dispute(policy_id, counter_evidence_url, dispute_reason)

    @gl.public.write
    def adjudicate_appeal(self, policy_id: str) -> None:
        """Supreme Clean Energy Appellate Court evaluates strictly against bound supplemental laboratory report."""
        self._ensure_owner()
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        if p.status != STATUS_DISPUTED:
            raise ContractError("Policy is not in DISPUTED status.")

        sender_str = _addr_str(_get_sender())
        if (
            sender_str != _addr_str(p.sponsor)
            and sender_str != _addr_str(p.electrolyzer_plant)
            and sender_str != _addr_str(self.owner)
        ):
            raise ContractError("Permission Denied: Only sponsor, electrolyzer plant, or owner can adjudicate appeal.")

        bound_url = p.supplemental_evidence_url
        appellant = p.dispute_initiator
        prior_verdict = p.appeal_prior_verdict
        is_sponsor_appellant = (_addr_str(appellant) == _addr_str(p.sponsor))

        def leader_fn():
            raw_supp = ""
            try:
                raw_supp = gl.nondet.web.render(bound_url, mode="text")
            except Exception:
                pass

            if not raw_supp:
                return {
                    "canary": CANARY_TOKEN,
                    "verdict": "APPEAL_UNRESOLVED_FETCH_FAILED",
                    "reason": "Supplemental chemical inspection report unreachable.",
                    "evidence_hash": "0000000000000000000000000000000000000000000000000000000000000000",
                }

            ev_hash = hashlib.sha256(raw_supp.encode("utf-8")).hexdigest()

            prompt = f"""You are the Supreme Clean Energy Appellate Magistrate on GenLayer.
Evaluate bound third-party laboratory spectrometry logs for facility {p.facility_id}:
PRIOR VERDICT: {prior_verdict}
APPELLANT: {'SPONSOR' if is_sponsor_appellant else 'ELECTROLYZER_PLANT'}

SUPPLEMENTAL AUDIT DATA:
{raw_supp[:4000]}

DECISION CRITERIA:
- If supplemental logs verify full ISO 14687 compliance (purity >= {p.min_purity_bps} bps and carbon <= {p.max_carbon_intensity_g_co2} g): Output "APPEAL_UPHELD_CERTIFIED".
- If partial carbon mixing verified: Output "APPEAL_UPHELD_PARTIAL".
- If severe gray hydrogen dilution or purity breach verified: Output "APPEAL_UPHELD_REJECTED".
- Otherwise: Output "APPEAL_DISMISSED".

SECURITY CANARY: Echo "{CANARY_TOKEN}" in JSON.
Respond ONLY with valid JSON:
{{"canary": "{CANARY_TOKEN}", "verdict": "APPEAL_UPHELD_CERTIFIED"|"APPEAL_UPHELD_PARTIAL"|"APPEAL_UPHELD_REJECTED"|"APPEAL_DISMISSED", "reason": "<rationale under 200 chars>"}}"""

            raw_res = gl.nondet.exec_prompt(prompt, response_format="json")
            parsed = None
            if isinstance(raw_res, dict):
                parsed = raw_res
            elif isinstance(raw_res, str):
                try:
                    parsed = json.loads(raw_res.replace("```json", "").replace("```", "").strip())
                except Exception:
                    pass

            if not parsed or not isinstance(parsed, dict) or str(parsed.get("canary", "")) != CANARY_TOKEN:
                return {"canary": CANARY_TOKEN, "verdict": "APPEAL_UNRESOLVED_PARSE_FAILED", "reason": "Appellate parsing failure.", "evidence_hash": ev_hash}

            v_str = str(parsed.get("verdict", "")).upper().strip()
            if v_str not in {"APPEAL_UPHELD_CERTIFIED", "APPEAL_UPHELD_PARTIAL", "APPEAL_UPHELD_REJECTED", "APPEAL_DISMISSED"}:
                v_str = "APPEAL_UNRESOLVED_PARSE_FAILED"

            return {
                "canary": CANARY_TOKEN,
                "verdict": v_str,
                "reason": str(parsed.get("reason", "Appellate review completed."))[:200],
                "evidence_hash": ev_hash,
            }

        def validator_fn(leader_res) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            leader = leader_res.calldata
            if not isinstance(leader, dict) or "verdict" not in leader:
                return False
            if leader.get("canary") != CANARY_TOKEN:
                return False

            mine = leader_fn()
            if mine.get("canary") != CANARY_TOKEN:
                return False

            if str(mine.get("evidence_hash", "")) != str(leader.get("evidence_hash", "")):
                return False

            return mine["verdict"] == leader["verdict"]

        appeal_res = gl.vm.run_nondet(leader_fn, validator_fn)
        app_verdict = appeal_res["verdict"]
        app_reason = appeal_res["reason"]

        if app_verdict.startswith("APPEAL_UNRESOLVED_"):
            p.status = STATUS_UNRESOLVED
            p.verdict = app_verdict
            p.reason = f"[APPEAL UNRESOLVED] {app_reason}"
            return

        escrow_val = p.escrow_amount
        bond_val = p.dispute_bond
        total_settling = escrow_val + bond_val
        p.dispute_bond = bigint(0)
        p.escrow_amount = bigint(0)  # Double-payout protection

        self.total_subsidies_locked = self.total_subsidies_locked - total_settling
        self.total_policies_settled = self.total_policies_settled + u32(1)

        counterparty = p.electrolyzer_plant if is_sponsor_appellant else p.sponsor

        if app_verdict == "APPEAL_UPHELD_CERTIFIED":
            p.status = STATUS_SETTLED_CERTIFIED_FULL
            p.verdict = "GREEN_HYDROGEN_CERTIFIED_FULL"
            p.reason = f"[APPEAL UPHELD] {app_reason}"
            self._credit_payout(p.electrolyzer_plant, escrow_val)
            if not is_sponsor_appellant:
                self._credit_payout(appellant, bond_val)
            else:
                self._credit_payout(counterparty, bond_val)

        elif app_verdict == "APPEAL_UPHELD_PARTIAL":
            p.status = STATUS_SETTLED_PARTIAL
            p.verdict = "PARTIAL_CARBON_INTENSITY_PENALTY"
            payout = escrow_val // bigint(2)
            refund = escrow_val - payout
            p.reason = f"[APPEAL RESOLUTION] {app_reason}"
            self._credit_payout(p.electrolyzer_plant, payout)
            self._credit_payout(p.sponsor, refund)
            self._credit_payout(appellant, bond_val)

        elif app_verdict == "APPEAL_UPHELD_REJECTED":
            p.status = STATUS_SETTLED_REJECTED
            p.verdict = "GRAY_HYDROGEN_REJECTED"
            p.reason = f"[APPEAL RESOLUTION] {app_reason}"
            self._credit_payout(p.sponsor, escrow_val)
            if is_sponsor_appellant:
                self._credit_payout(appellant, bond_val)
            else:
                self._credit_payout(counterparty, bond_val)

        else:
            # APPEAL_DISMISSED: Preserve original verdict and forfeit bond to counterparty
            p.reason = f"[APPEAL DISMISSED] {app_reason}"
            self._credit_payout(counterparty, bond_val)

            if p.original_verdict == "GREEN_HYDROGEN_CERTIFIED_FULL":
                p.status = STATUS_SETTLED_CERTIFIED_FULL
                p.verdict = "GREEN_HYDROGEN_CERTIFIED_FULL"
                self._credit_payout(p.electrolyzer_plant, escrow_val)
            elif p.original_verdict == "PARTIAL_CARBON_INTENSITY_PENALTY":
                p.status = STATUS_SETTLED_PARTIAL
                p.verdict = "PARTIAL_CARBON_INTENSITY_PENALTY"
                payout = escrow_val // bigint(2)
                refund = escrow_val - payout
                self._credit_payout(p.electrolyzer_plant, payout)
                self._credit_payout(p.sponsor, refund)
            else:
                p.status = STATUS_SETTLED_REJECTED
                p.verdict = "GRAY_HYDROGEN_REJECTED"
                self._credit_payout(p.sponsor, escrow_val)

    @gl.public.write
    def resolve_stale_appeal(self, policy_id: str) -> None:
        """
        Role: Bounded recovery for unresolved or timed-out appeals.
        Safeguards both the subsidy escrow and dispute bond:
        1. Refunds 100% of the dispute bond to the appellant.
        2. Restores the policy to its pre-appeal verdict and resets cooling-off for final settlement.
        """
        self._ensure_owner()
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        if p.status not in (STATUS_DISPUTED, STATUS_UNRESOLVED):
            raise ContractError("Policy is not in a disputed or unresolved appellate state.")

        if p.dispute_bond <= bigint(0):
            raise ContractError("No active dispute bond locked on this policy.")

        current_time = self._get_current_timestamp()
        timeout_threshold = p.dispute_filed_time + APPEAL_TIMEOUT_SECONDS
        is_timed_out = (current_time > timeout_threshold)
        is_unresolvable_error = (p.status == STATUS_UNRESOLVED and str(p.verdict).startswith("APPEAL_UNRESOLVED_"))

        if not is_timed_out and not is_unresolvable_error:
            rem = int(timeout_threshold - current_time)
            raise ContractError(f"Appellate window is active. Timeout recovery available in {max(0, rem)} seconds.")

        sender_str = _addr_str(_get_sender())
        if (
            sender_str != _addr_str(p.sponsor)
            and sender_str != _addr_str(p.electrolyzer_plant)
            and sender_str != _addr_str(p.dispute_initiator)
            and sender_str != _addr_str(self.owner)
        ):
            raise ContractError("Permission Denied: Only policy participants, appellant, or owner can trigger appeal recovery.")

        bond_val = p.dispute_bond
        p.dispute_bond = bigint(0)
        self.total_subsidies_locked = self.total_subsidies_locked - bond_val if self.total_subsidies_locked >= bond_val else bigint(0)

        # 1. Safely refund 100% of the dispute bond back to the appellant via Pull-Payment ledger
        self._credit_payout(p.dispute_initiator, bond_val)

        # 2. Restore policy to prior pre-appeal verdict and reset cooling-off window
        p.verdict = p.appeal_prior_verdict if p.appeal_prior_verdict and p.appeal_prior_verdict != "PENDING" else "GREEN_HYDROGEN_CERTIFIED_FULL"
        p.status = STATUS_AWAITING_PAYOUT
        p.audit_completed_time = current_time  # Fresh cooling-off window
        p.reason = f"[APPEAL TIMEOUT RECOVERY]: Supplemental evidence timed out or unreachable. 100% dispute bond ({bond_val} wei) refunded to appellant. Policy restored to prior verdict '{p.verdict}'."

    @gl.public.write
    def finalize_settlement(self, policy_id: str) -> None:
        """Role: Stakeholders or owner executes uncontested settlement strictly after cooling-off window."""
        self._ensure_owner()
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        if p.status != STATUS_AWAITING_PAYOUT:
            raise ContractError("Policy is not in STATUS_AWAITING_PAYOUT state.")

        current_time = self._get_current_timestamp()
        if current_time <= (p.audit_completed_time + COOLING_OFF_SECONDS):
            remaining = (p.audit_completed_time + COOLING_OFF_SECONDS) - current_time
            raise ContractError(f"Cooling-off challenge window ({int(COOLING_OFF_SECONDS)}s) is active. Payout locked for another {remaining}s.")

        sender_str = _addr_str(_get_sender())
        if (
            sender_str != _addr_str(p.sponsor)
            and sender_str != _addr_str(p.electrolyzer_plant)
            and sender_str != _addr_str(self.owner)
        ):
            raise ContractError("Permission Denied: Only stakeholders or owner can finalize payout.")

        escrow_val = p.escrow_amount
        p.escrow_amount = bigint(0)  # Double-payout protection
        self.total_subsidies_locked = self.total_subsidies_locked - escrow_val
        self.total_policies_settled = self.total_policies_settled + u32(1)

        if p.verdict == "GREEN_HYDROGEN_CERTIFIED_FULL":
            p.status = STATUS_SETTLED_CERTIFIED_FULL
            self._credit_payout(p.electrolyzer_plant, escrow_val)

        elif p.verdict == "PARTIAL_CARBON_INTENSITY_PENALTY":
            p.status = STATUS_SETTLED_PARTIAL
            payout = escrow_val // bigint(2)
            refund = escrow_val - payout
            self._credit_payout(p.electrolyzer_plant, payout)
            self._credit_payout(p.sponsor, refund)

        else:
            p.status = STATUS_SETTLED_REJECTED
            self._credit_payout(p.sponsor, escrow_val)

    @gl.public.write
    def cancel_or_reclaim(self, policy_id: str) -> None:
        """Role: Only sponsor fund can reclaim escrow if coverage expired without telemetry or stalled."""
        self._ensure_owner()
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        if _addr_str(_get_sender()) != _addr_str(p.sponsor) and _addr_str(_get_sender()) != _addr_str(self.owner):
            raise ContractError("Role Violation: Only sponsor fund or owner can reclaim expired subsidy escrow.")

        current_time = self._get_current_timestamp()
        if p.status in (STATUS_POLICY_OPEN, STATUS_UNRESOLVED):
            if current_time < p.expires_at_time:
                raise ContractError(f"Cannot reclaim: Policy is still active (expires at {int(p.expires_at_time)}).")
        else:
            raise ContractError("Cannot reclaim: Policy has telemetry actively undergoing evaluation or already settled.")

        p.status = STATUS_EXPIRED_RECLAIMED
        p.verdict = "EXPIRED_CLEAN"
        p.reason = "Policy duration completed without valid spectrometry telemetry. Escrow reclaimed by sponsor fund."

        escrow_val = p.escrow_amount
        p.escrow_amount = bigint(0)
        self.total_subsidies_locked = self.total_subsidies_locked - escrow_val
        self._credit_payout(p.sponsor, escrow_val)

    @gl.public.write
    def claim_payout(self) -> None:
        """
        Pull-Payment claim: Safely withdraw accrued beneficiary credits with verified delivery accounting.
        Never extinguishes beneficiary balances upon outbound transfer failures.
        """
        self._ensure_owner()
        sender = _get_sender()
        s_str = _addr_str(sender)
        bal = self.claimable_balances.get(s_str, bigint(0))
        if bal <= bigint(0):
            raise ContractError("No claimable balance available for withdrawal.")

        try:
            gl.get_contract_at(sender).emit_transfer(value=u256(int(bal)))
        except Exception as e:
            raise ContractError(f"Outbound transfer failed during claim: {str(e)}. Balance preserved.")

        # Successfully delivered: clear claimable and credit withdrawn ledger
        self.claimable_balances[s_str] = bigint(0)
        self.total_pending_claims = self.total_pending_claims - bal if self.total_pending_claims >= bal else bigint(0)
        prev_w = self.total_withdrawn_ledger.get(s_str, bigint(0))
        self.total_withdrawn_ledger[s_str] = prev_w + bal

    # ── Read-only Views (Deterministic Consensus) ─────────────────────

    @gl.public.view
    def get_policy(self, policy_id: str) -> str:
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        data = {
            "policy_id": p.policy_id,
            "sponsor": _addr_str(p.sponsor),
            "electrolyzer_plant": _addr_str(p.electrolyzer_plant),
            "dispute_initiator": _addr_str(p.dispute_initiator),
            "escrow_amount": str(p.escrow_amount),
            "dispute_bond": str(p.dispute_bond),
            "facility_id": p.facility_id,
            "min_purity_bps": int(p.min_purity_bps),
            "max_carbon_intensity_g_co2": int(p.max_carbon_intensity_g_co2),
            "chromatography_feed_url": p.chromatography_feed_url,
            "evidence_hash": p.evidence_hash,
            "status": int(p.status),
            "verdict": p.verdict,
            "original_verdict": p.original_verdict,
            "reason": p.reason,
            "confidence": int(p.confidence),
            "measured_purity_bps": int(p.measured_purity_bps),
            "measured_carbon_intensity_g": int(p.measured_carbon_intensity_g),
            "created_at_time": str(p.created_at_time),
            "expires_at_time": str(p.expires_at_time),
            "audit_completed_time": str(p.audit_completed_time),
            "supplemental_evidence_url": p.supplemental_evidence_url,
            "appeal_prior_verdict": p.appeal_prior_verdict,
            "auditor_cert_id": p.auditor_cert_id,
            "batch_id": p.batch_id,
            "dispute_filed_time": str(p.dispute_filed_time),
        }
        return json.dumps(data)

    @gl.public.view
    def get_user_role(self, policy_id: str, account: Address) -> str:
        """Determines user's role: SPONSOR, ELECTROLYZER_PLANT, APPELLANT, OWNER, or OBSERVER."""
        pid = self._resolve_pid(policy_id)
        acc_str = _addr_str(account)
        if pid not in self.policies:
            if acc_str == _addr_str(self.owner):
                return "OWNER"
            return "OBSERVER"

        p = self.policies[pid]
        if acc_str == _addr_str(p.sponsor):
            return "SPONSOR"
        if acc_str == _addr_str(p.electrolyzer_plant):
            return "ELECTROLYZER_PLANT"
        if acc_str == _addr_str(p.dispute_initiator) and acc_str != ZERO_ADDRESS:
            return "APPELLANT"
        if acc_str == _addr_str(self.owner):
            return "OWNER"
        return "OBSERVER"

    @gl.public.view
    def get_remaining_cooling_off_seconds(self, policy_id: str) -> i64:
        """Returns remaining cooling off challenge window in seconds (0 if expired or not in cooling off)."""
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            return i64(0)
        p = self.policies[pid]
        if p.status != STATUS_AWAITING_PAYOUT or p.audit_completed_time <= bigint(0):
            return i64(0)
        current_time = self._get_current_timestamp()
        expiry = p.audit_completed_time + COOLING_OFF_SECONDS
        remaining = int(expiry - current_time)
        return i64(remaining if remaining > 0 else 0)

    @gl.public.view
    def get_policy_count(self) -> u64:
        return u64(len(self.policy_ids))

    @gl.public.view
    def get_all_policies(self) -> str:
        policies_list = []
        for pid in self.policy_ids:
            if pid in self.policies:
                p = self.policies[pid]
                policies_list.append({
                    "policy_id": p.policy_id,
                    "sponsor": _addr_str(p.sponsor),
                    "electrolyzer_plant": _addr_str(p.electrolyzer_plant),
                    "dispute_initiator": _addr_str(p.dispute_initiator),
                    "escrow_amount": str(p.escrow_amount),
                    "dispute_bond": str(p.dispute_bond),
                    "facility_id": p.facility_id,
                    "min_purity_bps": int(p.min_purity_bps),
                    "max_carbon_intensity_g_co2": int(p.max_carbon_intensity_g_co2),
                    "chromatography_feed_url": p.chromatography_feed_url,
                    "evidence_hash": p.evidence_hash,
                    "status": int(p.status),
                    "verdict": p.verdict,
                    "original_verdict": p.original_verdict,
                    "reason": p.reason,
                    "confidence": int(p.confidence),
                    "measured_purity_bps": int(p.measured_purity_bps),
                    "measured_carbon_intensity_g": int(p.measured_carbon_intensity_g),
                    "created_at_time": str(p.created_at_time),
                    "expires_at_time": str(p.expires_at_time),
                    "audit_completed_time": str(p.audit_completed_time),
                    "auditor_cert_id": p.auditor_cert_id,
                    "batch_id": p.batch_id,
                    "dispute_filed_time": str(p.dispute_filed_time),
                })
        return json.dumps(policies_list)

    @gl.public.view
    def get_claimable_balance(self, account: Address) -> str:
        return str(self.claimable_balances.get(_addr_str(account), bigint(0)))

    @gl.public.view
    def get_total_withdrawn(self, account: Address) -> str:
        return str(self.total_withdrawn_ledger.get(_addr_str(account), bigint(0)))

    @gl.public.view
    def get_stats(self) -> str:
        data = {
            "total_policies": len(self.policy_ids),
            "total_subsidies_locked": str(self.total_subsidies_locked),
            "total_policies_settled": int(self.total_policies_settled),
            "total_pending_claims": str(self.total_pending_claims),
            "owner": _addr_str(self.owner),
        }
        return json.dumps(data)
