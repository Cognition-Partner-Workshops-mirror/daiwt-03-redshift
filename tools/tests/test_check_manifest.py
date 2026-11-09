"""check_manifest: catches broken manifests, accepts the real one."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools import check_manifest


def test_real_manifest_is_clean():
    assert check_manifest.checkManifest() == []


def test_missing_legacy_file_is_flagged(tmp_path):
    import yaml
    manifest_path = tmp_path / "units.yaml"
    data = yaml.safe_load(check_manifest.MANIFEST.read_text())
    data["units"]["daily_revenue"]["legacy"] = ["legacy/redshift/units/daily_revenue/nope.sql"]
    manifest_path.write_text(yaml.safe_dump(data))
    errors = check_manifest.checkManifest(manifest_path)
    assert any("missing file" in e for e in errors)


def test_wave_listing_must_match_units(tmp_path):
    import yaml
    manifest_path = tmp_path / "units.yaml"
    data = yaml.safe_load(check_manifest.MANIFEST.read_text())
    data["waves"][0]["units"] = []
    manifest_path.write_text(yaml.safe_dump(data))
    errors = check_manifest.checkManifest(manifest_path)
    assert any("waves list" in e for e in errors)
