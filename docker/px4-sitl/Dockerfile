# docker/px4-sitl/Dockerfile - Golden Enterprise Edition
# Validated by Chief Software Architect
# Fixes: GID Conflict + 'awk' package name error

FROM px4io/px4-dev-simulation-focal:2022-08-12 AS builder
WORKDIR /root/PX4-Autopilot
# Using shallow clone to speed up CI/CD build time
RUN git clone --recursive --depth 1 --branch v1.14.0 https://github.com/PX4/PX4-Autopilot.git .
# Run build in headless mode to reduce resource consumption
RUN DONT_RUN=1 HEADLESS=1 make px4_sitl_default

FROM px4io/px4-dev-simulation-focal:2022-08-12 AS final
ENV DEBIAN_FRONTEND=noninteractive \
    PX4_HOME_LAT=30.0444 \
    PX4_HOME_LON=31.2357 \
    PX4_HOME_ALT=100 \
    PX4_SIM_SPEED_FACTOR=1 \
    PX4_SIM_MODEL=gazebo-classic_iris

# Standardization of User ID across the platform
ARG APP_USER=px4
ARG APP_UID=1001
ARG APP_GID=1001

# GOLDEN FIX: Recursive cleanup logic
# 1. Identify conflict. 2. Remove conflict. 3. Create clean user/group.
# Note: 'awk' is pre-installed in this base image, so we use it for logic but don't re-install it.
RUN existing_group=$(getent group $APP_GID | cut -d: -f1) && \
    if [ -n "$existing_group" ]; then \
        linked_user=$(getent passwd | awk -F: -v gid=$APP_GID '$4 == gid {print $1}'); \
        if [ -n "$linked_user" ]; then \
            echo "Removing conflicting user: $linked_user"; \
            userdel -r -f $linked_user; \
        fi; \
        if getent group $existing_group; then \
            groupdel $existing_group; \
        fi; \
    fi && \
    groupadd -g $APP_GID $APP_USER && \
    useradd -u $APP_UID -g $APP_GID -d /home/$APP_USER -s /bin/bash -m $APP_USER && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    iproute2 \
    dnsutils \
    net-tools && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/px4-source-cache

# ✅ التعديل الجوهري: نسخ الملفات إلى الكاش لكي يجدها الـ entrypoint
COPY --from=builder /root/PX4-Autopilot /opt/px4-source-cache
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /root/PX4-Autopilot

# Standard PX4 Ports
EXPOSE 14540 14556 14557 18570

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["make", "px4_sitl", "gazebo-classic_iris"]
