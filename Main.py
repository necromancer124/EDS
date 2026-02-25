from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import time

# --- SETTINGS ---
THRESHOLD = 0.40
MUTE_DURATION = 2
SAFE_LEVEL = 0.35
CHECK_INTERVAL = 0.01
USE_MUTE = False      # True = mute, False = lower to 10%
LOWER_PERCENT = 0.10  # 10%


def lowerVolume(volume):
    original_volume = volume.GetMasterVolumeLevelScalar()
    volume.SetMasterVolumeLevelScalar(LOWER_PERCENT, None)
    return original_volume


def fade_up(volume, target_volume):
    step = 0.02
    while volume.GetMasterVolumeLevelScalar() < target_volume:
        current = volume.GetMasterVolumeLevelScalar()
        volume.SetMasterVolumeLevelScalar(
            min(current + step, target_volume),
            None
        )
        time.sleep(0.05)


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
    original_volume = None

    try:
        while True:
            raw_peak = meter.GetPeakValue()
            master_vol = volume.GetMasterVolumeLevelScalar()

            # Conditional detection logic
            if USE_MUTE:
                actual_level = raw_peak * master_vol
            else:
                actual_level = raw_peak

            line_output = ""

            # 1. Trigger
            if actual_level > THRESHOLD and not muted_by_script:
                trigger_level = actual_level * 100
                mute_time = time.time()
                muted_by_script = True

                if USE_MUTE:
                    volume.SetMute(1, None)
                else:
                    original_volume = lowerVolume(volume)

            # 2. Maintenance
            if muted_by_script:
                elapsed = time.time() - mute_time

                if elapsed < MUTE_DURATION:
                    countdown = MUTE_DURATION - elapsed
                    action = "MUTED" if USE_MUTE else "LOWERED"
                    line_output = f"[{action}] Too Loud ({trigger_level:.1f}%) | Wait: {countdown:.1f}s"
                else:
                    # Stay low until truly safe
                    if actual_level < SAFE_LEVEL:
                        if USE_MUTE:
                            volume.SetMute(0, None)
                        else:
                            if original_volume is not None:
                                fade_up(volume, original_volume)

                        muted_by_script = False
                    else:
                        line_output = f"[WAIT] Still loud ({actual_level * 100:.1f}%)"

            # 3. Normal View
            if not muted_by_script:
                bar = '█' * int(30 * actual_level) + '-' * (30 - int(30 * actual_level))
                line_output = f"[OK] Level: [{bar}] {actual_level * 100:5.1f}%"

            print(f"\r{line_output:<80}", end="", flush=True)
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        volume.SetMute(0, None)
        print("\n\nExiting and Restoring...")


if __name__ == "__main__":
    main()