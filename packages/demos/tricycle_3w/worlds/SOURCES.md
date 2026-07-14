# Warehouse world source

`warehouse.pgm` and `warehouse.yaml` are sourced from Clearpath Robotics'
`clearpath_nav2_demos` repository:

https://github.com/clearpathrobotics/clearpath_nav2_demos/tree/jazzy/maps

The upstream files are distributed under the BSD 3-Clause License. The
license text is preserved in `LICENSE-BSD-3-CLAUSE.txt`.

Lappa uses this occupancy image only as simulation ground truth for collision
checks and synthetic LiDAR. The map displayed as live SLAM output is rebuilt
independently by ROS2 SLAM Toolbox from `/scan`, `/odom`, and TF.
