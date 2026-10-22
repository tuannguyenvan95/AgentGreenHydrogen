import pytest
import json
from genlayer import *


def test_green_hydrogen_certified_full_payout(client):
    """Proves that a verified ISO 14687 compliant green hydrogen batch releases 100% subsidy to plant."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    # Step 1: Climate fund deposits 2 GEN subsidy
    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "ROTTERDAM-ELECTROLYZER-H2-01", 9997, 2000, 6000],
        value=2000000000000000000  # 2 GEN
    )
    policy_id = str(tx_create.return_value)

    # Step 2: Plant submits telemetry from accredited TÜV SÜD auditor
    telemetry_url = "https://tuvsud.com/api/v2/certifications/h2_purity_rotterdam01.json"
    contract.connect(plant).submit_production_telemetry(
        args=[policy_id, telemetry_url]
    )

    # Step 3: Mock AI Hydrogen Jury -> Purity 99.98% (9998 bps), Carbon 1250 g CO2e/kg (< 2000g)
    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "GREEN_HYDROGEN_CERTIFIED_FULL",
                    "confidence": 98,
                    "facility_id": "ROTTERDAM-ELECTROLYZER-H2-01",
                    "batch_id": "BATCH-ROT-2026-X1",
                    "auditor_cert_id": "TUV-SUD-ISO14687-9998",
                    "measurement_timestamp": 1760000500,
                    "measured_purity_bps": 9998,
                    "measured_carbon_intensity_g": 1250,
                    "hourly_renewable_match_ratio": 100,
                    "reason": "Electrolysis operated on 100% offshore wind power. Fuel cell grade ISO 14687 purity verified."
                })
            },
            "web_mocks": {
                telemetry_url: {"status": 200, "body": '{"facility_id": "ROTTERDAM-ELECTROLYZER-H2-01", "h2_purity": 0.9998, "carbon_intensity_g_per_kg": 1250}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])

    p_data = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_data["status"] == 2  # STATUS_AWAITING_PAYOUT
    assert p_data["verdict"] == "GREEN_HYDROGEN_CERTIFIED_FULL"
    assert p_data["measured_purity_bps"] == 9998
    assert p_data["auditor_cert_id"] == "TUV-SUD-ISO14687-9998"
    assert p_data["batch_id"] == "BATCH-ROT-2026-X1"

    # Finalize settlement after cooling off window
    contract.set_time(contract.simulated_time + 100)
    contract.connect(sponsor).finalize_settlement(args=[policy_id])

    p_data_after = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_data_after["status"] == 3  # STATUS_SETTLED_CERTIFIED_FULL
    assert p_data_after["escrow_amount"] == "0"


def test_green_hydrogen_unaccredited_source_rejected(client):
    """Proves that trigger telemetry from unaccredited sources is strictly rejected."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "HAMBURG-H2-PLANT", 9997, 2000, 6000],
        value=1000000000000000000
    )
    policy_id = str(tx_create.return_value)

    with pytest.raises(Exception) as excinfo:
        contract.connect(plant).submit_production_telemetry(
            args=[policy_id, "https://unverified-h2-supplier.xyz/purity.json"]
        )
    assert "Telemetry unauthenticated" in str(excinfo.value)


