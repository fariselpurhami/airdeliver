# docker/px4-sitl/Dockerfile

FROM px4io/px4-dev-simulation-focal:2022-08-12 AS builder

RUN apt-get update && apt-get install -y \
    net-tools \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install kconfiglib

WORKDIR /root
RUN git clone https://github.com/PX4/PX4-Autopilot.git --recursive --depth 1 --branch v1.14.0 /root/PX4-Autopilot

WORKDIR /root/PX4-Autopilot
RUN git submodule sync --recursive
RUN git submodule update --init --recursive --force

RUN HEADLESS=1 make px4_sitl_default

FROM px4io/px4-dev-simulation-focal:2022-08-12 AS final

RUN apt-get update && apt-get install -y net-tools && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/PX4-Autopilot /root/PX4-Autopilot
COPY entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh

WORKDIR /root/PX4-Autopilot

ENTRYPOINT ["/root/entrypoint.sh"]
CMD ["/bin/bash", "-c", "HEADLESS=1 make px4_sitl gazebo_iris"]
