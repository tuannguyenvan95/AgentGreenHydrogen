import sys
import types
from pathlib import Path
import json
import hashlib
import re

# Mock genlayer module if not loaded natively
if 'genlayer' not in sys.modules:
    gl_mod = types.ModuleType('genlayer')

    class _Address:
        def __init__(self, val=""):
            if isinstance(val, int):
                self.as_hex = f"0x{val:040x}".lower()
            else:
                self.as_hex = str(val).lower()
            try:
                clean_hex = self.as_hex.replace("0x", "")
                self.as_bytes = bytes.fromhex(clean_hex)
            except Exception:
                self.as_bytes = b"\x00" * 20

        def __str__(self):
            return self.as_hex

        def __repr__(self):
            return self.as_hex

        def __eq__(self, other):
            return str(self).lower() == str(other).lower()

    gl_mod.Address = _Address
    gl_mod.u8 = int
    gl_mod.u32 = int
    gl_mod.u64 = int
    gl_mod.u256 = int
    gl_mod.bigint = int
    gl_mod.TreeMap = dict
    gl_mod.DynArray = list
    gl_mod.allow_storage = lambda cls: cls

    class _GL:
        pass

    gl_mod.gl = _GL()

    class _Contract:
        pass

    gl_mod.Contract = _Contract
    sys.modules['genlayer'] = gl_mod

import pytest

CANARY_TOKEN = "CANARY_AGENT_GREEN_HYDROGEN_V1"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
SECONDS_PER_BLOCK = 3
COOLING_OFF_BLOCKS = 24
COOLING_OFF_SECONDS = COOLING_OFF_BLOCKS * SECONDS_PER_BLOCK  # 72 seconds
DEFAULT_SUBSIDY_EXPIRY_SECONDS = 86400 * 30                   # 30 days

STATUS_POLICY_OPEN = 0
STATUS_TELEMETRY_SUBMITTED = 1
STATUS_AWAITING_PAYOUT = 2
STATUS_SETTLED_CERTIFIED_FULL = 3
STATUS_SETTLED_PARTIAL = 4
STATUS_SETTLED_REJECTED = 5
STATUS_DISPUTED = 6
STATUS_EXPIRED_RECLAIMED = 7
STATUS_UNRESOLVED = 8

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


class _MockTxResult:
    def __init__(self, return_value):
        self.return_value = return_value

    def __str__(self):
        return str(self.return_value)

    def __int__(self):
        return int(self.return_value)

    def __eq__(self, other):
        if isinstance(other, _MockTxResult):
            return self.return_value == other.return_value
        return self.return_value == other


class _MockCallResult:
    def __init__(self, val):
        self._val = val

    def call(self):
        return self._val


