from spleeter.separator import Separator
from pydub import AudioSegment
import os

# Function to convert MP3 to WAV
def convert_mp3_to_wav(mp3_file, output_wav_file):
    audio = AudioSegment.from_file(mp3_file)
    audio.export(output_wav_file, format="wav")
    return output_wav_file

# Paths
input_audio = "olivia_dean_olyb"
input_audio_mp3 = f"{input_audio}.mp3"  # Replace with your MP3 file path
output_directory = input_audio     # Replace with your desired output folder path
os.makedirs(output_directory, exist_ok=True)   # Create output directory if it doesn't exist

# Convert MP3 to WAV
input_audio_wav = os.path.join(output_directory, f"{input_audio}.wav")
convert_mp3_to_wav(input_audio_mp3, input_audio_wav)

# Initialize Spleeter
separator = Separator('spleeter:2stems')  # 2 stems: vocals and accompaniment

# Perform separation
separator.separate_to_file(input_audio_wav, output_directory)

print(f"Separated audio files saved to: {output_directory}")
