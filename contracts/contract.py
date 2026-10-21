# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import json
import hashlib

CANARY_TOKEN = "CANARY_AGENT_GREEN_HYDROGEN_V1"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Time & Cooling-Off Parameters
SECONDS_PER_BLOCK = 3
COOLING_OFF_BLOCKS = 24
COOLING_OFF_SECONDS = bigint(COOLING_OFF_BLOCKS * SECONDS_PER_BLOCK)  # 72 seconds
DEFAULT_SUBSIDY_EXPIRY_SECONDS = bigint(86400 * 30)                   # 30 days coverage

# Lifecycle Statuses
STATUS_POLICY_OPEN = u8(0)           # Climate Fund deposited subsidy escrow, awaiting production telemetry
STATUS_TELEMETRY_SUBMITTED = u8(1)   # Electrolyzer plant submitted gas chromatography and renewable certificates
STATUS_AWAITING_PAYOUT = u8(2)       # AI Hydrogen Jury rendered verdict, cooling-off active
STATUS_SETTLED_CERTIFIED_FULL = u8(3)# ISO 14687 compliant green hydrogen confirmed, 100% subsidy released
STATUS_SETTLED_PARTIAL = u8(4)       # Carbon intensity breach / minor grid mixing, 50% penalty
STATUS_SETTLED_REJECTED = u8(5)      # Gray hydrogen detected / purity failure, 100% refunded to fund
STATUS_DISPUTED = u8(6)              # Under appellate review with 10% staked bond
STATUS_EXPIRED_RECLAIMED = u8(7)     # Policy expired with zero telemetry, reclaimed by fund
STATUS_UNRESOLVED = u8(8)            # Telemetry fetch, parse, or canary failure (protected non-settling state)


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