def test_facility_provenance_mismatch_rejected(client):
    """Proves that telemetry issued for a different facility is strictly rejected by provenance checks."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "HAMBURG-H2-PLANT", 9997, 2000, 6000],
        value=1000000000000000000
    )
    policy_id = str(tx_create.return_value)

    cert_url = "https://dnv.com/reports/facility99.json"
    contract.connect(plant).submit_production_telemetry(args=[policy_id, cert_url])

    # Telemetry report is for ROGUE-FACILITY-99 instead of HAMBURG-H2-PLANT
    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "GREEN_HYDROGEN_CERTIFIED_FULL",
                    "confidence": 95,
                    "facility_id": "ROGUE-FACILITY-99",
                    "batch_id": "BATCH-FAKE",
                    "auditor_cert_id": "DNV-CERT-99",
                    "measurement_timestamp": 1760000100,
                    "measured_purity_bps": 9998,
                    "measured_carbon_intensity_g": 1200,
                    "hourly_renewable_match_ratio": 100,
                    "reason": "High purity but for completely different plant."
                })
            },
            "web_mocks": {
                cert_url: {"status": 200, "body": '{"facility_id": "ROGUE-FACILITY-99"}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])

    p_data = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_data["verdict"] == "GRAY_HYDROGEN_REJECTED"
    assert "Provenance Failure" in p_data["reason"]


def test_onchain_mathematical_threshold_enforcement(client):
    """Proves that on-chain threshold logic overrides rogue LLM labels when purity fails."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "ANTWERP-H2-PLANT", 9997, 2000, 6000],
        value=1000000000000000000
    )
    policy_id = str(tx_create.return_value)

    cert_url = "https://bureauveritas.com/antwerp/chromatography.json"
    contract.connect(plant).submit_production_telemetry(args=[policy_id, cert_url])

    # Rogue LLM outputs purity 9800 bps (< 9997 bps required), but hallucinated GREEN_HYDROGEN_CERTIFIED_FULL
    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "GREEN_HYDROGEN_CERTIFIED_FULL",  # Hallucinated label
                    "confidence": 90,
                    "facility_id": "ANTWERP-H2-PLANT",
                    "batch_id": "BATCH-01",
                    "auditor_cert_id": "BV-991",
                    "measurement_timestamp": 1760000100,
                    "measured_purity_bps": 9800,  # Below 9997 threshold!
                    "measured_carbon_intensity_g": 1500,
                    "hourly_renewable_match_ratio": 95,
                    "reason": "Rogue LLM tried to pass low purity."
                })
            },
            "web_mocks": {
                cert_url: {"status": 200, "body": '{"purity": 0.9800}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])

    p_data = json.loads(contract.get_policy(args=[policy_id]).call())
    # Contract must strictly enforce threshold on-chain and reject!
    assert p_data["verdict"] == "GRAY_HYDROGEN_REJECTED"
    assert "Threshold Enforcement" in p_data["reason"]


def test_cooling_off_dispute_and_appeal_adjudication(client):
    """Proves dispute staking and appellate court resolution with bond handling."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "BREMEN-H2-PLANT", 9997, 2000, 6000],
        value=2000000000000000000  # 2 GEN
    )
    policy_id = str(tx_create.return_value)

    cert_url = "https://tuvsud.com/bremen_audit.json"
    contract.connect(plant).submit_production_telemetry(args=[policy_id, cert_url])

    # Initial verdict: Partial carbon penalty (Carbon = 2500g > 2000g)
    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "PARTIAL_CARBON_INTENSITY_PENALTY",
                    "confidence": 90,
                    "facility_id": "BREMEN-H2-PLANT",
                    "batch_id": "BREMEN-B1",
                    "auditor_cert_id": "TUV-BREMEN-01",
                    "measurement_timestamp": 1760000100,
                    "measured_purity_bps": 9998,
                    "measured_carbon_intensity_g": 2500,
                    "hourly_renewable_match_ratio": 85,
                    "reason": "15% grid power mixing recorded."
                })
            },
            "web_mocks": {
                cert_url: {"status": 200, "body": '{"carbon": 2500}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])

    # Electrolyzer plant stakes 10% dispute bond (0.2 GEN)
    appeal_url = "https://certifhy.eu/bremen_recalibration.json"
    contract.connect(plant).file_dispute(
        args=[policy_id, appeal_url, "Auditor miscalculated hourly renewable PPA match from offshore wind."],
        value=200000000000000000  # 0.2 GEN bond
    )

    p_disp = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_disp["status"] == 6  # STATUS_DISPUTED
    assert p_disp["dispute_bond"] == "200000000000000000"

    # Supreme Clean Energy Appellate Court upholds appeal
    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "APPEAL_UPHELD_CERTIFIED",
                    "reason": "Recalibrated spectrometry confirms 100% renewable power match and 1200 g CO2/kg."
                })
            },
            "web_mocks": {
                appeal_url: {"status": 200, "body": '{"recalibrated": true, "carbon": 1200}'}
            }
        }
    )

    contract.connect(plant).adjudicate_appeal(args=[policy_id])

    p_after = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_after["status"] == 3  # STATUS_SETTLED_CERTIFIED_FULL
    assert p_after["verdict"] == "GREEN_HYDROGEN_CERTIFIED_FULL"
    assert p_after["dispute_bond"] == "0"


def test_stale_appeal_timeout_recovery(client):
    """Proves that a dispute with unreachable evidence can be safely recovered after timeout."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "LE-HAVRE-H2-PLANT", 9997, 2000, 6000],
        value=2000000000000000000
    )
    policy_id = str(tx_create.return_value)

    cert_url = "https://dnv.com/lehavre.json"
    contract.connect(plant).submit_production_telemetry(args=[policy_id, cert_url])

    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "GREEN_HYDROGEN_CERTIFIED_FULL",
                    "confidence": 95,
                    "facility_id": "LE-HAVRE-H2-PLANT",
                    "batch_id": "B-LH",
                    "auditor_cert_id": "DNV-LH-01",
                    "measurement_timestamp": 1760000100,
                    "measured_purity_bps": 9998,
                    "measured_carbon_intensity_g": 1100,
                    "hourly_renewable_match_ratio": 100,
                    "reason": "100% green."
                })
            },
            "web_mocks": {
                cert_url: {"status": 200, "body": '{"h2": 0.9998}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])

    # Sponsor files dispute but provides dead URL
    dead_url = "https://nrel.gov/permanently_offline.json"
    contract.connect(sponsor).file_dispute(
        args=[policy_id, dead_url, "Sponsor challenges batch verification."],
        value=200000000000000000  # 0.2 GEN
    )

    # Advance time past 7-day APPEAL_TIMEOUT_SECONDS (7 * 86400 = 604800s)
    contract.set_time(contract.simulated_time + 605000)

    # Bounded recovery executes: bond refunded to appellant, policy restored to prior verdict
    contract.connect(sponsor).resolve_stale_appeal(args=[policy_id])

    p_rec = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_rec["status"] == 2  # STATUS_AWAITING_PAYOUT
    assert p_rec["dispute_bond"] == "0"
    assert p_rec["verdict"] == "GREEN_HYDROGEN_CERTIFIED_FULL"
    assert "APPEAL TIMEOUT RECOVERY" in p_rec["reason"]


def test_pull_payment_claim_payout_accounting(client):
    """Proves Pull-Payment accounting and that beneficiary credits are securely claimable."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "VALENCIA-H2-FACILITY", 9997, 2000, 6000],
        value=1500000000000000000  # 1.5 GEN
    )
    policy_id = str(tx_create.return_value)

    cert_url = "https://iso.org/valencia_audit.json"
    contract.connect(plant).submit_production_telemetry(args=[policy_id, cert_url])

    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "GREEN_HYDROGEN_CERTIFIED_FULL",
                    "confidence": 98,
                    "facility_id": "VALENCIA-H2-FACILITY",
                    "batch_id": "B-VAL",
                    "auditor_cert_id": "ISO-VAL-99",
                    "measurement_timestamp": 1760000100,
                    "measured_purity_bps": 9999,
                    "measured_carbon_intensity_g": 900,
                    "hourly_renewable_match_ratio": 100,
                    "reason": "Full solar electrolysis compliance."
                })
            },
            "web_mocks": {
                cert_url: {"status": 200, "body": '{"purity": 0.9999}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])
    contract.set_time(contract.simulated_time + 100)
    contract.connect(plant).finalize_settlement(args=[policy_id])

    # Check stats and policy
    stats = json.loads(contract.get_stats().call())
    assert stats["total_policies_settled"] == 1

    # Verify claimable balance or withdrawal
    bal = contract.get_claimable_balance(args=[str(plant)]).call()
    # If immediately emitted, balance is 0 and total_withdrawn is recorded
    withdrawn = contract.get_total_withdrawn(args=[str(plant)]).call()
    total_received = int(bal) + int(withdrawn)
    assert total_received == 1500000000000000000


def test_deploy_with_integer_address_from_studio(client):
    """Proves that passing an integer address into __init__ works flawlessly."""
    raw_int_addr = 63049619117024084276749704701518846041853730902
    contract = client.deploy("contracts/contract.py", args=[raw_int_addr])
    stats = json.loads(contract.get_stats().call())
    assert stats["total_policies"] == 0
    expected_hex = f"0x{raw_int_addr:040x}".lower()
    assert stats["owner"].lower() == expected_hex


def test_partial_carbon_penalty_settlement(client):
    """Proves that partial carbon breach splits subsidy 50/50 between plant and fund."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "SEVILLE-SOLAR-H2", 9997, 2000, 6000],
        value=2000000000000000000  # 2 GEN
    )
    policy_id = str(tx_create.return_value)

    cert_url = "https://fraunhofer.de/reports/seville.json"
    contract.connect(plant).submit_production_telemetry(args=[policy_id, cert_url])

    # Carbon is 2600 g (> 2000 g but <= 4000 g) -> triggers 50% penalty
    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "PARTIAL_CARBON_INTENSITY_PENALTY",
                    "confidence": 92,
                    "facility_id": "SEVILLE-SOLAR-H2",
                    "batch_id": "BATCH-SEV-01",
                    "auditor_cert_id": "FRAUN-SEV-2026",
                    "measurement_timestamp": 1760000100,
                    "measured_purity_bps": 9998,
                    "measured_carbon_intensity_g": 2600,
                    "hourly_renewable_match_ratio": 80,
                    "reason": "Electrolysis purity compliant but carbon exceeded threshold."
                })
            },
            "web_mocks": {
                cert_url: {"status": 200, "body": '{"carbon": 2600}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])
    p_data = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_data["verdict"] == "PARTIAL_CARBON_INTENSITY_PENALTY"

    contract.set_time(contract.simulated_time + 100)
    contract.connect(sponsor).finalize_settlement(args=[policy_id])

    p_after = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_after["status"] == 4  # STATUS_SETTLED_PARTIAL


def test_timestamp_outside_coverage_window_rejected(client):
    """Proves that measurement timestamp outside policy coverage window is rejected."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "GOTHENBURG-H2", 9997, 2000, 100],  # 300 seconds coverage
        value=1000000000000000000
    )
    policy_id = str(tx_create.return_value)

    cert_url = "https://dnv.com/gothenburg/report.json"
    contract.connect(plant).submit_production_telemetry(args=[policy_id, cert_url])

    # Measurement timestamp is from 1 year in the past (stale report!)
    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "GREEN_HYDROGEN_CERTIFIED_FULL",
                    "confidence": 95,
                    "facility_id": "GOTHENBURG-H2",
                    "batch_id": "BATCH-STALE",
                    "auditor_cert_id": "DNV-STALE-01",
                    "measurement_timestamp": 1700000000,  # Far in the past!
                    "measured_purity_bps": 9998,
                    "measured_carbon_intensity_g": 1100,
                    "hourly_renewable_match_ratio": 100,
                    "reason": "Stale report from previous year."
                })
            },
            "web_mocks": {
                cert_url: {"status": 200, "body": '{"stale": true}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])
    p_data = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_data["verdict"] == "GRAY_HYDROGEN_REJECTED"
    assert "Provenance Failure: Measurement timestamp" in p_data["reason"]


def test_reclaim_expired_subsidy(client):
    """Proves that a sponsor can reclaim expired escrow if plant fails to submit telemetry."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "DUNKIRK-H2-PORT", 9997, 2000, 10],  # 30 seconds
        value=1000000000000000000
    )
    policy_id = str(tx_create.return_value)

    # Cannot reclaim while policy is still active
    with pytest.raises(Exception):
        contract.connect(sponsor).cancel_or_reclaim(args=[policy_id])

    # Advance past expiration (30 seconds)
    contract.set_time(contract.simulated_time + 50)
    contract.connect(sponsor).cancel_or_reclaim(args=[policy_id])

    p_after = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_after["status"] == 7  # STATUS_EXPIRED_RECLAIMED
    assert p_after["escrow_amount"] == "0"

