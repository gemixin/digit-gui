# DIGIT-GUI

## Overview

**DIGIT-GUI** is a graphical user interface built with **Tkinter** for managing settings and capturing images from a single [DIGIT](https://digit.ml/) tactile sensor.

## Requirements

- **Operating System:** Linux only (DIGIT sensors are supported on Linux only)  
- **Tested Environment:** Ubuntu 22.04, Python 3.13  
- **Python Environment:** Use a regular Python virtual environment (Tkinter and Anaconda have compatibility issues on Linux)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/gemixin/digit-gui.git
   cd digit-gui

2. **(Optional) Set up a virtual environment:** 
    ```bash
    python3 -m venv venv
    source venv/bin/activate

3. **Install the required package:**  
    Tkinter is included with Python by default. Install the DIGIT interface library:
    ```bash
    pip install digit-interface

## Running the GUI

1. Connect your DIGIT sensor via USB.

2. Run the GUI script:
    ```bash
    python digit_gui.py

## Known Issues
- **VGA Mode Bug**:
The [digit-interface](https://github.com/facebookresearch/digit-interface) library has a known issue with VGA mode producing glitchy output.  
  See [issue #10](https://github.com/facebookresearch/digit-interface/issues/10).  
  ✅ **Recommendation:** Stick to **QVGA mode** for reliable operation.

## Citation

If you use DIGIT or this repo in your research, please cite:

**DIGIT: A Novel Design for a Low-Cost Compact High-Resolution Tactile Sensor with Application to In-Hand Manipulation**  
Mike Lambeta, Po-Wei Chou, Stephen Tian, Brian Yang, Benjamin Maloon, Victoria Rose Most, Dave Stroud, Raymond Santos, Ahmad Byagowi, Gregg Kammerer, Dinesh Jayaraman, Roberto Calandra  
_IEEE Robotics and Automation Letters (RA-L), vol. 5, no. 3, pp. 3838–3845, 2020_  
[https://doi.org/10.1109/LRA.2020.2977257](https://doi.org/10.1109/LRA.2020.2977257)