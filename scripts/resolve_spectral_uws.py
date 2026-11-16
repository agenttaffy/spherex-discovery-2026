"""Bounded, resumable IRSA UWS calibration queries. No science FITS are written."""
from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime, UTC
import io
import json
import re
import time
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree as ET

import httpx
from astropy.io import fits

from study_motion_multidetector import WORK
from app.science.spectral_calibration import spectral_calibration_plane_id

ASYNC_URL = "https://irsa.ipac.caltech.edu/TAP/async"
LOGS = WORK / "tap_uws"
TERMINAL = {"COMPLETED", "ABORT", "ABORTED", "ERROR", "CANCELLED", "CANCELED", "ARCHIVED"}


def sampled_planes():
    planes = {}
    for row in json.loads((WORK / "cutouts.json").read_text()):
        if not row.get("file"):
            continue
        with fits.open(WORK / row["file"]) as hdul:
            detector = str(hdul["IMAGE"].header["DETECTOR"])
            if detector != "6":
                planes.setdefault(detector, set()).add(spectral_calibration_plane_id(hdul))
    return planes


def checked_job_url(location):
    url = urljoin(ASYNC_URL + "/", location)
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != "irsa.ipac.caltech.edu"
            or not re.fullmatch(r"/TAP/async/[0-9]+", parts.path) or parts.query or parts.fragment):
        raise ValueError("IRSA did not return a supported UWS job location")
    return url


def parse_result(body, planes):
    if body.lstrip().startswith("<"):
        root = ET.fromstring(body)
        status = [node.get("value") for node in root.findall(".//{*}INFO") if node.get("name") == "QUERY_STATUS"]
        if not status or any(value != "OK" for value in status):
            raise ValueError(f"TAP result status {status!r}")
        table = root.find(".//{*}TABLE")
        if table is None or table.find(".//{*}TABLEDATA") is None:
            raise ValueError("Expected VOTable TABLEDATA result")
        fields = [node.get("name", "").lower() for node in table.findall("{*}FIELD")]
        records = [dict(zip(fields, (col.text or "" for col in row.findall("{*}TD")), strict=True))
                   for row in table.findall(".//{*}TR")]
    else:
        reader = csv.DictReader(io.StringIO(body.lstrip("\ufeff")))
        fields = reader.fieldnames or []
        records = list(reader)
    expected = {"planeid", "uri", "contentchecksum"}
    if not expected.issubset(fields) or any(r["planeid"] not in planes for r in records):
        raise ValueError("TAP result lacks required provenance or contains an unexpected plane")
    return [{k: r[k] for k in sorted(expected)} for r in records]


