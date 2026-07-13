"""ROS2 node for `simple_arm` — synthetic joint motion + tip topic."""
from __future__ import annotations

import math
import sys


def main() -> None:
    try:
        import rclpy
        from geometry_msgs.msg import PointStamped
        from rclpy.node import Node
        from std_msgs.msg import Float64MultiArray
    except ImportError:
        print(
            "[simple_arm] rclpy not available — use Lappa native sim offline, "
            "or Docker: lappa docker launch --demo simple_arm"
        )
        return

    class ArmNode(Node):
        def __init__(self) -> None:
            super().__init__("teleop")
            self.j0 = 0.4
            self.j1 = -0.6
            self.t = 0.0
            self.pub_j = self.create_publisher(Float64MultiArray, "joint_states_array", 10)
            self.pub_tip = self.create_publisher(PointStamped, "tip", 10)
            self.create_timer(0.05, self._tick)
            self.get_logger().info("[simple_arm] ROS2 node up · /joint_states_array /tip")

        def _tick(self) -> None:
            self.t += 0.05
            self.j0 = 0.4 + 0.3 * math.sin(self.t)
            self.j1 = -0.6 + 0.2 * math.cos(self.t * 1.3)
            msg = Float64MultiArray()
            msg.data = [self.j0, self.j1]
            self.pub_j.publish(msg)
            # planar FK L1=0.5 L2=0.4
            x = 0.5 * math.cos(self.j0) + 0.4 * math.cos(self.j0 + self.j1)
            y = 0.5 * math.sin(self.j0) + 0.4 * math.sin(self.j0 + self.j1)
            tip = PointStamped()
            tip.header.stamp = self.get_clock().now().to_msg()
            tip.header.frame_id = "base_link"
            tip.point.x = x
            tip.point.y = y
            tip.point.z = 0.0
            self.pub_tip.publish(tip)

    rclpy.init(args=sys.argv)
    node = ArmNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
