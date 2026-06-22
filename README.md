# 🐻 Bear Audio Limiter
A "True Volume" per-app audio limiter for Windows that prevents sudden loud spikes from ruining your hearing or your speakers.

## 🚀 Overview
Bear Audio Limiter calculates the real output volume by multiplying the **Peak Volume x App Volume x Master Volume**. If any application exceeds a defined threshold, Bear instantly lowers its volume or mutes it, then gradually restores it once the audio is safe.

## ✨ Features
- **Real-time Monitoring**: Tracks the actual output of every running application.
- **Predictive Protection**: Instantly reacts to audio spikes before they hit your ears.
- **Customizable Thresholds**: Adjust trigger levels, safe return levels, and mute durations.
- **System Tray Integration**: Runs quietly in the background with a monitor window for real-time stats.
- **Smart Recovery**: Gradually fades volume back to original levels to avoid jarring jumps.

## 🛠️ Installation

### Prerequisites
- Windows OS
- Python 3.8+

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/necromancer124/BE.git
   cd BE
   ```
2. Install required dependencies:
   ```bash
   pip install pycaw comtypes pystray Pillow
   ```
3. Run the application:
   ```bash
   python Bear.pyw
   ```

## ⚙️ Configuration
The app saves your settings in `%APPDATA%/Bear_AudioLimiter/config.json`.
- **Threshold**: The volume level that triggers protection.
- **Safe Level**: The volume level that must be reached before restoring original volume.
- **Mute Duration**: How long to hold the volume low.

## 📜 License
This project is licensed under the MIT License.
