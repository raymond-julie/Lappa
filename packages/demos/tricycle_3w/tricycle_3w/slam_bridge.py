"""Export live ROS2 SLAM topics for the desktop IDE viewport."""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path


def _quaternion_yaw(z: float, w: float) -> float:
    return 2.0 * math.atan2(float(z), float(w))


def main() -> None:
    try:
        import rclpy
        from nav_msgs.msg import OccupancyGrid, Odometry
        from rclpy.node import Node
        from rclpy.qos import (
            DurabilityPolicy,
            QoSProfile,
            ReliabilityPolicy,
            qos_profile_sensor_data,
        )
        from sensor_msgs.msg import LaserScan
    except ImportError:
        print("[slam_bridge] rclpy is required; run this node inside ROS2 Docker")
        return

    class SlamBridgeNode(Node):
        def __init__(self) -> None:
            super().__init__("lappa_slam_bridge")
            self.declare_parameter(
                "snapshot_path",
                "/ws/src/tricycle_3w/.lappa_runtime/slam_snapshot.json",
            )
            self.declare_parameter("write_interval", 0.25)
            self.snapshot_path = Path(
                str(self.get_parameter("snapshot_path").value)
            )
            self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            self.map_snapshot: dict | None = None
            self.pose = {"x": 0.0, "y": 0.0, "theta": 0.0}
            self.twist = {"linear_x": 0.0, "angular_z": 0.0}
            self.scan: list[float] = []
            self.scan_frame = "laser"

            map_qos = QoSProfile(
                depth=1,
                reliability=ReliabilityPolicy.RELIABLE,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
            )
            self.create_subscription(OccupancyGrid, "map", self._on_map, map_qos)
            self.create_subscription(Odometry, "odom", self._on_odom, 10)
            self.create_subscription(
                LaserScan,
                "scan",
                self._on_scan,
                qos_profile_sensor_data,
            )
            interval = max(
                0.1,
                float(self.get_parameter("write_interval").value),
            )
            self.create_timer(interval, self._write_snapshot)
            self.get_logger().info(
                f"[slam_bridge] exporting /map to {self.snapshot_path}"
            )

        def _on_map(self, message: OccupancyGrid) -> None:
            width = int(message.info.width)
            height = int(message.info.height)
            cells: list[list[int]] = []
            occupied = 0
            free = 0
            for index, raw_value in enumerate(message.data):
                value = int(raw_value)
                if value < 0:
                    continue
                row, column = divmod(index, width)
                cells.append([column, row, value])
                if value >= 50:
                    occupied += 1
                else:
                    free += 1
            known = occupied + free
            total = max(1, width * height)
            orientation = message.info.origin.orientation
            self.map_snapshot = {
                "frame_id": message.header.frame_id or "map",
                "width": width,
                "height": height,
                "resolution": float(message.info.resolution),
                "origin": {
                    "x": float(message.info.origin.position.x),
                    "y": float(message.info.origin.position.y),
                    "yaw": _quaternion_yaw(orientation.z, orientation.w),
                },
                "known_cells": known,
                "occupied_cells": occupied,
                "free_cells": free,
                "coverage_percent": known / total * 100.0,
                "cells": cells,
            }

        def _on_odom(self, message: Odometry) -> None:
            orientation = message.pose.pose.orientation
            self.pose = {
                "x": float(message.pose.pose.position.x),
                "y": float(message.pose.pose.position.y),
                "theta": _quaternion_yaw(orientation.z, orientation.w),
            }
            self.twist = {
                "linear_x": float(message.twist.twist.linear.x),
                "angular_z": float(message.twist.twist.angular.z),
            }

        def _on_scan(self, message: LaserScan) -> None:
            self.scan = [float(value) for value in message.ranges]
            self.scan_frame = message.header.frame_id or "laser"

        def _write_snapshot(self) -> None:
            if self.map_snapshot is None:
                return
            snapshot = {
                "source": "slam_toolbox",
                "updated_at": time.time(),
                "map": self.map_snapshot,
                "pose": self.pose,
                "twist": self.twist,
                "scan": self.scan,
                "topics": {
                    "map": "/map",
                    "odom": "/odom",
                    "scan": "/scan",
                    "scan_frame": self.scan_frame,
                },
            }
            temporary = self.snapshot_path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(snapshot, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(temporary, self.snapshot_path)

    rclpy.init(args=sys.argv)
    node = SlamBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
