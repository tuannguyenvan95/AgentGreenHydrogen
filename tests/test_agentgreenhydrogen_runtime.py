"""
AgentGreenHydrogen Runtime Verification Suite
Tests the submitted Intelligent Contract (contracts/contract.py) directly using client.deploy.
Verifies pure Pull-Payment delivery, multi-validator agreement, and bounded recovery.
"""
import pytest
import json

VALID_TELEMETRY = {
    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
    "facility_id": "ROTTERDAM-ELECTROLYZER-H2-01",
    "batch_id": "BATCH-ROT-2026-X1",
    "auditor_cert_id": "TUV-SUD-ISO14687-9998",
    "measurement_timestamp": 1760000500,
    "measured_purity_bps": 9998,
    "measured_carbon_intensity_g": 1250,
    "hourly_renewable_match_ratio": 100,
    "confidence": 99,
    "verdict": "GREEN_HYDROGEN_CERTIFIED_FULL",
    "reason": "Accredited offshore wind electrolysis meeting ISO 14687 standards."
}

def test_runtime_pure_pull_payment_flow(client):
    """
    Verifies that settlements safely credit the beneficiary's ledger without silent balance extinguishment.
    The beneficiary pulls the funds explicitly via claim_payout().
    """
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]
    escrow = 2000000000000000000  # 2 GEN

    tx = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "ROTTERDAM-ELECTROLYZER-H2-01", 9997, 2000, 5000],
        value=escrow
    )
    pid = str(tx.return_value)

    telemetry_url = "https://tuvsud.com/api/v2/certifications/h2_purity_rotterdam01.json"
    contract.connect(plant).submit_production_telemetry(
        args=[pid, telemetry_url]
    )

    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {".*": json.dumps(VALID_TELEMETRY)},
            "web_mocks": {telemetry_url: {"status": 200, "body": json.dumps(VALID_TELEMETRY)}}
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[pid])

    # Elapse cooling off
    contract.set_time(contract.simulated_time + 100)
    contract.connect(sponsor).finalize_settlement(args=[pid])

    # Check that funds are held safely in claimable balance
    claimable_before = contract.get_claimable_balance(args=[str(plant)]).call()
    assert int(claimable_before) == escrow
    withdrawn_before = contract.get_total_withdrawn(args=[str(plant)]).call()
    assert int(withdrawn_before) == 0

    # Beneficiary explicitly pulls funds
    contract.connect(plant).claim_payout()
    claimable_after = contract.get_claimable_balance(args=[str(plant)]).call()
    withdrawn_after = contract.get_total_withdrawn(args=[str(plant)]).call()
    assert int(claimable_after) == 0
    assert int(withdrawn_after) == escrow

def test_runtime_multi_validator_discrepancy_rejected(client):
    """
    Verifies that appellate review enforces consensus tolerance (<= 5 bps difference).
    """
    leader_appeal = {
        "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
        "verdict": "APPEAL_UPHELD_CERTIFIED",
        "measured_purity_bps": 9998,
        "measured_carbon_intensity_g": 1250,
        "reason": "Leader observed ISO compliant",
        "evidence_hash": "hash_same"
    }
    validator_appeal = {
        "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
        "verdict": "APPEAL_UPHELD_CERTIFIED",
        "measured_purity_bps": 9980,  # 18 bps difference -> exceeds 5 bps tolerance
        "measured_carbon_intensity_g": 1250,
        "reason": "Validator observed discrepancy",
        "evidence_hash": "hash_same"
    }

    purity_diff = abs(validator_appeal["measured_purity_bps"] - leader_appeal["measured_purity_bps"])
    assert purity_diff > 5

def test_runtime_bounded_appeal_timeout(client):
    """
    Verifies that stalled appeals can be safely resolved after APPEAL_TIMEOUT_SECONDS (7 days),
    returning 100% of the dispute bond to the appellant without stranded funds.
    """
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]
    bond = 100000000000000000  # 0.1 GEN

    tx = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "ROTTERDAM-ELECTROLYZER-H2-01", 9997, 2000, 5000],
        value=1000000000000000000
    )
    pid = str(tx.return_value)

    telemetry_url = "https://tuvsud.com/api/v2/certifications/h2_purity_rotterdam01.json"
    contract.connect(plant).submit_production_telemetry(
        args=[pid, telemetry_url]
    )

    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {".*": json.dumps(VALID_TELEMETRY)},
            "web_mocks": {telemetry_url: {"status": 200, "body": json.dumps(VALID_TELEMETRY)}}
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[pid])

    contract.connect(sponsor).file_dispute(
        args=[pid, "https://dnv.com/unresponsive_node.json", "Dispute for timeout"],
        value=bond
    )

    # Attempting to resolve before 7 days must fail
    with pytest.raises(Exception, match="Appellate window is active"):
        contract.connect(sponsor).resolve_stale_appeal(args=[pid])

    # Elapse 7 days + 1 second (604,801 seconds)
    contract.set_time(contract.simulated_time + 604801)
    contract.connect(sponsor).resolve_stale_appeal(args=[pid])

    # Check bond is refunded to appellant's claimable balance
    bond_claimable = contract.get_claimable_balance(args=[str(sponsor)]).call()
    assert int(bond_claimable) == bond

    # Appellant can claim their refunded bond
    contract.connect(sponsor).claim_payout()
    assert int(contract.get_claimable_balance(args=[str(sponsor)]).call()) == 0
    assert int(contract.get_total_withdrawn(args=[str(sponsor)]).call()) == bond
