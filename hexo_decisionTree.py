import os
import pandas as pd
import numpy as np
from scipy.signal import find_peaks

class SleepDataProcessor:
    def __init__(self, file_path, epoch_length=20, thresholds=None, corrected_thresholds=None):
        self.file_path = file_path
        self.epoch_length = epoch_length
        self.thresholds = thresholds if thresholds is not None else [0.5, 1.1, 0.6]
        self.corrected_thresholds = corrected_thresholds if corrected_thresholds is not None else [0.5, 1.2, 0.6]
        self.data = None
        self.time_seconds = None
        self.hr_epochs = None
        self.br_epochs = None
        self.activity_epochs = None
        self.classification = None
        self.classification_corrected = None

    def load_data(self):
        self.data = pd.read_csv(self.file_path)
        self.time_seconds = self.data['time [s/256]'] / 256

    def preprocess_signals(self):
        def preprocess_signal(signal):
            return signal.dropna()

        self.hr = preprocess_signal(self.data['heart_rate [bpm](/api/datatype/19/)'])
        self.br = preprocess_signal(self.data['breathing_rate [rpm](/api/datatype/33/)'])
        self.activity = preprocess_signal(self.data['activity [g](/api/datatype/49/)'])

    def segment_into_epochs(self):
        def segment_signal(time, signal, epoch_length):
            start_time = time.iloc[0]
            epochs = []
            current_epoch = []
            for t, d in zip(time, signal):
                if t - start_time < epoch_length:
                    current_epoch.append(d)
                else:
                    epochs.append(current_epoch)
                    start_time = t
                    current_epoch = [d]
            if current_epoch:
                epochs.append(current_epoch)
            return np.array([np.mean(epoch) for epoch in epochs if len(epoch) > 0])

        self.hr_epochs = segment_signal(self.time_seconds, self.hr, self.epoch_length)
        self.br_epochs = segment_signal(self.time_seconds, self.br, self.epoch_length)
        self.activity_epochs = segment_signal(self.time_seconds, self.activity, self.epoch_length)

    def handle_artifacts(self):
        def detect_artifacts(signal, threshold=3):
            artifacts = np.abs(signal - np.nanmean(signal)) > threshold * np.nanstd(signal)
            signal[artifacts] = np.nan
            return signal

        def fill_nan_with_last_valid(signal):
            valid_idx = np.where(~np.isnan(signal))[0]
            if valid_idx.size == 0:
                return signal
            last_valid = valid_idx[0]
            for i in range(len(signal)):
                if np.isnan(signal[i]):
                    signal[i] = signal[last_valid]
                else:
                    last_valid = i
            return signal

        self.hr_epochs = fill_nan_with_last_valid(detect_artifacts(self.hr_epochs))
        self.br_epochs = fill_nan_with_last_valid(detect_artifacts(self.br_epochs))
        self.activity_epochs = fill_nan_with_last_valid(detect_artifacts(self.activity_epochs))

    def compute_variability(self):
        def compute_hrv(hr, q=20):
            return np.array([np.mean(np.abs(hr[max(0, i-q):i+q+1] - hr[max(0, i+1-q):i+q+2])) for i in range(len(hr))])

        def compute_brv(br, q=20):
            return np.array([np.mean(np.abs(br[max(0, i-q):i+q+1] - br[max(0, i+1-q):i+q+2])) for i in range(len(br))])

        def compute_body_movement(activity, p=0.01):
            return np.log2(p + activity)

        self.hrv = compute_hrv(self.hr_epochs)
        self.brv = compute_brv(self.br_epochs)
        self.body_movement = compute_body_movement(self.activity_epochs)

    def classify_sleep_stages(self, thresholds):
        def classify(hrv, brv, body_movement, thresholds):
            k1, k2, k3 = thresholds
            mean_hrv = np.mean(hrv)
            mean_brv = np.mean(brv)
            mean_body_movement = np.mean(body_movement)
            
            rem_sleep = (hrv > k1 * mean_hrv) & (brv > k2 * mean_brv) & (body_movement < k3 * mean_body_movement)
            wake = body_movement > k3 * mean_body_movement
            nrem_sleep = ~rem_sleep & ~wake
            
            return rem_sleep, wake, nrem_sleep

        rem_sleep, wake, nrem_sleep = classify(self.hrv, self.brv, self.body_movement, thresholds)
        
        classification = np.zeros(len(self.hrv))
        classification[rem_sleep] = 2  # REM sleep
        classification[wake] = 0  # Wake
        classification[nrem_sleep] = 1  # NREM sleep
        
        return classification

    def apply_corrections(self):
        def apply_sleep_corrections(rem_sleep, wake, nrem_sleep):
            wake[:4*3] = True  # First 4 minutes as Wake
            sleep_onset = np.where(nrem_sleep[4*3:] == True)[0][0] + 4*3  # First occurrence of NREM after 4 minutes
            wake[:sleep_onset] = True
            
            # Sleep offset correction
            sleep_offset_start = np.where((nrem_sleep == True) | (rem_sleep == True))[0][-1]
            wake[sleep_offset_start+1:] = True
            
            return rem_sleep, wake, nrem_sleep

        rem_sleep_corrected, wake_corrected, nrem_sleep_corrected = apply_sleep_corrections(self.rem_sleep.copy(), self.wake.copy(), self.nrem_sleep.copy())
        self.classification_corrected = np.zeros(len(self.hrv))
        self.classification_corrected[rem_sleep_corrected] = 2  # REM sleep
        self.classification_corrected[wake_corrected] = 0  # Wake
        self.classification_corrected[nrem_sleep_corrected] = 1  # NREM sleep

    def process(self):
        self.load_data()
        self.preprocess_signals()
        self.segment_into_epochs()
        self.handle_artifacts()
        self.compute_variability()

        # Classification without corrections
        self.classification = self.classify_sleep_stages(self.thresholds)
        result_without_corrections = {
            'hr_mean': self.hr_epochs,
            'br_mean': self.br_epochs,
            'activity_mean': self.activity_epochs,
            'classification': self.classification
        }

        # Classification with corrections
        self.classification_corrected = self.classify_sleep_stages(self.corrected_thresholds)
        self.apply_corrections()
        result_with_corrections = {
            'hr_mean': self.hr_epochs,
            'br_mean': self.br_epochs,
            'activity_mean': self.activity_epochs,
            'classification': self.classification_corrected
        }

        return result_without_corrections, result_with_corrections

class FolderProcessor:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.results = []

    def process_all_files(self):
        for file_name in os.listdir(self.folder_path):
            if file_name.endswith('.csv'):
                file_path = os.path.join(self.folder_path, file_name)
                processor = SleepDataProcessor(file_path)
                result_without_corrections, result_with_corrections = processor.process()
                self.results.append((file_name, result_without_corrections, result_with_corrections))

    def get_results(self):
        return self.results

# Example usage
folder_path = '/mnt/data/your_folder_name'
folder_processor = FolderProcessor(folder_path)
folder_processor.process_all_files()
results = folder_processor.get_results()

for file_name, result_without_corrections, result_with_corrections in results:
    print(f"Results for {file_name} without corrections:")
    print(result_without_corrections)
    print(f"Results for {file_name} with corrections:")
    print(result_with_corrections)
