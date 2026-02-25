from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import time

# --- SETTINGS ---
THRESHOLD = 0.40
SAFE_LEVEL = 0.35
CHECK_INTERVAL = 0.01

USE_MUTE = False
LOWER_PERCENT = 0.10
WAIT_TIME = 1.0


def main():
    devices = AudioUtilities.GetDeviceEnumerator()
    endpoint = devices.GetDefaultAudioEndpoint(0, 0)

    meter_interface = endpoint.Activate(
        IAudioMeterInformation._iid_, CLSCTX_ALL, None
    )
    meter = cast(meter_interface, POINTER(IAudioMeterInformation))

    volume_interface = endpoint.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
    )
    volume = cast(volume_interface, POINTER(IAudioEndpointVolume))

    print("--- Limiter Active ---")
    print("Monitoring... (Ctrl+C to stop)")

    protected = False
    original_volume = None

    try:
        while True:
            raw_peak = meter.GetPeakValue()
            master_vol = volume.GetMasterVolumeLevelScalar()
            actual_level = raw_peak * master_vol

            line_output = ""

            # --- Trigger ---
            if actual_level > THRESHOLD and not protected:
                protected = True
                original_volume = master_vol

                if USE_MUTE:
                    volume.SetMute(1, None)
                else:
                    volume.SetMasterVolumeLevelScalar(LOWER_PERCENT, None)

                time.sleep(WAIT_TIME)

            # --- Protection Logic ---
            if protected:

                # Restore previous level
                if USE_MUTE:
                    volume.SetMute(0, None)
                else:
                    volume.SetMasterVolumeLevelScalar(original_volume, None)

                time.sleep(WAIT_TIME)

                # Re-check output level
                raw_peak = meter.GetPeakValue()
                master_vol = volume.GetMasterVolumeLevelScalar()
                actual_level = raw_peak * master_vol

                if actual_level < SAFE_LEVEL:
                    protected = False
                    original_volume = None
                else:
                    # Still loud → go back to 10%
                    if USE_MUTE:
                        volume.SetMute(1, None)
                    else:
                        volume.SetMasterVolumeLevelScalar(LOWER_PERCENT, None)

            # --- Visual Display ---
            if not protected:
                bar = '█' * int(30 * actual_level) + '-' * (
                    30 - int(30 * actual_level)
                )
                line_output = f"[OK] Level: [{bar}] {actual_level * 100:5.1f}%"
            else:
                line_output = f"[PROTECT] Level: {actual_level * 100:5.1f}%"

            print(f"\r{line_output:<80}", end="", flush=True)
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        volume.SetMute(0, None)
        print("\n\nExiting and Restoring...")


if __name__ == "__main__":
    main()