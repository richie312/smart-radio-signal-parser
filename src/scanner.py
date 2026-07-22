import time
from controller import RadioController

def run_synchronized_exploration_sweep():
    radio = RadioController()
    
    # --- FM BROADCAST MICRO-SCAN CONFIGURATION ---
    # Targets a highly active local FM station core frequency
    start_freq = 91100000  # 91.100000 MHz
    end_freq   = 91105000  # 91.105000 MHz (Tracking a tight 5 kHz window)
    
    # 500 Hz step size allows you to hear the audio drift slightly 
    # away from the perfect center without taking forever to sweep
    step_size  = 500        
    
    # 1.0 second pause per step to analyze audio quality updates
    dwell_time = 1.0        
    
    print(f"\n--- Initializing FM Wideband Micro-Sweep ---")
    print(f"Target Range: {start_freq/1e6:.6f} MHz to {end_freq/1e6:.6f} MHz")
    print(f"Config Dwell: {dwell_time} second | Step Size: {step_size} Hz")
    print("[Action Required] Set Demodulator to WFM and increase Bandwidth to 180000+ in SDR++!\n")
    


    print(f"\n--- Initializing Synchronized Spectrum Mapping Sweep ---")
    print("Watching the SDR++ GUI update its frequency display in real-time...")
    
    current_freq = start_freq
    while current_freq <= end_freq:
        # 1. Send the command to update the software tuner
        if not radio.tune_frequency(current_freq):
            print("[Error] Failed to connect to Rigctl Server.")
            break
            
        # 2. Wait for the graphic waterfall to transition
        time.sleep(dwell_time)
        
        # 3. Query the hardware to confirm it successfully shifted coordinates
        confirmed_freq = radio.verify_active_frequency()
        freq_mhz = current_freq / 1e6
        
        if confirmed_freq == current_freq:
            print(f"[TUNED] {freq_mhz:.1f} MHz | Network Sync: OK ✅ | Status: Monitoring Spectrum")
        else:
            print(f"[TUNED] {freq_mhz:.1f} MHz | Network Sync: MISMATCH ❌")
            
        current_freq += step_size
        
    print("\n--- Spectrum Mapping Sweep Finished ---")

if __name__ == "__main__":
    # Call the exact matched function name
    run_synchronized_exploration_sweep()
