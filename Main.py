from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import time

# --- SETTINGS ---
THRESHOLD = 0.40
MUTE_DURATION = 5
SAFE_LEVEL = 0.35
CHECK_INTERVAL = 0.01


def main():
    devices = AudioUtilities.GetDeviceEnumerator()
    endpoint = devices.GetDefaultAudioEndpoint(0, 0)

    meter_interface = endpoint.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
    meter = cast(meter_interface, POINTER(IAudioMeterInformation))

    volume_interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(volume_interface, POINTER(IAudioEndpointVolume))

    print("--- Limiter Active ---")
    print("Monitoring... (Press Ctrl+C to stop)")

    muted_by_script = False
    mute_time = 0
    trigger_level = 0

    try:
        while True:
            raw_peak = meter.GetPeakValue()
            master_vol = volume.GetMasterVolumeLevelScalar()
            actual_level = raw_peak * master_vol
            current_mute_state = volume.GetMute()

            line_output = ""

            # 1. Trigger Mute
            if actual_level > THRESHOLD and not muted_by_script:
                volume.SetMute(1, None)
                muted_by_script = True
                mute_time = time.time()
                trigger_level = actual_level * 100  # Store what it was for the display

            # 2. Mute Maintenance & Unmute Logic
            if muted_by_script:
                if current_mute_state == 0:
                    volume.SetMute(1, None)

                elapsed = time.time() - mute_time

                if elapsed < MUTE_DURATION:
                    # Still in the forced mute period
                    countdown = MUTE_DURATION - elapsed
                    line_output = f"[MUTED] Too Loud ({trigger_level:.1f}%) | Wait: {countdown:.1f}s"
                else:
                    # Time is up, but is it safe?
                    if raw_peak < SAFE_LEVEL:
                        volume.SetMute(0, None)
                        muted_by_script = False
                    else:
                        line_output = f"[WAIT] Still loud ({raw_peak * 100:.1f}%) | Waiting for silence..."

            # 3. Normal Operating View
            if not muted_by_script:
                bar = '█' * int(30 * actual_level) + '-' * (30 - int(30 * actual_level))
                line_output = f"[OK] Level: [{bar}] {actual_level * 100:5.1f}%"

            # Clear and rewrite whole line
            # The extra spaces at the end ensure old long messages are wiped
            print(f"\r{line_output:<80}", end="", flush=True)

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        volume.SetMute(0, None)
        print("\n\nExiting and Unmuting...")


if __name__ == "__main__":
    main()