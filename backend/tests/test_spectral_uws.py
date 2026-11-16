import asyncio
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import resolve_spectral_uws as uws


def test_votable_empty_success_is_distinct_from_tap_error():
    empty = '<VOTABLE><RESOURCE><INFO name="QUERY_STATUS" value="OK"/><TABLE>' \
        '<FIELD name="planeid"/><FIELD name="uri"/><FIELD name="contentchecksum"/>' \
        '<DATA><TABLEDATA/></DATA></TABLE></RESOURCE></VOTABLE>'
    assert uws.parse_result(empty, {"p"}) == []
    for status in ("ERROR", "OVERFLOW"):
        with pytest.raises(ValueError, match="TAP result status"):
            uws.parse_result(empty.replace('value="OK"', f'value="{status}"'), {"p"})
    with pytest.raises(ValueError, match="unexpected plane"):
        uws.parse_result("planeid,uri,contentchecksum\nwrong,uri,md5:a\n", {"p"})


def test_job_runner_submits_starts_polls_and_fetches(monkeypatch, tmp_path):
    monkeypatch.setattr(uws, "LOGS", tmp_path)
    phases = iter(["PENDING", "QUEUED", "EXECUTING", "COMPLETED"])
    requests = []

    def respond(request):
        requests.append((request.method, request.url.path, request.content))
        if request.url.path == "/TAP/async":
            return httpx.Response(303, headers={"Location": "/TAP/async/123"})
        if request.method == "POST":
            return httpx.Response(303)
        if request.url.path.endswith("/phase"):
            return httpx.Response(200, text=next(phases))
        return httpx.Response(200, text="planeid,uri,contentchecksum\np,uri,md5:a\n")

    async def test():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await uws.run_job(client, "D3", {"p"}, 1, 0)

    result = asyncio.run(test())
    assert result["rows"] == [{"planeid": "p", "uri": "uri", "contentchecksum": "md5:a"}]
    assert [r[2] for r in requests if r[:2] == ("POST", "/TAP/async/123/phase")] == [b"PHASE=RUN"]
    assert requests[-1][:2] == ("GET", "/TAP/async/123/results/result")


def test_expiring_local_window_leaves_queued_job_alone(monkeypatch, tmp_path):
    monkeypatch.setattr(uws, "LOGS", tmp_path)
    calls = []

    def respond(request):
        calls.append((request.method, request.url.path))
        return httpx.Response(200, text="QUEUED")

    async def test():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            prior = dict(job_url="https://irsa.ipac.caltech.edu/TAP/async/123", events=[])
            return await uws.run_job(client, "D5", {"p"}, .03, .005, prior)

    result = asyncio.run(test())
    assert result["phase"] == "QUEUED"
    assert "left alone" in result["outcome"]
    assert calls and set(calls) == {("GET", "/TAP/async/123/phase")}
    assert "rows" not in result


def test_502_proxy_response_is_not_a_missing_artifact(monkeypatch, tmp_path):
    monkeypatch.setattr(uws, "LOGS", tmp_path)

    async def test():
        handler = lambda request: httpx.Response(502, text="Proxy Error")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await uws.run_job(client, "D2", {"p"}, 1, 0)

    result = asyncio.run(test())
    assert result["outcome"] == "submission failed or unconfirmed"
    assert result["events"][0]["body"] == "Proxy Error"
    assert "rows" not in result and "job_url" not in result


def test_502_while_polling_backs_off_without_restarting_job(monkeypatch, tmp_path):
    monkeypatch.setattr(uws, "LOGS", tmp_path)
    calls = []
    def respond(request):
        calls.append((request.method, request.url.path))
        return httpx.Response(502, text="Proxy Error")
    async def test():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await uws.run_job(client, "D1-D4", {"p"}, .03, 0,
                                     dict(job_url="https://irsa.ipac.caltech.edu/TAP/async/123", events=[]))
    result = asyncio.run(test())
    assert calls == [("GET", "/TAP/async/123/phase")]
    assert "left alone" in result["outcome"] and "rows" not in result


def test_documented_query_string_submission_can_read_uws_job_document(monkeypatch, tmp_path):
    monkeypatch.setattr(uws, "LOGS", tmp_path)

    def respond(request):
        assert request.method == "GET"
        if request.url.path == "/TAP/async":
            assert "planeid IN ('p')" in request.url.params["QUERY"]
            return httpx.Response(200, text='<job xmlns="http://www.ivoa.net/xml/UWS/v1.0"><jobId>12</jobId></job>')
        if request.url.path.endswith("/phase"):
            return httpx.Response(200, text="COMPLETED")
        return httpx.Response(200, text="planeid,uri,contentchecksum\n")

    async def test():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await uws.run_job(client, "D3", {"p"}, 1, 0, use_get=True)

    result = asyncio.run(test())
    assert result["job_url"] == uws.ASYNC_URL + "/12"
    assert result["outcome"] == "completed with zero rows"
