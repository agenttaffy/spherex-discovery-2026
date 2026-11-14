import pytest
from app.services.irsa_client import IRSAClient, OBSERVATION_REGISTRY
from app.models.schemas import ObservationRecord

def test_irsa_client_parse():
    client = IRSAClient()
    # Check timestamp conversion
    utc = client._mjd_to_utc("60794.593497")
    assert utc is not None
    assert "2025-04-29" in utc

def test_observation_registry_insertion():
    OBSERVATION_REGISTRY["test_obs_1"] = {
        "id": "test_obs_1",
        "obs_id": "test_1",
        "collection": "spherex_dr1",
        "detector": "SPHEREx-D1",
        "access_url": "https://example.com/test.fits",
        "ra": 100.0,
        "dec": 20.0
    }
    assert "test_obs_1" in OBSERVATION_REGISTRY
