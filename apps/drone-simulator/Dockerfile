# apps/drone-simulator/Dockerfile

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PX4_SIM_SPEED_FACTOR=1

RUN apt-get update && apt-get install -y \
    git \
    wget \
    cmake \
    build-essential \
    ninja-build \
    python3-pip \
    python3-jinja2 \
    python3-toml \
    python3-numpy \
    python3-packaging \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir pyserial empy PyYAML

WORKDIR /root
RUN git clone https://github.com/PX4/PX4-Autopilot.git --recursive --depth 1 --branch v1.14.0
WORKDIR /root/PX4-Autopilot

EXPOSE 14540/udp
EXPOSE 14550/udp

ENV PX4_HOME_LAT=34.0522
ENV PX4_HOME_LON=-118.2437
ENV PX4_HOME_ALT=0

CMD ["make", "px4_sitl", "gazebo"]
