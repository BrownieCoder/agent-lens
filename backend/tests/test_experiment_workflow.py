"""Independent expectations for split isolation and persisted fixture provenance."""
import argparse
import importlib.util
from pathlib import Path

import pytest

from test_api import client, clean_database, sample_run


spec = importlib.util.spec_from_file_location(
    "experiment_fixture", Path(__file__).resolve().parents[2] / "scripts/verify_experiment.py"
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


@pytest.mark.parametrize("split,pairs", [("exploration", 4), ("holdout", 2)])
def test_execute_one_split_preserves_pairs_metadata_and_case_links(client, tmp_path, split, pairs):
    manifest = fixture.experiment(split)
    assert len(manifest["rows"]) == pairs * 2
    assert {row["split"] for row in manifest["rows"]} == {split}
    result = fixture.execute_mock_experiment(client, manifest, tmp_path)
    assert result["runs"] == pairs * 2 and result["pairs"] == pairs
    assert result["provider_calls"] == result["human_reviews"] == 0
    runs = client.get("/runs").json()
    cases = client.get("/regression-cases").json()
    assert len(cases) == pairs
    for case in cases:
        linked = client.get(f"/regression-cases/{case['id']}/runs").json()
        assert len(linked) == 2
        assert {run["prompt_version"] for run in linked} == {"baseline-v1", "risk-aware-v2"}
    for run in runs:
        assert len(run["prompt_template_hash"]) == 64
        assert run["generation_parameters"]["method"] == "deterministic supplied text"
        assert run["dataset_name"] == run["experiment_name"] == f"synthetic-pairs-v2-{split}"
        assert run["estimated_cost"] is None and run["latency_ms"] is None
    report = (tmp_path / "evaluation-summary.md").read_text()
    other = "holdout" if split == "exploration" else "exploration"
    assert f"synthetic-experiment-{other}" not in report
    assert f"**Runs:** {pairs * 2}" in report
    assert client.get("/dashboard/calibration").json()["review_count"] == 0


def test_execution_refuses_mixed_splits_before_any_write(client, tmp_path):
    with pytest.raises(ValueError, match="exactly one split"):
        fixture.execute_mock_experiment(client, fixture.experiment(), tmp_path)
    assert client.get("/runs").json() == client.get("/regression-cases").json() == []


@pytest.mark.parametrize("existing", ["run", "case"])
def test_execution_preserves_nonempty_target(client, tmp_path, existing):
    if existing == "run":
        client.post("/runs", json=sample_run())
    else:
        client.post("/regression-cases", json={"name": "keep", "input_text": "synthetic", "expected_focus": "keep"})
    before = [client.get(path).json() for path in ("/runs", "/regression-cases")]
    with pytest.raises(ValueError, match="Target contains"):
        fixture.execute_mock_experiment(client, fixture.experiment("exploration"), tmp_path)
    assert [client.get(path).json() for path in ("/runs", "/regression-cases")] == before


@pytest.mark.parametrize("url", ["https://example.com", "http://192.168.1.2:8000", "http://localhost.evil.invalid",
                                 "http://user:secret@localhost:8000", "http://localhost/api", "http://localhost?x=1"])
def test_execution_url_rejects_nonlocal_or_ambiguous_destinations(url):
    with pytest.raises(argparse.ArgumentTypeError):
        fixture.local_api_url(url)


def test_fixture_inputs_are_disjoint_between_splits():
    exploration = {row["run"]["input_text"] for row in fixture.experiment("exploration")["rows"]}
    holdout = {row["run"]["input_text"] for row in fixture.experiment("holdout")["rows"]}
    assert len(exploration) == 4 and len(holdout) == 2 and exploration.isdisjoint(holdout)
