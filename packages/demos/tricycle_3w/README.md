# tricycle_3w

Three-wheel base with one steered front wheel and a fixed rear axle.

Open the package in Lappa IDE and choose **Run** in the Simulation panel.
Click the viewport, then drive with:

| Control | Action |
| --- | --- |
| `W` / `Up` | Forward |
| `S` / `Down` | Reverse |
| `A` / `Left` | Steer left |
| `D` / `Right` | Steer right |
| `Space` | Brake |

The same controls publish `geometry_msgs/msg/Twist` to `/cmd_vel` when this
demo is active in Docker. `angular.z` is the front steering angle in radians.
Enable **Auto map** to follow mapping waypoints automatically. The node emits
180-ray `/scan` data and TF for `odom -> base_link -> laser`; the launch file
starts ROS2 SLAM Toolbox in mapping mode and publishes the occupancy grid on
`/map`. Keyboard input temporarily overrides autonomous exploration.

The native simulator works without ROS2. For a real ROS2 node, select Humble
or another supported distro in **ROS2 / Docker**, start the runtime, and launch
`tricycle_3w`.
