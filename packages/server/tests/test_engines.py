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
    st = eng.step(dt=0.1)
    assert st.x > 0
    assert abs(st.y) < 0.2


def test_omni_strafe():
    eng = create_engine("omni_3w")
    eng.state.running = True
    eng.set_cmd(linear_x=0.0, linear_y=1.0, angular_z=0.0)
    st = eng.step(dt=0.1)
    assert st.y > 0


def test_arm_fk_updates():
    eng = create_engine("simple_arm")
    eng.state.running = True
    eng.set_cmd(linear_x=0.5, angular_z=-0.2)
    st = eng.step(dt=0.1)
    assert len(st.joints) == 2
    assert st.lidar  # synthetic


def test_burst_ticks_still_move():
    """GUI / tight loops used to get dt≈0 and freeze the robot."""
    eng = create_engine("diff_drive_2w")
    eng.state.running = True
    eng.set_cmd(linear_x=1.0, angular_z=0.0)
    for _ in range(5):
        eng.step()  # no sleep — must still integrate via floor dt
    assert eng.state.x > 0
    assert eng.state.t > 0


def test_trajectory_csv():
    from lappa.sim.session import SimSession

    s = SimSession()
    s.start("diff_drive_2w")
    s.cmd(0.5, 0.0, 0.2)
    for _ in range(3):
        s.tick()
    csv = s.trajectory_csv()
    assert "t,x,y,theta" in csv
    assert csv.count("\n") >= 3
    # pose must advance without manual clock hacking
    assert s.engine is not None
    assert s.engine.state.x != 0.0 or s.engine.state.theta != 0.0
    s.stop()
