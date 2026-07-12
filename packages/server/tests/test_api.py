import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from lappa.api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "diff_drive_2w" in body["demos"]


def test_demos_and_sim():
    r = client.get("/api/demos")
    assert r.status_code == 200
    assert len(r.json()) >= 5

    r = client.post("/api/sim/start", json={"demo": "diff_drive_2w"})
    assert r.status_code == 200
    assert r.json()["state"]["running"] is True

    client.post("/api/sim/cmd", json={"linear_x": 0.5, "angular_z": 0.1})
    st = client.get("/api/sim/state").json()
    assert "x" in st

    client.post("/api/sim/stop")


def test_docker_status_endpoint():
    r = client.get("/api/docker/status")
    assert r.status_code == 200
    assert "available" in r.json()
