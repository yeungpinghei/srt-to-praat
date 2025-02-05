# This Python script converts an SRT file to a Praat TextGrid file
# What this script does:
#   1. Extract the duration of the input audio file
#   2. Find unmarked silent intervals in the SRT file and add them to the TextGrid
#   3. Optional: Assign separate tiers to individual speakers in the TextGrid if speaker info is provided at the beginning of subtitle text
#   4. Optional: Separate consecutive uppercase letters (e.g., SRT -> S R T)
#   5. Optional: Convert numbers to word form in English (e.g., 25 -> twenty-five)
#   6. Generates a CSV file which logs all instances of consecutive uppercase letters and numbers.
# Ping Hei Yeung (github.com/yeungpinghei/)
# Feb 5, 2025

import re
import argparse
from collections import defaultdict
from pydub.utils import mediainfo
import inflect
import csv
inflect_engine = inflect.engine()

# define a class for intervals based on the basic template for an SRT interval
class Interval:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text

    def __repr__(self):
        return f"Interval({self.start}, {self.end}, '{self.text}')"

def write_csv(changes_list, csv_file_path):
    """ Writes the changes (timestamp, original text, processed text) to a CSV file. """
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'Original Subtitle', 'Processed Subtitle'])
        writer.writerows(changes_list)

def srt_to_textgrid(srt_file, audio_file, textgrid_file, csv_file, diarize, convert_numbers):
    """ Convert an SRT file to a Praat TextGrid file. Log changes to a CSV file. """
    speaker_intervals, changes_list = parse_srt(srt_file, audio_file, diarize, convert_numbers)
    audio_duration = get_audio_duration(audio_file)

    # Create the TextGrid file
    create_textgrid(speaker_intervals, audio_duration, textgrid_file)

    # Write the changes to CSV
    if changes_list:
        write_csv(changes_list, csv_file)
    else:
        print("No changes to write to CSV.")

def create_textgrid(speaker_intervals, audio_duration, output_path):
    """ Creates a TextGrid file. """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('File type = "ooTextFile"\n')
        f.write('Object class = "TextGrid"\n\n')

        f.write(f'xmin = 0\n')
        f.write(f'xmax = {audio_duration}\n')
        f.write('tiers? <exists>\n')
        f.write('size = ' + str(len(speaker_intervals)) + '\n')
        f.write('item []: \n')

        # Add tiers for each speaker
        for idx, (speaker, intervals) in enumerate(speaker_intervals.items(), start=1):
            f.write(f'    item [{idx}]: \n')
            f.write(f'        class = "IntervalTier"\n')
            f.write(f'        name = "{speaker}"\n')
            f.write(f'        xmin = 0\n')
            f.write(f'        xmax = {audio_duration}\n')

            # Calculate the number of intervals
            num_intervals = len(intervals)
            f.write(f'        intervals: size = {num_intervals}\n')

            # Add the intervals for the speaker
            for i, interval in enumerate(intervals):
                f.write(f'        intervals [{i+1}]:\n')
                f.write(f'            xmin = {interval.start}\n')
                f.write(f'            xmax = {interval.end}\n')
                f.write(f'            text = "{interval.text}"\n')

    print(f"TextGrid file created at {output_path}")

def replace_numbers(text, convert_numbers):
    """ Convert numbers to word form. """
    if not convert_numbers:
        return text

    # Step 1: Identify and convert percentage ranges (e.g., "10% to 30%" → "ten to thirty percent")
    def replace_percentage_range(match):
        num1, num2 = match.groups()
        return f"{inflect_engine.number_to_words(int(num1))} to {inflect_engine.number_to_words(int(num2))} percent"

    text = re.sub(r'(\d+)% to (\d+)%', replace_percentage_range, text)

    # Step 2: Convert standalone percentages (e.g., "45%" → "forty-five percent")
    def replace_percentages(match):
        num = match.group(1)
        return f"{inflect_engine.number_to_words(int(num))} percent"

    text = re.sub(r'(\d+)%', replace_percentages, text)

    # Step 3: Convert ordinal numbers
    def replace_ordinal_numbers(match):
        num_only = match.group(1)
        return inflect_engine.number_to_words(inflect_engine.ordinal(num_only))

    text = re.sub(r'(\d+)(st|nd|rd|th)', replace_ordinal_numbers, text)

    # Step 4: Handle currency
    def convert_currency(match):
        currency = match.group(1)
        return f"{currency} dollars"
    
    text = re.sub(r'\$(\d+)', convert_currency, text)

    # Step 5: Convert 4-digit numbers
    def four_digit_number(match):
        four_digit = match.group(0)
        four_digit = int(four_digit)
        # Handle multiples of 1000 (e.g., 1000, 2000, 3000)
        if four_digit % 1000 == 0:
            return inflect_engine.number_to_words(four_digit)
        else:
            # Split the number into two two-digit numbers
            first_part = four_digit // 100  # First two digits
            second_part = four_digit % 100  # Last two digits

            if second_part != 0:
                # Convert numbers like 2025 into "twenty twenty-five"
                first_part_words = inflect_engine.number_to_words(first_part)
                second_part_words = inflect_engine.number_to_words(second_part)
                return f"{first_part_words} {second_part_words}"
            else:
                # Convert numbers like 1400 into "fourteen hundred"
                first_part_words = inflect_engine.number_to_words(first_part)
                return f"{first_part_words} hundred"

    text = re.sub(r'\d{4}', four_digit_number, text)

    # Step 6: Convert other numbers
    def replace_number_match(match):
        num_str = match.group(0)

        # Handle decades (e.g., "70s" -> "seventies")
        if re.match(r'^\d0s$', num_str):  # Matches "70s", "80s", etc.
            decade = int(num_str[:-1])  # Extracts number (e.g., "70" from "70s")
            return inflect_engine.number_to_words(decade).replace("y", "ie") + "s"

        return inflect_engine.number_to_words(int(num_str))
    # Apply the conversion for general numbers
    text = re.sub(r'\d+s?', replace_number_match, text)

    return text  # Return the modified text

