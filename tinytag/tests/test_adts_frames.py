# SPDX-FileCopyrightText: 2026 tinytag Contributors
# SPDX-License-Identifier: MIT

# pylint: disable=missing-class-docstring,missing-function-docstring
# pyright: reportPrivateUsage=false

"""Tests for raw ADTS AAC streams."""

from __future__ import annotations

import os
import tempfile

from io import BytesIO
from unittest import TestCase

from tinytag import ParseError, TinyTag, TinyTagException
from tinytag.tinytag import _ADTS, _MPEG


def make_adts_frame(payload: bytes = b'\x00' * 32,
                    *,
                    samplerate_index: int = 4,  # 44100 Hz
                    channels: int = 2,
                    protection_absent: bool = True,
                    blocks_in_frame: int = 0,
                    mpeg2_id: bool = False,
                    frame_length: int | None = None) -> bytes:
    """Build a minimal, valid ADTS frame header followed by payload."""
    header_size = 7 if protection_absent else 9
    if frame_length is None:
        frame_length = header_size + len(payload)
    second_byte = (
        0xF0
        | (0x08 if mpeg2_id else 0x00)
        | (0x01 if protection_absent else 0x00)
    )
    third_byte = (
        (0x01 << 6)  # AAC-LC profile (object type 2 -> profile id 1)
        | ((samplerate_index & 0x0F) << 2)
        | ((channels >> 2) & 0x01)
    )
    fourth_byte = (
        ((channels & 0x03) << 6)
        | ((frame_length >> 11) & 0x03)
    )
    fifth_byte = (frame_length >> 3) & 0xFF
    sixth_byte = (
        ((frame_length & 0x07) << 5)
        | 0x1F  # high five bits of 0x7FF buffer fullness
    )
    seventh_byte = 0xFC | (blocks_in_frame & 0x03)
    header = bytes((
        0xFF, second_byte, third_byte, fourth_byte,
        fifth_byte, sixth_byte, seventh_byte
    ))
    if not protection_absent:
        header += b'\x00\x00'  # CRC
    return header + payload


TEN_FRAME_SAMPLE = make_adts_frame() * 10


class AdtsTest(TestCase):

    def test_ten_frames_44100_stereo(self) -> None:
        tag = TinyTag.get(file_obj=BytesIO(TEN_FRAME_SAMPLE))
        self.assertIsInstance(tag, _ADTS)
        self.assertIsInstance(tag, _MPEG)
        self.assertEqual(tag.mime_type, 'audio/aac')
        self.assertEqual(tag.samplerate, 44100)
        self.assertEqual(tag.channels, 2)
        # each AAC frame contains 1024 samples
        self.assertEqual(tag.duration, 10240 / 44100)
        assert tag.duration is not None
        self.assertAlmostEqual(tag.duration, 10240 / 44100, places=12)
        self.assertFalse(tag.is_lossless)

    def test_path_and_file_object_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'sample.aac')
            with open(path, 'wb') as fh:
                fh.write(TEN_FRAME_SAMPLE)
            path_tag = TinyTag.get(path)
            with open(path, 'rb') as fh:
                handle_tag = TinyTag.get(file_obj=fh)
        self.assertEqual(path_tag.duration, handle_tag.duration)
        self.assertEqual(path_tag.samplerate, handle_tag.samplerate)
        self.assertEqual(path_tag.channels, handle_tag.channels)
        self.assertEqual(path_tag.mime_type, handle_tag.mime_type)
        self.assertEqual(path_tag.duration, 10240 / 44100)

    def test_extension_supported(self) -> None:
        self.assertTrue(TinyTag.is_supported('sound.aac'))
        self.assertIn('.aac', TinyTag.SUPPORTED_FILE_EXTENSIONS)

    def test_crc_frames(self) -> None:
        sample = make_adts_frame(protection_absent=False) * 10
        tag = TinyTag.get(file_obj=BytesIO(sample))
        self.assertEqual(tag.samplerate, 44100)
        self.assertEqual(tag.channels, 2)
        self.assertEqual(tag.duration, 10240 / 44100)

    def test_mpeg2_id_bit(self) -> None:
        tag = TinyTag.get(file_obj=BytesIO(
            make_adts_frame(mpeg2_id=True) * 10))
        self.assertEqual(tag.samplerate, 44100)
        self.assertEqual(tag.duration, 10240 / 44100)

    def test_mono_other_sample_rate(self) -> None:
        tag = TinyTag.get(file_obj=BytesIO(
            make_adts_frame(samplerate_index=7, channels=1) * 5))
        self.assertEqual(tag.samplerate, 22050)
        self.assertEqual(tag.channels, 1)
        self.assertEqual(tag.duration, 5 * 1024 / 22050)

    def test_bad_sync_raises(self) -> None:
        broken = bytearray(TEN_FRAME_SAMPLE)
        frame_size = len(TEN_FRAME_SAMPLE) // 10
        broken[5 * frame_size] ^= 0xFF  # corrupt sync of frame six
        with self.assertRaises(ParseError):
            TinyTag.get(
                filename='broken.aac', file_obj=BytesIO(bytes(broken)))

    def test_bad_initial_sync_with_aac_extension_raises(self) -> None:
        with self.assertRaises(TinyTagException):
            TinyTag.get(
                filename='broken.aac',
                file_obj=BytesIO(b'not an adts stream' * 4))

    def test_invalid_frame_length_raises(self) -> None:
        frame = bytearray(make_adts_frame())
        bad_length = 4  # smaller than the seven byte header
        frame[3] = (frame[3] & 0xFC) | ((bad_length >> 11) & 0x03)
        frame[4] = (bad_length >> 3) & 0xFF
        frame[5] = (frame[5] & 0x1F) | ((bad_length & 0x07) << 5)
        with self.assertRaises(ParseError):
            TinyTag.get(
                filename='length.aac',
                file_obj=BytesIO(bytes(frame) * 3))

    def test_truncated_trailing_header_raises(self) -> None:
        with self.assertRaises(ParseError):
            TinyTag.get(file_obj=BytesIO(
                TEN_FRAME_SAMPLE + make_adts_frame()[:4]))

    def test_truncated_last_frame_payload_raises(self) -> None:
        declared_large = make_adts_frame(
            b'\x00' * 4, frame_length=500)
        stream = make_adts_frame() * 9 + declared_large
        with self.assertRaises(ParseError):
            TinyTag.get(filename='tail.aac', file_obj=BytesIO(stream))

    def test_header_only_trailing_frame_raises(self) -> None:
        # header announces a payload that is not present in the stream
        trailing = make_adts_frame(b'\x00' * 200)[:7]
        with self.assertRaises(ParseError):
            TinyTag.get(file_obj=BytesIO(TEN_FRAME_SAMPLE + trailing))
