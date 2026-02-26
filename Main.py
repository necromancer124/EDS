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
    "THRESHOLD": 0.20,  # Internal: 0.20 | User: 20%
    "SAFE_LEVEL": 0.15,  # Internal: 0.15 | User: 15%
    "MUTE_DURATION": 1.5,
    "USE_MUTE": False,
    "LOWER_PERCENT": 0.10  # Internal: 0.10 | User: 10%
}


def load_config():
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
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)


def setup_menu(config):
    os.system('cls' if os.name == 'nt' else 'clear')
    os.system('color 0e')
    print("--- ⚙️ User-Friendly Settings ---")
    print("Enter whole numbers (1-100) for percentages.")
    print("Leave blank to keep the current value.\n")

    def get_percent_input(prompt, current_decimal):
        current_pct = int(current_decimal * 100)
        val = input(f"{prompt} [Current: {current_pct}%]: ").strip()
        if not val: return current_decimal
        try:
            # Convert user 0-100 input back to 0.0-1.0 for the code
            new_val = float(val) / 100
            return max(0.0, min(1.0, new_val))
        except ValueError:
            return current_decimal

    def get_float(prompt, current):
        val = input(f"{prompt} [Current: {current}s]: ").strip()
        if not val: return current
        try:
            return float(val)2
        except ValueError:
            return current

    def get_bool(prompt, current):
        val = input(f"{prompt} (y/n) [Current: {'y' if current else 'n'}]: ").strip().lower()
        if not val: return current
        return val == 'y'

    config["THRESHOLD"] = get_percent_input("Set Trigger THRESHOLD (1-100%)", config["THRESHOLD"])
    config["SAFE_LEVEL"] = get_percent_input("Set SAFE_LEVEL to restore (1-100%)", config["SAFE_LEVEL"])
    config["MUTE_DURATION"] = get_float("Set MUTE_DURATION (seconds)", config["MUTE_DURATION"])
    config["USE_MUTE"] = get_bool("Mute completely?", config["USE_MUTE"])
    if not config["USE_MUTE"]:
        config["LOWER_PERCENT"] = get_percent_input("Set volume level to DROP to", config["LOWER_PERCENT"])

    save_config(config)
    print("\n✅ Settings saved and converted!")
    time.sleep(1.5)


def show_help(config):
    os.system('cls' if os.name == 'nt' else 'clear')
    os.system('color 0b')
    action = "MUTE" if config['USE_MUTE'] else f"LOWER to {int(config['LOWER_PERCENT'] * 100)}%"

    print("==================================================")
    print("               🐾 BEAR HELP & STATUS              ")
    print("==================================================")
    print(f" CURRENT LIVE SETTINGS:")
    print(f" > Trigger Protection: Above {int(config['THRESHOLD'] * 100)}%")
    print(f" > Recovery Level:     Below {int(config['SAFE_LEVEL'] * 100)}%")
    print(f" > Cooldown Wait:      {config['MUTE_DURATION']} seconds")
    print(f" > Bear's Action:      {action}")
    print("==================================================")
    print("\nHow the 'True Volume' Math Works:")
    print("Actual Sound = (App Peak) * (Windows Master Volume)")
    print("\nExample:")
    print("- If Windows is 100% and App spikes to 50% -> Bear sees 50%.")
    print("- If Windows is 50% and App spikes to 50%  -> Bear sees 25%.")
    print("\nThis ensures that if you lower your Master volume,")
    print("the limiter becomes more 'relaxed' automatically.")
    print("==================================================")
    input("\nPress Enter to return to menu...")


def run_limiter(config):
    os.system('cls' if os.name == 'nt' else 'clear')
    os.system('color 0b')
    print("--- 🐾 BEAR PROTECT ACTIVE ---")
    print("Reaction Speed: MAX | Press Ctrl+C to stop.\n")

    devices = AudioUtilities.GetDeviceEnumerator()
    endpoint = devices.GetDefaultAudioEndpoint(0, 0)
    master_interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    master_volume_control = master_interface.QueryInterface(IAudioEndpointVolume)

    app_states = {}

    try:
        while True:
            global_master_vol = master_volume_control.GetMasterVolumeLevelScalar()
            sessions = AudioUtilities.GetAllSessions()

            max_true_level = 0.0
            loudest_app = ""
            any_protected = False
            protected_name = ""

            for session in sessions:
                if not session.Process: continue
                name = session.Process.name()

                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                volume_control = session._ctl.QueryInterface(ISimpleAudioVolume)

                raw_peak = meter.GetPeakValue()

                if name not in app_states:
                    app_states[name] = [volume_control.GetMasterVolume(), 0, False, 0]

                # Accurate Math: Peak scaled only by Master Volume
                true_actual = raw_peak * global_master_vol

                if true_actual > max_true_level:
                    max_true_level = true_actual
                    loudest_app = name

                # --- TRIGGER ---
                if not app_states[name][2] and true_actual > config["THRESHOLD"]:
                    app_states[name][0] = volume_control.GetMasterVolume()
                    app_states[name][1] = time.time()
                    app_states[name][2] = True
                    if config["USE_MUTE"]:
                        volume_control.SetMute(1, None)
                    else:
                        volume_control.SetMasterVolume(config["LOWER_PERCENT"], None)

                # --- RESTORE ---
                elif app_states[name][2]:
                    any_protected = True
                    protected_name = name
                    elapsed = time.time() - app_states[name][1]

                    if elapsed > config["MUTE_DURATION"] and true_actual < config["SAFE_LEVEL"]:
                        app_states[name][3] += 1
                        if app_states[name][3] > 10:
                            if config["USE_MUTE"]:
                                volume_control.SetMute(0, None)
                            else:
                                volume_control.SetMasterVolume(app_states[name][0], None)
                            app_states[name][2] = False
                            app_states[name][3] = 0
                    else:
                        app_states[name][3] = 0

            if any_protected:
                os.system('color 0c')
                line = f"⚠️ [PROTECTING] {protected_name} is too LOUD!"
            else:
                os.system('color 0b')
                bar_len = 25
                filled = int(bar_len * min(max_true_level, 1.0))
                bar = '█' * filled + '-' * (bar_len - filled)
                line = f"[OK] {loudest_app[:12]:<12} |{bar}| {int(max_true_level * 100):3}%"

            print(f"\r{line:<80}", end="", flush=True)
            time.sleep(0.01)

    except KeyboardInterrupt:
        os.system('color 07')
        for session in AudioUtilities.GetAllSessions():
            if session.Process:
                vc = session._ctl.QueryInterface(ISimpleAudioVolume)
                vc.SetMute(0, None)
        print("\n\n🐾 Bear is sleeping. Volumes restored.")


def main_menu():
    while True:
        config = load_config()
        os.system('color 0e')
        os.system('cls' if os.name == 'nt' else 'clear')
        mode = "MUTE" if config["USE_MUTE"] else f"DROP TO {int(config['LOWER_PERCENT'] * 100)}%"

        print("=======================================")
        print("        🐾 BEAR AUDIO LIMITER          ")
        print("=======================================")
        print(f" LIMIT: {int(config['THRESHOLD'] * 100)}% | ACTION: {mode}")
        print("=======================================")
        print("1. Start Limiter")
        print("2. Setup / Settings")
        print("3. Help / Info")
        print("4. Exit")
        print("=======================================")

        choice = input("Select (1-4): ").strip()

        if choice == '1':
            run_limiter(config)
            time.sleep(1)
        elif choice == '2':
            setup_menu(config)
        elif choice == '3':
            show_help(config)
        elif choice == '4':
            sys.exit()


if __name__ == "__main__":
    main_menu()