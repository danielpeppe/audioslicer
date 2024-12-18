import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from spleeter.separator import Separator
import pygame
import threading
import time

# Initialize Pygame mixer
pygame.mixer.init()


def convert_mp3_to_wav(mp3_file, output_wav_file):
    from pydub import AudioSegment
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
        self.vocals_volume = tk.DoubleVar(value=1.0)       # default volume 1.0
        self.accompaniment_volume = tk.DoubleVar(value=1.0)
        self.track_position = tk.DoubleVar(value=0)
        self.track_length = 0
        self.is_playing = False
        self.is_paused = False

        # UI Elements
        self.create_gui()

        # Timer for updating seek slider
        self.update_timer = threading.Thread(target=self.update_seek_slider, daemon=True)
        self.update_timer.start()

    def create_gui(self):
        # Buttons for controls
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

        # Sliders for volume (vertical)
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

        # Seek slider
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

            # Separate stems using Spleeter
            separator = Separator('spleeter:2stems')
            separator.separate_to_file(wav_path, output_directory)

            # Assign paths
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

    def play_audio(self):
        """Plays vocals and accompaniment on separate channels."""
        if not self.vocals_path or not self.accompaniment_path:
            messagebox.showerror("Error", "No audio to play.")
            return

        pygame.mixer.quit()
        pygame.mixer.init()

        # Load and play vocals
        vocals_sound = pygame.mixer.Sound(self.vocals_path)
        accompaniment_sound = pygame.mixer.Sound(self.accompaniment_path)

        self.vocals_channel = pygame.mixer.Channel(0)
        self.accompaniment_channel = pygame.mixer.Channel(1)

        self.vocals_channel.play(vocals_sound, loops=-1)
        self.accompaniment_channel.play(accompaniment_sound, loops=-1)

        self.track_length = max(vocals_sound.get_length(), accompaniment_sound.get_length())
        self.seek_slider.config(to=self.track_length)

        self.is_playing = True
        self.pause_button.config(state="normal")
        self.stop_button.config(state="normal")

        self.update_volume()

    def pause_audio(self):
        """Pauses or resumes playback."""
        if self.is_paused:
            self.vocals_channel.unpause()
            self.accompaniment_channel.unpause()
            self.is_paused = False
        else:
            self.vocals_channel.pause()
            self.accompaniment_channel.pause()
            self.is_paused = True

    def stop_audio(self):
        """Stops playback."""
        pygame.mixer.stop()
        self.is_playing = False
        self.pause_button.config(state="disabled")
        self.stop_button.config(state="disabled")

    def update_volume(self, event=None):
        """Updates the volume of vocals and accompaniment based on slider values."""
        if hasattr(self, 'vocals_channel') and hasattr(self, 'accompaniment_channel'):
            self.vocals_channel.set_volume(self.vocals_volume.get())
            self.accompaniment_channel.set_volume(self.accompaniment_volume.get())

    def seek_audio(self, event=None):
        """Seeks to a specific position in the audio."""
        position = self.track_position.get()
        if hasattr(self, 'vocals_channel') and hasattr(self, 'accompaniment_channel'):
            self.vocals_channel.set_position(position)
            self.accompaniment_channel.set_position(position)

    def update_seek_slider(self):
        """Updates the seek slider in real-time."""
        while True:
            if self.is_playing and not self.is_paused:
                current_position = self.vocals_channel.get_position() if hasattr(self, 'vocals_channel') else 0
                self.track_position.set(current_position)
            time.sleep(0.5)


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioMixerApp(root)
    root.mainloop()
