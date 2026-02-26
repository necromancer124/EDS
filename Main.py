from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, ISimpleAudioVolume, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import time
import sys
import os
import json
import math

# --- APP DATA SETUP ---
APP_FOLDER = os.path.join(os.getenv('APPDATA'), 'Bear_AudioLimiter')
CONFIG_FILE = os.path.join(APP_FOLDER, 'config.json')

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
    except Exception:
        return DEFAULT_CONFIG


def save_config(config):
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)


def setup_menu(config):
    os.system('cls' if os.name == 'nt' else 'clear');
    os.system('color 0e')
    print("--- ⚙️ Settings ---")

    def get_pct(prompt, current):
        val = input(f"{prompt} [Current: {int(current * 100)}%]: ").strip()
        return float(val) / 100 if val else current

    config["THRESHOLD"] = get_pct("Trigger Threshold", config["THRESHOLD"])
    config["SAFE_LEVEL"] = get_pct("Safe Level", config["SAFE_LEVEL"])
    val = input(f"Mute Time (sec) [{config['MUTE_DURATION']}s]: ").strip()
    if val: config["MUTE_DURATION"] = float(val)
    val = input(f"Mute completely? (y/n) [{'y' if config['USE_MUTE'] else 'n'}]: ").strip().lower()
    if val: config["USE_MUTE"] = (val == 'y')
    if not config["USE_MUTE"]:
        config["LOWER_PERCENT"] = get_pct("Drop Volume To", config["LOWER_PERCENT"])
    save_config(config)


def show_help(config):
    os.system('cls' if os.name == 'nt' else 'clear');
    os.system('color 0b')
    print("=======================================")
    print("        🐾 BEAR LIMITER HELP          ")
    print("=======================================")
    print(f"Trigger: Above {int(config['THRESHOLD'] * 100)}%")
    print(f"Safe Level: Below {int(config['SAFE_LEVEL'] * 100)}%")
    print("---------------------------------------")
    print("GHOST-CHECK LOGIC:")
    print("1. It checks the 'raw' app volume")
    print("   WHILE the sound is still lowered.")
    print("2. It only un-mutes/swells IF the")
    print("   check comes back 100% clean.")
    print("=======================================")
    input("\nPress Enter to return...")


def run_limiter(config):
    os.system('cls' if os.name == 'nt' else 'clear');
    os.system('color 0b')
    print("--- 🐾 BEAR PROTECT ACTIVE ---")
    print("GHOST-CHECK + EXPONENTIAL | Ctrl+C to stop.\n")
    devices = AudioUtilities.GetDeviceEnumerator()
    endpoint = devices.GetDefaultAudioEndpoint(0, 0)
    master_interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    master_vol_control = master_interface.QueryInterface(IAudioEndpointVolume)
    app_states = {}

    try:
        while True:
            global_master = master_vol_control.GetMasterVolumeLevelScalar()
            sessions = AudioUtilities.GetAllSessions()
            max_true_level, loudest_app, any_protected, protected_name = 0.0, "", False, ""

            for session in sessions:
                if not session.Process: continue
                name = session.Process.name()
                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                volume_control = session._ctl.QueryInterface(ISimpleAudioVolume)

                raw_peak = meter.GetPeakValue()
                app_mixer = volume_control.GetMasterVolume()
                true_actual = raw_peak * app_mixer * global_master

                if name not in app_states: app_states[name] = [app_mixer, 0, False, 0]
                if true_actual > max_true_level: max_true_level, loudest_app = true_actual, name

                # --- 1. THE TRIGGER ---
                if not app_states[name][2] and true_actual > config["THRESHOLD"]:
                    app_states[name][0] = app_mixer
                    app_states[name][1] = time.time()
                    app_states[name][2] = True
                    if config["USE_MUTE"]:
                        volume_control.SetMute(1, None)
                    else:
                        volume_control.SetMasterVolume(config["LOWER_PERCENT"], None)

                # --- 2. THE GHOST-CHECK RESTORE ---
                elif app_states[name][2]:
                    any_protected, protected_name = True, name
                    elapsed = time.time() - app_states[name][1]

                    # We check the RAW peak coming from the app
                    # Formula: raw_peak * (original volume) * master
                    # This tells us how loud it WOULD be if we restored right now
                    potential_volume = raw_peak * app_states[name][0] * global_master

                    # If the POTENTIAL volume is still too high, reset the lock
                    if potential_volume > config["THRESHOLD"]:
                        app_states[name][1] = time.time()
                        app_states[name][3] = 0

                    if elapsed >= config["MUTE_DURATION"]:
                        if potential_volume < config["SAFE_LEVEL"]:
                            app_states[name][3] += 1
                            # Must be safe for 50 cycles BEFORE touching volume
                            if app_states[name][3] >= 50:
                                if config["USE_MUTE"]: volume_control.SetMute(0, None)

                                # --- EXPONENTIAL SWELL ---
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
                        app_states[name][3] = 0

            # --- VISUALS ---
            bar = '█' * int(25 * min(max_true_level, 1.0)) + '-' * (25 - int(25 * min(max_true_level, 1.0)))
            os.system('color 0c' if any_protected else 'color 0b')
            status = f"⚠️ [LOCKED] {protected_name[:12]}" if any_protected else f"[OK] {loudest_app[:12]}"
            print(f"\r{status:<18} |{bar}| {int(max_true_level * 100):3}%", end="", flush=True)

    except KeyboardInterrupt:
        os.system('color 07')
        for session in AudioUtilities.GetAllSessions():
            if session.Process: session._ctl.QueryInterface(ISimpleAudioVolume).SetMute(0, None)
        print("\n\n🐾 Bear is sleeping.")


def main_menu():
    while True:
        config = load_config()
        os.system('color 0e');
        os.system('cls' if os.name == 'nt' else 'clear')
        mode = "MUTE" if config["USE_MUTE"] else f"DROP TO {int(config['LOWER_PERCENT'] * 100)}%"
        print("=======================================")
        print("        🐾 BEAR AUDIO LIMITER          ")
        print("=======================================")
        print(f" LIMIT: {int(config['THRESHOLD'] * 100)}% | ACTION: {mode}")
        print("=======================================")
        print("1. Start Limiter\n2. Setup / Settings\n3. Help / Info\n4. Exit")
        c = input("Select: ").strip()
        if c == '1':
            run_limiter(config)
        elif c == '2':
            setup_menu(config)
        elif c == '3':
            show_help(config)
        elif c == '4':
            sys.exit()


if __name__ == "__main__": main_menu()