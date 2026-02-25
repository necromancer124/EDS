from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import time

# --- SETTINGS ---
THRESHOLD = 0.25  # Trigger protection when actual output > 25%
SAFE_LEVEL = 0.20  # Peak must drop below this to restore
MUTE_DURATION = 2.0  # Seconds to stay protected before testing again
CHECK_INTERVAL = 0.01

USE_MUTE = False  # True = Mute completely, False = Lower volume
LOWER_PERCENT = 0.20  # Volume level for "Lowered" mode (20%)


def main():
    # Initialize Audio Devices
    devices = AudioUtilities.GetDeviceEnumerator()
    endpoint = devices.GetDefaultAudioEndpoint(0, 0)

    meter_interface = endpoint.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
    meter = cast(meter_interface, POINTER(IAudioMeterInformation))

    volume_interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(volume_interface, POINTER(IAudioEndpointVolume))

    print("--- Limiter Active ---")
    print(f"Monitoring... Trigger: {THRESHOLD * 100}% | Safe: {SAFE_LEVEL * 100}%")

    protected = False
    protection_start_time = 0
    trigger_level = 0
    original_volume = None

    try:
        while True:
            # 1. CHECK THE SOUND FIRST
            raw_peak = meter.GetPeakValue()
            master_vol = volume.GetMasterVolumeLevelScalar()
            actual_level = raw_peak * master_vol

            line_output = ""

            # 2. TRIGGER IF TOO LOUD
            if actual_level > THRESHOLD and not protected:
                trigger_level = actual_level * 100
                protection_start_time = time.time()
                protected = True
                original_volume = master_vol

                if USE_MUTE:
                    volume.SetMute(1, None)
                else:
                    volume.SetMasterVolumeLevelScalar(LOWER_PERCENT, None)

            # 3. PROTECTION LOGIC & VISUALS
            if protected:
                elapsed = time.time() - protection_start_time

                if elapsed < MUTE_DURATION:
                    # Counting down until the next check
                    countdown = MUTE_DURATION - elapsed
                    action_text = "MUTED" if USE_MUTE else "LOWERED"
                    line_output = f"[{action_text}] Too Loud ({trigger_level:.1f}%) | Wait: {countdown:.1f}s"
                else:
                    # --- THE SAFE CHECK SEQUENCE ---
                    line_output = "[CHECKING] Testing volume safely..."
                    print(f"\r{line_output:<85}", end="", flush=True)

                    # A. Mute first to prevent a sudden loud blast
                    volume.SetMute(1, None)

                    # B. Restore the original volume level behind the mute
                    volume.SetMasterVolumeLevelScalar(original_volume, None)

                    # C. Give the system a tiny fraction of a second to register the new peak
                    time.sleep(0.1)

                    # D. Check the actual level now that volume is restored
                    check_peak = meter.GetPeakValue()
                    check_level = check_peak * original_volume

                    # E. Decide what to do next
                    if check_level < SAFE_LEVEL:
                        # It is safe! Unmute and exit protection mode.
                        volume.SetMute(0, None)
                        protected = False
                    else:
                        # Still too loud!
                        if not USE_MUTE:
                            # Go back to the lowered percentage, then unmute so you can hear it
                            volume.SetMasterVolumeLevelScalar(LOWER_PERCENT, None)
                            volume.SetMute(0, None)

                        # Reset the timer so it waits another MUTE_DURATION before testing again
                        protection_start_time = time.time()

            # 4. NORMAL VISUAL (Only displays if we are not protected)
            if not protected:
                bar_len = 30
                filled = int(bar_len * actual_level)
                bar = '█' * min(filled, bar_len) + '-' * max(0, bar_len - filled)
                line_output = f"[OK] Level: [{bar}] {actual_level * 100:5.1f}%"

            # Print to console and overwrite the line
            if protected and elapsed >= MUTE_DURATION:
                pass  # Skip the regular print during the checking phase so we don't overwrite the [CHECKING] text too fast
            else:
                print(f"\r{line_output:<85}", end="", flush=True)

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        # Restore on exit
        volume.SetMute(0, None)
        if original_volume is not None:
            volume.SetMasterVolumeLevelScalar(original_volume, None)
        print("\n\nExiting... Volume Restored.")


if __name__ == "__main__":
    main()