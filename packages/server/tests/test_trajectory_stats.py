from lappa.sim.session import SimSession


def test_trajectory_stats_empty():
    s = SimSession()
    st = s.trajectory_stats()
    assert st["points"] == 0


def test_trajectory_stats_after_ticks():
    s = SimSession()
    s.start("diff_drive_2w")
    s.cmd(0.2, 0.0, 0.0)
    for _ in range(5):
        s.tick()
    st = s.trajectory_stats()
    assert st["points"] >= 5
    assert st["distance_m"] >= 0.0
    assert "avg_speed_mps" in st
    assert "max_speed_mps" in st
    assert st["max_speed_mps"] >= 0.0
    assert "net_displacement_m" in st
    assert st["net_displacement_m"] >= 0.0
    assert "path_efficiency" in st
    assert 0.0 <= st["path_efficiency"] <= 1.0 + 1e-6
    assert "idle_time_s" in st
    assert st["idle_time_s"] >= 0.0
    status = s.status()
    assert "trajectory_stats" in status
    assert status["trajectory_stats"]["points"] == st["points"]