class _MockContractInstance:
    def __init__(self, client, contract_path, *deploy_args, **deploy_kwargs):
        self.client = client
        self.contract_path = contract_path
        self.caller = client.accounts[0]
        self.owner = client.accounts[0]
        args_list = deploy_kwargs.get("args") or (deploy_args[0] if deploy_args else None)
        if args_list and len(args_list) > 0 and args_list[0] is not None:
            raw_own = args_list[0]
            if isinstance(raw_own, int):
                self.owner = f"0x{raw_own:040x}".lower()
            else:
                self.owner = str(raw_own).lower()
        self.policies = {}
        self.policy_ids = []
        self.policy_counter = 0
        self.total_subsidies_locked = 0
        self.total_policies_settled = 0
        self.claimable_balances = {}
        self.simulated_time = 1760000000

    def connect(self, account):
        self.caller = str(account).lower()
        return self

    def set_time(self, t):
        self.simulated_time = t

    def create_subsidy_policy(self, args, value=0):
        plant = str(args[0]).lower().strip()
        fac_id = str(args[1]).strip()
        min_purity = int(args[2])
        max_carbon = int(args[3])
        dur_blocks = int(args[4]) if len(args) > 4 else 6000

        if int(value) <= 0:
            raise Exception("Subsidy escrow deposit must be greater than 0 GEN.")
        if len(fac_id) < 4:
            raise Exception("Valid hydrogen production facility ID required (>= 4 chars).")
        if plant == ZERO_ADDRESS:
            raise Exception("Valid electrolyzer plant address required.")
        if self.caller == plant:
            raise Exception("Sponsor cannot designate themselves as electrolyzer plant.")

        self.policy_counter += 1
        pid = str(self.policy_counter)
        dur_secs = dur_blocks * 3 if dur_blocks > 0 else DEFAULT_SUBSIDY_EXPIRY_SECONDS
        expires_at = self.simulated_time + dur_secs

        self.policies[pid] = {
            "policy_id": pid,
            "sponsor": self.caller,
            "electrolyzer_plant": plant,
            "dispute_initiator": ZERO_ADDRESS,
            "escrow_amount": int(value),
            "dispute_bond": 0,
            "facility_id": fac_id,
            "min_purity_bps": min_purity,
            "max_carbon_intensity_g_co2": max_carbon,
            "chromatography_feed_url": "",
            "evidence_hash": "",
            "status": STATUS_POLICY_OPEN,
            "verdict": "PENDING",
            "original_verdict": "PENDING",
            "reason": "Subsidy policy active. Monitored for ISO 14687 hydrogen purity and renewable energy attribution.",
            "confidence": 0,
            "measured_purity_bps": 0,
            "measured_carbon_intensity_g": 0,
            "created_at_time": self.simulated_time,
            "expires_at_time": expires_at,
            "audit_completed_time": 0,
            "supplemental_evidence_url": "",
            "appeal_prior_verdict": "",
        }
        self.policy_ids.append(pid)
        self.total_subsidies_locked += int(value)
        return _MockTxResult(pid)

    def submit_production_telemetry(self, args):
        pid = str(args[0]).strip()
        feed_url = str(args[1]).strip()

        if pid not in self.policies:
            raise Exception(f"Policy {pid} does not exist.")
        p = self.policies[pid]
        if p["status"] not in (STATUS_POLICY_OPEN, STATUS_UNRESOLVED):
            raise Exception("Policy is not open for production telemetry submission.")
        if self.caller != p["electrolyzer_plant"]:
            raise Exception("Role Violation: Only registered electrolyzer plant can submit telemetry.")
        if not _is_accredited_hydrogen_auditor(feed_url):
            raise Exception("Telemetry unauthenticated: Must originate from an accredited testing agency (TÜV SÜD, DNV, Bureau Veritas, NREL).")
        if self.simulated_time > p["expires_at_time"]:
            raise Exception("Coverage duration for this subsidy policy has expired.")

        p["chromatography_feed_url"] = feed_url
        p["status"] = STATUS_TELEMETRY_SUBMITTED
        p["reason"] = "Gas chromatography and renewable matching telemetry submitted. Ready for on-chain AI Tribunal verification."
        return _MockTxResult(True)

    def adjudicate_hydrogen_quality(self, args):
        pid = str(args[0]).strip()
        if pid not in self.policies:
            raise Exception(f"Policy {pid} does not exist.")
        p = self.policies[pid]
        if p["status"] not in (STATUS_TELEMETRY_SUBMITTED, STATUS_UNRESOLVED):
            raise Exception("Policy is not awaiting quality adjudication.")
        if self.caller not in (p["sponsor"], p["electrolyzer_plant"], self.owner):
            raise Exception("Permission Denied: Only sponsor, electrolyzer plant, or owner can trigger adjudication.")

        feed_url = p["chromatography_feed_url"]
        web_mocks = self.client.provider.web_mocks
        llm_mocks = self.client.provider.llm_mocks

        body_raw = None
        for k, v in web_mocks.items():
            if k in feed_url or feed_url in k:
                body_raw = v.get("body", "")
                break

        if body_raw is None:
            p["status"] = STATUS_UNRESOLVED
            p["verdict"] = "UNRESOLVED_FETCH_FAILED"
            p["reason"] = "Chromatography inspection report unreachable or empty."
            p["evidence_hash"] = "0" * 64
            return _MockTxResult(True)

        ev_hash = hashlib.sha256(body_raw.encode("utf-8")).hexdigest()

        matched_llm = None
        for pat, resp in llm_mocks.items():
            matched_llm = resp
            break

        if not matched_llm:
            raise Exception("No mock found for LLM prompt.")

        parsed = json.loads(matched_llm)
        if parsed.get("canary") != CANARY_TOKEN:
            p["status"] = STATUS_UNRESOLVED
            p["verdict"] = "UNRESOLVED_CANARY_FAILED"
            p["reason"] = "Security canary mismatch detected in jury output."
            p["evidence_hash"] = ev_hash
            return _MockTxResult(True)

        verdict = parsed.get("verdict", "")
        if verdict.startswith("UNRESOLVED_"):
            p["status"] = STATUS_UNRESOLVED
            p["verdict"] = verdict
            p["reason"] = parsed.get("reason", "")
            p["evidence_hash"] = ev_hash
            return _MockTxResult(True)

        p["verdict"] = verdict
        p["original_verdict"] = verdict
        p["confidence"] = parsed.get("confidence", 85)
        p["measured_purity_bps"] = parsed.get("measured_purity_bps", 0)
        p["measured_carbon_intensity_g"] = parsed.get("measured_carbon_intensity_g", 0)
        p["reason"] = parsed.get("reason", "")
        p["evidence_hash"] = ev_hash
        p["status"] = STATUS_AWAITING_PAYOUT
        p["audit_completed_time"] = self.simulated_time
        return _MockTxResult(True)

    def appeal_verdict(self, args, value=0):
        pid = str(args[0]).strip()
        reason = str(args[1]).strip()
        supp_url = str(args[2]).strip()

        if pid not in self.policies:
            raise Exception(f"Policy {pid} does not exist.")
        p = self.policies[pid]
        if p["status"] != STATUS_AWAITING_PAYOUT:
            raise Exception("Can only appeal policies in AWAITING_PAYOUT status.")
        if self.caller not in (p["sponsor"], p["electrolyzer_plant"]):
            raise Exception("Role Violation: Only sponsor or electrolyzer plant can file an appeal.")
        if self.simulated_time > (p["audit_completed_time"] + COOLING_OFF_SECONDS):
            raise Exception(f"Dispute cooling-off window ({COOLING_OFF_SECONDS}s) has expired.")
        if not _is_accredited_hydrogen_auditor(supp_url):
            raise Exception("Supplemental telemetry unauthenticated: Must originate from an accredited testing agency.")

        req_bond = (p["escrow_amount"] * 10) // 100
        if req_bond == 0:
            req_bond = 1
        if int(value) < req_bond:
            raise Exception(f"Must stake at least 10% dispute bond ({req_bond} wei).")
        if len(reason) < 10:
            raise Exception("Detailed dispute justification (>= 10 chars) required.")

        p["appeal_prior_verdict"] = p["verdict"]
        p["status"] = STATUS_DISPUTED
        p["dispute_initiator"] = self.caller
        p["dispute_bond"] = int(value)
        p["supplemental_evidence_url"] = supp_url
        p["reason"] = f"[DISPUTE by {self.caller[:8]}]: {reason} | Prior: {p['reason']}"
        self.total_subsidies_locked += int(value)
        return _MockTxResult(True)

    def adjudicate_appeal(self, args):
        pid = str(args[0]).strip()
        if pid not in self.policies:
            raise Exception(f"Policy {pid} does not exist.")
        p = self.policies[pid]
        if p["status"] != STATUS_DISPUTED:
            raise Exception("Policy is not in DISPUTED status.")
        if self.caller not in (p["sponsor"], p["electrolyzer_plant"], self.owner):
            raise Exception("Permission Denied: Only sponsor, electrolyzer plant, or owner can adjudicate appeal.")

        web_mocks = self.client.provider.web_mocks
        llm_mocks = self.client.provider.llm_mocks

        body_raw = None
        for k, v in web_mocks.items():
            if k in p["supplemental_evidence_url"] or p["supplemental_evidence_url"] in k:
                body_raw = v.get("body", "")
                break

        if body_raw is None:
            p["status"] = STATUS_UNRESOLVED
            p["verdict"] = "APPEAL_UNRESOLVED_FETCH_FAILED"
            p["reason"] = "[APPEAL UNRESOLVED] Supplemental chemical inspection report unreachable."
            return _MockTxResult(True)

        matched_llm = None
        for pat, resp in llm_mocks.items():
            matched_llm = resp
            break

        parsed = json.loads(matched_llm)
        app_verdict = parsed.get("verdict", "")
        app_reason = parsed.get("reason", "")

        if app_verdict.startswith("APPEAL_UNRESOLVED_"):
            p["status"] = STATUS_UNRESOLVED
            p["verdict"] = app_verdict
            p["reason"] = f"[APPEAL UNRESOLVED] {app_reason}"
            return _MockTxResult(True)

        escrow_val = p["escrow_amount"]
        bond_val = p["dispute_bond"]
        p["escrow_amount"] = 0
        p["dispute_bond"] = 0
        self.total_subsidies_locked -= (escrow_val + bond_val)
        self.total_policies_settled += 1

        is_sponsor_appellant = (p["dispute_initiator"] == p["sponsor"])
        counterparty = p["electrolyzer_plant"] if is_sponsor_appellant else p["sponsor"]

        if app_verdict == "APPEAL_UPHELD_CERTIFIED":
            p["status"] = STATUS_SETTLED_CERTIFIED_FULL
            p["verdict"] = "GREEN_HYDROGEN_CERTIFIED_FULL"
            p["reason"] = f"[APPEAL UPHELD] {app_reason}"
        elif app_verdict == "APPEAL_UPHELD_PARTIAL":
            p["status"] = STATUS_SETTLED_PARTIAL
            p["verdict"] = "PARTIAL_CARBON_INTENSITY_PENALTY"
            p["reason"] = f"[APPEAL RESOLUTION] {app_reason}"
        elif app_verdict == "APPEAL_UPHELD_REJECTED":
            p["status"] = STATUS_SETTLED_REJECTED
            p["verdict"] = "GRAY_HYDROGEN_REJECTED"
            p["reason"] = f"[APPEAL RESOLUTION] {app_reason}"
        else:
            p["reason"] = f"[APPEAL DISMISSED] {app_reason}"
            if p["original_verdict"] == "GREEN_HYDROGEN_CERTIFIED_FULL":
                p["status"] = STATUS_SETTLED_CERTIFIED_FULL
                p["verdict"] = "GREEN_HYDROGEN_CERTIFIED_FULL"
            elif p["original_verdict"] == "PARTIAL_CARBON_INTENSITY_PENALTY":
                p["status"] = STATUS_SETTLED_PARTIAL
                p["verdict"] = "PARTIAL_CARBON_INTENSITY_PENALTY"
            else:
                p["status"] = STATUS_SETTLED_REJECTED
                p["verdict"] = "GRAY_HYDROGEN_REJECTED"

        return _MockTxResult(True)

    def finalize_settlement(self, args):
        pid = str(args[0]).strip()
        if pid not in self.policies:
            raise Exception(f"Policy {pid} does not exist.")
        p = self.policies[pid]
        if p["status"] == STATUS_UNRESOLVED:
            raise Exception("Cannot settle policy in an unresolved error state. Escrow remains protected.")
        if p["status"] != STATUS_AWAITING_PAYOUT:
            raise Exception("Policy is not awaiting settlement payout.")
        if self.caller not in (p["sponsor"], p["electrolyzer_plant"], self.owner):
            raise Exception("Permission Denied: Only stakeholders or owner can finalize payout.")
        if self.simulated_time <= (p["audit_completed_time"] + COOLING_OFF_SECONDS):
            raise Exception(f"Cooling-off challenge window ({COOLING_OFF_SECONDS}s) is still active.")

        escrow_val = p["escrow_amount"]
        p["escrow_amount"] = 0
        self.total_subsidies_locked -= escrow_val
        self.total_policies_settled += 1

        if p["verdict"] == "GREEN_HYDROGEN_CERTIFIED_FULL":
            p["status"] = STATUS_SETTLED_CERTIFIED_FULL
        elif p["verdict"] == "PARTIAL_CARBON_INTENSITY_PENALTY":
            p["status"] = STATUS_SETTLED_PARTIAL
        else:
            p["status"] = STATUS_SETTLED_REJECTED

        return _MockTxResult(True)

    def cancel_or_reclaim(self, args):
        pid = str(args[0]).strip()
        if pid not in self.policies:
            raise Exception(f"Policy {pid} does not exist.")
        p = self.policies[pid]
        if self.caller != p["sponsor"]:
            raise Exception("Role Violation: Only sponsor can reclaim expired subsidy escrow.")
        if p["status"] in (STATUS_POLICY_OPEN, STATUS_UNRESOLVED):
            if self.simulated_time < p["expires_at_time"]:
                raise Exception(f"Cannot reclaim: Policy is still active (expires at {p['expires_at_time']}).")
        else:
            raise Exception("Cannot reclaim: Policy has telemetry actively undergoing evaluation or already settled.")

        p["status"] = STATUS_EXPIRED_RECLAIMED
        p["verdict"] = "EXPIRED_CLEAN"
        p["reason"] = "Policy duration completed without valid spectrometry telemetry. Escrow reclaimed by sponsor."
        escrow_val = p["escrow_amount"]
        p["escrow_amount"] = 0
        self.total_subsidies_locked -= escrow_val
        return _MockTxResult(True)

    def claim_payout(self):
        bal = self.claimable_balances.get(self.caller, 0)
        if bal <= 0:
            raise Exception("No claimable balance available for withdrawal.")
        self.claimable_balances[self.caller] = 0
        return _MockTxResult(True)

    def get_user_role(self, args):
        pid = str(args[0]).strip()
        account = str(args[1]).strip().lower()
        if pid not in self.policies:
            if account == self.owner:
                return _MockCallResult("OWNER")
            return _MockCallResult("OBSERVER")
        p = self.policies[pid]
        if account == p["sponsor"]:
            return _MockCallResult("SPONSOR")
        if account == p["electrolyzer_plant"]:
            return _MockCallResult("ELECTROLYZER_PLANT")
        if account == p["dispute_initiator"] and account != ZERO_ADDRESS:
            return _MockCallResult("APPELLANT")
        if account == self.owner:
            return _MockCallResult("OWNER")
        return _MockCallResult("OBSERVER")

    def get_remaining_cooling_off_seconds(self, args):
        pid = str(args[0]).strip()
        if pid not in self.policies:
            return _MockCallResult(0)
        p = self.policies[pid]
        if p["status"] != STATUS_AWAITING_PAYOUT or p["audit_completed_time"] <= 0:
            return _MockCallResult(0)
        expiry = p["audit_completed_time"] + COOLING_OFF_SECONDS
        rem = expiry - self.simulated_time
        return _MockCallResult(max(0, rem))

    def get_policy(self, args):
        pid = str(args[0]).strip()
        if pid not in self.policies:
            raise Exception(f"Policy {pid} does not exist.")
        p = self.policies[pid]
        return _MockCallResult(json.dumps({
            "policy_id": p["policy_id"],
            "sponsor": p["sponsor"],
            "electrolyzer_plant": p["electrolyzer_plant"],
            "dispute_initiator": p["dispute_initiator"],
            "escrow_amount": str(p["escrow_amount"]),
            "dispute_bond": str(p["dispute_bond"]),
            "facility_id": p["facility_id"],
            "min_purity_bps": p["min_purity_bps"],
            "max_carbon_intensity_g_co2": p["max_carbon_intensity_g_co2"],
            "chromatography_feed_url": p["chromatography_feed_url"],
            "evidence_hash": p["evidence_hash"],
            "status": p["status"],
            "verdict": p["verdict"],
            "original_verdict": p["original_verdict"],
            "reason": p["reason"],
            "confidence": p["confidence"],
            "measured_purity_bps": p["measured_purity_bps"],
            "measured_carbon_intensity_g": p["measured_carbon_intensity_g"],
            "created_at_time": str(p["created_at_time"]),
            "expires_at_time": str(p["expires_at_time"]),
            "audit_completed_time": str(p["audit_completed_time"]),
            "supplemental_evidence_url": p["supplemental_evidence_url"],
            "appeal_prior_verdict": p["appeal_prior_verdict"],
        }))

    def get_policy_count(self):
        return _MockCallResult(len(self.policy_ids))

    def get_all_policies(self):
        return _MockCallResult(json.dumps(list(self.policies.values())))

    def get_stats(self):
        return _MockCallResult(json.dumps({
            "total_policies": len(self.policy_ids),
            "total_subsidies_locked": str(self.total_subsidies_locked),
            "total_policies_settled": self.total_policies_settled,
            "owner": self.owner,
        }))


class _MockProvider:
    def __init__(self):
        self.llm_mocks = {}
        self.web_mocks = {}

    def make_request(self, method, params):
        if method == "sim_installMocks":
            if "llm_mocks" in params:
                self.llm_mocks.update(params["llm_mocks"])
            if "web_mocks" in params:
                self.web_mocks.update(params["web_mocks"])
            return True
        return None


class _MockClient:
    def __init__(self):
        self.accounts = [
            "0x1111111111111111111111111111111111111111",
            "0x2222222222222222222222222222222222222222",
            "0x3333333333333333333333333333333333333333",
            "0x4444444444444444444444444444444444444444",
        ]
        self.provider = _MockProvider()

    def deploy(self, path, *args, **kwargs):
        return _MockContractInstance(self, path, *args, **kwargs)


@pytest.fixture
def client():
    return _MockClient()
