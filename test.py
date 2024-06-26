import numpy as np
import pandas as pd
from time import time, strftime, gmtime
from optparse import OptionParser
from pylsl import StreamInlet, resolve_byprop
from sklearn.linear_model import LinearRegression
import datetime
import pytz

# Default filename with current time
default_fname = ("data_%s.csv" % strftime("%Y-%m-%d-%H.%M.%S", gmtime()))

# Set up option parser
parser = OptionParser()
parser.add_option("-d", "--duration",
                  dest="duration", type='int', default=36000,  # 10 hours in seconds
                  help="Duration of the recording in seconds.")
parser.add_option("-f", "--filename",
                  dest="filename", type='str', default=default_fname,
                  help="Name of the recording file.")

# dejitter timestamps
dejitter = False

(options, args) = parser.parse_args()

print("Looking for an EEG stream...")
streams = resolve_byprop('type', 'EEG', timeout=2)

if len(streams) == 0:
    raise RuntimeError("Can't find EEG stream")

print("Start acquiring data")
inlet = StreamInlet(streams[0], max_chunklen=12)
eeg_time_correction = inlet.time_correction()

info = inlet.info()
description = info.desc()

freq = info.nominal_srate()
Nchan = info.channel_count()

ch = description.child('channels').first_child()
ch_names = [ch.child_value('label')]
for i in range(1, Nchan):
    ch = ch.next_sibling()
    ch_names.append(ch.child_value('label'))

res = []
timestamps = []
t_init = time()
print('Start recording at time t=%.3f' % t_init)
while (time() - t_init) < options.duration:
    try:
        data, timestamp = inlet.pull_chunk(timeout=1.0, max_samples=12)
        if timestamp:
            res.append(data)
            timestamps.extend(timestamp)
    except KeyboardInterrupt:
        break

res = np.concatenate(res, axis=0)
timestamps = np.array(timestamps)

if dejitter:
    y = timestamps
    X = np.atleast_2d(np.arange(0, len(y))).T
    lr = LinearRegression()
    lr.fit(X, y)
    timestamps = lr.predict(X)

# Correct timestamps by adding t_init
corrected_timestamps = timestamps + eeg_time_correction + (t_init - timestamps[0])

# Convert timestamps to local time and format them
new_york_tz = pytz.timezone('America/New_York')
timestamps_local = [datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).astimezone(new_york_tz).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] for ts in corrected_timestamps]

res = np.c_[timestamps_local, res]
data = pd.DataFrame(data=res, columns=['timestamps'] + ch_names)

data.to_csv(options.filename, float_format='%.3f', index=False)

print('Done!')
