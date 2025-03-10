import os
import re
import time
import logging
import argparse
import shutil
import sys
import unicodedata
from itertools import cycle
from shutil import get_terminal_size
from threading import Thread
from rich.progress import TextColumn

# Force UTF-8 for stdout and stderr
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Update URLs to be dynamic based on the subdomain
COURSE_URL = "https://{portal_name}.udemy.com/api-2.0/courses/{course_id}/"
CURRICULUM_URL = "https://{portal_name}.udemy.com/api-2.0/courses/{course_id}/subscriber-curriculum-items/?page_size=200&fields[lecture]=title,object_index,is_published,sort_order,created,asset,supplementary_assets,is_free&fields[quiz]=title,object_index,is_published,sort_order,type&fields[practice]=title,object_index,is_published,sort_order&fields[chapter]=title,object_index,is_published,sort_order&fields[asset]=title,filename,asset_type,status,time_estimation,is_external&caching_intent=True"
LECTURE_URL = "https://{portal_name}.udemy.com/api-2.0/users/me/subscribed-courses/{course_id}/lectures/{lecture_id}?fields[lecture]=asset,description,download_url,is_free,last_watched_second&fields[asset]=asset_type,media_sources,captions,download_urls,slide_urls,external_url"
QUIZ_URL = "https://{portal_name}.udemy.com/api-2.0/quizzes/{quiz_id}/assessments/?version=1&page_size=200&fields[assessment]=id,assessment_type,prompt,correct_response,section,question_plain,related_lectures"
LINK_ASSET_URL = "https://{portal_name}.udemy.com/api-2.0/users/me/subscribed-courses/{course_id}/lectures/{lecture_id}/supplementary-assets/{asset_id}/?fields[asset]=external_url"
FILE_ASSET_URL = "https://{portal_name}.udemy.com/api-2.0/users/me/subscribed-courses/{course_id}/lectures/{lecture_id}/supplementary-assets/{asset_id}/?fields[asset]=download_urls"
ARTICLE_URL = "https://{portal_name}.udemy.com/api-2.0/assets/{article_id}/?fields[asset]=@min,status,delayed_asset_message,processing_errors,body"

HOME_DIR = os.getcwd()
DOWNLOAD_DIR = os.path.join(HOME_DIR, "courses")

LOG_DIR = os.path.join(HOME_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOG_DIR, f"{time.strftime('%Y-%m-%d')}.log")

# Make sure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logger
logger = logging.getLogger('udemy-dl')
logger.setLevel(logging.INFO)

# Create console handler with UTF-8 encoding
console_handler = logging.StreamHandler(sys.stdout)  # Explicitly use stdout
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s : %(message)s'))

# Create file handler with UTF-8 encoding
file_handler = logging.FileHandler(LOG_FILE_PATH, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s : %(message)s'))

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

class LogFormatter(logging.Formatter):
    RESET = "\x1b[0m"
    COLOR_CODES = {
        'INFO': "\x1b[32m",    # Green
        'WARNING': "\x1b[33m", # Yellow
        'ERROR': "\x1b[31m",   # Red
        'CRITICAL': "\x1b[41m" # Red background
    }

    def format(self, record):
        original_levelname = record.levelname
        
        log_color = self.COLOR_CODES.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        
        formatted_message = super().format(record)
        
        record.levelname = original_levelname
        
        return formatted_message

class LoadAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values if values is not None else True)


# Source: https://stackoverflow.com/questions/22029562/python-how-to-make-simple-animated-loading-while-process-is-running
class Loader:
    def __init__(self, desc="Processing", timeout=0.1):
        self.desc = desc
        self.timeout = timeout
        self._thread = Thread(target=self._animate, daemon=True)
        self.steps = ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"]
        self.done = False

    def start(self):
        self._thread.start()
        return self

    def _animate(self):
        for c in cycle(self.steps):
            if self.done:
                break
            print(f"\r{self.desc} {c}", flush=True, end="")
            time.sleep(self.timeout)

    def __enter__(self):
        self.start()
        return self

    def stop(self):
        self.done = True
        # Clear the spinner line
        cols = shutil.get_terminal_size(fallback=(80, 20)).columns
        print("\r" + " " * cols, end="", flush=True)
        print("\r", end="", flush=True)

    def __exit__(self, exc_type, exc_value, tb):
        self.stop()

class ElapsedTimeColumn(TextColumn):
    def __init__(self, *args, **kwargs):
        super().__init__("{elapsed_time}", *args, **kwargs)
        self.start_time = time.time()

    def render(self, task):
        if task.completed==100:
            return "[green]Completed[/green]"

        elapsed = time.time() - self.start_time
        formatted_time = f"[yellow]{elapsed:.2f}s[/yellow]"
        return formatted_time
    
def remove_emojis_and_binary(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
        "\U0001F680-\U0001F6FF"  # Transport & Map Symbols
        "\U0001F700-\U0001F77F"  # Alchemical Symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"  # Enclosed Characters
        "]+", 
        flags=re.UNICODE
    )

    text = emoji_pattern.sub(r'', text)

    # Remove only control characters while keeping all valid Unicode characters
    text = ''.join(c for c in text if not unicodedata.category(c).startswith('C'))

    return text

def timestamp_to_seconds(timestamp):
    hours, minutes, seconds = timestamp.split(':')
    seconds, fraction = seconds.split('.')
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(fraction) / 100
    return total_seconds

def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}hr {minutes}min {seconds}s" if hours > 0 else f"{minutes}min {seconds}s"

def parse_chapter_filter(chapter_str):
    """
    Given a string like "1,3-5,7,9-11", return a set of chapter numbers.
    """
    chapters = set()
    for part in chapter_str.split(','):
        if '-' in part:
            try:
                start, end = part.split('-')
                start = int(start.strip())
                end = int(end.strip())
                chapters.update(range(start, end + 1))
            except ValueError:
                logger.error("Invalid range in --chapter argument: %s", part)
                sys.exit(1)
        else:
            try:
                chapters.add(int(part.strip()))
            except ValueError:
                logger.error("Invalid chapter number in --chapter argument: %s", part)
                sys.exit(1)
    return chapters
