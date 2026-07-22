import asyncio

# --- CONFIGURATION CONSTANTS ---
IP = "127.0.0.1"
PORT = 4532                  # Your active, working Rigctl Server port

async def send_rigctl_command(command_str):
    """
    Opens a non-blocking network socket, sends a control string to SDR++, 
    and captures the return validation message.
    """
    try:
        reader, writer = await asyncio.open_connection(IP, PORT)
        
        formatted_cmd = f"{command_str}\n".encode('utf-8')
        writer.write(formatted_cmd)
        await writer.drain()
        
        response = await reader.read(1024)
        decoded_resp = response.decode('utf-8').strip()
        
        writer.close()
        await writer.wait_closed()
        return decoded_resp
    except Exception:
        return "ERROR"

async def run_async_flight_trigger_system():
    print(f"\n--- Launching Async Rigctl Flight Trigger Engine ---")
    print(f"Monitoring SDR++ active VFO state on port {PORT}...")
    print("Mode: Manual Tuning Mode Enabled (Steer frequencies inside the GUI).")
    print("Standing by... Squelch activity will automatically map to the recorder...")

    is_recording = False
    consecutive_silence_ticks = 0

    while True:
        # 1. Ask the active Rigctl server if the squelch gate is open
        # 'x' is the rigctl protocol token to query squelch activity
        squelch_reply = await send_rigctl_command("x")
        
        # 2. Evaluate transmission states
        if "1" in squelch_reply:
            print("🎤", end="", flush=True) # Voice signal detected breaking through!
            consecutive_silence_ticks = 0    # Reset our hang-up countdown timer
            
            if not is_recording:
                print("\n[TRANSMISSION DETECTED] -> Triggering SDR++ GUI Recorder...")
                await send_rigctl_command("R 1") # Remotely click the Record button ON [1.1]
                is_recording = True
                
        elif "0" in squelch_reply:
            print(".", end="", flush=True) # Stationary static background noise / silence
            
            if is_recording:
                consecutive_silence_ticks += 1
                
                # If dead silence lasts for ~1.5 seconds, the pilot has stopped speaking
                if consecutive_silence_ticks > 15:
                    print("\n[TRANSMISSION ENDED] -> Stopping SDR++ GUI Recorder.")
                    await send_rigctl_command("R 0") # Remotely click the Record button OFF [1.1]
                    is_recording = False
                    consecutive_silence_ticks = 0
        else:
            print("\n[Warning] Rigctl handshake missed. Reconnecting stream...")
            await asyncio.sleep(1.5)

        # Pause asynchronously for 100ms before auditing the spectrum grid again
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    try:
        asyncio.run(run_async_flight_trigger_system())
    except KeyboardInterrupt:
        print("\n[Shutting Down] Rigctl flight trigger closed safely.")
