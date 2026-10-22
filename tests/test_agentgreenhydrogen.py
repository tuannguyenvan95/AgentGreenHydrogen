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
                    "measured_purity_bps": 9998,
                    "measured_carbon_intensity_g": 1250,
                    "reason": "Electrolysis operated on 100% offshore wind power. Fuel cell grade ISO 14687 purity verified."
                })
            },
            "web_mocks": {
                telemetry_url: {"status": 200, "body": '{"h2_purity": 0.9998, "carbon_intensity_g_per_kg": 1250}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])

    p_data = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_data["status"] == 2  # STATUS_AWAITING_PAYOUT
    assert p_data["verdict"] == "GREEN_HYDROGEN_CERTIFIED_FULL"
    assert p_data["measured_purity_bps"] == 9998

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

    # Fake blog link must be reverted
    with pytest.raises(Exception) as exc_info:
        contract.connect(plant).submit_production_telemetry(
            args=[policy_id, "https://my-unverified-energy-blog.com/h2_report.json"]
        )
    assert "Telemetry unauthenticated" in str(exc_info.value)


def test_partial_carbon_penalty(client):
    """Proves that partial grid mixing incurs a 50% penalty on the subsidy."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "TEXAS-GULF-ELECTROLYZER", 9997, 2000, 6000],
        value=1000000000000000000
    )
    policy_id = str(tx_create.return_value)

    dnv_url = "https://dnv.com/reports/texas_h2_carbon_intensity.json"
    contract.connect(plant).submit_production_telemetry(args=[policy_id, dnv_url])

    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "PARTIAL_CARBON_INTENSITY_PENALTY",
                    "confidence": 92,
                    "measured_purity_bps": 9997,
                    "measured_carbon_intensity_g": 3200,
                    "reason": "Hydrogen purity reaches ISO 14687 threshold, but 18% fossil peaking electricity mixed into stack."
                })
            },
            "web_mocks": {
                dnv_url: {"status": 200, "body": '{"h2_purity": 0.9997, "carbon_intensity_g_per_kg": 3200}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])
    p_data = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_data["status"] == 2  # STATUS_AWAITING_PAYOUT
    assert p_data["verdict"] == "PARTIAL_CARBON_INTENSITY_PENALTY"

    contract.set_time(contract.simulated_time + 80)
    contract.connect(sponsor).finalize_settlement(args=[policy_id])
    p_settled = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_settled["status"] == 4  # STATUS_SETTLED_PARTIAL


def test_gray_hydrogen_rejection(client):
    """Proves that gray hydrogen or severe purity failure results in total refund to climate fund."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "BAVARIA-PEM-FACILITY", 9997, 2000, 6000],
        value=1500000000000000000
    )
    policy_id = str(tx_create.return_value)

    bv_url = "https://bureauveritas.com/h2/bavaria_chromatography.json"
    contract.connect(plant).submit_production_telemetry(args=[policy_id, bv_url])

    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "GRAY_HYDROGEN_REJECTED",
                    "confidence": 99,
                    "measured_purity_bps": 9850,
                    "measured_carbon_intensity_g": 9500,
                    "reason": "Steam methane reforming detected. Carbon intensity violates green threshold by 475%."
                })
            },
            "web_mocks": {
                bv_url: {"status": 200, "body": '{"h2_purity": 0.9850, "carbon_intensity_g_per_kg": 9500}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])
    p_data = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_data["verdict"] == "GRAY_HYDROGEN_REJECTED"

    contract.set_time(contract.simulated_time + 100)
    contract.connect(sponsor).finalize_settlement(args=[policy_id])
    p_settled = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_settled["status"] == 5  # STATUS_SETTLED_REJECTED


def test_cooling_off_dispute_and_appeal(client):
    """Proves that an appeal with 10% staked bond can overturn or uphold quality verdicts."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "ANTWERP-CLUSTER-04", 9997, 2000, 6000],
        value=2000000000000000000  # 2 GEN
    )
    policy_id = str(tx_create.return_value)

    certifhy_url = "https://certifhy.eu/certificates/antwerp_04.json"
    contract.connect(plant).submit_production_telemetry(args=[policy_id, certifhy_url])

    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "PARTIAL_CARBON_INTENSITY_PENALTY",
                    "confidence": 88,
                    "measured_purity_bps": 9997,
                    "measured_carbon_intensity_g": 2400,
                    "reason": "Minor grid intensity flag during wind lull."
                })
            },
            "web_mocks": {
                certifhy_url: {"status": 200, "body": '{"h2_purity": 0.9997, "carbon_intensity_g_per_kg": 2400}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])

    # Producer appeals within cooling off window with 10% bond (0.2 GEN)
    supp_audit_url = "https://fraunhofer.de/energy/antwerp_corrected_audit.json"
    contract.connect(plant).appeal_verdict(
        args=[policy_id, "Battery storage system smoothed the grid lull, zero fossil power used.", supp_audit_url],
        value=200000000000000000  # 0.2 GEN
    )

    p_disputed = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_disputed["status"] == 6  # STATUS_DISPUTED
    assert p_disputed["dispute_bond"] == "200000000000000000"

    # Supreme tribunal evaluates appeal
    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "APPEAL_UPHELD_CERTIFIED",
                    "reason": "Battery energy storage discharge verified. Carbon intensity recomputed to 1800 g CO2e/kg."
                })
            },
            "web_mocks": {
                supp_audit_url: {"status": 200, "body": '{"battery_backed": true, "corrected_carbon_intensity": 1800}'}
            }
        }
    )

    contract.connect(plant).adjudicate_appeal(args=[policy_id])
    p_resolved = json.loads(contract.get_policy(args=[policy_id]).call())
    assert p_resolved["status"] == 3  # STATUS_SETTLED_CERTIFIED_FULL
    assert p_resolved["verdict"] == "GREEN_HYDROGEN_CERTIFIED_FULL"
    assert p_resolved["dispute_bond"] == "0"


def test_sponsor_cannot_self_designate_electrolyzer(client):
    """Proves that a sponsor cannot designate their own address as the electrolyzer plant."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]

    with pytest.raises(Exception) as exc_info:
        contract.connect(sponsor).create_subsidy_policy(
            args=[str(sponsor), "SELF-PLANT-01", 9997, 2000, 6000],
            value=1000000000000000000
        )
    assert "Sponsor" in str(exc_info.value)


def test_role_based_access_control(client):
    """Proves strict role enforcement across sponsor, plant, and unauthorized third parties."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]
    intruder = client.accounts[2]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "ROLE-CHECK-PLANT", 9997, 2000, 6000],
        value=1000000000000000000
    )
    policy_id = str(tx_create.return_value)

    # 1. Role verification view
    role_sponsor = contract.get_user_role(args=[policy_id, str(sponsor)]).call()
    role_plant = contract.get_user_role(args=[policy_id, str(plant)]).call()
    role_intruder = contract.get_user_role(args=[policy_id, str(intruder)]).call()

    assert role_sponsor == "SPONSOR"
    assert role_plant == "ELECTROLYZER_PLANT"
    assert role_intruder == "OBSERVER"

    # 2. Intruder cannot submit telemetry
    with pytest.raises(Exception) as exc_info:
        contract.connect(intruder).submit_production_telemetry(
            args=[policy_id, "https://tuvsud.com/api/h2.json"]
        )
    assert "Role Violation" in str(exc_info.value)

    # 3. Intruder cannot reclaim
    with pytest.raises(Exception) as exc_reclaim:
        contract.connect(intruder).cancel_or_reclaim(args=[policy_id])
    assert "Role Violation" in str(exc_reclaim.value)


def test_cooling_off_countdown_tracking(client):
    """Proves accurate remaining cooling-off seconds calculation."""
    contract = client.deploy("contracts/contract.py")
    sponsor = client.accounts[0]
    plant = client.accounts[1]

    tx_create = contract.connect(sponsor).create_subsidy_policy(
        args=[str(plant), "COUNTDOWN-PLANT", 9997, 2000, 6000],
        value=1000000000000000000
    )
    policy_id = str(tx_create.return_value)

    cert_url = "https://tuvsud.com/api/report.json"
    contract.connect(plant).submit_production_telemetry(args=[policy_id, cert_url])

    client.provider.make_request(
        method="sim_installMocks",
        params={
            "llm_mocks": {
                ".*": json.dumps({
                    "canary": "CANARY_AGENT_GREEN_HYDROGEN_V1",
                    "verdict": "GREEN_HYDROGEN_CERTIFIED_FULL",
                    "confidence": 95,
                    "measured_purity_bps": 9998,
                    "measured_carbon_intensity_g": 1100,
                    "reason": "100% compliant."
                })
            },
            "web_mocks": {
                cert_url: {"status": 200, "body": '{"h2": 0.9998}'}
            }
        }
    )

    contract.connect(plant).adjudicate_hydrogen_quality(args=[policy_id])

    # Initial cooling off should be 72 seconds
    rem_initial = contract.get_remaining_cooling_off_seconds(args=[policy_id]).call()
    assert rem_initial == 72

    # Advance 30 seconds
    contract.set_time(contract.simulated_time + 30)
    rem_mid = contract.get_remaining_cooling_off_seconds(args=[policy_id]).call()
    assert rem_mid == 42

    # Advance beyond 72 seconds -> returns 0
    contract.set_time(contract.simulated_time + 50)
    rem_done = contract.get_remaining_cooling_off_seconds(args=[policy_id]).call()
    assert rem_done == 0
