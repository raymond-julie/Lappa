from lappa.sim.engines import DiffDrive2W, _lidar_scan


def test_lidar_hits_obstacles_shorter_than_max() -> None:
    ranges = _lidar_scan(0.0, 0.0, 0.0, n=36, max_range=3.0)
    assert len(ranges) == 36
    assert min(ranges) < 3.0  # at least one ray hits a default obstacle
    assert max(ranges) <= 3.0


def test_engine_lidar_updates_when_running() -> None:
    eng = DiffDrive2W("diff_drive_2w")
    eng.state.running = True
    eng.set_cmd(linear_x=0.2)
    st = eng.step(dt=0.05)
    assert len(st.lidar) == 36
    assert min(st.lidar) < 3.0
