# srt-to-praat
<p align="center">
<img src="https://github.com/yeungpinghei/srt-to-praat/blob/main/logo.png" alt="srt-to-praat" width="700">
</p>

This Python script converts .srt subtitle files to Praat .TextGrid files with extra features to accomodate .srt files generated by [whisper.cpp](https://github.com/ggerganov/whisper.cpp) and [whisperX](https://github.com/m-bain/whisperX). Unlike [SrtToTextgrid](https://github.com/rctatman/SrtToTextgrid/tree/master), it automatically adds silent intervals to the .srt file and convert it to .TextGrid format in one go.

# Requirements
This script requires `pydub` and `inflect`. You can install them by entering the following commands in your Terminal/Command Prompt:
```
pip install pydub
```
```
pip install inflect
```

# Usage
Go to Terminal/Command Prompt and run the following command:
```
python3 srt_to_tg.py srt_input media_input tg_output csv_output -d -c
```
# Arguments
`srt_input`: Path to the input .srt file.

`media_input`: Path to the input audio file. This is needed to determine the total duration of the output .textGrid file. A wide range of media formats are supported.

**Video**: MXF, MKV, OGM, AVI, DivX, WMV, QuickTime, RealVideo, Mpeg-1, MPEG-2, MPEG-4, DVD-Video (VOB), DivX, XviD, MSMPEG4, ASP, H.264 (Mpeg-4 AVC)

**Audio**: OGG, MP3, WAV, RealAudio, AC3, DTS, AAC, M4A, AU, AIFF, Opus.

`tg_output`: Path to the output .TextGrid file.

`csv_output`: Path to the output .csv file. The script generates a CSV file which logs all instances of consecutive uppercase letters and numbers in the subtitles. It is important to edit them out if you intend to use forced alignment tools like [Montreal Forced Aligner (MFA)](https://montreal-forced-aligner.readthedocs.io/) as they do not process acronyms and numbers properly.

# Options
`-d`, `--diarize` enables speaker diarization if each subtitle in your .srt file starts with the name of the speaker in the format `[SPEAKER_NAME]:` It gives each speaker a separate tier in the TextGrid file.

`-c`, `--convert-numbers` adds space in between consecutive uppercase letters (e.g., **SRT** → **S R T**) and converts numbers to English words (e.g., **25** → **twenty-five**). I recommend you to have this enabled if you intend to use forced alignment tools like MFA afterwards.
