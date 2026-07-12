"""Native kinematics simulators (no ROS2 host install required)."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Twist:
    linear_x: float = 0.0
    linear_y: float = 0.0
    angular_z: float = 0.0


@dataclass
class SimState:
    demo: str
    kind: str
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0
    joints: list[float] = field(default_factory=list)
    twist: Twist = field(default_factory=Twist)
    lidar: list[float] = field(default_factory=list)
    t: float = 0.0
    running: bool = False
    mode: str = "native"  # native | docker
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "demo": self.demo,
            "kind": self.kind,
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "theta": round(self.theta, 4),
            "joints": [round(j, 4) for j in self.joints],
            "twist": {
                "linear_x": self.twist.linear_x,
                "linear_y": self.twist.linear_y,
                "angular_z": self.twist.angular_z,
            },
            "lidar": [round(r, 3) for r in self.lidar],
            "t": round(self.t, 3),
            "running": self.running,
            "mode": self.mode,
            "message": self.message,
        }


def _wrap(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


def _lidar_circle(n: int = 36, radius: float = 3.0, noise: float = 0.0) -> list[float]:
    # Synthetic free-space ring (placeholder until map obstacles)
    base = radius
    return [base + noise * math.sin(i) for i in range(n)]


class BaseEngine:
    kind = "base"

    def __init__(self, demo: str):
        self.state = SimState(demo=demo, kind=self.kind)
        self._last = time.monotonic()

    def set_cmd(self, linear_x: float = 0.0, linear_y: float = 0.0, angular_z: float = 0.0) -> None:
        self.state.twist = Twist(linear_x, linear_y, angular_z)

    def step(self) -> SimState:
        now = time.monotonic()
        dt = min(0.1, max(0.0, now - self._last))
        self._last = now
        if self.state.running:
            self._integrate(dt)
            self.state.t += dt
            self.state.lidar = _lidar_circle()
        return self.state

    def _integrate(self, dt: float) -> None:
        raise NotImplementedError

    def reset(self) -> None:
        demo, kind = self.state.demo, self.state.kind
        mode = self.state.mode
        self.state = SimState(demo=demo, kind=kind, mode=mode)
        self._last = time.monotonic()


class DiffDrive2W(BaseEngine):
    kind = "diff_drive_2w"

    def _integrate(self, dt: float) -> None:
        v = self.state.twist.linear_x
        w = self.state.twist.angular_z
        th = self.state.theta
        self.state.x += v * math.cos(th) * dt
        self.state.y += v * math.sin(th) * dt
        self.state.theta = _wrap(th + w * dt)


class Omni3W(BaseEngine):
    kind = "omni_3w"

    def _integrate(self, dt: float) -> None:
        vx = self.state.twist.linear_x
        vy = self.state.twist.linear_y
        w = self.state.twist.angular_z
        th = self.state.theta
        c, s = math.cos(th), math.sin(th)
        self.state.x += (c * vx - s * vy) * dt
        self.state.y += (s * vx + c * vy) * dt
        self.state.theta = _wrap(th + w * dt)


class Tricycle3W(BaseEngine):
    kind = "tricycle_3w"

    def _integrate(self, dt: float) -> None:
        # linear_x = speed, angular_z treated as steering rate → curvature
        v = self.state.twist.linear_x
        steer = max(-1.2, min(1.2, self.state.twist.angular_z))
        L = 0.35  # wheelbase
        th = self.state.theta
        self.state.x += v * math.cos(th) * dt
        self.state.y += v * math.sin(th) * dt
        if abs(L) > 1e-6:
            self.state.theta = _wrap(th + (v / L) * math.tan(steer) * dt)


class Ackermann4W(BaseEngine):
    kind = "ackermann_4w"

    def _integrate(self, dt: float) -> None:
        v = self.state.twist.linear_x
        delta = max(-0.7, min(0.7, self.state.twist.angular_z))
        L = 0.5
        th = self.state.theta
        self.state.x += v * math.cos(th) * dt
        self.state.y += v * math.sin(th) * dt
        self.state.theta = _wrap(th + (v / L) * math.tan(delta) * dt)


class SimpleArm(BaseEngine):
    kind = "simple_arm"

    def __init__(self, demo: str):
        super().__init__(demo)
        self.state.joints = [0.4, -0.6]
        self.state.x = 0.0
        self.state.y = 0.0

    def _integrate(self, dt: float) -> None:
        # twist.linear_x / angular_z drive joint velocities
        j0 = self.state.joints[0] + self.state.twist.linear_x * dt
        j1 = self.state.joints[1] + self.state.twist.angular_z * dt
        self.state.joints = [
            max(-2.5, min(2.5, j0)),
            max(-2.5, min(2.5, j1)),
        ]
        # FK tip for canvas
        l1, l2 = 0.6, 0.5
        self.state.x = l1 * math.cos(self.state.joints[0]) + l2 * math.cos(
            self.state.joints[0] + self.state.joints[1]
        )
        self.state.y = l1 * math.sin(self.state.joints[0]) + l2 * math.sin(
            self.state.joints[0] + self.state.joints[1]
        )


ENGINES: dict[str, type[BaseEngine]] = {
    "diff_drive_2w": DiffDrive2W,
    "omni_3w": Omni3W,
    "tricycle_3w": Tricycle3W,
    "ackermann_4w": Ackermann4W,
    "simple_arm": SimpleArm,
}


def create_engine(demo_id: str) -> BaseEngine:
    cls = ENGINES.get(demo_id, DiffDrive2W)
    return cls(demo_id)