class Contract(gl.Contract):
    """
    AgentGreenHydrogen: Autonomous Green Hydrogen Purity & Renewable Electrolysis Subsidy Escrow
    Target Network: GenLayer StudioNet (Chain ID: 61999)
    """
    policies: TreeMap[str, HydrogenPolicy]
    policy_ids: DynArray[str]
    total_subsidies_locked: bigint
    total_policies_settled: u32
    policy_counter: u64
    owner: Address
    claimable_balances: TreeMap[str, bigint]

    def __init__(self, initial_owner: Address = Address(ZERO_ADDRESS)):
        deployer = Address(ZERO_ADDRESS)
        try:
            deployer = _get_sender()
        except Exception:
            pass

        target_owner = initial_owner if _addr_str(initial_owner) != ZERO_ADDRESS else deployer

        self.owner = target_owner
        self.total_subsidies_locked = bigint(0)
        self.total_policies_settled = u32(0)
        self.policy_counter = u64(0)

    def _resolve_pid(self, policy_id) -> str:
        return str(policy_id).strip()

    def _ensure_owner(self) -> None:
        if _addr_str(self.owner) == ZERO_ADDRESS:
            self.owner = _get_sender()

    def _safe_transfer(self, recipient: Address, amount: bigint) -> None:
        """Transfers native GEN tokens with Pull-Payment fallback to eliminate lost funds."""
        if amount <= bigint(0):
            return
        r_addr = _to_address(recipient)
        rec_str = _addr_str(r_addr)
        try:
            gl.get_contract_at(r_addr).emit_transfer(value=u256(int(amount)))
        except Exception:
            curr = self.claimable_balances.get(rec_str, bigint(0))
            self.claimable_balances[rec_str] = curr + amount

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

    # ── Public Write Methods ──────────────────────────────────────────

    @gl.public.write.payable
    def create_subsidy_policy(
        self,
        electrolyzer_plant: Address,
        facility_id: str,
        min_purity_bps: u32,
        max_carbon_intensity_g_co2: u32,
        duration_blocks: u32
    ) -> str:
        """Climate fund deposits subsidy allocation for accredited hydrogen electrolysis."""
        self._ensure_owner()
        escrow = bigint(gl.message.value)
        if escrow <= bigint(0):
            raise ContractError("Subsidy escrow deposit must be greater than 0 GEN.")

        clean_fac = str(facility_id).strip()
        if len(clean_fac) < 4:
            raise ContractError("Valid hydrogen production facility ID required (>= 4 chars).")

        p_addr = _to_address(electrolyzer_plant)
        if _addr_str(p_addr) == ZERO_ADDRESS:
            raise ContractError("Valid electrolyzer plant address required.")

        s_addr = _to_address(_get_sender())
        if _addr_str(s_addr) == _addr_str(p_addr):
            raise ContractError("Sponsor cannot designate themselves as electrolyzer plant.")

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
            reason="Subsidy policy active. Monitored for ISO 14687 hydrogen purity and renewable energy attribution.",
            confidence=u8(0),
            measured_purity_bps=u32(0),
            measured_carbon_intensity_g=u32(0),
            created_at_time=current_time,
            expires_at_time=expires_at,
            audit_completed_time=bigint(0),
            supplemental_evidence_url="",
            appeal_prior_verdict="",
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
        """Electrolyzer facility submits accredited gas chromatography and hourly renewable matching data."""
        self._ensure_owner()
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        if p.status not in (STATUS_POLICY_OPEN, STATUS_UNRESOLVED):
            raise ContractError("Policy is not open for production telemetry submission.")

        sender = _get_sender()
        if _addr_str(sender) != _addr_str(p.electrolyzer_plant):
            raise ContractError("Role Violation: Only registered electrolyzer plant can submit telemetry.")

        clean_url = str(chromatography_feed_url).strip()
        if not _is_accredited_hydrogen_auditor(clean_url):
            raise ContractError("Telemetry unauthenticated: Must originate from an accredited testing agency (TÜV SÜD, DNV, Bureau Veritas, NREL).")

        current_time = self._get_current_timestamp()
        if current_time > p.expires_at_time:
            raise ContractError("Coverage duration for this subsidy policy has expired.")

        p.chromatography_feed_url = clean_url
        p.status = STATUS_TELEMETRY_SUBMITTED
        p.reason = "Gas chromatography and renewable matching telemetry submitted. Ready for on-chain AI Tribunal verification."

    @gl.public.write
    def adjudicate_hydrogen_quality(self, policy_id: str) -> None:
        """AI Clean Energy Jury evaluates hydrogen purity (ISO 14687) and lifecycle carbon intensity."""
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
                    "measured_purity_bps": 0,
                    "measured_carbon_intensity_g": 0,
                    "reason": "Chromatography inspection report unreachable or empty.",
                    "evidence_hash": "0000000000000000000000000000000000000000000000000000000000000000",
                }

            ev_hash = hashlib.sha256(raw_feed.encode("utf-8")).hexdigest()

            prompt = f"""You are the Chief Industrial Chemist and Clean Hydrogen Standards Magistrate on GenLayer.
Evaluate the gas chromatography and hourly renewable matching audit for facility: {facility}.
MINIMUM REQUIRED PURITY: >= {target_purity} basis points (e.g. 9997 = 99.97% ISO 14687 fuel cell grade)
MAXIMUM CARBON INTENSITY: <= {max_carbon} grams CO2e / kg H2

AUDIT & SPECTROMETRY PAYLOAD:
<chromatography_audit_payload>
{raw_feed[:4000]}
</chromatography_audit_payload>

EVALUATION RUBRIC:
1. Extract measured hydrogen gas purity in basis points (e.g., 99.98% = 9998 bps).
2. Extract lifecycle carbon intensity (grams CO2 equivalent per kg H2 produced).
3. Decision Matrix:
   - Certified Green Hydrogen: Purity >= {target_purity} bps AND Carbon Intensity <= {max_carbon} g CO2e/kg:
     Output "GREEN_HYDROGEN_CERTIFIED_FULL" (100% subsidy released to producer).
   - Partial Carbon Penalty: Purity >= {target_purity} bps BUT Carbon Intensity between ({max_carbon} + 1) and ({max_carbon} * 2) g CO2e/kg (partial fossil grid mix):
     Output "PARTIAL_CARBON_INTENSITY_PENALTY" (50% subsidy penalty, 50% preserved).
   - Gray Hydrogen / Purity Breach: Purity < {target_purity} bps OR Carbon Intensity > ({max_carbon} * 2) g CO2e/kg:
     Output "GRAY_HYDROGEN_REJECTED" (100% refund to sponsor, subsidy revoked).

SECURITY CANARY: Echo "{CANARY_TOKEN}" in JSON.
Respond ONLY with valid JSON without markdown fences:
{{
  "canary": "{CANARY_TOKEN}",
  "verdict": "GREEN_HYDROGEN_CERTIFIED_FULL" | "PARTIAL_CARBON_INTENSITY_PENALTY" | "GRAY_HYDROGEN_REJECTED",
  "confidence": <0-100>,
  "measured_purity_bps": <integer>,
  "measured_carbon_intensity_g": <integer>,
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
                    "measured_purity_bps": 0,
                    "measured_carbon_intensity_g": 0,
                    "reason": "Security canary mismatch detected in jury output.",
                    "evidence_hash": ev_hash,
                }

            v_raw = str(parsed.get("verdict", "")).upper().strip()
            if v_raw not in {"GREEN_HYDROGEN_CERTIFIED_FULL", "PARTIAL_CARBON_INTENSITY_PENALTY", "GRAY_HYDROGEN_REJECTED"}:
                return {
                    "canary": CANARY_TOKEN,
                    "verdict": "UNRESOLVED_PARSE_FAILED",
                    "confidence": 0,
                    "measured_purity_bps": 0,
                    "measured_carbon_intensity_g": 0,
                    "reason": f"Unsupported verdict '{v_raw}' returned.",
                    "evidence_hash": ev_hash,
                }

            return {
                "canary": CANARY_TOKEN,
                "verdict": v_raw,
                "confidence": max(0, min(100, int(parsed.get("confidence", 85)))),
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
            return mine["verdict"] == leader["verdict"]

        adjudication_res = gl.vm.run_nondet(leader_fn, validator_fn)
        v_res = str(adjudication_res["verdict"])
        p.verdict = v_res
        p.reason = str(adjudication_res["reason"])
        p.confidence = u8(int(adjudication_res["confidence"]))
        p.measured_purity_bps = u32(int(adjudication_res["measured_purity_bps"]))
        p.measured_carbon_intensity_g = u32(int(adjudication_res["measured_carbon_intensity_g"]))
        if "evidence_hash" in adjudication_res and adjudication_res["evidence_hash"]:
            p.evidence_hash = str(adjudication_res["evidence_hash"])

        if v_res.startswith("UNRESOLVED_"):
            p.status = STATUS_UNRESOLVED
            p.audit_completed_time = bigint(0)
        else:
            p.original_verdict = v_res
            current_time = self._get_current_timestamp()
            p.status = STATUS_AWAITING_PAYOUT
            p.audit_completed_time = current_time

    @gl.public.write.payable
    def appeal_verdict(
        self,
        policy_id: str,
        dispute_reason: str,
        supplemental_audit_url: str
    ) -> None:
        """Sponsor or Producer can appeal within 24 blocks (~72s) with a 10% staked bond."""
        self._ensure_owner()
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        if p.status != STATUS_AWAITING_PAYOUT:
            raise ContractError("Can only appeal policies in AWAITING_PAYOUT status.")

        sender = _get_sender()
        if _addr_str(sender) != _addr_str(p.sponsor) and _addr_str(sender) != _addr_str(p.electrolyzer_plant):
            raise ContractError("Role Violation: Only sponsor or electrolyzer plant can file an appeal.")

        current_time = self._get_current_timestamp()
        if current_time > (p.audit_completed_time + COOLING_OFF_SECONDS):
            raise ContractError(f"Dispute cooling-off window ({int(COOLING_OFF_SECONDS)}s) has expired.")

        clean_url = str(supplemental_audit_url).strip()
        if not _is_accredited_hydrogen_auditor(clean_url):
            raise ContractError("Supplemental telemetry unauthenticated: Must originate from an accredited testing agency.")

        required_bond = (p.escrow_amount * bigint(10)) // bigint(100)
        if required_bond == bigint(0):
            required_bond = bigint(1)

        staked = bigint(gl.message.value)
        if staked < required_bond:
            raise ContractError(f"Must stake at least 10% dispute bond ({int(required_bond)} wei).")

        clean_reason = str(dispute_reason).strip()
        if len(clean_reason) < 10:
            raise ContractError("Detailed dispute justification (>= 10 chars) required.")

        p.appeal_prior_verdict = p.verdict
        p.status = STATUS_DISPUTED
        p.dispute_initiator = _to_address(sender)
        p.dispute_bond = staked
        p.supplemental_evidence_url = clean_url
        p.reason = f"[DISPUTE by {_addr_str(sender)[:8]}]: {clean_reason} | Prior: {p.reason}"
        self.total_subsidies_locked = self.total_subsidies_locked + staked

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
                }

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
                return {"canary": CANARY_TOKEN, "verdict": "APPEAL_UNRESOLVED_PARSE_FAILED", "reason": "Appellate parsing failure."}

            v_str = str(parsed.get("verdict", "")).upper().strip()
            if v_str not in {"APPEAL_UPHELD_CERTIFIED", "APPEAL_UPHELD_PARTIAL", "APPEAL_UPHELD_REJECTED", "APPEAL_DISMISSED"}:
                v_str = "APPEAL_UNRESOLVED_PARSE_FAILED"

            return {
                "canary": CANARY_TOKEN,
                "verdict": v_str,
                "reason": str(parsed.get("reason", "Appellate review completed."))[:200]
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
            self._safe_transfer(p.electrolyzer_plant, escrow_val)
            if not is_sponsor_appellant:
                self._safe_transfer(appellant, bond_val)
            else:
                self._safe_transfer(counterparty, bond_val)

        elif app_verdict == "APPEAL_UPHELD_PARTIAL":
            p.status = STATUS_SETTLED_PARTIAL
            p.verdict = "PARTIAL_CARBON_INTENSITY_PENALTY"
            payout = escrow_val // bigint(2)
            refund = escrow_val - payout
            p.reason = f"[APPEAL RESOLUTION] {app_reason}"
            self._safe_transfer(p.electrolyzer_plant, payout)
            self._safe_transfer(p.sponsor, refund)
            self._safe_transfer(appellant, bond_val)

        elif app_verdict == "APPEAL_UPHELD_REJECTED":
            p.status = STATUS_SETTLED_REJECTED
            p.verdict = "GRAY_HYDROGEN_REJECTED"
            p.reason = f"[APPEAL RESOLUTION] {app_reason}"
            self._safe_transfer(p.sponsor, escrow_val)
            if is_sponsor_appellant:
                self._safe_transfer(appellant, bond_val)
            else:
                self._safe_transfer(counterparty, bond_val)

        else:
            # APPEAL_DISMISSED: Preserve original verdict and forfeit bond to counterparty
            p.reason = f"[APPEAL DISMISSED] {app_reason}"
            self._safe_transfer(counterparty, bond_val)

            if p.original_verdict == "GREEN_HYDROGEN_CERTIFIED_FULL":
                p.status = STATUS_SETTLED_CERTIFIED_FULL
                p.verdict = "GREEN_HYDROGEN_CERTIFIED_FULL"
                self._safe_transfer(p.electrolyzer_plant, escrow_val)
            elif p.original_verdict == "PARTIAL_CARBON_INTENSITY_PENALTY":
                p.status = STATUS_SETTLED_PARTIAL
                p.verdict = "PARTIAL_CARBON_INTENSITY_PENALTY"
                payout = escrow_val // bigint(2)
                refund = escrow_val - payout
                self._safe_transfer(p.electrolyzer_plant, payout)
                self._safe_transfer(p.sponsor, refund)
            else:
                p.status = STATUS_SETTLED_REJECTED
                p.verdict = "GRAY_HYDROGEN_REJECTED"
                self._safe_transfer(p.sponsor, escrow_val)

    @gl.public.write
    def finalize_settlement(self, policy_id: str) -> None:
        """Executes uncontested settlement strictly after 24 blocks (~72s) cooling-off window."""
        self._ensure_owner()
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        if p.status == STATUS_UNRESOLVED or p.verdict.startswith("UNRESOLVED_") or p.verdict.startswith("APPEAL_UNRESOLVED_"):
            raise ContractError("Cannot settle policy in an unresolved error state. Escrow remains protected.")

        if p.status != STATUS_AWAITING_PAYOUT:
            raise ContractError("Policy is not awaiting settlement payout.")

        sender_str = _addr_str(_get_sender())
        if (
            sender_str != _addr_str(p.sponsor)
            and sender_str != _addr_str(p.electrolyzer_plant)
            and sender_str != _addr_str(self.owner)
        ):
            raise ContractError("Permission Denied: Only stakeholders or owner can finalize payout.")

        current_time = self._get_current_timestamp()
        if current_time <= (p.audit_completed_time + COOLING_OFF_SECONDS):
            raise ContractError(f"Cooling-off challenge window ({int(COOLING_OFF_SECONDS)}s) is still active.")

        escrow_val = p.escrow_amount
        p.escrow_amount = bigint(0)  # Double-payout protection
        self.total_subsidies_locked = self.total_subsidies_locked - escrow_val
        self.total_policies_settled = self.total_policies_settled + u32(1)

        if p.verdict == "GREEN_HYDROGEN_CERTIFIED_FULL":
            p.status = STATUS_SETTLED_CERTIFIED_FULL
            self._safe_transfer(p.electrolyzer_plant, escrow_val)

        elif p.verdict == "PARTIAL_CARBON_INTENSITY_PENALTY":
            p.status = STATUS_SETTLED_PARTIAL
            payout = escrow_val // bigint(2)
            refund = escrow_val - payout
            self._safe_transfer(p.electrolyzer_plant, payout)
            self._safe_transfer(p.sponsor, refund)

        else:
            p.status = STATUS_SETTLED_REJECTED
            self._safe_transfer(p.sponsor, escrow_val)

    @gl.public.write
    def cancel_or_reclaim(self, policy_id: str) -> None:
        """Sponsor reclaims escrow if policy expired without telemetry or stalled in unresolved state."""
        self._ensure_owner()
        pid = self._resolve_pid(policy_id)
        if pid not in self.policies:
            raise ContractError(f"Policy {pid} does not exist.")

        p = self.policies[pid]
        if _addr_str(_get_sender()) != _addr_str(p.sponsor):
            raise ContractError("Role Violation: Only sponsor can reclaim expired subsidy escrow.")

        current_time = self._get_current_timestamp()
        if p.status in (STATUS_POLICY_OPEN, STATUS_UNRESOLVED):
            if current_time < p.expires_at_time:
                raise ContractError(f"Cannot reclaim: Policy is still active (expires at {int(p.expires_at_time)}).")
        else:
            raise ContractError("Cannot reclaim: Policy has telemetry actively undergoing evaluation or already settled.")

        p.status = STATUS_EXPIRED_RECLAIMED
        p.verdict = "EXPIRED_CLEAN"
        p.reason = "Policy duration completed without valid spectrometry telemetry. Escrow reclaimed by sponsor."

        escrow_val = p.escrow_amount
        p.escrow_amount = bigint(0)
        self.total_subsidies_locked = self.total_subsidies_locked - escrow_val
        self._safe_transfer(p.sponsor, escrow_val)

    @gl.public.write
    def claim_payout(self) -> None:
        """Pull-payment safety withdrawal: Beneficiary claims safely buffered balances."""
        self._ensure_owner()
        sender = _get_sender()
        s_str = _addr_str(sender)
        bal = self.claimable_balances.get(s_str, bigint(0))
        if bal <= bigint(0):
            raise ContractError("No claimable balance available for withdrawal.")

        self.claimable_balances[s_str] = bigint(0)
        try:
            gl.get_contract_at(sender).emit_transfer(value=u256(int(bal)))
        except Exception:
            self.claimable_balances[s_str] = bal
            raise ContractError("Outbound transfer failed during claim. Balance safely preserved.")

    # ── Read-only Views ───────────────────────────────────────────────

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
            "created_at_block": str(p.created_at_time),
            "expires_at_block": str(p.expires_at_time),
            "audit_completed_block": str(p.audit_completed_time),
        }
        return json.dumps(data)

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
                })
        return json.dumps(policies_list)

    @gl.public.view
    def get_claimable_balance(self, account: Address) -> str:
        return str(self.claimable_balances.get(_addr_str(account), bigint(0)))

    @gl.public.view
    def get_stats(self) -> str:
        data = {
            "total_policies": len(self.policy_ids),
            "total_subsidies_locked": str(self.total_subsidies_locked),
            "total_policies_settled": int(self.total_policies_settled),
            "owner": _addr_str(self.owner),
        }
        return json.dumps(data)
