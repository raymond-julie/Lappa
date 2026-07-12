#!/usr/bin/env bash
set -e
source /opt/ros/humble/setup.bash
if [ -d /ws/src ]; then
  echo "[lappa] workspace sources present under /ws/src"
fi
exec "$@"
