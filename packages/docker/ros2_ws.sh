#!/usr/bin/env bash
# Lappa ROS2 workspace helper — source distro, colcon build package, ros2 launch.
# Usage (inside container):
#   /ros2_ws.sh build [pkg...]
#   /ros2_ws.sh launch <pkg> [launch_file]
#   /ros2_ws.sh status
#   /ros2_ws.sh stop
set -euo pipefail

WS="${LAPPA_WS:-/ws}"
DISTRO="${ROS_DISTRO:-humble}"
if [ -f /ws/ros2_distro.txt ]; then
  DISTRO="$(tr -d '[:space:]' < /ws/ros2_distro.txt || true)"
  DISTRO="${DISTRO:-humble}"
fi

source_ros() {
  if [ -f "/opt/ros/${DISTRO}/setup.bash" ]; then
    # shellcheck disable=SC1090
    source "/opt/ros/${DISTRO}/setup.bash"
  else
    echo "[lappa] ERROR: ROS2 distro not found at /opt/ros/${DISTRO}" >&2
    ls /opt/ros 2>/dev/null || true
    exit 2
  fi
  if [ -f "${WS}/install/setup.bash" ]; then
    # shellcheck disable=SC1091
    source "${WS}/install/setup.bash"
  fi
  export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}"
}

cmd_build() {
  source_ros
  mkdir -p "${WS}/src" "${WS}/build" "${WS}/install" "${WS}/log"
  cd "${WS}"
  if [ "$#" -eq 0 ]; then
    echo "[lappa] colcon build (all packages under /ws/src)"
    colcon build --symlink-install --event-handlers console_direct+
  else
    echo "[lappa] colcon build --packages-select $*"
    colcon build --symlink-install --packages-select "$@" --event-handlers console_direct+
  fi
  # shellcheck disable=SC1091
  source "${WS}/install/setup.bash"
  echo "[lappa] build ok · packages:"
  ros2 pkg list 2>/dev/null | head -40 || true
}

cmd_launch() {
  local pkg="${1:-}"
  local launch_file="${2:-sim.launch.py}"
  if [ -z "$pkg" ]; then
    echo "usage: $0 launch <package> [launch_file]" >&2
    exit 1
  fi
  source_ros
  # Ensure package is built as ament package
  if ! ros2 pkg prefix "$pkg" >/dev/null 2>&1; then
    echo "[lappa] package $pkg not installed — building…"
    cmd_build "$pkg"
    source_ros
  fi
  if ! ros2 pkg prefix "$pkg" >/dev/null 2>&1; then
    echo "[lappa] ERROR: ros2 does not see package '$pkg' after colcon build" >&2
    echo "[lappa] /ws/src contents:" >&2
    ls -la "${WS}/src" >&2 || true
    exit 3
  fi
  # Stop previous launch
  pkill -f "ros2 launch ${pkg}" 2>/dev/null || true
  pkill -f "sim.launch" 2>/dev/null || true
  sleep 0.5
  echo "[lappa] ros2 launch ${pkg} ${launch_file}  (ROS_DISTRO=${DISTRO})"
  nohup ros2 launch "$pkg" "$launch_file" > /tmp/lappa_ros2_launch.log 2>&1 &
  echo $! > /tmp/lappa_ros2_launch.pid
  sleep 2
  echo "[lappa] launch pid=$(cat /tmp/lappa_ros2_launch.pid 2>/dev/null || echo '?')"
  echo "[lappa] nodes:"
  ros2 node list 2>/dev/null || true
  echo "[lappa] topics:"
  ros2 topic list 2>/dev/null || true
  tail -n 30 /tmp/lappa_ros2_launch.log 2>/dev/null || true
}

cmd_status() {
  source_ros
  echo "ROS_DISTRO=${DISTRO}"
  echo "which ros2=$(command -v ros2 || echo missing)"
  ros2 --version 2>/dev/null || true
  echo "--- pkgs (lappa demos) ---"
  ros2 pkg list 2>/dev/null | grep -E 'diff_drive|omni|tricycle|ackermann|simple_arm' || echo "(none built yet)"
  echo "--- nodes ---"
  ros2 node list 2>/dev/null || true
  echo "--- topics ---"
  ros2 topic list 2>/dev/null || true
  if [ -f /tmp/lappa_ros2_launch.pid ]; then
    echo "launch_pid=$(cat /tmp/lappa_ros2_launch.pid)"
  fi
  if [ -f /tmp/lappa_ros2_launch.log ]; then
    echo "--- launch log (tail) ---"
    tail -n 20 /tmp/lappa_ros2_launch.log
  fi
}

cmd_stop() {
  pkill -f "ros2 launch" 2>/dev/null || true
  pkill -f "sim.launch" 2>/dev/null || true
  rm -f /tmp/lappa_ros2_launch.pid
  echo "[lappa] stopped ros2 launch processes"
}

case "${1:-}" in
  build) shift; cmd_build "$@" ;;
  launch) shift; cmd_launch "$@" ;;
  status) cmd_status ;;
  stop) cmd_stop ;;
  *)
    echo "usage: $0 {build|launch|status|stop} …" >&2
    exit 1
    ;;
esac
