from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import time

# --- SETTINGS ---
THRESHOLD = 0.25  #"Real" loudness limit
MUTE_DURATION = 5  # Minimum time to stay muted
SAFE_LEVEL = 0.15  # Raw signal must drop below this before unmuting
CHECK_INTERVAL = 0.05


def main():
    devices = AudioUtilities.GetDeviceEnumerator()
    endpoint = devices.GetDefaultAudioEndpoint(0, 0)

    meter_interface = endpoint.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
    meter = cast(meter_interface, POINTER(IAudioMeterInformation))

    volume_interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(volume_interface, POINTER(IAudioEndpointVolume))

    print(f"--- Stubborn 40% Limiter Active ---")
    print(f"Monitoring... (Will force mute even if you move the slider)")

    muted_by_script = False
    mute_time = 0

    try:
        while True:
            # 1. Get raw signal and master volume
            raw_peak = meter.GetPeakValue()
            master_vol = volume.GetMasterVolumeLevelScalar()
            actual_level = raw_peak * master_vol

            # Check if Windows unmuted itself behind the script's back
            current_mute_state = volume.GetMute()

            # 2. Logic: Should we Mute?
            if actual_level > THRESHOLD and not muted_by_script:
                volume.SetMute(1, None)
                muted_by_script = True
                mute_time = time.time()
                print(f"\n[!] LIMIT HIT: {actual_level * 100:.1f}% - Muting...")

            # 3. Logic: Maintenance (Force mute if Windows tries to unmute)
            if muted_by_script:
                # If Windows unmuted but our timer isn't done, force it back to Mute
                if current_mute_state == 0:
                    volume.SetMute(1, None)

                elapsed = time.time() - mute_time
                if elapsed >= MUTE_DURATION:
                    if raw_peak < SAFE_LEVEL:
                        volume.SetMute(0, None)
                        muted_by_script = False
                        print(f"\n[✓] SAFE: Unmuted (Signal: {raw_peak * 100:.1f}%)")
                    else:
                        print(f"\r[WAIT] Still loud... Signal: {raw_peak * 100:>5.1f}%", end="")

            # Visual feedback
            if not muted_by_script:
                bar = '█' * int(30 * actual_level) + '-' * (30 - int(30 * actual_level))
                print(f"\r[OK] Level: [{bar}] {actual_level * 100:>5.1f}%", end="", flush=True)

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        volume.SetMute(0, None)
        print("\n\nExiting and Unmuting...")


if __name__ == "__main__":
    main()