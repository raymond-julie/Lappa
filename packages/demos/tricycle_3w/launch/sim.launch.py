from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    params = str(
        Path(get_package_share_directory("tricycle_3w"))
        / "config"
        / "params.yaml"
    )
    robot_description = Command(
        [
            FindExecutable(name="xacro"),
            " ",
            PathJoinSubstitution(
                [
                    FindPackageShare("tricycle_3w"),
                    "urdf",
                    "robot.urdf.xacro",
                ]
            ),
        ]
    )
    return LaunchDescription(
        [
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                output="screen",
                parameters=[
                    {
                        "robot_description": ParameterValue(
                            robot_description,
                            value_type=str,
                        )
                    }
                ],
            ),
            Node(
                package="tricycle_3w",
                executable="teleop",
                name="teleop",
                output="screen",
                parameters=[params],
            ),
            Node(
                package="slam_toolbox",
                executable="async_slam_toolbox_node",
                name="slam_toolbox",
                output="screen",
                parameters=[params],
            ),
            Node(
                package="tricycle_3w",
                executable="slam_bridge",
                name="lappa_slam_bridge",
                output="screen",
                parameters=[params],
            ),
        ]
    )
