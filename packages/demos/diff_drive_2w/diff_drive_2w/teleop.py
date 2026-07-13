"""ROS2 teleop + synthetic odom/scan for `diff_drive_2w`.

When run via `ros2 launch diff_drive_2w sim.launch.py` (Docker/colcon), this node
publishes /odom and /scan and subscribes to /cmd_vel.
Without rclpy (host without ROS2), falls back to a one-line message.
"""
from __future__ import annotations

import math
import sys


def main() -> None:
    try:
        import rclpy
        from geometry_msgs.msg import Twist
        from nav_msgs.msg import Odometry
        from rclpy.node import Node
        from sensor_msgs.msg import LaserScan
    except ImportError:
        print(
            "[diff_drive_2w] rclpy not available — use Lappa native sim offline, "
            "or Docker: lappa docker launch --demo diff_drive_2w"
        )
        return

    class TeleopNode(Node):
        def __init__(self) -> None:
            super().__init__("teleop")
            self.kind = "diff"
            self.x = 0.0
            self.y = 0.0
            self.th = 0.0
            self.cmd = Twist()
            self.create_subscription(Twist, "cmd_vel", self._on_cmd, 10)
            self.pub_odom = self.create_publisher(Odometry, "odom", 10)
            self.pub_scan = self.create_publisher(LaserScan, "scan", 10)
            self.dt = 0.05
            self.create_timer(self.dt, self._tick)
            self.get_logger().info(
                f"[diff_drive_2w] ROS2 node up · kind={self.kind} · /cmd_vel → /odom /scan"
            )

        def _on_cmd(self, msg: Twist) -> None:
            self.cmd = msg

        def _tick(self) -> None:
            vx = float(self.cmd.linear.x)
            vy = float(self.cmd.linear.y) if self.kind == "omni" else 0.0
            wz = float(self.cmd.angular.z)
            # simple unicycle / omni integrate in world frame
            c, s = math.cos(self.th), math.sin(self.th)
            self.x += (c * vx - s * vy) * self.dt
            self.y += (s * vx + c * vy) * self.dt
            self.th += wz * self.dt
            now = self.get_clock().now().to_msg()
            odom = Odometry()
            odom.header.stamp = now
            odom.header.frame_id = "odom"
            odom.child_frame_id = "base_link"
            odom.pose.pose.position.x = self.x
            odom.pose.pose.position.y = self.y
            odom.pose.pose.orientation.z = math.sin(self.th / 2.0)
            odom.pose.pose.orientation.w = math.cos(self.th / 2.0)
            odom.twist.twist.linear.x = vx
            odom.twist.twist.linear.y = vy
            odom.twist.twist.angular.z = wz
            self.pub_odom.publish(odom)
            scan = LaserScan()
            scan.header.stamp = now
            scan.header.frame_id = "laser"
            scan.angle_min = -math.pi
            scan.angle_max = math.pi
            n = 36
            scan.angle_increment = (2 * math.pi) / n
            scan.range_min = 0.05
            scan.range_max = 8.0
            # synthetic wall circle ~3m with slight motion
            base = 3.0 + 0.2 * math.sin(self.x + self.y)
            scan.ranges = [float(base + 0.05 * math.sin(i)) for i in range(n)]
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