def process_text(text, timestamp, changes_list, convert_numbers):
    original_text = text

    # Convert numbers into written forms
    text = replace_numbers(text, convert_numbers)

    # Separate consecutive uppercase letters (e.g., SRT -> S R T)
    if convert_numbers:
        text = re.sub(r'(?<=[A-Z])(?=[A-Z])', ' ', text)

    # Record instances of consecutive uppercase letters or numbers in the CSV file
    if re.search(r'\d|[A-Z]{2,}', original_text):
        changes_list.append([timestamp, original_text, text])
    return text

def time_to_seconds(time_str):
    """ Converts a time string in the format HH:MM:SS,SSS into seconds. """
    hours, minutes, seconds = time_str.split(":")
    seconds, milliseconds = seconds.split(",")
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000.0
    return total_seconds

def get_audio_duration(audio_file):
    """ Returns the duration of the audio file in seconds. """
    try:
        audio_info = mediainfo(audio_file)
        if not audio_info or 'duration' not in audio_info:
            raise ValueError(f"Fail to read the media file or unsupported format: {audio_file}")
        duration = float(audio_info['duration'])
        return duration
    except Exception as e:
        raise RuntimeError(f"Error processing file '{audio_file}': {e}")

def add_silent_intervals(speaker_intervals, media_duration):
    """ Adds silent intervals for each speaker. """
    updated_intervals = defaultdict(list)

    for speaker, intervals in speaker_intervals.items():
        # Sort intervals by start time
        intervals.sort(key=lambda x: x.start)

        # If the first subtitle starts after 0, add a silent interval at the beginning
        if intervals[0].start > 0:
            updated_intervals[speaker].append(Interval(0, intervals[0].start, ""))

        # Add silent intervals in between subtitles for each speaker
        for i in range(len(intervals)):
            updated_intervals[speaker].append(intervals[i])

            if i < len(intervals) - 1:
                current_end = intervals[i].end
                next_start = intervals[i + 1].start

                if next_start > current_end:
                    silent_start = current_end
                    silent_end = next_start
                    silent_interval = Interval(silent_start, silent_end, "")
                    updated_intervals[speaker].append(silent_interval)

        # If the last subtitle ends before the media duration, add a silent interval at the end
        if intervals[-1].end < media_duration:
            updated_intervals[speaker].append(Interval(intervals[-1].end, media_duration, ""))

    return updated_intervals

def parse_srt(file_path, audio_file, diarize, convert_numbers):
    # Parses an SRT file and extracts subtitles with start time, end time, speaker, and text.
    with open(file_path, 'r', encoding='utf-8') as f:
        srt_data = f.read()

    # Split by subtitle blocks
    blocks = re.split(r'\n\s*\n', srt_data.strip())

    speaker_intervals = defaultdict(list)  # Group intervals by speaker
    changes_list = []  # Store changes for CSV logging

    media_duration = get_audio_duration(audio_file)  # Get media file duration

    for block in blocks:
        lines = block.split('\n')
        if len(lines) < 3:
            continue

        # Extract start time, end time, and speaker
        time_range = lines[1]
        start_time, end_time = time_range.split(' --> ')
        start_seconds = time_to_seconds(start_time)
        end_seconds = time_to_seconds(end_time)

        # Only keep subtitles that end within the media duration
        if end_seconds > media_duration:
            continue  # Skip this subtitle if it goes beyond the media duration

        # Extract speaker and text
        speaker_text = lines[2].strip()

        if diarize:  # If diarization is enabled, extract speaker info
            speaker_match = re.match(r"\[([^\]]+)\]: (.*)", speaker_text)
            
            if speaker_match:
                speaker = speaker_match.group(1)
                text = speaker_match.group(2)
                # Process the text (apply transformations and track changes)
                processed_text = process_text(text, time_range, changes_list, convert_numbers)
                # Store the interval under the speaker's name
                speaker_intervals[speaker].append(Interval(start_seconds, end_seconds, processed_text))
            else:
                continue  # Skip any lines that do not match the expected speaker format
        else:  # If diarization is not enabled, treat everything as a single speaker
            speaker = "Speaker"
            text = speaker_text
            processed_text = process_text(text, time_range, changes_list, convert_numbers)
            speaker_intervals[speaker].append(Interval(start_seconds, end_seconds, processed_text))

    # Add silent intervals
    speaker_intervals = add_silent_intervals(speaker_intervals, media_duration)
    # Return the appropriate data structure based on diarization
    return speaker_intervals, changes_list

def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Convert an SRT file to a Praat TextGrid file", epilog="This script is created by Ping Hei Yeung (github.com/yeungpinghei/)")
    parser.add_argument("srt_input", help="Path to the input .srt file")
    parser.add_argument("media_input", help="Path to the input audio file")
    parser.add_argument("tg_output", help="Path to the output .TextGrid file")
    parser.add_argument("csv_output", help="Path to the output .csv file")
    parser.add_argument("-d", "--diarize", action="store_true", help="Enable speaker diarization")
    parser.add_argument("-c", "--convert_numbers", action="store_true", help="Enable conversion of numbers to English words")

    # Parse arguments
    args = parser.parse_args()

    # Run the conversion
    srt_to_textgrid(args.srt_input, args.media_input, args.tg_output, args.csv_output, args.diarize, args.convert_numbers)

if __name__ == "__main__":
    main()
