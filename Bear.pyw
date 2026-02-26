from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, ISimpleAudioVolume, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import pythoncom
import time
import threading
import os
import json
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import pystray
from pystray import MenuItem as item
import sys

# --- APP DATA SETUP ---
APP_FOLDER = os.path.join(os.getenv('APPDATA'), 'Bear_AudioLimiter')
CONFIG_FILE = os.path.join(APP_FOLDER, 'config.json')
ICON_PATH = "icon.png"  # Make sure your icon is named this!

DEFAULT_CONFIG = {
    "THRESHOLD": 0.20,
    "SAFE_LEVEL": 0.15,
    "MUTE_DURATION": 1.5,
    "USE_MUTE": False,
    "LOWER_PERCENT": 0.10
}


def load_config():
    if not os.path.exists(APP_FOLDER): os.makedirs(APP_FOLDER)
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG


def save_config(config_to_save):
    with open(CONFIG_FILE, 'w') as f: json.dump(config_to_save, f, indent=4)


config = load_config()
running = True
root = None
max_vol_var = None
loudest_app_var = None
status_var = None
tk_icon = None


# --- ICON LOADER ---
def load_my_icon():
    """Loads your custom icon.png file."""
    if os.path.exists(ICON_PATH):
        return Image.open(ICON_PATH)
    else:
        # Fallback to a simple colored square if file is missing so it doesn't crash
        return Image.new('RGB', (64, 64), color=(255, 140, 0))


# --- THE LOGIC (Prediction & Protection) ---
def limiter_logic():
    global config, running
    pythoncom.CoInitialize()

    devices = AudioUtilities.GetDeviceEnumerator()
    endpoint = devices.GetDefaultAudioEndpoint(0, 0)
    master_interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    master_vol_control = master_interface.QueryInterface(IAudioEndpointVolume)
    app_states = {}

    while running:
        try:
            global_master = master_vol_control.GetMasterVolumeLevelScalar()
            sessions = AudioUtilities.GetAllSessions()

            max_view_level = 0.0
            current_loudest = "None"
            is_defending = False

            for session in sessions:
                if not session.Process: continue
                name = session.Process.name()
                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                volume_control = session._ctl.QueryInterface(ISimpleAudioVolume)

                raw_peak = meter.GetPeakValue()
                app_mixer = volume_control.GetMasterVolume()
                true_actual = raw_peak * app_mixer * global_master

                if name not in app_states: app_states[name] = [app_mixer, 0, False, 0]

                if not app_states[name][2] and true_actual > config["THRESHOLD"]:
                    app_states[name][0] = app_mixer
                    app_states[name][1] = time.time()
                    app_states[name][2] = True
                    if config["USE_MUTE"]:
                        volume_control.SetMute(1, None)
                    else:
                        volume_control.SetMasterVolume(config["LOWER_PERCENT"], None)

                if app_states[name][2]:
                    is_defending = True
                    elapsed = time.time() - app_states[name][1]
                    potential_volume = raw_peak * app_states[name][0] * global_master

                    if potential_volume > max_view_level:
                        max_view_level = potential_volume
                        current_loudest = name

                    if potential_volume > config["THRESHOLD"]:
                        app_states[name][1] = time.time()
                        app_states[name][3] = 0

                    if elapsed >= config["MUTE_DURATION"]:
                        if potential_volume < config["SAFE_LEVEL"]:
                            app_states[name][3] += 1
                            if app_states[name][3] >= 50:
                                if config["USE_MUTE"]: volume_control.SetMute(0, None)

                                start_v = config["LOWER_PERCENT"] if not config["USE_MUTE"] else 0.001
                                end_v = app_states[name][0]
                                for step in range(1, 41):
                                    ratio = step / 40
                                    new_v = start_v * (end_v / start_v) ** ratio
                                    volume_control.SetMasterVolume(new_v, None)
                                    time.sleep(0.001)
                                app_states[name][2], app_states[name][3] = False, 0
                        else:
                            app_states[name][3] = 0
                else:
                    if true_actual > max_view_level:
                        max_view_level = true_actual
                        current_loudest = name

            if max_vol_var: max_vol_var.set(int(max_view_level * 100))
            if loudest_app_var: loudest_app_var.set(current_loudest)
            if status_var: status_var.set("⚠️ DEFENDING" if is_defending else "✅ OK")

        except:
            pass
        time.sleep(0.05)
    pythoncom.CoUninitialize()


# --- UI WINDOWS ---
def apply_icon(win):
    """Utility to set your custom icon to any popup window."""
    global tk_icon
    if tk_icon:
        win.iconphoto(False, tk_icon)


