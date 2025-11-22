#docker/px4-sitl/Dockerfile

FROM px4io/px4-dev-simulation-focal:2022-08-12 AS builder

WORKDIR /root/PX4-Autopilot

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/PX4/PX4-Autopilot.git --recursive --depth 1 --branch v1.14.0 .

RUN DONT_RUN=1 HEADLESS=1 make px4_sitl_default

FROM px4io/px4-dev-simulation-focal:2022-08-12 AS final

ENV DEBIAN_FRONTEND=noninteractive \
    PX4_HOME_LAT=30.0444 \
    PX4_HOME_LON=31.2357 \
    PX4_HOME_ALT=100 \
    PX4_SIM_SPEED_FACTOR=1 \
    PX4_SIM_MODEL=gazebo-classic_iris

WORKDIR /root/PX4-Autopilot

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iproute2 \
    dnsutils \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/PX4-Autopilot /opt/px4-source-cache
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 14540 14556 14557 18570

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["make", "px4_sitl", "gazebo-classic_iris"]
