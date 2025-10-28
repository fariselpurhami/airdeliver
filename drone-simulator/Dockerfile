# file: drone-simulator/Dockerfile
# Use official PX4 simulation image
FROM px4io/px4-dev-simulation-jammy:latest

# Set working directory (optional)
WORKDIR /px4

# The base image entrypoint usually handles starting SITL.
# We might need to override it or add arguments if specific setup is needed.
# For now, rely on the base image's default behavior.

# Expose MAVLink UDP port for companion connection
EXPOSE 14540/udp
# Expose Gazebo ports if needed for visualization (optional)
# EXPOSE 11345

# Default command (often starts Gazebo + SITL)
# Check the base image documentation for exact startup command if customization is needed.
# Example: CMD ["make", "px4_sitl", "gazebo"]
