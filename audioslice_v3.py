import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from spleeter.separator import Separator
import pygame
import threading
import time
from pydub import AudioSegment

pygame.mixer.init()

def convert_mp3_to_wav(mp3_file, output_wav_file):
    audio = AudioSegment.from_file(mp3_file)
    audio.export(output_wav_file, format="wav")
    return output_wav_file

class AudioMixerApp:
    def __init__(self, master):
        self.master = master
        master.title("Audio Mixer")

        # Variables
        self.vocals_path = None
        self.accompaniment_path = None
        self.vocals_volume = tk.DoubleVar(value=1.0)
        self.accompaniment_volume = tk.DoubleVar(value=1.0)
        self.track_position = tk.DoubleVar(value=0)
        self.track_length = 0
        self.is_playing = False
        self.is_paused = False

        # Manual position tracking
        self.current_offset = 0.0
        self.play_start_time = 0.0

        # Audio segments (loaded once we have paths)
        self.vocals_segment = None
        self.accompaniment_segment = None

        self.create_gui()

        # Timer for updating seek slider
        self.update_timer = threading.Thread(target=self.update_seek_slider, daemon=True)
        self.update_timer.start()

    def create_gui(self):
        controls_frame = tk.Frame(self.master)
        controls_frame.grid(row=0, column=0, columnspan=4, pady=10)

        self.select_track_button = tk.Button(controls_frame, text="Select Track", command=self.select_track)
        self.select_track_button.grid(row=0, column=0, padx=10)

        self.select_folder_button = tk.Button(controls_frame, text="Select Folder", command=self.select_folder)
        self.select_folder_button.grid(row=0, column=1, padx=10)

        self.play_button = tk.Button(controls_frame, text="Play", command=self.play_audio, state="disabled")
        self.play_button.grid(row=0, column=2, padx=10)

        self.pause_button = tk.Button(controls_frame, text="Pause", command=self.pause_audio, state="disabled")
        self.pause_button.grid(row=0, column=3, padx=10)

        self.stop_button = tk.Button(controls_frame, text="Stop", command=self.stop_audio, state="disabled")
        self.stop_button.grid(row=0, column=4, padx=10)

        mixer_frame = tk.Frame(self.master)
        mixer_frame.grid(row=1, column=0, columnspan=4, pady=10)

        vocals_frame = tk.Frame(mixer_frame)
        vocals_frame.pack(side="left", padx=20)
        tk.Label(vocals_frame, text="Vocals Volume").pack()
        self.vocals_slider = ttk.Scale(vocals_frame, from_=1.0, to=0.0, variable=self.vocals_volume, orient="vertical", command=self.update_volume)
        self.vocals_slider.pack()

        accompaniment_frame = tk.Frame(mixer_frame)
        accompaniment_frame.pack(side="left", padx=20)
        tk.Label(accompaniment_frame, text="Accompaniment Volume").pack()
        self.accompaniment_slider = ttk.Scale(accompaniment_frame, from_=1.0, to=0.0, variable=self.accompaniment_volume, orient="vertical", command=self.update_volume)
        self.accompaniment_slider.pack()

        seek_frame = tk.Frame(self.master)
        seek_frame.grid(row=2, column=0, columnspan=4, pady=10)
        self.seek_slider = ttk.Scale(seek_frame, from_=0, to=100, variable=self.track_position, orient="horizontal", command=self.seek_audio)
        self.seek_slider.pack(fill="x", padx=20)

    def select_track(self):
        file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        if file_path:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_directory = os.path.join(os.getcwd(), base_name)
            os.makedirs(output_directory, exist_ok=True)

            wav_path = os.path.join(output_directory, f"{base_name}.wav")
            convert_mp3_to_wav(file_path, wav_path)

            separator = Separator('spleeter:2stems')
            separator.separate_to_file(wav_path, output_directory)

            self.vocals_path = os.path.join(output_directory, base_name, "vocals.wav")
            self.accompaniment_path = os.path.join(output_directory, base_name, "accompaniment.wav")

            if not os.path.exists(self.vocals_path) or not os.path.exists(self.accompaniment_path):
                messagebox.showerror("Error", "Separation failed. Check files.")
                return

            self.play_button.config(state="normal")

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            vocals_path = os.path.join(folder_path, "vocals.wav")
            accompaniment_path = os.path.join(folder_path, "accompaniment.wav")

            if not os.path.exists(vocals_path) or not os.path.exists(accompaniment_path):
                messagebox.showerror("Error", "Folder does not contain required files.")
                return

            self.vocals_path = vocals_path
            self.accompaniment_path = accompaniment_path
            self.play_button.config(state="normal")

    def load_segments(self):
        """Load the full audio segments if not already loaded."""
        if self.vocals_path and self.accompaniment_path and (self.vocals_segment is None or self.accompaniment_segment is None):
            self.vocals_segment = AudioSegment.from_wav(self.vocals_path)
            self.accompaniment_segment = AudioSegment.from_wav(self.accompaniment_path)
            self.track_length = max(len(self.vocals_segment), len(self.accompaniment_segment)) / 1000.0
            self.seek_slider.config(to=self.track_length)

    def play_audio(self):
        if not self.vocals_path or not self.accompaniment_path:
            messagebox.showerror("Error", "No audio to play.")
            return

        self.load_segments()

        # Slice at current_offset
        start_ms = int(self.current_offset * 1000)
        vocals_slice = self.vocals_segment[start_ms:]
        accompaniment_slice = self.accompaniment_segment[start_ms:]

        # Export slices to temp WAV
        vocals_slice.export("temp_vocals.wav", format="wav")
        accompaniment_slice.export("temp_accompaniment.wav", format="wav")

        pygame.mixer.quit()
        pygame.mixer.init()

        self.vocals_sound = pygame.mixer.Sound("temp_vocals.wav")
        self.accompaniment_sound = pygame.mixer.Sound("temp_accompaniment.wav")

        self.vocals_channel = pygame.mixer.Channel(0)
        self.accompaniment_channel = pygame.mixer.Channel(1)

        self.vocals_channel.play(self.vocals_sound, loops=-1)
        self.accompaniment_channel.play(self.accompaniment_sound, loops=-1)

        self.is_playing = True
        self.pause_button.config(state="normal")
        self.stop_button.config(state="normal")

        # Reset timing if starting fresh
        if self.current_offset == 0.0:
            self.play_start_time = time.time()

        self.update_volume()

    def pause_audio(self):
        if not self.is_playing:
            return
        if self.is_paused:
            # Unpausing
            self.vocals_channel.unpause()
            self.accompaniment_channel.unpause()
            self.play_start_time = time.time()
            self.is_paused = False
        else:
            # Pausing
            self.current_offset += time.time() - self.play_start_time
            self.vocals_channel.pause()
            self.accompaniment_channel.pause()
            self.is_paused = True

    def stop_audio(self):
        pygame.mixer.stop()
        self.is_playing = False
        self.pause_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        self.current_offset = 0.0
        self.is_paused = False

    def update_volume(self, event=None):
        if hasattr(self, 'vocals_channel') and hasattr(self, 'accompaniment_channel'):
            self.vocals_channel.set_volume(self.vocals_volume.get())
            self.accompaniment_channel.set_volume(self.accompaniment_volume.get())

    def seek_audio(self, event=None):
        if not self.is_playing:
            return

        # Get desired position
        new_position = self.track_position.get()

        # Stop current playback
        self.vocals_channel.stop()
        self.accompaniment_channel.stop()

        # Update offset and time
        self.current_offset = new_position
        self.play_start_time = time.time()

        # Replay from new offset using the slicing method
        self.play_audio()

    def update_seek_slider(self):
        while True:
            if self.is_playing:
                if self.is_paused:
                    current_position = self.current_offset
                else:
                    current_position = self.current_offset + (time.time() - self.play_start_time)

                # Clamp to track length
                if current_position > self.track_length:
                    current_position = self.track_length
                    # Optionally stop if the track ends
                    # self.stop_audio()

                self.track_position.set(current_position)
            time.sleep(0.1)

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioMixerApp(root)
    root.mainloop()
