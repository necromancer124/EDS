from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import time

# --- SETTINGS ---
THRESHOLD = 0.40
SAFE_LEVEL = 0.35
CHECK_INTERVAL = 0.01

USE_MUTE = False      # True = mute, False = lower to 10%
LOWER_PERCENT = 0.10  # 10%

STEP_UP = 0.02
STEP_DOWN = 0.05


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

            # Always use output-based detection
            actual_level = raw_peak * master_vol

            line_output = ""

            # Trigger
            if actual_level > THRESHOLD and not protected:
                protected = True

                if USE_MUTE:
                    volume.SetMute(1, None)
                else:
                    original_volume = master_vol
                    volume.SetMasterVolumeLevelScalar(LOWER_PERCENT, None)

            # Protection mode
            if protected:

                current_volume = volume.GetMasterVolumeLevelScalar()

                # If still too loud → step down
                if actual_level > SAFE_LEVEL:

                    if not USE_MUTE:
                        new_volume = max(
                            current_volume - STEP_DOWN,
                            LOWER_PERCENT
                        )
                        volume.SetMasterVolumeLevelScalar(new_volume, None)
                        line_output = f"[STEP DOWN] {new_volume * 100:.1f}%"
                    else:
                        line_output = "[MUTED] Waiting..."

                else:
                    # Safe → step up
                    if USE_MUTE:
                        volume.SetMute(0, None)
                        protected = False
                    else:
                        if current_volume < original_volume:
                            new_volume = min(
                                current_volume + STEP_UP,
                                original_volume
                            )
                            volume.SetMasterVolumeLevelScalar(
                                new_volume, None
                            )
                            line_output = f"[FADING UP] {new_volume * 100:.1f}%"
                        else:
                            # Fully restored
                            protected = False
                            original_volume = None

            # Normal display
            if not protected:
                bar = '█' * int(30 * actual_level) + '-' * (
                    30 - int(30 * actual_level)
                )
                line_output = f"[OK] Level: [{bar}] {actual_level * 100:5.1f}%"

            print(f"\r{line_output:<80}", end="", flush=True)
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        volume.SetMute(0, None)
        print("\n\nExiting and Restoring...")


if __name__ == "__main__":
    main()