"""Allow running as `python -m llmc`."""
import sys
from .cli import main

sys.exit(main())
