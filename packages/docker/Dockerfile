# Lappa ROS2 show-mode runtime (optional)
FROM ros:humble-ros-base

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    ros-humble-geometry-msgs \
    ros-humble-sensor-msgs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws
# Workspace mounted at runtime: /ws/src/<package>
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash", "-lc", "source /opt/ros/humble/setup.bash && echo 'Lappa ROS2 ready' && sleep infinity"]
