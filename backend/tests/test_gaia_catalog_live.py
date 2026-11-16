import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.catalog_service import CatalogService


RESPONSE = """#RESOURCE=yCat_1355
#Title: Gaia DR3
Source\tRA_ICRS\tDE_ICRS\tpmRA\tpmDE\tPlx\tGmag
 \tdeg\tdeg\tmas/yr\tmas/yr\tmas\tmag
-------------------\t---------------\t---------------\t---------\t---------\t---------\t---------
1648328016354496384\t248.16737836729\t+66.75500674547\t-20.643\t6.149\t1.2509\t6.374379
1648328016354500352\t248.16979981748\t+66.75556346743\t \t \t \t19.244020
"""


def test_gaia_preserves_large_ids_missing_motion_and_catalog_provenance():
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=httpx.Response(200, text=RESPONSE, request=httpx.Request("GET", "https://example.org")))):
        sources = asyncio.run(CatalogService().query_catalog(248.167227, 66.755024, 0.08))
    assert sources[0]["source_id"] == "Gaia DR3 1648328016354496384"
    assert sources[0]["provenance"] == "VizieR Gaia DR3 (J2016.0)"
    assert sources[0]["pm_ra"] == -20.643
    assert sources[1]["pm_ra"] is None and sources[1]["pm_dec"] is None


@pytest.mark.parametrize("body,status", [("<html>maintenance</html>", 200), ("unavailable", 503)])
def test_catalog_outages_do_not_fabricate_results(body, status):
    response = httpx.Response(status, text=body, request=httpx.Request("GET", "https://example.org"))
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
        with TestClient(app) as client:
            result = client.get("/api/science/catalogs?ra=248.167227&dec=66.755024&radius=0.08")
    assert result.status_code == 503
    assert "unavailable" in result.json()["detail"]
