#!/usr/bin/env python3
"""Recover a reusable template from two already-downloaded live responses.

This script performs no network requests. Keep the input responses outside Git.
It removes generated bootstrap data and titles, then requires byte-identical
templates. Review the output before updating the capture's provenance manifest.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

BOOTSTRAP = re.compile(r"<script>window\.__TICKET__ = (.*?);</script>", re.S)
TITLE = re.compile(r"<title>.*?</title>", re.S)


def normalize(source):
    matches = BOOTSTRAP.findall(source)
    if len(matches) != 1 or len(TITLE.findall(source)) != 1:
        raise ValueError("Expected exactly one title and one bootstrap block")
    bootstrap = json.loads(matches[0])
    if set(bootstrap) != {"jobId", "jobName", "prefix", "saving", "state", "sync"}:
        raise ValueError("Bootstrap shape changed; review source before capture")
    if not isinstance(bootstrap["state"], dict):
        raise ValueError("Expected an object for ticket state")
    source = TITLE.sub("<title>__TITLE__ · Job Ticket</title>", source, count=1)
    source = BOOTSTRAP.sub("<script>window.__TICKET__ = __BOOTSTRAP__;</script>", source, count=1)
    return source


def capture(blank_path, saved_path):
    blank = normalize(Path(blank_path).read_bytes().decode("utf-8"))
    saved = normalize(Path(saved_path).read_bytes().decode("utf-8"))
    if blank != saved:
        raise ValueError("Responses differ outside title/bootstrap; inspect locally, do not publish")
    return blank.encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blank_response", type=Path)
    parser.add_argument("saved_response", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = capture(args.blank_response, args.saved_response)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(f"Captured {len(result)} bytes; SHA-256 {hashlib.sha256(result).hexdigest()}")


if __name__ == "__main__":
    main()
