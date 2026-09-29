import sys
from pathlib import Path

# Make the project root (file-organizer/) importable so tests can
# `import organizer`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
