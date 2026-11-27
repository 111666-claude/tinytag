# SPDX-FileCopyrightText: 2026 tinytag Contributors
# SPDX-License-Identifier: MIT

"""Generate the APEv2-tagged Musepack SV7 test sample.

The source sample (sv7_sample.mpc) is a short public-domain (CC0-1.0)
Musepack SV7 file. This script appends a deterministic APEv2 tag so the
resulting sv7_with_ape.mpc has a known, fixed layout for the unit tests.
"""

from __future__ import annotations

import os
import struct
import sys

PREAMBLE = b'APETAGEX'
FOOTER_SIZE = 32
HAS_HEADER = 1 << 31
IS_HEADER = 1 << 29


def make_item(key: str, value: bytes, flags: int = 0) -> bytes:
    """Build a single APEv2 tag item from a key and a raw value."""
    key_bytes = key.encode('ascii') + b'\x00'
    return struct.pack('<II', len(value), flags) + key_bytes + value


def make_ape_tag(items: list[bytes]) -> bytes:
    """Build a complete APEv2 tag (header, items and footer)."""
    item_count = len(items)
    item_data = b''.join(items)
    # The tag size covers the items and the footer, not the header
    tag_size = len(item_data) + FOOTER_SIZE
    header = (
        PREAMBLE
        + struct.pack(
            '<IIII', 2000, tag_size, item_count, HAS_HEADER | IS_HEADER
        )
        + b'\x00' * 8
    )
    footer = (
        PREAMBLE
        + struct.pack('<IIII', 2000, tag_size, item_count, HAS_HEADER)
        + b'\x00' * 8
    )
    return header + item_data + footer


def main() -> None:
    """Regenerate sv7_with_ape.mpc next to its source sample."""
    base_path = os.path.normpath(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "..", ".."
        )
    )
    sample_dir = os.path.join(base_path, "tinytag", "tests", "samples")
    source_path = os.path.join(sample_dir, "sv7_sample.mpc")
    dest_path = os.path.join(sample_dir, "sv7_with_ape.mpc")
    with open(source_path, 'rb') as source:
        audio = source.read()
    if not audio.startswith(b'MP+\x07'):
        raise SystemExit('Source is not an SV7 Musepack file')
    items = [
        make_item('Title', 'Click Test'.encode('utf-8')),
        make_item('Artist', 'Test Artist'.encode('utf-8')),
        make_item('Track', b'3'),
        # Multi-value text item, null separated
        make_item('Genre', b'Pop\x00Rock'),
        # Unknown field, exposed under the 'other' dictionary
        make_item('Custom Field', b'custom value'),
        # Binary item, skipped instead of decoded as text
        make_item(
            'Cover Art (Front)', b'front.jpg\x00\xff\xd8\xff\xe0binary',
            flags=1
        ),
        # Locator item (type 2), mapped as a text URL
        make_item('Website', b'https://example.invalid/music', flags=2),
    ]
    with open(dest_path, 'wb') as dest:
        dest.write(audio + make_ape_tag(items))
    print(f'Wrote {dest_path}')


if __name__ == '__main__':
    sys.exit(main())
