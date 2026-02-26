# 🐾 Bear Audio Limiter

**Bear** is a "True Volume" per-app limiter for Windows. Unlike standard limiters that only look at your master volume slider, Bear calculates the actual output reaching your ears by factoring in the **App's Mixer Level**, the **Global Master Volume**, and the **Audio Peak** in real-time.

## ✨ Features

* **True Volume Calculation**: Uses the precise formula:

$$V_{true} = \text{Peak} \times \text{App\_Slider} \times \text{Master\_Slider}$$


* **Persistent Settings**: Saves your configuration to `%APPDATA%\Bear_AudioLimiter\config.json` so your settings are remembered every time you launch.
* **Two Protection Modes**: Choose between completely muting a loud app or dynamically lowering its volume to a safe percentage.
* **Visual Monitor**: A live terminal-based "VU Meter" showing exactly which app is loudest at any given millisecond.
* **Auto-Restore**: Automatically returns the volume to original levels once the loud noise has subsided for a set duration.

---

## 🚀 Installation & Setup

### 1. Requirements

* Windows 10 or 11
* Python 3.x installed

### 2. One-Click Install

1. Open the project folder.
2. Double-click `setup.bat`. This will automatically install the required Windows audio libraries (`pycaw` and `comtypes`).

---

## 🎮 Usage

### Launching the App

Simply double-click **`start_bear.bat`**.
The app will open a terminal window with a clean menu:

1. **Start Limiter**: Begins monitoring your audio immediately.
2. **Setup / Settings**: Change your thresholds and mute preferences.
3. **Help / Info**: View definitions of settings and file paths.
4. **Exit**: Closes the application and restores all volumes.

> **Pro-Tip:** Right-click `start_bear.bat` and select **"Send to > Desktop (create shortcut)"** to keep Bear accessible right from your desktop.

---

## ⚙️ Configuration Options

| Setting | Description |
| --- | --- |
| **THRESHOLD** | The volume level (e.g., 0.25 for 25%) that triggers the protection. |
| **SAFE_LEVEL** | The volume level the app must drop below to be considered "safe." |
| **MUTE_DURATION** | Seconds to wait before the app attempts to restore your volume. |
| **USE_MUTE** | `y` to mute the app completely; `n` to just lower it. |
| **LOWER_PERCENT** | The specific volume level to drop to if `USE_MUTE` is off. |

---

## 📂 Project Structure

* `bear_limiter.py`: The core Python logic and menu system.
* `setup.bat`: One-click dependency installer.
* `start_bear.bat`: The primary application launcher.
* `config.json`: (Auto-generated) Found in `AppData\Roaming\Bear_AudioLimiter`.

## 🛡️ License

This project is open-source. Please see the [LICENSE](https://github.com/necromancer124/BE/blob/master/LICENCE) file for full details regarding usage and distribution.

