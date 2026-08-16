"""Lightweight OOXML checks for the generated PowerPoint deck."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
EXPECTED_TITLES = [
    "PROBLEM UNDERSTANDING AND OBJECTIVE",
    "SOLUTION ARCHITECTURE AND DESIGN FLOW",
    "IMPLEMENTATION HIGHLIGHTS",
    "CHALLENGES AND LEARNINGS",
    "DEMO SUMMARY AND NEXT STEPS",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pptx", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    with ZipFile(args.pptx) as archive:
        names = archive.namelist()
        slides = sorted(
            (
                name
                for name in names
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            ),
            key=lambda name: int(re.search(r"\d+", Path(name).stem).group()),
        )
        if len(slides) != 5:
            errors.append(f"Expected 5 slides, found {len(slides)}")
        for index, (name, expected) in enumerate(zip(slides, EXPECTED_TITLES), start=1):
            root = ET.fromstring(archive.read(name))
            text = "".join(node.text or "" for node in root.findall(".//a:t", NS))
            if expected not in text:
                errors.append(f"Slide {index} is missing exact title: {expected}")
        note_files = [name for name in names if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)]
        if len(note_files) != 5:
            errors.append(f"Expected notes on 5 slides, found {len(note_files)} notes slides")
        else:
            for name in note_files:
                root = ET.fromstring(archive.read(name))
                text = "".join(node.text or "" for node in root.findall(".//a:t", NS))
                if "[Sources]" not in text or "[/Sources]" not in text:
                    errors.append(f"Missing [Sources] block in {name}")

    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print("PASS: exactly 5 slides, all required titles, and source-note blocks are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