def open_settings():
    root.after(0, _create_settings_win)


def _create_settings_win():
    settings_win = tk.Toplevel(root)
    settings_win.title("Bear Settings")
    settings_win.geometry("400x520")
    settings_win.attributes("-topmost", True)
    apply_icon(settings_win)
    settings_win.configure(padx=20, pady=20)

    def add_setting(label_text, key, from_val, to_val, is_percent=True):
        frame = tk.Frame(settings_win)
        frame.pack(fill="x", pady=10)
        display_val = int(config[key] * 100) if is_percent else config[key]
        suffix = "%" if is_percent else "s"
        lbl = tk.Label(frame, text=f"{label_text}: {display_val}{suffix}", font=("Arial", 10, "bold"))
        lbl.pack(side="top", anchor="w")
        var = tk.DoubleVar(value=config[key])

        def update_lbl(val):
            v = float(val)
            config[key] = v
            lbl.config(text=f"{label_text}: {int(v * 100) if is_percent else round(v, 1)}{suffix}")

        ttk.Scale(frame, from_=from_val, to=to_val, variable=var, orient="horizontal", command=update_lbl).pack(
            fill="x")

    add_setting("Trigger Threshold", "THRESHOLD", 0.01, 1.0)
    add_setting("Safe Level (Return volume below this)", "SAFE_LEVEL", 0.01, 1.0)
    add_setting("Drop Volume To (If not muting)", "LOWER_PERCENT", 0.0, 0.5)
    add_setting("Mute Duration (Seconds)", "MUTE_DURATION", 0.1, 5.0, is_percent=False)

    m_var = tk.BooleanVar(value=config['USE_MUTE'])
    tk.Checkbutton(settings_win, text="Mute completely on spike?", variable=m_var, font=("Arial", 9)).pack(pady=10,
                                                                                                           anchor="w")

    def save():
        config["USE_MUTE"] = m_var.get()
        save_config(config)
        settings_win.destroy()

    tk.Button(settings_win, text="Save & Close", command=save, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
              pady=10).pack(fill="x", pady=20)


def show_monitor():
    root.after(0, _create_monitor_win)


def _create_monitor_win():
    global max_vol_var, loudest_app_var, status_var
    monitor_win = tk.Toplevel(root)
    monitor_win.title("Bear Monitor")
    monitor_win.geometry("320x220")
    monitor_win.attributes("-topmost", True)
    apply_icon(monitor_win)
    monitor_win.configure(padx=15, pady=15)

    status_var = tk.StringVar(value="✅ OK")
    status_lbl = tk.Label(monitor_win, textvariable=status_var, font=("Arial", 14, "bold"))
    status_lbl.pack()

    tk.Label(monitor_win, text="Loudest App:", font=("Arial", 9, "italic")).pack(pady=(10, 0))
    loudest_app_var = tk.StringVar(value="None")
    tk.Label(monitor_win, textvariable=loudest_app_var, font=("Arial", 11, "bold"), fg="#333").pack()

    max_vol_var = tk.IntVar(value=0)
    num_lbl = tk.Label(monitor_win, text="0%", font=("Arial", 22, "bold"))
    num_lbl.pack(pady=5)

    progress = ttk.Progressbar(monitor_win, length=280, variable=max_vol_var, maximum=100)
    progress.pack()

    def update_ui():
        if max_vol_var and status_var:
            val = max_vol_var.get()
            num_lbl.config(text=f"{val}%")
            if "DEFENDING" in status_var.get():
                status_lbl.config(fg="red")
                num_lbl.config(fg="red")
            else:
                status_lbl.config(fg="green")
                num_lbl.config(fg="black")
            monitor_win.after(100, update_ui)

    update_ui()

    def on_close():
        global max_vol_var, loudest_app_var, status_var
        max_vol_var = loudest_app_var = status_var = None
        monitor_win.destroy()

    monitor_win.protocol("WM_DELETE_WINDOW", on_close)


# --- SYSTEM TRAY ---
def setup_tray():
    icon_img = load_my_icon()

    def on_quit(icon):
        global running
        running = False
        icon.stop()
        root.quit()

    menu = pystray.Menu(
        item('Show Monitor', show_monitor),
        item('Settings', open_settings),
        item('Exit', on_quit)
    )
    icon = pystray.Icon("BearLimiter", icon_img, "Bear Audio Limiter", menu)
    icon.run()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    # Load icon once for the Windows
    my_img = load_my_icon()
    tk_icon = ImageTk.PhotoImage(my_img)

    threading.Thread(target=limiter_logic, daemon=True).start()
    threading.Thread(target=setup_tray, daemon=True).start()

    root.mainloop()