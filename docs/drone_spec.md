# AirDeliver Drone Hardware & Companion Specification

This document outlines the hardware and software requirements for the drone companion computer used in the AirDeliver system.

## 1. Flight Controller

* **Platform:** Pixhawk Standard Autopilot (e.g., Cube Orange, Pixhawk 6X)
* **Firmware:** PX4 Pro Stable Release (v1.14 or later recommended)
* **Protocol:** MAVLink v2

## 2. Companion Computer

* **Recommended Platforms:**
    * Raspberry Pi 4 Model B (4GB or 8GB RAM recommended)
    * NVIDIA Jetson Nano / Orin Nano (for future vision processing)
    * Intel NUC (for higher performance needs)
* **Operating System:** Ubuntu 22.04 LTS (Server or Desktop)
* **Minimum Specs:**
    * CPU: ARM Cortex-A72 (Quad-core 1.5GHz) or equivalent x86
    * RAM: 4GB
    * Storage: 32GB High-speed MicroSD card or NVMe SSD
    * Connectivity: Ethernet, USB 3.0 ports

## 3. Communication Interfaces

* **Companion <-> Pixhawk:**
    * **Primary:** Serial connection via UART (e.g., `/dev/serial0` on RPi) connected to `TELEM1` or `TELEM2` port on Pixhawk. Baud rate: 921600 recommended for MAVSDK.
    * **Alternative (SITL/Testing):** UDP connection (Companion listens on `udp://:14540`, PX4 SITL sends to `udp://<companion_ip>:14540`).
* **Companion <-> Network (Internet):**
    * **Required:** High-reliability Cellular Modem (4G LTE / 5G) with external antennas, connected via USB or M.2 slot. (e.g., Quectel, Sierra Wireless modules). Requires appropriate data plan.
    * **Optional (Ground/Testing):** Wi-Fi or Ethernet connection.
* **Companion <-> Payload Mechanism:**
    * **Servo:** Direct connection to GPIO pins (e.g., RPi GPIO) using libraries like `RPi.GPIO` or `pigpio`. Requires appropriate level shifting and power supply for servo. Pinout: TBD (e.g., GPIO 18).
    * **Serial/PWM Controller:** Connection via USB-Serial adapter or dedicated PWM controller board (e.g., PCA9685 via I2C) if more complex control is needed.
    * **Weight Sensor:** Connection via ADC (e.g., ADS1115 via I2C) or serial interface depending on sensor type. Pinout: TBD.

## 4. Payload Mechanism

* **MVP:** Servo-actuated release hook.
    * Servo Type: High-torque metal gear servo (e.g., MG996R or better).
    * Power: Separate BEC providing stable 5V/6V power.
* **Phase 2:** Controlled winch or advanced gripper (details TBD).
* **Sensors:**
    * Required: Limit switch or feedback mechanism to confirm hook open/closed state.
    * Recommended: Load cell / weight sensor integrated into hook assembly to confirm payload presence and release.

## 5. Power System

* Companion computer requires a stable 5V power supply (3A minimum recommended for RPi 4 + peripherals), typically provided by a BEC connected to the drone's main battery.
* Payload mechanism (servo, winch) requires separate, appropriately rated power supply.

## 6. Software Dependencies (Companion OS)

* Python 3.10+
* MAVSDK-Python library (ensure compatibility with target architecture)
* `websockets` library
* `python-dotenv`
* `structlog`
* `httpx` (if needed for direct API calls from companion)
* `pyserial` (if using serial MAVLink)
* `RPi.GPIO` / `pigpio` / `smbus2` (as needed for hardware interfaces)
* `prometheus-client` (optional for local metrics)
