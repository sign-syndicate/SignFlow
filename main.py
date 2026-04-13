"""SignFlow Root Entry Point - Run this to start the application."""
import sys
from pathlib import Path

# Add root to path so Code can be imported
sys.path.insert(0, str(Path(__file__).parent))

from Code.main import main

if __name__ == "__main__":
    raise SystemExit(main())
