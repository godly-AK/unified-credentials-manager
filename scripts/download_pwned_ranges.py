"""Download a bounded, reproducible subset of Pwned Passwords for offline use.

This operator command never receives a user-entered password. The running UCM
API continues to query only its local blocklist database.
"""
import argparse
import hashlib
import json
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests


RANGE_URL = "https://api.pwnedpasswords.com/range/"
SUFFIX_LINE = re.compile(r"^([0-9A-F]{35}):([1-9][0-9]*)$")


def download_range(prefix: str) -> tuple[str, list[str]]:
    response = requests.get(RANGE_URL + prefix, headers={"User-Agent": "UCM-offline-blocklist/1"}, timeout=30)
    response.raise_for_status()
    rows = []
    for number, line in enumerate(response.text.splitlines(), 1):
        match = SUFFIX_LINE.fullmatch(line.strip())
        if not match:
            raise ValueError(f"Invalid range response for {prefix}, line {number}.")
        rows.append(prefix + match.group(1) + ":" + match.group(2))
    if not rows:
        raise ValueError(f"Empty range response for {prefix}.")
    return prefix, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix-count", type=int, default=256,
                        help="Number of evenly spaced SHA-1 prefixes, from 1 to 65536")
    parser.add_argument("--include-prefix", action="append", default=[],
                        help="Additional five-character SHA-1 prefix to include")
    parser.add_argument("--output", type=Path, default=Path(".demo/hibp-ranges-sha1.txt"))
    args = parser.parse_args()
    if not 1 <= args.prefix_count <= 65536:
        parser.error("--prefix-count must be between 1 and 65536.")
    extras = [value.upper() for value in args.include_prefix]
    if any(not re.fullmatch(r"[0-9A-F]{5}", value) for value in extras):
        parser.error("--include-prefix must contain exactly five hex characters.")
    # Even spacing avoids concentrating the sample in one small hash region.
    prefixes = sorted({f"{i * 1048576 // args.prefix_count:05X}" for i in range(args.prefix_count)} | set(extras))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for prefix, rows in pool.map(download_range, prefixes):
            results[prefix] = rows
    descriptor, temporary_name = tempfile.mkstemp(prefix="ucm-hibp-", suffix=".txt", dir=args.output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("w", encoding="ascii", newline="\n") as stream:
            for prefix in prefixes:
                stream.write("\n".join(results[prefix]) + "\n")
        checksum = hashlib.sha256(temporary.read_bytes()).hexdigest()
        os.replace(temporary, args.output)
    finally:
        temporary.unlink(missing_ok=True)
    manifest = {
        "source": RANGE_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "prefixes": len(prefixes),
        "full_prefix_space": 1048576,
        "hashes": sum(len(rows) for rows in results.values()),
        "sha256": checksum,
        "scope": "partial offline sample; not the complete Pwned Passwords corpus",
    }
    args.output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {manifest['hashes']} breach hashes from {len(prefixes)} prefixes to {args.output}")
    print("This is a partial offline sample; the remaining prefixes are not covered.")


if __name__ == "__main__":
    main()
