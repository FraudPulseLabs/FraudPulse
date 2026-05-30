# src/utils/inspect_model.py
"""
Inspect the versions of sklearn and lightgbm embedded in the model pickle.

Run from backend/:
    python -m src.utils.inspect_model
"""

import pickle
import pathlib
import re
import sys

from src.core.config import ML_ARTEFACTS_DIR

MODEL_PATH = ML_ARTEFACTS_DIR / "fraud_model.pkl"

if not MODEL_PATH.exists():
    print(f"Model not found at {MODEL_PATH}")
    sys.exit(1)
 
with open(MODEL_PATH, "rb") as f:
    raw = f.read()
 
# sklearn stores its version as a plain string next to the module name.
# Look specifically for patterns adjacent to "sklearn" and "lightgbm".
print("=== Scanning pickle for library version strings ===\n")
 
# Find all occurrences of version-like strings near known package names
for package in ["scikit-learn", "sklearn", "lightgbm", "lgb", "numpy", "pandas"]:
    # Find the byte offset of the package name
    needle = package.encode()
    idx = 0
    found = []
    while True:
        pos = raw.find(needle, idx)
        if pos == -1:
            break
        # Extract surrounding 60 bytes and look for a version string
        chunk = raw[max(0, pos - 5): pos + 80].decode(errors="replace")
        versions = re.findall(r'\d+\.\d+\.\d+', chunk)
        for v in versions:
            if v not in found:
                found.append(v)
        idx = pos + 1
 
    if found:
        print(f"  {package:<20} → {found}")
    else:
        print(f"  {package:<20} → not found in pickle")
 
# Also try loading just enough of the pickle to read __getstate__
print("\n=== Attempting partial unpickle for _sklearn_version ===\n")
try:
    import io
    import pickletools
 
    buf = io.BytesIO(raw)
    # Walk the pickle opcodes looking for _sklearn_version strings
    version_keys = []
    for opcode, arg, pos in pickletools.genops(buf):
        if isinstance(arg, str) and "sklearn_version" in arg.lower():
            version_keys.append((pos, arg))
        # The string immediately after _sklearn_version is the version number
    if version_keys:
        print(f"  Found _sklearn_version references at byte offsets:")
        for pos, key in version_keys:
            print(f"    offset={pos}  key={key}")
    else:
        print("  No _sklearn_version key found via pickletools")
 
    # Try to find the actual version value by reading the pickle op after the key
    buf.seek(0)
    ops = list(pickletools.genops(buf))
    for i, (opcode, arg, pos) in enumerate(ops):
        if isinstance(arg, str) and arg == "_sklearn_version":
            # The value is typically a few ops later
            for j in range(i + 1, min(i + 5, len(ops))):
                next_arg = ops[j][1]
                if isinstance(next_arg, str) and re.match(r'\d+\.\d+', next_arg):
                    print(f"\n  _sklearn_version = {next_arg}")
                    break
 
except Exception as e:
    print(f"  pickletools scan failed: {e}")
 
print("\nDone. Use the sklearn version above to pin requirements.txt.")