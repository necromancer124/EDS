from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, ISimpleAudioVolume
import time
import sys

# --- SETTINGS ---
THRESHOLD = 0.25  # 25% Trigger
SAFE_LEVEL = 0.20  # 20% Safe to return
MUTE_DURATION = 2.0
USE_MUTE = False  # True = Mute app, False = Lower to 20%
LOWER_PERCENT = 0.20


def main():
    print("--- Per-App Limiter Active (Single Line Mode) ---")
    app_states = {}  # { "Name": [original_vol, start_time, is_protected, safe_ticks] }

    try:
        while True:
            sessions = AudioUtilities.GetAllSessions()
            loudest_app = ""
            max_level = 0.0
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

                orig_vol, start_time, is_protected, safe_ticks = app_states[name]
                predicted_actual = raw_peak * orig_vol

                # Update max level for display
                if predicted_actual > max_level:
                    max_level = predicted_actual
                    loudest_app = name

                # --- TRIGGER ---
                if not is_protected and predicted_actual > THRESHOLD:
                    app_states[name][0] = volume_control.GetMasterVolume()
                    app_states[name][1] = time.time()
                    app_states[name][2] = True
                    if USE_MUTE:
                        volume_control.SetMute(1, None)
                    else:
                        volume_control.SetMasterVolume(LOWER_PERCENT, None)

                # --- RESTORE ---
                elif is_protected:
                    any_protected = True
                    protected_name = name
                    elapsed = time.time() - start_time
                    if elapsed > MUTE_DURATION and predicted_actual < SAFE_LEVEL:
                        app_states[name][3] += 1
                        if app_states[name][3] > 15:  # Stability check
                            if USE_MUTE:
                                volume_control.SetMute(0, None)
                            else:
                                volume_control.SetMasterVolume(orig_vol, None)
                            app_states[name][2] = False
                    else:
                        app_states[name][3] = 0

            # --- SINGLE LINE VISUALS ---
            if any_protected:
                line = f"[PROTECT] {protected_name} is BLOCKED | Level: {max_level * 100:5.1f}%"
            elif max_level > 0.001:
                bar_len = 30
                filled = int(bar_len * max_level)
                bar = '█' * filled + '-' * (bar_len - filled)
                line = f"[OK] {loudest_app[:12]}: [{bar}] {max_level * 100:5.1f}%"
            else:
                line = "[IDLE] Monitoring..."

            # \r moves back to start of line, <80 pads it to clear old text
            print(f"\r{line:<80}", end="", flush=True)
            time.sleep(0.02)

    except KeyboardInterrupt:
        # Cleanup
        for session in AudioUtilities.GetAllSessions():
            if session.Process:
                vc = session._ctl.QueryInterface(ISimpleAudioVolume)
                vc.SetMute(0, None)
        print("\n\nExiting and Restoring...")


if __name__ == "__main__":
    main()