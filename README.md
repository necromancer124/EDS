# 🐾 Bear Audio Limiter

**Bear** is a "True Volume" per-app limiter for Windows. Unlike standard limiters that only look at your master volume slider, Bear uses **Prediction Logic** to calculate the actual output reaching your ears by factoring in the App's Mixer Level, Global Master Volume, and Audio Peak in real-time.

## ✨ Features

* **Prediction Logic**: Calculates $TrueActual = RawPeak \times AppVolume \times MasterVolume$. This allows Bear to "see" if an app is still loud even while it is muted or muffled.
* **Stealth Background Mode**: Runs as a `.pyw` file, staying hidden in your System Tray (the arrow) with your custom icon.
* **Visual Monitor**: A GUI window showing a live percentage of the loudest app and a "DEFENDING" status indicator.
* **Smooth Restore**: Uses exponential math to fade volume back in smoothly—preventing "audio pops" when the protection releases.
* **Persistence**: Auto-saves your settings to `%APPDATA%\Bear_AudioLimiter\config.json`.

---

## 🚀 Installation & Setup

### 1. Requirements

* **Windows 10 or 11**
* **Python 3.10+** (Make sure "Add to PATH" was checked during Python installation)

### 2. One-Click Setup

1. Download the repository and ensure `BearLimiter.pyw`, `icon.png`, and `Install_Bear.bat` are in the same folder.
2. Double-click **`Install_Bear.bat`**.
3. The installer will:
* Install all dependencies (`pycaw`, `Pillow`, `pystray`, etc.).
* **Ask to run at Startup**: Type `y` to have Bear protect your ears automatically every time you turn on your PC.



---

## 🎮 Usage

### Controls

Once installed, look for your **custom icon** in the System Tray (near the clock). Right-click it to:

* **Show Monitor**: Open the live "VU Meter" to see which app is currently the loudest.
* **Settings**: Open the GUI to adjust thresholds and mute durations.
* **Exit**: Completely closes the limiter and restores all app volumes.

---

## ⚙️ Configuration Options

| Setting | Description |
| --- | --- |
| **Trigger Threshold** | The volume level (e.g., 20%) that triggers protection. |
| **Safe Level** | The level the audio must drop below before Bear restores volume. |
| **Mute Duration** | How many seconds to wait before attempting to restore volume. |
| **Drop Volume To** | If "Mute" is off, Bear will muffle the app to this specific level. |
| **Mute Mode** | Toggle between completely silencing a spike or just lowering it. |

---

## 📂 Project Structure

* `BearLimiter.pyw`: The core application (runs in the background).
* `icon.png`: Your custom branding for the tray and windows.
* `Install_Bear.bat`: The primary installer and startup-configurer.
* `config.json`: Found in `AppData\Roaming\Bear_AudioLimiter`.

---

## 🛡️ License

This project is open-source. Please see the [LICENSE](https://github.com/necromancer124/BE/blob/master/LICENCE) file for details.


## 🔒 Version Integrity (v1.0.0)
To ensure you have the official, untampered version of Bear Limiter, you can verify the file hash of `BearLimiter.pyw`:

* **Version:** 1.0.0 "Initial GUI Release"
Perfect! That output is exactly what you need. It looks professional and gives your users total confidence that the code hasn't been modified.

Here is the **Security & Integrity** section formatted for your `README.md`. You can paste this right at the bottom of the file.

---

### 🛡️ Security & Integrity Verification (v1.0.0)

To ensure you are running the official, untampered version of **Bear**, you can verify the SHA-256 hashes. Compare the output of your local files with the official manifest below.

#### Official Manifest

| SHA-256 Hash | File Name |
| --- | --- |
| `ADA278CE5BB09FB43B6CEEFA7897E904554E0D31971C69A48489D02F03E9D38F` | **Bear.pyw** |
| `27B242B9FCA8130238EFFDABDC3B2EBEBC4F6B986D8729F7ECED0F3313E10E55` | **icon.png** |
| `2E2296B96D10A11701D81781E16F968BBEA0F5451965148C995D0C5A1CB9CD40` | **Install_Bear.bat** |

#### How to verify on your machine

Open **PowerShell** in the project folder and run this one-liner:

```powershell
Get-FileHash Bear.pyw, icon.png, Install_Bear.bat | Select-Object Hash, @{N='Name';E={Split-Path $_.Path -Leaf}} | Format-Table -AutoSize

```
