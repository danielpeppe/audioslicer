
## Dependencies

```py -3.10 -m venv .venv```
```py -m pip install spleeter```
```py -m pip install --upgrade "numpy<2.0.0"```
```py -m pip install pygame```
```winget install "FFmpeg (Essentials Build)"```

## Notes

You may need to uninstall and reinstall ffmpeg and ffmpeg-python in pip:
```py -m pip uninstall ffmpeg ffmpeg-python```
```py -m pip install ffmpeg-python``

If you want to enable GPU with TensorFlow, install the compatible cuda drivers:
https://www.tensorflow.org/install/source#tested_build_configurations