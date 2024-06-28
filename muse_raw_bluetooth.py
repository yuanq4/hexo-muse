import csv
from datetime import datetime
from muselsl import stream, list_muses
from pylsl import StreamInlet, resolve_byprop
import threading
import asyncio
import nest_asyncio
import os
import signal

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

EEG_CHANNELS = ['TP9', 'AF7', 'AF8', 'TP10', 'Right AUX']

stop_event = threading.Event()

def store_eeg_data():
    """Store EEG data in real-time from a Muse stream with timestamps."""
    print("Resolving EEG stream...")
    streams = resolve_byprop('type', 'EEG', timeout=2)
    if not streams:
        print("No EEG stream found.")
        return

    inlet = StreamInlet(streams[0])

    # Ensure the 'data' directory exists
    os.makedirs('data', exist_ok=True)

    # Open a CSV file for writing
    filename = f"data/eeg_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    try:
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            # Write the header row
            writer.writerow(['timestamp'] + EEG_CHANNELS)

            print(f"Storing EEG data to {filename}")
            try:
                while not stop_event.is_set():
                    sample, timestamp = inlet.pull_sample()
                    if sample:
                        # Write the sample with timestamp to the CSV file
                        writer.writerow([datetime.fromtimestamp(timestamp).isoformat()] + sample)
            except KeyboardInterrupt:
                pass
    except Exception as e:
        print(f"Failed to write to CSV file: {e}")

async def start_stream(address):
    await stream(address, ppg_enabled=False, acc_enabled=False, gyro_enabled=False)

async def main_async():
    muse_name = "MuseS-7C3A"
    muses = list_muses()
    target_muse = None

    for muse in muses:
        if muse['name'] == muse_name:
            target_muse = muse
            break

    if target_muse:
        print(f"Streaming from {target_muse['name']}...")

        stream_task = asyncio.create_task(start_stream(target_muse['address']))

        try:
            store_thread = threading.Thread(target=store_eeg_data)
            store_thread.start()
            await stream_task
        except KeyboardInterrupt:
            print("Stopping stream...")
        finally:
            print("Stream has ended")
            stop_event.set()
            store_thread.join()
            if not stream_task.cancelled():
                stream_task.cancel()
            await asyncio.sleep(1)  # Give some time for the task to cancel
    else:
        print(f"No Muse device found with the name {muse_name}.")

def handle_exit(signum, frame):
    print("Received exit signal. Stopping...")
    stop_event.set()

def main():
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
