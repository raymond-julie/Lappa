DIAGONAL_DISTANCE_SQRT = DIAGONAL_DISTANCE_SQRTDIAGONAL_DISTANCE = 2.0STEP_SIZE_SEGMENT = 0.12STEP_SIZE = 0.04MAX_EXPANSIONS = 100_000MAX_PIXEL_VALUE = 255DEFAULTSEGMENT_RADIUS = 0.24DEFAULT_RESOLUTION = 0.05FREE_THRESHOLD = 0.196SELF_CLEARANCE_RADIUS = 0.18"""ROS2 command, odometry, and scan node for the tricycle demo.

The /cmd_vel angular.z field is interpreted as the front steering angle in
radians. The node publishes the resulting yaw rate in /odom.
"""

from __future__ import annotations

import heapq
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class OccupancyWorld:
    """PGM-backed ground-truth world used for collision and lidar simulation."""

    width: int
    height: int
    resolution: float
    origin_x: float
    origin_y: float
    free_pixel_min: int
    pixels: bytes
    source: str
    _clear_cache: dict[tuple[int, int, int], bool] = field(
        default_factory=dict,
        repr=False,
    )

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> OccupancyWorld:
        metadata: dict[str, str] = {}
        for raw_line in yaml_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()

        image_path = yaml_path.parent / metadata["image"]
        width, height, pixels = _read_pgm(image_path)
        origin = json.loads(metadata.get("origin", "[0, 0, 0]"))
        resolution = float(metadata.get("resolution", "DEFAULT_RESOLUTION"))
        free_threshold = float(metadata.get("free_thresh", "FREE_THRESHOLD"))
        return cls(
            width=width,
            height=height,
            resolution=resolution,
            origin_x=float(origin[0]),
            origin_y=float(origin[1]),
            free_pixel_min=round(MAX_PIXEL_VALUE * (1.0 - free_threshold)),
            pixels=pixels,
            source=str(yaml_path),
        )

    def world_to_image(self, x: float, y: float) -> tuple[int, int]:
        column = math.floor((x - self.origin_x) / self.resolution)
        map_row = math.floor((y - self.origin_y) / self.resolution)
        return column, self.height - 1 - map_row

    def image_to_world(self, column: int, row: int) -> tuple[float, float]:
        x = self.origin_x + (column + 0.5) * self.resolution
        y = self.origin_y + (self.height - row - 0.5) * self.resolution
        return x, y

    def is_blocked(self, x: float, y: float) -> bool:
        column, row = self.world_to_image(x, y)
        if not (0 <= column < self.width and 0 <= row < self.height):
            return True
        return self.pixels[row * self.width + column] < self.free_pixel_min

    def is_clear(self, x: float, y: float, radius: float = DEFAULTsegment_RADIUS) -> bool:
        center_column, center_row = self.world_to_image(x, y)
        cell_radius = max(1, math.ceil(radius / self.resolution))
        radius_squared = (radius / self.resolution) ** 2
        for row_offset in range(-cell_radius, cell_radius + 1):
            for column_offset in range(-cell_radius, cell_radius + 1):
                if column_offset**2 + row_offset**2 > radius_squared:
                    continue
                column = center_column + column_offset
                row = center_row + row_offset
                if not (0 <= column < self.width and 0 <= row < self.height):
                    return False
                if self.pixels[row * self.width + column] < self.free_pixel_min:
                    return False
        return True

    def ray_distance(
        self,
        x: float,
        y: float,
        angle: float,
        max_range: float,
    ) -> float:
        step = max(self.resolution, STEP_SIZE)
        distance = 0.1
        while distance <= max_range:
            px = x + math.cos(angle) * distance
            py = y + math.sin(angle) * distance
            if self.is_blocked(px, py):
                return distance
            distance += step
        return max_range

    def segment_is_clear(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        radius: float = 0.24,
    ) -> bool:
        distance = math.dist(start, end)
        steps = max(1, math.ceil(distance / STEP_SIZE SEGMENT))
        for index in range(steps + 1):
            ratio = index / steps
            x = start[0] + (end[0] - start[0]) * ratio
            y = start[1] + (end[1] - start[1]) * ratio
            if not self.is_clear(x, y, radius):
                return False
        return True

    def plan_path(
        self,
        start: tuple[float, float],
        goal: tuple[float, float],
        radius: float = 0.24,
    ) -> list[tuple[float, float]]:
        """Plan a clearance-aware path on a SELF_CLEARANCE_RADIUS m lattice."""
        stride = max(1, round(0.18 / self.resolution))
        grid_width = math.ceil(self.width / stride)
        grid_height = math.ceil(self.height / stride)

        def world_to_grid(point: tuple[float, float]) -> tuple[int, int]:
            column, row = self.world_to_image(*point)
            return column // stride, row // stride

        def grid_to_world(node: tuple[int, int]) -> tuple[float, float]:
            column = min(self.width - 1, node[0] * stride + stride // 2)
            row = min(self.height - 1, node[1] * stride + stride // 2)
            return self.image_to_world(column, row)

        radius_key = round(radius / self.resolution)

        def navigable(node: tuple[int, int]) -> bool:
            column, row = node
            if not (0 <= column < grid_width and 0 <= row < grid_height):
                return False
            cache_key = (column, row, radius_key)
            cached = self._clear_cache.get(cache_key)
            if cached is None:
                cached = self.is_clear(*grid_to_world(node), radius)
                self._clear_cache[cache_key] = cached
            return cached

        def nearest_navigable(node: tuple[int, int]) -> tuple[int, int] | None:
            if navigable(node):
                return node
            for search_radius in range(1, 24):
                candidates: set[tuple[int, int]] = set()
                for offset in range(-search_radius, search_radius + 1):
                    candidates.add((node[0] + offset, node[1] - search_radius))
                    candidates.add((node[0] + offset, node[1] + search_radius))
                    candidates.add((node[0] - search_radius, node[1] + offset))
                    candidates.add((node[0] + search_radius, node[1] + offset))
                for candidate in candidates:
                    if navigable(candidate):
                        return candidate
            return None

        start_node = nearest_navigable(world_to_grid(start))
        goal_node = nearest_navigable(world_to_grid(goal))
        if start_node is None or goal_node is None:
            return []

        frontier: list[tuple[float, tuple[int, int]]] = [(0.0, start_node)]
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        costs = {start_node: 0.0}
        expansions = 0
        neighbors = [
            (-1, -1, math.sqrt(DIAGONAL_DISTANCE)),
            (0, -1, 1.0),
            (1, -1, math.DIAGONAL_DISTANCE_SQRT),
            (-1, 0, 1.0),
            (1, 0, 1.0),
            (-1, 1, math.sqrt(2.0)),
            (0, 1, 1.0),
            (1, 1, math.sqrt(2.0)),
        ]
        while frontier and expansions < MAX_EXPANSIONS:
            _, current = heapq.heappop(frontier)
            expansions += 1
            if current == goal_node:
                break
            current_cost = costs[current]
            for dx, dy, step_cost in neighbors:
                candidate = current[0] + dx, current[1] + dy
                if not navigable(candidate):
                    continue
                new_cost = current_cost + step_cost
                if new_cost >= costs.get(candidate, math.inf):
                    continue
                costs[candidate] = new_cost
                came_from[candidate] = current
                heuristic = math.hypot(
                    goal_node[0] - candidate[0],
                    goal_node[1] - candidate[1],
                )
                heapq.heappush(frontier, (new_cost + heuristic, candidate))

        if goal_node not in costs:
            return []
        nodes = [goal_node]
        while nodes[-1] != start_node:
            nodes.append(came_from[nodes[-1]])
        nodes.reverse()
        points = [start, *(grid_to_world(node) for node in nodes[1:])]
        if self.is_clear(*goal, radius):
            points.append(goal)

        simplified = [points[0]]
        anchor = 0
        while anchor < len(points) - 1:
            candidate = len(points) - 1
            while candidate > anchor + 1 and not self.segment_is_clear(
                points[anchor],
                points[candidate],
                radius,
            ):
                candidate -= 1
            simplified.append(points[candidate])
            anchor = candidate
        return simplified[1:]


def _read_pgm(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    index = 0

    def token() -> bytes:
        nonlocal index
        while index < len(data):
            if data[index] == ord("#"):
                index = data.find(b"\n", index)
                if index < 0:
                    raise ValueError(f"invalid PGM comment in {path}")
            elif data[index] in b" \t\r\n":
                index += 1
            else:
                break
        start = index
        while index < len(data) and data[index] not in b" \t\r\n":
            index += 1
        return data[start:index]

    magic = token()
    if magic != b"P5":
        raise ValueError(f"unsupported PGM format {magic!r} in {path}")
    width = int(token())
    height = int(token())
    max_value = int(token())
    if not 0 < max_value <= 255:
        raise ValueError(f"unsupported PGM max value {max_value}")
    if data[index : index + 2] == b"\r\n":
        index += 2
    elif index < len(data) and data[index] in b" \t\r\n":
        index += 1
    pixels = data[index : index + width * height]
    if len(pixels) != width * height:
        raise ValueError(f"truncated PGM data in {path}")
    return width, height, pixels


def load_occupancy_world(name: str = "warehouse") -> OccupancyWorld | None:
    candidates: list[Path] = []
    try:
        from ament_index_python.packages import get_package_share_directory

        candidates.append(
            Path(get_package_share_directory("tricycle_3w"))
            / "worlds"
            / f"{name}.yaml"
        )
    except (ImportError, LookupError):
        pass
    candidates.append(Path(__file__).resolve().parents[1] / "worlds" / f"{name}.yaml")
    for candidate in candidates:
        if candidate.is_file():
            return OccupancyWorld.from_yaml(candidate)
    return None


ROOM_OBSTACLES = [
    (0.0, 4.0, 4.08, 0.08),
    (0.0, -4.0, 4.08, 0.08),
    (4.0, 0.0, 0.08, 4.08),
    (-4.0, 0.0, 0.08, 4.08),
    (2.0, 0.5, 0.35, 0.35),
    (-1.5, 1.2, 0.4, 0.25),
    (0.8, -1.8, 0.3, 0.5),
    (1.2, 1.5, 0.25, 0.25),
    (-0.2, 2.4, 1.2, 0.15),
    (2.6, -0.8, 0.15, 0.9),
    (0.0, -2.2, 0.2, 0.2),
    (-2.4, -0.5, 0.35, 0.35),
    (1.8, -1.6, 0.3, 0.2),
    (-0.9, 1.8, 0.15, 0.15),
    (0.5, 0.9, 0.28, 0.28),
    (-1.8, -1.5, 0.35, 0.2),
    (2.2, 1.0, 0.4, 0.15),
    (1.5, 2.0, 0.3, 0.3),
]
AUTO_WAYPOINTS = [
    (2.5, 0.0),
    (2.5, 2.5),
    (0.0, 2.8),
    (-2.6, 2.5),
    (-2.6, -2.5),
    (0.0, -2.8),
    (2.5, -2.5),
]
WAREHOUSE_WAYPOINTS = [
    (10.0, 2.0),
    (10.0, -10.0),
    (10.0, -20.0),
    (4.0, -20.0),
    (4.0, -7.0),
    (-3.5, -7.0),
    (-3.5, -20.0),
    (-10.5, -20.0),
    (-10.5, -7.0),
    (-10.0, 1.0),
    (-9.5, 7.0),
    (10.0, 7.0),
    (10.0, 14.0),
    (0.0, 14.0),
    (-9.5, 14.0),
    (-8.0, 21.0),
    (0.0, 21.0),
    (10.0, 21.0),
]


def _wrap(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def _ray_hit_aabb(
    ox: float,
    oy: float,
    dx: float,
    dy: float,
    obstacle: tuple[float, float, float, float],
    max_range: float,
) -> float | None:
    cx, cy, half_width, half_height = obstacle
    inverse_x = 1e9 if abs(dx) < 1e-9 else 1.0 / dx
    inverse_y = 1e9 if abs(dy) < 1e-9 else 1.0 / dy
    tx1 = (cx - half_width - ox) * inverse_x
    tx2 = (cx + half_width - ox) * inverse_x
    ty1 = (cy - half_height - oy) * inverse_y
    ty2 = (cy + half_height - oy) * inverse_y
    near = max(min(tx1, tx2), min(ty1, ty2))
    far = min(max(tx1, tx2), max(ty1, ty2))
    if far < 0 or near > far:
        return None
    distance = near if near >= 0 else far
    return distance if 0.1 <= distance <= max_range else None


def _scan_ranges(
    x: float,
    y: float,
    theta: float,
    rays: int,
    max_range: float,
    world: OccupancyWorld | None = None,
) -> list[float]:
    ranges: list[float] = []
    for index in range(rays):
        angle = theta - math.pi + (2 * math.pi * index / rays)
        if world is not None:
            ranges.append(world.ray_distance(x, y, angle, max_range))
            continue
        dx, dy = math.cos(angle), math.sin(angle)
        hit = max_range
        for obstacle in ROOM_OBSTACLES:
            distance = _ray_hit_aabb(x, y, dx, dy, obstacle, max_range)
            if distance is not None:
                hit = min(hit, distance)
        ranges.append(float(hit))
    return ranges


def _pose_is_clear(
    x: float,
    y: float,
    radius: float = 0.22,
    world: OccupancyWorld | None = None,
) -> bool:
    if world is not None:
        return world.is_clear(x, y, radius)
    for cx, cy, half_width, half_height in ROOM_OBSTACLES:
        nearest_x = max(cx - half_width, min(x, cx + half_width))
        nearest_y = max(cy - half_height, min(y, cy + half_height))
        if (x - nearest_x) ** 2 + (y - nearest_y) ** 2 < radius**2:
            return False
    return True


def main() -> None:
    try:
        import rclpy
        from geometry_msgs.msg import TransformStamped, Twist
        from nav_msgs.msg import Odometry
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import JointState, LaserScan
        from std_msgs.msg import Bool
        from tf2_ros import TransformBroadcaster
    except ImportError:
        print(
            "[tricycle_3w] rclpy not available; use Lappa native sim offline, "
            "or Docker: lappa docker launch --demo tricycle_3w"
        )
        return

    class TeleopNode(Node):
        def __init__(self) -> None:
            super().__init__("teleop")
            self.x = 0.0
            self.y = 0.0
            self.th = 0.0
            self.cmd = Twist()
            self.declare_parameter("wheelbase", 0.35)
            self.declare_parameter("max_linear", 1.0)
            self.declare_parameter("max_steering", 0.75)
            self.declare_parameter("command_timeout", 6.0)
            self.declare_parameter("manual_override_timeout", 3.0)
            self.declare_parameter("lidar_rays", 180)
            self.declare_parameter("lidar_range", 8.0)
            self.declare_parameter("laser_offset", 0.18)
            self.declare_parameter("auto_speed", 0.34)
            self.declare_parameter("world_map", "warehouse")
            self.declare_parameter("initial_x", 0.0)
            self.declare_parameter("initial_y", 0.0)
            self.declare_parameter("initial_yaw", 0.0)
            self.wheelbase = max(
                0.01, float(self.get_parameter("wheelbase").value)
            )
            self.max_linear = abs(
                float(self.get_parameter("max_linear").value)
            )
            self.max_steering = abs(
                float(self.get_parameter("max_steering").value)
            )
            self.command_timeout = max(
                0.1, float(self.get_parameter("command_timeout").value)
            )
            self.manual_override_timeout = max(
                0.1,
                float(self.get_parameter("manual_override_timeout").value),
            )
            self.lidar_rays = max(36, int(self.get_parameter("lidar_rays").value))
            self.lidar_range = max(
                1.0, float(self.get_parameter("lidar_range").value)
            )
            self.laser_offset = float(self.get_parameter("laser_offset").value)
            self.auto_speed = max(
                0.05, float(self.get_parameter("auto_speed").value)
            )
            world_name = str(self.get_parameter("world_map").value)
            self.world = load_occupancy_world(world_name)
            self.x = float(self.get_parameter("initial_x").value)
            self.y = float(self.get_parameter("initial_y").value)
            self.th = float(self.get_parameter("initial_yaw").value)
            if self.world is not None and not self.world.is_clear(
                self.x,
                self.y,
                0.24,
            ):
                raise RuntimeError(
                    f"initial pose ({self.x:.2f}, {self.y:.2f}) is blocked "
                    f"in {self.world.source}"
                )
            self.waypoints = (
                WAREHOUSE_WAYPOINTS if self.world is not None else AUTO_WAYPOINTS
            )
            self.last_command_at = time.monotonic()
            self.auto_explore = False
            self.auto_waypoint = 0
            self.auto_path: list[tuple[float, float]] = []
            self.auto_waypoint_started_at = time.monotonic()
            self.blocked = False
            self.front_wheel_position = 0.0
            self.rear_wheel_position = 0.0
            self.avoid_reverse_until = 0.0
            self.avoid_turn_until = 0.0
            self.avoid_direction = 1.0
            self.last_motion_vx = 0.0
            self.create_subscription(Twist, "cmd_vel", self._on_cmd, 10)
            self.create_subscription(
                Bool,
                "lappa/auto_explore",
                self._on_auto_explore,
                10,
            )
            self.pub_odom = self.create_publisher(Odometry, "odom", 10)
            self.pub_scan = self.create_publisher(
                LaserScan,
                "scan",
                qos_profile_sensor_data,
            )
            self.pub_joint_states = self.create_publisher(
                JointState,
                "joint_states",
                10,
            )
            self.tf_broadcaster = TransformBroadcaster(self)
            self.dt = 0.05
            self.create_timer(self.dt, self._tick)
            self.get_logger().info(
                "[tricycle_3w] ready: /cmd_vel + auto explore -> "
                "TF /odom /scan /joint_states "
                f"({self.lidar_rays}-ray lidar, wheelbase={self.wheelbase:.2f} m)"
            )
            if self.world is not None:
                self.get_logger().info(
                    "[tricycle_3w] world: "
                    f"{Path(self.world.source).name} "
                    f"{self.world.width}x{self.world.height} "
                    f"@ {self.world.resolution:.3f} m/cell"
                )
            else:
                self.get_logger().warn(
                    f"[tricycle_3w] world '{world_name}' not found; "
                    "using the built-in obstacle room"
                )

        def _on_cmd(self, msg: Twist) -> None:
            self.cmd = msg
            self.last_command_at = time.monotonic()

        def _on_auto_explore(self, msg: Bool) -> None:
            self.auto_explore = bool(msg.data)
            if self.auto_explore:
                self.auto_waypoint = 0
                self.auto_path.clear()
                self.auto_waypoint_started_at = time.monotonic()
                self.avoid_reverse_until = 0.0
                self.avoid_turn_until = 0.0
            state = "enabled" if self.auto_explore else "disabled"
            self.get_logger().info(f"[tricycle_3w] auto exploration {state}")

        def _auto_command(self) -> tuple[float, float]:
            now = time.monotonic()
            laser_x = self.x + math.cos(self.th) * self.laser_offset
            laser_y = self.y + math.sin(self.th) * self.laser_offset
            ranges = _scan_ranges(
                laser_x,
                laser_y,
                self.th,
                self.lidar_rays,
                self.lidar_range,
                self.world,
            )
            center = self.lidar_rays // 2
            sector_width = max(3, self.lidar_rays // 36)

            def sector(index: int) -> list[float]:
                return [
                    ranges[(index + offset) % self.lidar_rays]
                    for offset in range(-sector_width, sector_width + 1)
                ]

            corridor_clearance = []
            for index, distance in enumerate(ranges):
                angle = (index - center) / self.lidar_rays * math.tau
                if (
                    abs(angle) <= math.pi / 3
                    and abs(distance * math.sin(angle)) <= 0.36
                ):
                    corridor_clearance.append(distance * math.cos(angle))
            front = min(corridor_clearance, default=min(ranges))
            left = sum(sector(center + self.lidar_rays // 8))
            right = sum(sector(center - self.lidar_rays // 8))
            if self.blocked and self.last_motion_vx < -0.01:
                self.avoid_direction = 1.0 if left >= right else -1.0
                self.avoid_reverse_until = now
                self.avoid_turn_until = now + 2.2
                return self._safe_auto_command(
                    0.16,
                    self.avoid_direction * 0.72,
                )
            should_recover = self.blocked and now >= self.avoid_reverse_until
            if should_recover:
                self.avoid_direction = 1.0 if left >= right else -1.0
                self.avoid_reverse_until = now + 0.8
                self.avoid_turn_until = now + 2.0
            elif front < 0.85 and now >= self.avoid_turn_until:
                self.avoid_direction = 1.0 if left >= right else -1.0
                self.avoid_reverse_until = now
                self.avoid_turn_until = now + 1.6
            if now < self.avoid_reverse_until:
                return self._safe_auto_command(-0.20, 0.0)
            if now < self.avoid_turn_until:
                return self._safe_auto_command(
                    0.18,
                    self.avoid_direction * 0.72,
                )
            if front < 1.2:
                direction = 1.0 if left >= right else -1.0
                return self._safe_auto_command(0.14, direction * 0.68)

            target_x, target_y = self.waypoints[self.auto_waypoint]
            dx, dy = target_x - self.x, target_y - self.y
            if (
                math.hypot(dx, dy) < 0.35
                or now - self.auto_waypoint_started_at > 55.0
            ):
                self.auto_waypoint = (self.auto_waypoint + 1) % len(
                    self.waypoints
                )
                self.auto_path.clear()
                self.auto_waypoint_started_at = now
                target_x, target_y = self.waypoints[self.auto_waypoint]
                dx, dy = target_x - self.x, target_y - self.y
            if not self.auto_path:
                if self.world is not None:
                    self.auto_path = self.world.plan_path(
                        (self.x, self.y),
                        (target_x, target_y),
                        radius=0.27,
                    )
                else:
                    self.auto_path = [(target_x, target_y)]
                self.get_logger().info(
                    f"[tricycle_3w] exploration target {self.auto_waypoint + 1}/"
                    f"{len(self.waypoints)}: ({target_x:.1f}, {target_y:.1f}), "
                    f"path segments={len(self.auto_path)}"
                )
            while self.auto_path and math.dist(
                (self.x, self.y),
                self.auto_path[0],
            ) < 0.30:
                self.auto_path.pop(0)
            if self.auto_path:
                target_x, target_y = self.auto_path[0]
                dx, dy = target_x - self.x, target_y - self.y
            error = _wrap(math.atan2(dy, dx) - self.th)
            steering = max(
                -self.max_steering,
                min(self.max_steering, error * 1.25),
            )
            speed = self.auto_speed if abs(error) < 0.85 else self.auto_speed * 0.45
            return self._safe_auto_command(speed, steering)

        def _safe_auto_command(
            self,
            speed: float,
            steering: float,
        ) -> tuple[float, float]:
            direction = 1.0 if steering >= 0 else -1.0
            candidates = [
                (speed, steering),
                (0.13, direction * 0.72),
                (0.13, -direction * 0.72),
                (-0.16, 0.0),
            ]
            for candidate in candidates:
                if self._motion_is_clear(*candidate):
                    return candidate
            return 0.0, 0.0

        def _motion_is_clear(self, speed: float, steering: float) -> bool:
            x, y, theta = self.x, self.y, self.th
            for _ in range(8):
                x += math.cos(theta) * speed * 0.1
                y += math.sin(theta) * speed * 0.1
                theta += (speed / self.wheelbase) * math.tan(steering) * 0.1
                if not _pose_is_clear(
                    x,
                    y,
                    radius=0.24,
                    world=self.world,
                ):
                    return False
            return True

        def _active_command(self) -> tuple[float, float]:
            command_age = time.monotonic() - self.last_command_at
            command_nonzero = (
                abs(float(self.cmd.linear.x)) > 1e-4
                or abs(float(self.cmd.angular.z)) > 1e-4
            )
            manual_override = (
                command_nonzero and command_age <= self.manual_override_timeout
            )
            if self.auto_explore and not manual_override:
                return self._auto_command()
            if command_age > self.command_timeout:
                return 0.0, 0.0
            vx = max(
                -self.max_linear,
                min(self.max_linear, float(self.cmd.linear.x)),
            )
            steering = max(
                -self.max_steering,
                min(self.max_steering, float(self.cmd.angular.z)),
            )
            return vx, steering

        def _tick(self) -> None:
            vx, steering = self._active_command()
            self.last_motion_vx = vx
            yaw_rate = (vx / self.wheelbase) * math.tan(steering)
            next_x = self.x + math.cos(self.th) * vx * self.dt
            next_y = self.y + math.sin(self.th) * vx * self.dt
            next_theta = _wrap(self.th + yaw_rate * self.dt)
            was_blocked = self.blocked
            if _pose_is_clear(next_x, next_y, world=self.world):
                self.x = next_x
                self.y = next_y
                self.th = next_theta
                self.blocked = False
            else:
                self.blocked = True
                vx = 0.0
                yaw_rate = 0.0
            if self.blocked and not was_blocked:
                self.get_logger().warn(
                    "[tricycle_3w] footprint blocked; obstacle avoidance engaged"
                )

            now = self.get_clock().now().to_msg()
            odom = Odometry()
            odom.header.stamp = now
            odom.header.frame_id = "odom"
            odom.child_frame_id = "base_footprint"
            odom.pose.pose.position.x = self.x
            odom.pose.pose.position.y = self.y
            odom.pose.pose.orientation.z = math.sin(self.th / 2.0)
            odom.pose.pose.orientation.w = math.cos(self.th / 2.0)
            odom.twist.twist.linear.x = vx
            odom.twist.twist.angular.z = yaw_rate
            self.pub_odom.publish(odom)

            transform = TransformStamped()
            transform.header.stamp = now
            transform.header.frame_id = "odom"
            transform.child_frame_id = "base_footprint"
            transform.transform.translation.x = self.x
            transform.transform.translation.y = self.y
            transform.transform.rotation.z = math.sin(self.th / 2.0)
            transform.transform.rotation.w = math.cos(self.th / 2.0)
            self.tf_broadcaster.sendTransform(transform)

            self.front_wheel_position -= vx / 0.085 * self.dt
            self.rear_wheel_position -= vx / 0.10 * self.dt
            joints = JointState()
            joints.header.stamp = now
            joints.name = [
                "steering_joint",
                "front_wheel_joint",
                "rear_left_wheel_joint",
                "rear_right_wheel_joint",
            ]
            joints.position = [
                steering,
                self.front_wheel_position,
                self.rear_wheel_position,
                self.rear_wheel_position,
            ]
            self.pub_joint_states.publish(joints)

            scan = LaserScan()
            scan.header.stamp = now
            scan.header.frame_id = "laser"
            scan.angle_min = -math.pi
            scan.angle_increment = (2 * math.pi) / self.lidar_rays
            scan.angle_max = scan.angle_min + scan.angle_increment * (
                self.lidar_rays - 1
            )
            scan.scan_time = self.dt
            scan.time_increment = self.dt / self.lidar_rays
            scan.range_min = 0.1
            scan.range_max = self.lidar_range
            laser_x = self.x + math.cos(self.th) * self.laser_offset
            laser_y = self.y + math.sin(self.th) * self.laser_offset
            scan.ranges = _scan_ranges(
                laser_x,
                laser_y,
                self.th,
                self.lidar_rays,
                self.lidar_range,
                self.world,
            )
            self.pub_scan.publish(scan)

    rclpy.init(args=sys.argv)
    node = TeleopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
