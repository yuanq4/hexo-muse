import matplotlib.pyplot as plt
import numpy as np
from muselsl import stream, list_muses
from pylsl import StreamInlet, resolve_byprop
import threading
import asyncio
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

EEG_CHANNELS = ['TP9', 'AF7', 'AF8', 'TP10']

def plot_eeg_data():
    """Plot EEG data in real-time from a Muse stream."""
    print("Resolving EEG stream...")
    streams = resolve_byprop('type', 'EEG', timeout=2)
    if not streams:
        print("No EEG stream found.")
        return

    inlet = StreamInlet(streams[0])

    fig, axs = plt.subplots(len(EEG_CHANNELS), 1, figsize=(10, 8))
    plt.ion()

    for ax in axs:
        ax.set_ylim([-500, 500])
        ax.set_xlim([0, 100])

    lines = [ax.plot(np.zeros(100))[0] for ax in axs]
    fig.show()
    fig.canvas.draw()

    try:
        while True:
            sample, timestamp = inlet.pull_sample()
            if sample:
                for i, channel in enumerate(EEG_CHANNELS):
                    ydata = lines[i].get_ydata()
                    ydata = np.append(ydata[1:], sample[i])
                    lines[i].set_ydata(ydata)
                    axs[i].draw_artist(axs[i].patch)
                    axs[i].draw_artist(lines[i])

                fig.canvas.draw()
                fig.canvas.flush_events()
    except KeyboardInterrupt:
        pass

async def start_stream(address):
    await stream(address)

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
            plot_thread = threading.Thread(target=plot_eeg_data)
            plot_thread.start()
            await stream_task
        except KeyboardInterrupt:
            print("Stopping stream...")
        finally:
            print("Stream has ended")
            stream_task.cancel()
            await stream_task
            plot_thread.join()
    else:
        print(f"No Muse device found with the name {muse_name}.")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
