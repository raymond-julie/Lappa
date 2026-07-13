#!/usr/bin/env bash
set -e
DISTRO="${ROS_DISTRO:-}"
if [ -z "$DISTRO" ] && [ -f /ws/ros2_distro.txt ]; then
  DISTRO="$(tr -d '[:space:]' < /ws/ros2_distro.txt || true)"
fi
DISTRO="${DISTRO:-humble}"
export ROS_DISTRO="$DISTRO"

if [ -f "/opt/ros/${DISTRO}/setup.bash" ]; then
  # shellcheck disable=SC1090
  source "/opt/ros/${DISTRO}/setup.bash"
  echo "[lappa] ROS2 ${DISTRO} loaded from /opt/ros/${DISTRO}"
elif [ -f /opt/ros/humble/setup.bash ]; then
  source /opt/ros/humble/setup.bash
  echo "[lappa] ROS2 humble fallback loaded"
else
  echo "[lappa] WARNING: no ROS2 setup.bash found under /opt/ros" >&2
  ls /opt/ros 2>/dev/null || true
fi

if [ -f /ws/install/setup.bash ]; then
  # shellcheck disable=SC1091
  source /ws/install/setup.bash
  echo "[lappa] overlay workspace /ws/install sourced"
fi

if [ -d /ws/src ]; then
  echo "[lappa] package sources at /ws/src (IDE live edit → colcon build → ros2 launch)"
  ls -1 /ws/src 2>/dev/null | head -20 || true
fi

exec "$@"
