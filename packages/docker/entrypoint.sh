#!/usr/bin/env bash
set -e
DISTRO="${ROS_DISTRO:-}"
if [ -z "$DISTRO" ] && [ -f /ws/ros2_distro.txt ]; then
  DISTRO="$(tr -d '[:space:]' < /ws/ros2_distro.txt)"
fi
DISTRO="${DISTRO:-humble}"
if [ -f "/opt/ros/${DISTRO}/setup.bash" ]; then
  # shellcheck disable=SC1090
  source "/opt/ros/${DISTRO}/setup.bash"
elif [ -f /opt/ros/humble/setup.bash ]; then
  source /opt/ros/humble/setup.bash
fi
if [ -d /ws/src ]; then
  echo "[lappa] workspace sources mounted at /ws/src (IDE live edit)"
  ls -1 /ws/src 2>/dev/null | head -20 || true
fi
exec "$@"
