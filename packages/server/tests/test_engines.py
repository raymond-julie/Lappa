from lappa.sim.engines import create_engine, ENGINES


def test_all_engines_registered():
    for name in (
        "diff_drive_2w",
        "omni_3w",
        "tricycle_3w",
        "ackermann_4w",
        "simple_arm",
    ):
        assert name in ENGINES


def test_diff_drive_moves_forward():
    eng = create_engine("diff_drive_2w")
    eng.state.running = True
    eng.set_cmd(linear_x=1.0, angular_z=0.0)
    eng._last -= 0.1  # force dt
    st = eng.step()
    assert st.x > 0
    assert abs(st.y) < 0.2


def test_omni_strafe():
    eng = create_engine("omni_3w")
    eng.state.running = True
    eng.set_cmd(linear_x=0.0, linear_y=1.0, angular_z=0.0)
    eng._last -= 0.1
    st = eng.step()
    assert st.y > 0


def test_arm_fk_updates():
    eng = create_engine("simple_arm")
    eng.state.running = True
    eng.set_cmd(linear_x=0.5, angular_z=-0.2)
    eng._last -= 0.1
    st = eng.step()
    assert len(st.joints) == 2
    assert st.lidar  # synthetic
