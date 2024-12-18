import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from spleeter.separator import Separator
from pydub import AudioSegment
from pydub.playback import _play_with_simpleaudio
import threading
import math

# Ignore GPU warning
if 'CUDA_VISIBLE_DEVICES' not in os.environ:
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'


def convert_mp3_to_wav(mp3_file, output_wav_file):
    audio = AudioSegment.from_file(mp3_file)
    audio.export(output_wav_file, format="wav")
    return output_wav_file


class AudioMixerApp:
    def __init__(self, master):
        self.master = master
        master.title("Audio Mixer")

        # Variables
        self.input_audio_mp3 = None
        self.output_directory = None
        self.input_audio_wav = None
        self.vocals_path = None
        self.accompaniment_path = None
        self.vocals_volume = tk.DoubleVar(value=1.0)       # default volume 1.0 (0 dB)
        self.accompaniment_volume = tk.DoubleVar(value=1.0)
        self.vocals_player = None
        self.accompaniment_player = None
        self.is_playing = False

        # UI Elements
        self.select_track_button = tk.Button(master, text="Select Track", command=self.select_track)
        self.select_track_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.select_folder_button = tk.Button(master, text="Select Folder", command=self.select_folder)
        self.select_folder_button.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        self.play_button = tk.Button(master, text="Play", command=self.play_audio, state="disabled")
        self.play_button.grid(row=0, column=2, padx=10, pady=10, sticky="w")

        self.stop_button = tk.Button(master, text="Stop", command=self.stop_audio, state="disabled")
        self.stop_button.grid(row=0, column=3, padx=10, pady=10, sticky="w")

        # Vocals Slider
        tk.Label(master, text="Vocals Volume").grid(row=1, column=0, padx=10, sticky="w")
        self.vocals_slider = ttk.Scale(master, from_=0.0, to=2.0, variable=self.vocals_volume, orient="horizontal")
        self.vocals_slider.grid(row=1, column=1, padx=10, sticky="ew")

        # Accompaniment Slider
        tk.Label(master, text="Instruments Volume").grid(row=2, column=0, padx=10, sticky="w")
        self.accompaniment_slider = ttk.Scale(master, from_=0.0, to=2.0, variable=self.accompaniment_volume, orient="horizontal")
        self.accompaniment_slider.grid(row=2, column=1, padx=10, sticky="ew")

        # Column stretching
        master.columnconfigure(1, weight=1)

    def select_track(self):
        file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if file_path:
            self.input_audio_mp3 = file_path
            base_name = os.path.splitext(os.path.basename(self.input_audio_mp3))[0]
            self.output_directory = base_name
            os.makedirs(self.output_directory, exist_ok=True)

            # Convert MP3 to WAV
            self.input_audio_wav = os.path.join(self.output_directory, f"{base_name}.wav")
            convert_mp3_to_wav(self.input_audio_mp3, self.input_audio_wav)

            # Separate stems using Spleeter
            separator = Separator('spleeter:2stems')
            separator.separate_to_file(self.input_audio_wav, self.output_directory)

            # After separation, assign paths to vocals and accompaniment
            separated_dir = os.path.join(self.output_directory, base_name)
            self.vocals_path = os.path.join(separated_dir, "vocals.wav")
            self.accompaniment_path = os.path.join(separated_dir, "accompaniment.wav")

            if not (os.path.exists(self.vocals_path) and os.path.exists(self.accompaniment_path)):
                messagebox.showerror("Error", "Unable to find separated stems.")
                return

            # Enable the play button if files exist
            self.play_button.config(state="normal")

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            vocals_path = os.path.join(folder_path, "vocals.wav")
            accompaniment_path = os.path.join(folder_path, "accompaniment.wav")

            # Check if the required files exist
            if not os.path.exists(vocals_path) or not os.path.exists(accompaniment_path):
                messagebox.showerror("Error", "Folder does not contain required vocals.wav and accompaniment.wav files.")
                return

            # Update paths and enable playback
            self.vocals_path = vocals_path
            self.accompaniment_path = accompaniment_path
            print("Selected folder:")
            print("Vocals path:", self.vocals_path)
            print("Accompaniment path:", self.accompaniment_path)
            self.play_button.config(state="normal")

    def play_audio(self):
        if not (self.vocals_path and self.accompaniment_path):
            messagebox.showerror("Error", "No separated stems available.")
            return

        # Set playing flag
        self.is_playing = True

        # Start playback threads
        self.vocals_thread = threading.Thread(target=self.play_vocals, daemon=True)
        self.accompaniment_thread = threading.Thread(target=self.play_accompaniment, daemon=True)
        self.vocals_thread.start()
        self.accompaniment_thread.start()

        # Enable stop button
        self.stop_button.config(state="normal")

    def stop_audio(self):
        # Stop playback
        self.is_playing = False
        if self.vocals_player:
            self.vocals_player.stop()
        if self.accompaniment_player:
            self.accompaniment_player.stop()

        # Reset buttons
        self.stop_button.config(state="disabled")

    def play_vocals(self):
        try:
            vocals_seg = AudioSegment.from_file(self.vocals_path)
            while self.is_playing:
                adjusted_vocals = vocals_seg + self.linear_to_db(self.vocals_volume.get())
                self.vocals_player = _play_with_simpleaudio(adjusted_vocals)
                self.vocals_player.wait_done()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play vocals: {e}")

    def play_accompaniment(self):
        try:
            accompaniment_seg = AudioSegment.from_file(self.accompaniment_path)
            while self.is_playing:
                adjusted_accompaniment = accompaniment_seg + self.linear_to_db(self.accompaniment_volume.get())
                self.accompaniment_player = _play_with_simpleaudio(adjusted_accompaniment)
                self.accompaniment_player.wait_done()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play accompaniment: {e}")

    def linear_to_db(self, lin):
        if lin <= 0:
            return -float('inf')  # silence
        return 20 * math.log10(lin)


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioMixerApp(root)
    root.mainloop()
