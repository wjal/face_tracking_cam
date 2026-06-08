# Face-Tracking Pan/Tilt Camera System

![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%205-c51a4a?logo=raspberrypi&logoColor=white)
![Language](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?logo=opencv&logoColor=white)
![Arduino](https://img.shields.io/badge/Arduino-C++-00979D?logo=arduino&logoColor=white)
![Status](https://img.shields.io/badge/Status-Work%20In%20Progress-yellow)

A real-time, closed-loop face-tracking system that uses computer vision to detect a face and physically reorients a camera to keep it centered. A Raspberry Pi 5 performs frame capture and face detection, streams bounding-box coordinates over UART to an Arduino, which drives two servos mounted in a custom 3D-printed pan/tilt gimbal arm.

---

## Table of Contents

- [System Overview](#system-overview)
- [Hardware](#hardware)
- [Software Stack](#software-stack)
- [How It Works](#how-it-works)
- [UART Communication Protocol](#uart-communication-protocol)
- [Servo Control Logic](#servo-control-logic)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Roadmap](#roadmap)

---

## System Overview

```
┌──────────────────────────────────────┐    UART 9600 baud    ┌───────────────────────────────┐
│           Raspberry Pi 5             │  ─────────────────►  │            Arduino            │
│                                      │                      │                               │
│  ┌────────────┐    ┌───────────────┐ │  5-byte packet:      │  ┌──────────┐  ┌───────────┐  │
│  │  Pi Camera │──► │ OpenCV Haar   │ │  [0xFF]              │  │  Pan     │  │   Tilt    │  │
│  │  (CSI)     │    │ Face Detect   │ │  [X_lo][X_hi]        │  │  Servo   │  │   Servo   │  │
│  └────────────┘    └──────┬────────┘ │  [Y_lo][Y_hi]        │  └────┬─────┘  └─────┬─────┘  │
│                           │          │                      │       │               │        │
│                    BBox center (x,y) │                      └───────┼───────────────┼────────┘
│                                      │                              │               │
└──────────────────────────────────────┘                             ▼               ▼
                                                          ┌──────────────────────────────────┐
                                                          │  Custom 3D-Printed Pan/Tilt Arm  │
                                                          │  (2-joint gimbal-style mechanism) │
                                                          └──────────────────────────────────┘
```

The system forms a continuous closed-loop: the camera sees the face, the Pi computes the error from center, the Arduino corrects the servo angles, and the gimbal repositions the camera. Repeat.

---

## Hardware

| Component | Details |
|---|---|
| SBC | Raspberry Pi 5 |
| Camera | Raspberry Pi Camera Module (CSI interface) |
| Microcontroller | Arduino (Uno / Nano) |
| Servo – Pan | Standard RC hobby servo → pin D9 |
| Servo – Tilt | Standard RC hobby servo → pin D10 |
| Gimbal Mechanism | Custom 3D-printed pan/tilt arm (see below) |
| Level Converter | Custom-built 3.3 V → 5 V shifter using 2N7000 N-channel MOSFET (see below) |
| Pi ↔ Arduino Link | UART via GPIO 14/15 (TX/RX) → level converter → Arduino D0/D1 |

### Custom Pan/Tilt Gimbal

The camera mount is a custom-designed and 3D-printed two-joint arm. Each joint is driven by one servo, providing a pan axis (horizontal) and a tilt axis (vertical). The assembly functions as a gimbal, giving the camera roughly 180° of range on each axis. The geometry was designed around the servo horn attachment points to minimize backlash and distribute load evenly across the printed structure.

### Custom Logic-Level Converter

Rather than using an off-the-shelf level-shifter module, a discrete converter was designed and built around the **2N7000 N-channel enhancement-mode MOSFET** (TO-92 package). The circuit translates the Raspberry Pi's 3.3 V UART TX signal to a 5 V-compatible level for the Arduino's serial RX input, preventing any risk of back-driving the Pi's GPIO and ensuring clean signal levels across the voltage domain boundary.

The 2N7000 was chosen for its low threshold voltage (V<sub>GS(th)</sub> ≈ 0.8 – 3 V), making it reliably switchable by a 3.3 V gate signal, and its small TO-92 footprint. A schematic and bill of materials will be added to the `hardware/` directory.

---

## Software Stack

### Raspberry Pi — Python 3

| Library | Purpose |
|---|---|
| `picamera2` | Native Raspberry Pi Camera Module interface |
| `opencv-python` | Haar Cascade face detection, frame annotation |
| `pyserial` | UART serial communication |
| `numpy` | Frame array manipulation |
| `struct` | Binary packet packing for UART transmission |

### Arduino — C++

| Library | Purpose |
|---|---|
| `Servo.h` (built-in) | PWM servo angle control |
| `Serial` (built-in) | Hardware UART receive and debug output |

---

## How It Works

1. **Frame Capture** — `Picamera2` captures a `720 × 680` BGR frame at up to 30 fps over the CSI interface.
2. **Grayscale Conversion** — The frame is converted to grayscale to reduce the computational load on the Haar cascade.
3. **Face Detection** — OpenCV's Haar Cascade classifier (`haarcascade_frontalface_default.xml`) scans the frame. When multiple faces are detected, the first result is tracked.
4. **Center Calculation** — The center pixel of the face bounding box is computed as `(x + w/2, y + h/2)`.
5. **UART Transmission** — A 5-byte little-endian binary packet is packed with `struct` and transmitted over `/dev/serial0` to the Arduino.
6. **Error Computation** — The Arduino calculates the offset of the face center from the frame midpoint `(360, 340)`.
7. **Servo Correction** — A proportional controller (with dead zone) computes angular deltas for each axis and drives the servos accordingly.
8. **Performance Monitoring** — An exponential moving average (α = 0.1) tracks loop time and displays a live FPS estimate on the preview window.
9. **Video Recording** — The annotated output is simultaneously written to `face_track_proto.mp4` via OpenCV's `VideoWriter`.

---

## UART Communication Protocol

Each message is a fixed **5-byte little-endian binary packet**:

```
 Byte 0    Byte 1    Byte 2    Byte 3    Byte 4
┌────────┬──────────┬──────────┬──────────┬──────────┐
│  0xFF  │  X_low   │  X_high  │  Y_low   │  Y_high  │
└────────┴──────────┴──────────┴──────────┴──────────┘
  Start    ◄─── X center coord (uint16, LE) ───►   ◄─── Y center coord (uint16, LE) ───►
```

| Field | Type | Range | Description |
|---|---|---|---|
| `0xFF` | `uint8` | — | Frame sync / start byte |
| `X` | `uint16` little-endian | 0 – 720 | Horizontal pixel of face bounding box center |
| `Y` | `uint16` little-endian | 0 – 680 | Vertical pixel of face bounding box center |

> ⚠️ **Sync Note:** The frame dimensions (`FRAME_WIDTH = 720`, `FRAME_HEIGHT = 680`) are hardcoded on both sides. If the camera resolution is changed in `main.py`, the matching `#define` values in the Arduino sketch must also be updated.

**Raspberry Pi — packing:**
```python
ser.write(struct.pack('<BHH', 0xFF, int(x + w/2), int(y + h/2)))
```

**Arduino — unpacking:**
```cpp
uint8_t xLow  = Serial.read();
uint8_t xHigh = Serial.read();
uint8_t yLow  = Serial.read();
uint8_t yHigh = Serial.read();

x_coord = xLow  | (xHigh << 8);
y_coord = yLow  | (yHigh << 8);
```

---

## Servo Control Logic

The Arduino implements a **proportional controller with a dead zone** to prevent jitter when the face is already near-centered.

```
Frame center:  x_mid = 360,  y_mid = 340
Dead zone:     ± 35 pixels on each axis

Pan axis (horizontal):
  if |x_coord - x_mid| > 35:
      pan_move        = ((x_coord - x_mid) / x_mid) × 12 + 1
      pan_angle      -= pan_move          ← sign inverted for physical orientation

Tilt axis (vertical):
  if |y_coord - y_mid| > 35:
      tilt_move       = ((y_coord - y_mid) / y_mid) × 12 + 1
      tilt_angle     += tilt_move

Both axes clamped to [0°, 180°]
```

| Parameter | Value |
|---|---|
| Home position — Pan | 110° |
| Home position — Tilt | 10° |
| Max angular step per frame | ~13° |
| Servo range | 0° – 180° |
| Dead zone radius | ± 35 px |

The proportional gain (`12`) and dead zone (`35 px`) are empirically tuned constants. A PID controller is planned as a future improvement to reduce overshoot and oscillation.

---

## Project Structure

```
face_tracking/
├── hardware/
│   ├── CAM_SERVOS.stl                           # 3D-printable pan/tilt gimbal arm
│   └── level_converter (TODO)                   # 2N7000 logic-level converter schematic (TBD)
├── arduino/
│   └── src/
│       └── main.cpp                             # Arduino: UART RX, proportional servo control
├── pi/
│   ├── main                                     # Pi: frame capture, face detection, UART TX
│   └── data/
│       ├── haarcascade_frontalface_default.xml  # Haar face cascade model
│       └── haarcascade_eye.xml                  # Haar eye cascade (present, not yet active)
└── README.md
```

---

## Setup & Installation

### Raspberry Pi

#### 1. Enable UART and disable serial console

```bash
sudo raspi-config
# Navigate to: Interface Options → Serial Port
#   "Login shell accessible over serial?" → No
#   "Serial port hardware enabled?"       → Yes
```

Or manually in `/boot/firmware/config.txt`:
```
enable_uart=1
```

Reboot after making changes.

#### 2. Install Python dependencies

```bash
pip install picamera2 opencv-python pyserial numpy
```

#### 3. Add Haar cascade model files

Copy the two XML files into the `data/` directory. They ship with OpenCV and can be located with:

```bash
find / -name "haarcascade_frontalface_default.xml" 2>/dev/null
```

#### 4. Wire UART through the level converter

The Pi's 3.3 V TX line passes through the custom 2N7000 level-converter circuit before reaching the Arduino's 5 V RX pin.

| Signal path | Connection |
|---|---|
| Pi GPIO 14 (TX, 3.3 V) | → Level converter input |
| Level converter output (5 V) | → Arduino D0 (RX) |
| Pi GPIO 15 (RX) | → Arduino D1 (TX) *(currently unused — Pi only transmits)* |
| Pi GND | → Level converter GND → Arduino GND |

> See `hardware/` for the level converter schematic and BOM.

---

### Arduino

1. Open `arduino/servo_controller/main.cpp` in Arduino IDE or PlatformIO.
2. Connect servos:
   - Pan servo signal wire → **D9**
   - Tilt servo signal wire → **D10**
   - Both servo power/ground to an appropriate 5 V supply (not the Arduino's 5 V pin for two servos under load).
3. Compile and upload to the board.
4. Open the Serial Monitor at **9600 baud** to confirm `"Setup complete."` and verify live `pan angle` / `tilt` debug output.

---

## Usage

```bash
# On the Raspberry Pi
python3 main.py
```

- A live preview window labeled **"Camera"** opens showing the annotated color frame.
- A second window labeled **"FRAME"** shows the grayscale feed used for detection.
- A green bounding box is drawn around the first detected face.
- FPS and loop time are overlaid in the top-left corner.
- Press **`q`** in either preview window to exit cleanly.
- Output video is saved to `face_track_proto.mp4` in the working directory on exit.

> The script handles `KeyboardInterrupt` (Ctrl+C) gracefully, ensuring the serial port, VideoWriter, and camera are all properly released.

---

## Roadmap

- [ ] Arduino: replace polling loop with interrupt-driven serial handling and a cooperative task manager
- [ ] Replace proportional controller with a full **PID controller** to reduce overshoot and settling time
- [ ] Add multi-face selection logic (largest bounding box, or nearest to previous position)
- [ ] Re-enable and tune **eye detection** within the face ROI for sub-region tracking
- [ ] Tune dead zone and proportional gain constants with systematic testing
- [ ] Evaluate switching to a DNN-based face detector (`cv.dnn`) for improved accuracy and lighting robustness
- [ ] Gimbal v2: refined 3D-printed geometry for reduced backlash and cleaner cable routing

---

*Built as a personal embedded systems and computer vision project — integrating real-time image processing, custom firmware, binary UART protocol design, discrete circuit design (custom logic-level converter), and 3D-printed mechanical design into a single closed-loop tracking system.*
