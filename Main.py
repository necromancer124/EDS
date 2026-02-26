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
    os.system('cls' if os.name == 'nt' else 'clear')
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
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=======================================")
    print("        🐾 BEAR LIMITER HELP          ")
    print("=======================================")
    print(f"Trigger: {int(config['THRESHOLD'] * 100)}% | Safe: {int(config['SAFE_LEVEL'] * 100)}%")
    print("---------------------------------------")
    print("PREDICTION CALCULATION:")
    print("Bear calculates: RawPeak * SavedVol * Master")
    print("This allows Bear to 'see' the spike even")
    print("while the app is muffled or muted.")
    print("=======================================")
    input("\nPress Enter to return...")


def run_limiter(config):
    # Initial clear once at the start
    os.system('cls' if os.name == 'nt' else 'clear')
    print("--- 🐾 BEAR PROTECT ACTIVE ---")
    print("PREDICTION MODE | Ctrl+C to stop.\n")

    devices = AudioUtilities.GetDeviceEnumerator()
    endpoint = devices.GetDefaultAudioEndpoint(0, 0)
    master_interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    master_vol_control = master_interface.QueryInterface(IAudioEndpointVolume)
    app_states = {}

    last_was_protected = False

    try:
        while True:
            global_master = master_vol_control.GetMasterVolumeLevelScalar()
            sessions = AudioUtilities.GetAllSessions()
            max_view_level, loudest_app, any_protected, protected_name = 0.0, "", False, ""

            for session in sessions:
                if not session.Process: continue
                name = session.Process.name()
                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                volume_control = session._ctl.QueryInterface(ISimpleAudioVolume)

                raw_peak = meter.GetPeakValue()
                app_mixer = volume_control.GetMasterVolume()
                true_actual = raw_peak * app_mixer * global_master

                if name not in app_states: app_states[name] = [app_mixer, 0, False, 0]

                # --- 1. THE TRIGGER ---
                if not app_states[name][2] and true_actual > config["THRESHOLD"]:
                    app_states[name][0] = app_mixer
                    app_states[name][1] = time.time()
                    app_states[name][2] = True
                    if config["USE_MUTE"]:
                        volume_control.SetMute(1, None)
                    else:
                        volume_control.SetMasterVolume(config["LOWER_PERCENT"], None)

                # --- 2. PREDICTION & RESTORE LOGIC ---
                if app_states[name][2]:
                    any_protected, protected_name = True, name
                    elapsed = time.time() - app_states[name][1]
                    potential_volume = raw_peak * app_states[name][0] * global_master

                    if potential_volume > max_view_level: max_view_level = potential_volume

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
                        loudest_app = name

            # --- VISUALS (FIXED FLICKER) ---
            # Instead of os.system('color'), we use ANSI colors to avoid screen flash
            RED = "\033[91m"
            CYAN = "\033[96m"
            RESET = "\033[0m"

            bar_len = int(25 * min(max_view_level, 1.0))
            bar = '█' * bar_len + '-' * (25 - bar_len)

            color = RED if any_protected else CYAN
            status = f"⚠️ [PREDICT] {protected_name[:10]}" if any_protected else f"[OK] {loudest_app[:10]}"

            # \r moves cursor to start of line, \033[K clears the rest of the line
            print(f"\r{color}{status:<18} |{bar}| {int(max_view_level * 100):3}%{RESET}\033[K", end="", flush=True)

            time.sleep(0.01)  # Small delay to prevent CPU pegging

    except KeyboardInterrupt:
        # Reset colors and unmute all on exit
        print("\033[0m")
        for session in AudioUtilities.GetAllSessions():
            if session.Process:
                try:
                    session._ctl.QueryInterface(ISimpleAudioVolume).SetMute(0, None)
                except:
                    pass
        print("\n\n🐾 Bear is sleeping.")


def main_menu():
    # Enable ANSI support for Windows 10+
    os.system('')
    while True:
        config = load_config()
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