from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, ISimpleAudioVolume, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import time
import sys
import os
import json

# --- APP DATA SETUP ---
APP_FOLDER = os.path.join(os.getenv('APPDATA'), 'Bear_AudioLimiter')
CONFIG_FILE = os.path.join(APP_FOLDER, 'config.json')

DEFAULT_CONFIG = {
    "THRESHOLD": 0.25,
    "SAFE_LEVEL": 0.20,
    "MUTE_DURATION": 2.0,
    "USE_MUTE": False,
    "LOWER_PERCENT": 0.20
}


def load_config():
    """Loads the config from AppData, or creates it if it doesn't exist."""
    if not os.path.exists(APP_FOLDER):
        os.makedirs(APP_FOLDER)

    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG


def save_config(config):
    """Saves the config dictionary to AppData."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)


def setup_menu(config):
    """Interactive menu to change settings."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("--- Settings Configuration ---")
    print("Leave blank and press Enter to keep the current value.\n")

    def get_float(prompt, current):
        val = input(f"{prompt} [Current: {current}]: ").strip()
        if not val: return current
        try:
            return float(val)
        except ValueError:
            print("Invalid number. Keeping current value.")
            return current

    def get_bool(prompt, current):
        val = input(f"{prompt} (y/n) [Current: {'y' if current else 'n'}]: ").strip().lower()
        if not val: return current
        return val == 'y'

    config["THRESHOLD"] = get_float("Set Trigger THRESHOLD (e.g., 0.25 for 25%)", config["THRESHOLD"])
    config["SAFE_LEVEL"] = get_float("Set SAFE_LEVEL to restore volume (e.g., 0.20 for 20%)", config["SAFE_LEVEL"])
    config["MUTE_DURATION"] = get_float("Set MUTE_DURATION in seconds (e.g., 2.0)", config["MUTE_DURATION"])
    config["USE_MUTE"] = get_bool("Mute completely instead of lowering volume?", config["USE_MUTE"])
    config["LOWER_PERCENT"] = get_float("If not muting, set LOWER_PERCENT volume (e.g., 0.20 for 20%)",
                                        config["LOWER_PERCENT"])

    save_config(config)
    print("\nSettings saved successfully to:", CONFIG_FILE)
    time.sleep(2)


def show_help():
    """Displays help information and definitions."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("==================================================")
    print("                   HELP & INFO                    ")
    print("==================================================")
    print("How it works:")
    print("This app monitors the 'True Volume' of every individual app.")
    print("If an app spikes too loud, it gets muted or lowered instantly.\n")
    print("Settings Explanation:")
    print(" - THRESHOLD:     The volume % that triggers the protection.")
    print(" - SAFE_LEVEL:    The volume % required to be considered 'safe' again.")
    print(" - MUTE_DURATION: How long (seconds) to wait before checking if safe.")
    print(" - USE_MUTE:      If Yes, mutes the app completely. If No, just lowers it.")
    print(" - LOWER_PERCENT: The volume % to drop to if USE_MUTE is No.\n")
    print(f"Config File Location:\n{CONFIG_FILE}")
    print("==================================================")
    input("\nPress Enter to return to the menu...")


def run_limiter(config):
    """The main monitoring loop."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("--- True Volume Per-App Limiter Active ---")
    print("Press Ctrl+C to stop.\n")

    devices = AudioUtilities.GetDeviceEnumerator()
    endpoint = devices.GetDefaultAudioEndpoint(0, 0)
    master_interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    master_volume_control = master_interface.QueryInterface(IAudioEndpointVolume)

    app_states = {}

    try:
        while True:
            global_master_vol = master_volume_control.GetMasterVolumeLevelScalar()
            sessions = AudioUtilities.GetAllSessions()

            loudest_app = ""
            max_true_level = 0.0
            any_protected = False
            protected_name = ""

            for session in sessions:
                if not session.Process: continue
                name = session.Process.name()
                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                volume_control = session._ctl.QueryInterface(ISimpleAudioVolume)

                raw_peak = meter.GetPeakValue()
                app_mixer_vol = volume_control.GetMasterVolume()

                if name not in app_states:
                    app_states[name] = [app_mixer_vol, 0, False, 0]

                orig_vol, start_time, is_protected, safe_ticks = app_states[name]
                true_actual = raw_peak * app_mixer_vol * global_master_vol

                if true_actual > max_true_level:
                    max_true_level = true_actual
                    loudest_app = name

                # --- TRIGGER ---
                if not is_protected and true_actual > config["THRESHOLD"]:
                    app_states[name][0] = app_mixer_vol
                    app_states[name][1] = time.time()
                    app_states[name][2] = True
                    if config["USE_MUTE"]:
                        volume_control.SetMute(1, None)
                    else:
                        volume_control.SetMasterVolume(config["LOWER_PERCENT"], None)

                # --- RESTORE ---
                elif is_protected:
                    any_protected = True
                    protected_name = name
                    elapsed = time.time() - start_time
                    if elapsed > config["MUTE_DURATION"] and true_actual < config["SAFE_LEVEL"]:
                        app_states[name][3] += 1
                        if app_states[name][3] > 15:
                            if config["USE_MUTE"]:
                                volume_control.SetMute(0, None)
                            else:
                                volume_control.SetMasterVolume(orig_vol, None)
                            app_states[name][2] = False
                    else:
                        app_states[name][3] = 0

            # --- VISUALS ---
            if any_protected:
                line = f"[PROTECT] {protected_name} BLOCKED | True Level: {max_true_level * 100:5.1f}%"
            elif max_true_level > 0.001:
                bar_len = 30
                filled = int(bar_len * min(max_true_level, 1.0))
                bar = '█' * filled + '-' * (bar_len - filled)
                line = f"[OK] {loudest_app[:12]}: [{bar}] {max_true_level * 100:5.1f}%"
            else:
                line = "[IDLE] Monitoring True Output..."

            print(f"\r{line:<80}", end="", flush=True)
            time.sleep(0.02)

    except KeyboardInterrupt:
        for session in AudioUtilities.GetAllSessions():
            if session.Process:
                vc = session._ctl.QueryInterface(ISimpleAudioVolume)
                vc.SetMute(0, None)
        print("\n\nExiting and Restoring...")


def main_menu():
    """Main application loop."""
    config = load_config()

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')

        # Display Current Settings on the Home Screen
        mute_mode_text = "MUTE completely" if config["USE_MUTE"] else f"LOWER to {config['LOWER_PERCENT'] * 100:.0f}%"

        print("=======================================")
        print("        BEAR AUDIO LIMITER APP         ")
        print("=======================================")
        print(f" Current Config:")
        print(f"   Trigger: > {config['THRESHOLD'] * 100:.0f}%   | Restore: < {config['SAFE_LEVEL'] * 100:.0f}%")
        print(f"   Wait: {config['MUTE_DURATION']} seconds | Action: {mute_mode_text}")
        print("=======================================")
        print("1. Start Limiter")
        print("2. Setup / Settings")
        print("3. Help / Info")
        print("4. Exit")
        print("=======================================")

        choice = input("Select an option (1-4): ").strip()

        if choice == '1':
            run_limiter(config)
            time.sleep(1)
        elif choice == '2':
            setup_menu(config)
        elif choice == '3':
            show_help()
        elif choice == '4':
            print("Goodbye!")
            sys.exit()
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")
            time.sleep(1)


if __name__ == "__main__":
    main_menu()