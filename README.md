# DIGIT-UI

## Overview
A GUI created in TKinter for managing settings and viewing and capturing images from a single [DIGIT](https://digit.ml/) tactile sensor.

## Usage Instructions
### Requirements
As TKinter and Anaconda have compatibility issues on Linux, it's best to create a regular Python virtual environment to run this GUI.

TKinter is already installed with Python as default, so the only dependency is the [digit-interface library](https://github.com/facebookresearch/digit-interface), which you can install via pip using:  
`pip install digit-interface`

### Running the GUI
Clone this repository.
Connect your DIGIT sensor via USB and simply run the **digit_ui.py** script.  

## DIGIT Reference
Mike Lambeta, Po-Wei Chou, Stephen Tian, Brian Yang, Benjamin Maloon, Victoria Rose Most, Dave Stroud, Raymond Santos, Ahmad Byagowi, Gregg Kammerer, Dinesh Jayaraman, Roberto Calandra.  
“DIGIT: A Novel Design for a Low-Cost Compact High-Resolution Tactile Sensor with Application to In-Hand Manipulation.”  
IEEE Robotics and Automation Letters (RA-L), vol. 5, no. 3, pp. 3838–3845, 2020.  
https://doi.org/10.1109/LRA.2020.2977257
