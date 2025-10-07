import os
from pathlib import Path

ROOT_DIR = Path(os.getcwd())
OUTPUTS_DIR = ROOT_DIR / "outputs"
BASE_TIME_UNIT = 0.1
SEND_COMMAND_TIMEOUT = 10
PARAGRAPH_SEP = "=" * 60

# Infinite-output protection defaults
# Maximum allowed buffer growth (characters) before we short-circuit searches
MAX_BUFFER_GROWTH = 300_000
# Characters between repetitive checks in DevConn.search()
REPETITIVE_CHECK_INTERVAL = 5_000
# Minimum consecutive repeats to consider output as infinite/repetitive
REPETITIVE_PATTERN_THRESHOLD = 50

# OutputBuffer search window thresholds
# Warn if the searched substring length (from pos) exceeds this number
OUTPUT_SEARCH_WARN_THRESHOLD = 100_000
# When warning, clamp the search window to the last N characters of the buffer (not before pos)
OUTPUT_SEARCH_WINDOW_SIZE = 300_000
