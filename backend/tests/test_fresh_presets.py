import json
from pathlib import Path

from app.services.demo_service import DemoService


def test_fresh_checkout_presets_use_audited_preview_positions(tmp_path):
    """Preset centers must not depend on an untracked local FITS cache."""
    service = DemoService(tmp_path / "missing-local-manifest.json")
    manifest = Path(__file__).resolve().parents[2] / "data/manifests/demo_preview.json"
    rows = json.loads(manifest.read_text(encoding="utf-8"))
    presets = service.get_presets()
    assert len(presets) == 5
    for preset in presets:
        covered = [row for row in rows if row["target_name"] == preset.name and row.get("catalog_coverage") == "inside"]
        latest = max(covered, key=lambda row: row["utc_date"])
        assert [preset.ra, preset.dec] == latest["predicted_degrees"]
