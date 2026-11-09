"""Seed determinism: generating twice produces identical bytes."""
import hashlib
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
SEED_DIR = ROOT / "data" / "seed" / "csv"
GENERATOR = ROOT / "data" / "seed" / "generate_seed.py"


def snapshot():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(SEED_DIR.glob("*.csv"))}


def test_seed_is_deterministic():
    subprocess.run(["python", str(GENERATOR)], check=True, cwd=ROOT, capture_output=True)
    first = snapshot()
    assert first, "generator produced no csv files"
    subprocess.run(["python", str(GENERATOR)], check=True, cwd=ROOT, capture_output=True)
    assert snapshot() == first