async def run_job(client, name, planes, seconds, poll_interval, previous=None, *, use_get=False):
    started = time.monotonic()
    log = previous or {
        "name": name, "planes": sorted(planes), "submitted_utc": datetime.now(UTC).isoformat(),
        "query": "SELECT planeid, uri, contentchecksum FROM spherex.artifact WHERE planeid IN ("
        + ",".join(repr(p) for p in sorted(planes)) + ")",
        "events": [],
    }
    elapsed_before = log.get("total_observed_seconds", 0)
    path = LOGS / f"{name}.json"

    def save():
        log["total_observed_seconds"] = round(elapsed_before + time.monotonic() - started, 3)
        path.write_text(json.dumps(log, indent=2), encoding="utf-8")

    async def request(method, url, data=None):
        try:
            response = await client.request(method, url, data=data)
        except httpx.RequestError as exc:
            log["events"].append({"method": method, "url": url, "error": type(exc).__name__,
                                  "detail": str(exc), "utc": datetime.now(UTC).isoformat()})
            save()
            return None
        log["events"].append({"method": method, "url": url, "status": response.status_code,
                              "location": response.headers.get("location"), "retry_after": response.headers.get("Retry-After"),
                              "body": response.text, "utc": datetime.now(UTC).isoformat()})
        save()
        return response

    async def observe():
        job = log.get("job_url")
        if not job:
            params = {
                "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": log["query"],
            }
            if use_get:
                url = str(client.build_request("GET", ASYNC_URL, params=params).url)
                response = await request("GET", url)
            else:
                response = await request("POST", ASYNC_URL, params)
            location = response.headers.get("location") if response is not None and response.status_code == 303 else None
            if location is None and response is not None and response.is_success:
                if response.text.lstrip().startswith("<"):
                    document = ET.fromstring(response.text)
                    job_id = document.findtext("{*}jobId") if document.tag.rsplit("}", 1)[-1] == "job" else None
                    if job_id and job_id.isascii() and job_id.isdigit():
                        location = f"{ASYNC_URL}/{job_id}"
            if not location:
                log["outcome"] = "submission failed or unconfirmed"
                return
            job = checked_job_url(location)
            log["job_url"] = job
        log["outcome"] = "observing remote job"
        save()

        run_requested = any(e.get("method") == "POST" and e.get("url") == job + "/phase"
                            and e.get("status", 0) in (200, 202, 204, 303) for e in log["events"])
        while True:
            response = await request("GET", job + "/phase")
            delay = poll_interval
            if response is not None and response.is_success:
                phase = response.text.strip().upper()
                if re.fullmatch(r"[A-Z]+", phase):
                    log["phase"] = phase
                    save()
                    if phase == "COMPLETED":
                        result = await request("GET", job + "/results/result")
                        if result is None or not result.is_success:
                            log["outcome"] = "completed but result retrieval failed"
                            if result is None or result.status_code in (429, 502, 503, 504):
                                await asyncio.sleep(max(delay, 20))
                                continue
                        else:
                            log["rows"] = parse_result(result.text, planes)
                            log["outcome"] = "completed with rows" if log["rows"] else "completed with zero rows"
                        return
                    if phase in TERMINAL:
                        await request("GET", job)
                        await request("GET", job + "/error")
                        log["outcome"] = "terminal without successful result"
                        return
                    if phase in {"PENDING", "HELD"} and not run_requested:
                        submitted = await request("POST", job + "/phase", {"PHASE": "RUN"})
                        run_requested = submitted is not None and submitted.status_code in (200, 202, 204, 303)
            if response is not None and response.status_code in (429, 502, 503, 504):
                retry_after = response.headers.get("Retry-After", "")
                delay = max(delay, int(retry_after)) if retry_after.isdigit() else max(delay, 20)
            await asyncio.sleep(delay)

    try:
        async with asyncio.timeout(seconds):
            await observe()
    except TimeoutError:
        log["outcome"] = "local observation window ended; remote job left alone"
    except (ValueError, ET.ParseError) as exc:
        log["outcome"] = "unverified TAP response"
        log["validation_error"] = str(exc)
    finally:
        save()
    print(f"{name}: {log.get('job_url', 'no job URL')} | {log.get('phase', 'unknown')} | "
          f"{log['outcome']} | {log['total_observed_seconds']:.1f}s", flush=True)
    return log


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=150, choices=range(10, 601), metavar="10–600")
    parser.add_argument("--resume", action="store_true", help="Poll saved job URLs without creating duplicates.")
    parser.add_argument("--retry-unconfirmed", action="store_true", help="With --resume, retry submissions that returned no job URL.")
    parser.add_argument("--via-get", action="store_true", help="Use IRSA's documented query-string submission route.")
    parser.add_argument("--only", nargs="+", choices=("D1-D4", "D2", "D3", "D5"), help="Restrict scope to selected jobs.")
    args = parser.parse_args()
    if args.retry_unconfirmed and not args.resume:
        parser.error("--retry-unconfirmed requires --resume")
    planes = sampled_planes()
    scopes = {f"D{i}": planes[str(i)] for i in (3, 5, 2)}
    scopes["D1-D4"] = planes["1"] | planes["4"]
    LOGS.mkdir(exist_ok=True)
    async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=12, pool=15), follow_redirects=False) as client:
        calls = []
        for name, ids in scopes.items():
            if args.only and name not in args.only:
                continue
            path = LOGS / f"{name}.json"
            previous = json.loads(path.read_text()) if args.resume else None
            if previous and set(previous["planes"]) != ids:
                raise ValueError(f"Cannot resume {name} with different plane UUIDs")
            if previous and not previous.get("job_url") and not args.retry_unconfirmed:
                raise ValueError(f"Cannot resume {name} without a job URL; inspect the log before retrying")
            calls.append(run_job(client, name, ids, args.seconds, 10, previous, use_get=args.via_get))
        await asyncio.gather(*calls)
    reports = [json.loads(path.read_text()) for path in LOGS.glob("*.json")]
    rows = [row for report in reports for row in report.get("rows", [])]
    if rows:
        with (WORK / "spectral-artifacts.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["planeid", "uri", "contentchecksum"])
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    asyncio.run(main())
