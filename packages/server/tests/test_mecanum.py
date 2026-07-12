from lappa.sim.engines import Mecanum4W, create_engine


def test_mecanum_engine_strafes() -> None:
    eng = create_engine("mecanum_4w")
    assert isinstance(eng, Mecanum4W)
    eng.state.running = True
    eng.set_cmd(linear_x=0.0, linear_y=0.3, angular_z=0.0)
    st = eng.step(dt=0.1)
    assert abs(st.y) > 0.01
    assert len(st.joints) == 4


def test_tracked_alias() -> None:
    eng = create_engine("tracked_base")
    assert eng.kind == "mecanum_4w" or eng.__class__.__name__ == "Mecanum4W"
