# SPDX-FileCopyrightText: 2019-2026 tinytag Contributors
# SPDX-License-Identifier: MIT

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=missing-module-docstring
# pyright: reportPrivateUsage=false

from __future__ import annotations

import os.path

from io import BytesIO, TextIOWrapper
from pathlib import Path
from platform import python_implementation, system
from sys import stdout
from unittest import skipIf, TestCase

from tinytag import ParseError, TinyTagException, UnsupportedFormatError
from tinytag import (Chapter, Chapters, Image, Images, OtherFields,
                     OtherImages, TinyTag)
from tinytag.tinytag import (
    _ID3, _MPEG, _Ogg, _Wave, _Flac, _ASF, _MP4, _Aiff,
    _ChapterFrame, _ChapterTOC
)

TYPE_CHECKING = False

# Lazy imports for type checking
if TYPE_CHECKING:
    from typing import Any, BinaryIO, Mapping, Union
    ExpectedTag = Mapping[str, Union[str, float, OtherFields]]
    ExpectedImages = Mapping[str, Union[Image, OtherImages]]
else:
    ExpectedTag = dict
    ExpectedImages = dict

TEST_FILES: dict[str, ExpectedTag] = dict([
    ('vbri.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 222.19755102040816,
        'album': 'I Can Walk On Water I Can Fly',
        'year': '2007',
        'title': 'I Can Walk On Water I Can Fly',
        'artist': 'Basshunter',
        'track': 1,
        'filesize': 8192,
        'genre': 'Dance',
        'comment': 'Ripped by THSLIVE',
        'bitrate': 233.26042866799907,
    }),
    ('cbr.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.47020408163265304,
        'album': 'I Can Walk On Water I Can Fly',
        'year': '2007',
        'title': 'I Can Walk On Water I Can Fly',
        'artist': 'Basshunter',
        'track': 1,
        'filesize': 8186,
        'bitrate': 127.99548611111112,
        'genre': 'Dance',
        'comment': 'Ripped by THSLIVE',
    }),
    ('vbr_xing_header.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'bitrate': 185.19809602649008,
        'channels': 1,
        'samplerate': 44100,
        'duration': 3.944489795918367,
        'filesize': 91731,
    }),
    ('vbr_xing_header_2channel.mp3', {
        'other': OtherFields({
            'encoder_settings': [
                'LAME 32bits version 3.99.5 (http://lame.sf.net)'
            ],
            'tlen': ['249976']
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 2000,
        'album': "The Harpers' Masque",
        'artist': 'Knodel and Valencia',
        'bitrate': 46.26947346427078,
        'channels': 2,
        'duration': 250.04408163265308,
        'samplerate': 22050,
        'title': 'Lochaber No More',
        'year': '1992',
    }),
    ('id3v22-test.mp3', {
        'other': OtherFields({
            'encoded_by': ['iTunes v4.6'],
            'itunnorm': [
                ' 0000044E 00000061 00009B67 000044C3 00022478 00022182'
                ' 00007FCC 00007E5C 0002245E 0002214E'
            ],
            'itunes_cddb_1': [
                '9D09130B+174405+11+150+14097+27391+43983+65786+84877+99399+'
                '113226+132452+146426+163829'
            ],
            'itunes_cddb_tracknumber': ['3'],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'track_total': 11,
        'duration': 0.156734693877551,
        'album': 'Hymns for the Exiled',
        'year': '2004',
        'title': 'cosmic american',
        'artist': 'Anais Mitchell',
        'track': 3,
        'filesize': 5120,
        'bitrate': 160.0,
        'comment': 'Waterbug Records, www.anaismitchell.com',
    }),
    ('silence-44-s-v1.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'genre': 'Darkwave',
        'duration': 3.7355102040816326,
        'album': 'Quod Libet Test Data',
        'year': '2004',
        'title': 'Silence',
        'artist': 'piman',
        'track': 2,
        'filesize': 15070,
        'bitrate': 32.0,
    }),
    ('id3v1-latin1.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'genre': 'Rock',
        'album': 'The Young Americans',
        'title': 'Play Dead',
        'filesize': 256,
        'track': 12,
        'artist': 'Björk',
        'year': '1993',
        'comment': '                            ',
    }),
    ('UTF16.mp3', {
        'other': OtherFields({
            'musicbrainz artist id': ['664c3e0e-42d8-48c1-b209-1efca19c0325'],
            'musicbrainz album id': ['25322466-a29b-417b-b560-399687b91ddd'],
            'musicbrainz album artist id': [
                '664c3e0e-42d8-48c1-b209-1efca19c0325'
            ],
            'musicbrainz disc id': ['p.5xoyYRtCVFe2gt0mfTfsXrO9U-'],
            'musicip puid': ['6ff97581-1c73-fc05-b4e4-a4ccee12ec84'],
            'asin': ['B003KVNV4S'],
            'musicbrainz album status': ['Official'],
            'musicbrainz album type': ['Album'],
            'musicbrainz album release country': ['United States'],
            'ufid': [
                ('http://musicbrainz.org\x00'
                 'cf639964-eabb-4c40-9673-c2117e456ea5')
            ],
            'publisher': ['4AD'],
            'tdat': ['1105'],
            'media': ['Digital'],
            'tlen': ['203733'],
            'encoder_settings': [
                'LAME 32bits version 3.98.4 (http://www.mp3dev.org/)'
            ],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'track_total': 11,
        'track': 7,
        'artist': 'The National',
        'year': '2010',
        'album': 'High Violet',
        'title': 'Lemonworld',
        'filesize': 20480,
        'genre': 'Indie',
        'comment': 'Track 7',
    }),
    ('utf-8-id3v2.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'genre': 'Acustico',
        'track_total': 21,
        'track': 1,
        'filesize': 2119,
        'title': 'Gran día',
        'artist': 'Paso a paso',
        'album': 'S/T',
        'disc_total': 0,
        'year': '2003',
    }),
    ('utf-8-id3v2-invalid-string.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'genre': 'Acustico',
        'track_total': 21,
        'track': 1,
        'filesize': 2119,
        'title': '�ran día',
        'artist': 'Paso a paso',
        'album': 'S/T',
        'disc_total': 0,
        'year': '2003',
    }),
    ('empty_file.mp3', {
        'other': OtherFields(),
        'filesize': 0
    }),
    ('incomplete.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 3
    }),
    ('silence-44khz-56k-mono-1s.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 1,
        'samplerate': 44100,
        'duration': 1.0448979591836736,
        'filesize': 7280,
        'bitrate': 56.0,
    }),
    ('silence-22khz-mono-1s.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 1,
        'samplerate': 22050,
        'filesize': 4284,
        'bitrate': 32.0,
        'duration': 1.0710204081632653,
    }),
    ('id3v24-long-title.mp3', {
        'other': OtherFields({
            'copyright': [
                '2013 Marathon Artists under exclsuive license from '
                'Courtney Barnett'
            ]
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'track': 1,
        'disc_total': 1,
        'composer': 'Courtney Barnett',
        'album': 'The Double EP: A Sea of Split Peas',
        'filesize': 10000,
        'track_total': 12,
        'genre': 'AlternRock',
        'title': 'Out of the Woodwork',
        'artist': 'Courtney Barnett',
        'albumartist': 'Courtney Barnett',
        'disc': 1,
        'comment': 'Amazon.com Song ID: 240853806',
        'year': '2013',
    }),
    ('utf16be.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'title': '52-girls',
        'filesize': 2048,
        'track': 6,
        'album': 'party mix',
        'artist': 'The B52s',
        'genre': 'Rock',
        'year': '1981',
    }),
    ('id3v22.TCO.genre.mp3', {
        'other': OtherFields({
            'encoded_by': ['iTunes 11.0.4'],
            'itunnorm': [
                ' 000019F0 00001E2A 00009F9A 0000C689 000312A1 00030C1A'
                ' 0000902E 00008D36 00020882 000321D6'
            ],
            'itunsmpb': [
                ' 00000000 00000210 000007B9 00000000008FB737 00000000'
                ' 008242F1 00000000 00000000 00000000 00000000 00000000'
                ' 00000000'
            ],
            'itunpgap': ['0'],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 500,
        'album': 'ARTPOP',
        'artist': 'Lady GaGa',
        'genre': 'Pop',
        'title': 'Applause',
    }),
    ('id3_comment_utf_16_with_bom.mp3', {
        'other': OtherFields({
            'copyright': ['(c) 2008 nin'],
            'isrc': ['USTC40852229'],
            'bpm': ['60'],
            'url': ['www.nin.com'],
            'encoded_by': ['LAME 3.97'],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 19980,
        'album': 'Ghosts I-IV',
        'albumartist': 'Nine Inch Nails',
        'artist': 'Nine Inch Nails',
        'disc': 1,
        'disc_total': 2,
        'title': '1 Ghosts I',
        'track': 1,
        'track_total': 36,
        'year': '2008',
        'comment': '3/4 time',
    }),
    ('id3_comment_utf_16_double_bom.mp3', {
        'other': OtherFields({
            'label': ['Unclear']
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 512,
        'album': 'The Embrace',
        'artist': 'Johannes Heil & D.Diggler',
        'comment': 'Unclear',
        'title': 'The Embrace (Romano Alfieri Remix)',
        'year': '2012',
    }),
    ('id3_genre_id_out_of_bounds.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 512,
        'album': 'MECHANICAL ANIMALS',
        'artist': 'Manson',
        'genre': '(255)',
        'title': '01 GREAT BIG WHITE WORLD',
        'year': '0',
    }),
    ('image-text-encoding.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 1,
        'samplerate': 22050,
        'filesize': 11104,
        'title': 'image-encoding',
        'bitrate': 32.0,
        'duration': 1.0710204081632653,
    }),
    ('id3v1_does_not_overwrite_id3v2.mp3', {
        'other': OtherFields({
            'love rating': ['L'],
            'publisher': ['Century Media']
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 1130,
        'album': 'Somewhere Far Beyond',
        'albumartist': 'Blind Guardian',
        'artist': 'Blind Guardian',
        'genre': 'Power Metal',
        'title': 'Time What Is Time',
        'track': 1,
        'year': '1992',
    }),
    ('non_ascii_filename_äää.mp3', {
        'other': OtherFields({
            'encoder_settings': ['Lavf58.20.100']
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 80919,
        'channels': 2,
        'duration': 5.0416326530612245,
        'samplerate': 44100,
        'bitrate': 127.99980569948187,
    }),
    ('chinese_id3.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 1000,
        'album': '½ÇÂäÖ®¸è',
        'albumartist': 'ËÕÔÆ',
        'artist': 'ËÕÔÆ',
        'bitrate': 127.99998206155979,
        'channels': 2,
        'duration': 263.9412244897959,
        'genre': 'ÐÝÏÐÒôÀÖ',
        'samplerate': 44100,
        'title': '½ÇÂäÖ®¸è',
        'track': 1,
    }),
    ('cut_off_titles.mp3', {
        'other': OtherFields({
            'encoder_settings': ['Lavf54.29.104']
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 1000,
        'album': 'ERB',
        'artist': 'Epic Rap Battles Of History',
        'bitrate': 192.0,
        'channels': 2,
        'duration': 0.052244897959183675,
        'samplerate': 44100,
        'title': 'Tony Hawk VS Wayne Gretzky',
    }),
    ('id3_xxx_lang.mp3', {
        'other': OtherFields({
            'script': ['Latn'],
            'acoustid id': ['2dc0b571-a633-45b0-aa5e-f3d25e4e0020'],
            'musicbrainz album type': ['album'],
            'musicbrainz album artist id': [
                '078a9376-3c04-4280-b7d7-b20e158f345d'
            ],
            'musicbrainz artist id': ['078a9376-3c04-4280-b7d7-b20e158f345d'],
            'barcode': ['724386668721'],
            'musicbrainz album id': ['38b555fe-24c7-37b3-ad1b-f6dea9f1aafa'],
            'musicbrainz release track id': [
                '7f7c31a5-0905-39ba-ba72-68db91d3b9da'
            ],
            'catalog_number': ['7243 8 66687 2 1'],
            'musicbrainz release group id': [
                '0f21095a-e629-389c-981a-d9569e9673c9'
            ],
            'musicbrainz album status': ['official'],
            'asin': ['B000641ZIQ'],
            'musicbrainz album release country': ['US'],
            'isrc': ['USVI20400513'],
            'lyrics': ['Don\'t fret, precious'],
            'replaygain_track_gain': ['-3.95 dB'],
            'replaygain_track_peak': ['0.999969'],
            'replaygain_album_gain': ['-8.26 dB'],
            'publisher': ['Virgin Records America'],
            'media': ['CD'],
            'tso2': ['Perfect Circle, A'],
            'ufid': [
                ('http://musicbrainz.org\x00'
                 'd2b8f0e6-735a-42ee-adf0-7eca4e65cd72')
            ],
            'tsop': ['Perfect Circle, A'],
            'tory': ['2004'],
            'originalyear': ['2004'],
            'tdat': ['0211'],
            'ipls': [
                ('producer\x00Billy Howerdel\x00'
                 'producer\x00Maynard James Keenan\x00'
                 'engineer\x00Billy Howerdel\x00engineer\x00Critter')
            ],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 6943,
        'album': 'eMOTIVe',
        'albumartist': 'A Perfect Circle',
        'artist': 'A Perfect Circle',
        'composer': 'Billy Howerdel/Maynard James Keenan',
        'bitrate': 192.0,
        'channels': 2,
        'duration': 0.10448979591836735,
        'genre': 'Rock',
        'samplerate': 44100,
        'title': 'Counting Bodies Like Sheep to the Rhythm of the War Drums',
        'track': 10,
        'comment': '                            ',
        'disc': 1,
        'disc_total': 1,
        'track_total': 12,
        'year': '2004',
    }),
    ('vbr8.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 9504,
        'bitrate': 8.000000000000002,
        'channels': 1,
        'duration': 9.216,
        'other': OtherFields(),
        'samplerate': 8000,
    }),
    ('vbr8stereo.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 9504,
        'bitrate': 8.000000000000002,
        'channels': 2,
        'duration': 9.216,
        'other': OtherFields(),
        'samplerate': 8000,
    }),
    ('vbr11.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 9360,
        'bitrate': 7.9625,
        'channels': 1,
        'duration': 9.195102040816327,
        'other': OtherFields(),
        'samplerate': 11025,
    }),
    ('vbr11stereo.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 9360,
        'bitrate': 7.9625,
        'channels': 2,
        'duration': 9.195102040816327,
        'other': OtherFields(),
        'samplerate': 11025,
    }),
    ('vbr16.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 9432,
        'bitrate': 8.0,
        'channels': 1,
        'duration': 9.144,
        'other': OtherFields(),
        'samplerate': 16000,
    }),
    ('vbr16stereo.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 9432,
        'bitrate': 8.0,
        'channels': 2,
        'duration': 9.144,
        'other': OtherFields(),
        'samplerate': 16000,
    }),
    ('vbr22.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 9282,
        'bitrate': 7.962500000000001,
        'channels': 1,
        'duration': 9.11673469387755,
        'other': OtherFields(),
        'samplerate': 22050,
    }),
    ('vbr22stereo.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 9282,
        'bitrate': 7.962500000000001,
        'channels': 2,
        'duration': 9.11673469387755,
        'other': OtherFields(),
        'samplerate': 22050,
    }),
    ('vbr32.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 37008,
        'bitrate': 31.999999999999996,
        'channels': 1,
        'duration': 9.108,
        'other': OtherFields(),
        'samplerate': 32000,
    }),
    ('vbr32stereo.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 37008,
        'bitrate': 31.999999999999996,
        'channels': 2,
        'duration': 9.108,
        'other': OtherFields(),
        'samplerate': 32000,
    }),
    ('vbr44.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 36609,
        'bitrate': 31.849999999999998,
        'channels': 1,
        'duration': 9.09061224489796,
        'other': OtherFields(),
        'samplerate': 44100,
    }),
    ('vbr44stereo.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 36609,
        'bitrate': 31.849999999999998,
        'channels': 2,
        'duration': 9.09061224489796,
        'other': OtherFields(),
        'samplerate': 44100,
    }),
    ('vbr48.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 36672,
        'bitrate': 32.00000000000001,
        'channels': 1,
        'duration': 9.072,
        'other': OtherFields(),
        'samplerate': 48000,
    }),
    ('vbr48stereo.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 36672,
        'bitrate': 32.00000000000001,
        'channels': 2,
        'duration': 9.072,
        'other': OtherFields(),
        'samplerate': 48000,
    }),
    ('id3v24_genre_null_byte.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 256,
        'album': '\u79d8\u5bc6',
        'albumartist': 'aiko',
        'artist': 'aiko',
        'disc': 1,
        'genre': 'Pop',
        'title': '\u661f\u306e\u306a\u3044\u4e16\u754c',
        'track': 10,
        'year': '2008',
    }),
    ('vbr_xing_header_short.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 432,
        'bitrate': 8.000000000000002,
        'channels': 1,
        'duration': 0.144,
        'other': OtherFields(),
        'samplerate': 8000,
    }),
    ('id3_multiple_artists.mp3', {
        'other': OtherFields({
            'artist': [
                'artist2',
                'artist3',
                'artist4',
                'artist5',
                'artist6',
                'artist7',
            ]
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 2007,
        'bitrate': 31.849999999999998,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
        'artist': 'artist1',
        'genre': 'something 1',
    }),
    ('id3_frames.mp3', {
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 27576,
        'bitrate': 48.63492063492063,
        'channels': 1,
        'duration': 4.536,
        'samplerate': 16000,
        'other': OtherFields(),
    }),
    ('id3v22_with_image.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 2311,
        'title': 'image',
    }),
    ('utf16_no_bom.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 1069,
        'title': 'no bom test ë',
        'artist': 'no bom test 2 ë',
    }),
    ('title_after_image.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 2311,
        'title': 'title after image',
        'track': 1,
    }),
    ('grouping.mp3', {
        'other': OtherFields({
            'grouping': ['some grouping'],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 2007,
        'bitrate': 31.849999999999998,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
        'year': '2025',
        'track': 1,
        'track_total': 2,
    }),
    ('classical.mp3', {
        'other': OtherFields({
            'grouping': ['some grouping'],
            'work': ['some work'],
            'movement_name': ['some movement'],
            'movement': ['1'],
            'movement_total': ['2'],
            'show_movement': ['1']
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 2007,
        'bitrate': 31.849999999999998,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
        'composer': 'some composer',
        'genre': 'Classical',
        'year': '2025',
        'track': 1,
        'track_total': 2,
    }),
    ('empty_frame.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 2005,
        'bitrate': 32.0,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
        'album': 'some album',
        'artist': 'some artist',
    }),
    ('synced_lyrics_milliseconds.mp3', {
        'other': OtherFields({
            'lyrics': ['[00:00.00]\n[00:01.00]first line\n[00:01.55]second '
                       'line\n[00:05.99]third line'],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 2007,
        'bitrate': 31.849999999999998,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
    }),
    ('synced_lyrics_invalid.mp3', {
        'other': OtherFields({
            'lyrics': ['\nfirst line\nsecond line\nthird line'],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 2007,
        'bitrate': 31.849999999999998,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
    }),
    ('synced_lyrics_no_terminator_latin1.mp3', {
        'other': OtherFields({
            'lyrics': ['[18246:35.58]\n[18246:35.58]\n[18246:35.58]\n'
                       '[18246:35.58]\n[18246:35.58]\n[18246:35.58]\n'
                       '[18246:35.58]\n[18246:35.58]\n[18246:35.58]\n'
                       '[18246:35.58]\n[18246:35.58]\n[18246:35.58]'],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 498,
        'bitrate': 128.0,
        'channels': 2,
        'duration': 0.026122448979591838,
        'samplerate': 44100,
    }),
    ('synced_lyrics_no_terminator_utf16.mp3', {
        'other': OtherFields({
            'lyrics': ['[71580:52.86]\n[18175:35.68]\n[18175:35.68]\n'
                       '[18175:35.68]\n[18175:35.68]\n[18175:35.68]\n'
                       '[18175:35.68]\n[18175:35.68]\n[18175:35.68]\n'
                       '[18175:35.68]\n[18175:35.68]\n[18175:35.68]\n'
                       '[18175:35.68]'],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 507,
        'bitrate': 128.0,
        'channels': 2,
        'duration': 0.026122448979591838,
        'samplerate': 44100,
    }),
    ('xmp_data.mp3', {
        'other': OtherFields({
            'xmp': [
                '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>\n<x:'
                'xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Exempi + XMP Core 6'
                '.0.0">\n <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf'
                '-syntax-ns#">\n  <rdf:Description rdf:about=""\n    xmlns:xmp'
                'DM="http://ns.adobe.com/xmp/1.0/DynamicMedia/"\n    xmlns:dc='
                '"http://purl.org/dc/elements/1.1/"\n   xmpDM:artist="some art'
                'ist"\n   xmpDM:album="some album"\n   dc:test="value">\n   <d'
                'c:title>\n    <rdf:Alt>\n     <rdf:li xml:lang="x-default">so'
                'me title</rdf:li>\n    </rdf:Alt>\n   </dc:title>\n  </rdf:De'
                'scription>\n </rdf:RDF>\n</x:xmpmeta>'],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 5712,
        'bitrate': 31.849999999999998,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
    }),
    ('synced_lyrics_empty.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 1988,
        'bitrate': 31.849999999999998,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
    }),
    ('multi_value_utf16.mp3', {
        'other': OtherFields({
            'title': ['another title', 'yet another title'],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 1988,
        'bitrate': 31.849999999999998,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
        'title': 'some title',
    }),
    ('duplicate_fields.mp3', {
        'other': OtherFields({
            'title': ['new title', 'another title'],
            'artist': ['new artist', 'another artist'],
            'album': ['new album', 'another album'],
            'comment': ['new comment', 'another comment'],
            'track': ['2', '99'],
            'lyrics': ['duplicate lyrics', 'new lyrics', 'more lyrics'],
        }),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 3037,
        'bitrate': 31.849999999999998,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
        'title': 'duplicate title',
        'artist': 'duplicate artist',
        'album': 'duplicate album',
        'comment': 'duplicate comment',
        'track': 1,
        'genre': 'genre',
        'year': '1980',
    }),
    ('multiple_images.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 9633,
        'title': 'image',
    }),
    ('id3_broken_frame_size.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 1987,
        'bitrate': 31.849999999999998,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
    }),
    ('mpeg1_id3v1.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.1306122448979592,
        'filesize': 3888,
        'bitrate': 191.95749999999998,
        'title': 'some title',
    }),
    ('mpeg1_id3v2.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.1306122448979592,
        'filesize': 4815,
        'bitrate': 191.95749999999998,
        'title': 'some title',
    }),
    ('mpeg1_32khz_cbr.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 32000,
        'duration': 0.144,
        'filesize': 4320,
        'bitrate': 192.0,
    }),
    ('mpeg1_44_1khz_cbr.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.1306122448979592,
        'filesize': 3760,
        'bitrate': 191.95749999999998,
    }),
    ('mpeg1_48khz_cbr.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 48000,
        'duration': 0.144,
        'filesize': 4032,
        'bitrate': 192.0,
    }),
    ('mpeg2_id3v1.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 24000,
        'duration': 0.168,
        'filesize': 488,
        'bitrate': 7.999999999999999,
        'title': 'some title',
    }),
    ('mpeg2_id3v2.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 24000,
        'duration': 0.168,
        'filesize': 1415,
        'bitrate': 7.999999999999999,
        'title': 'some title',
    }),
    ('mpeg2_16khz_vbr.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 16000,
        'duration': 0.18,
        'filesize': 468,
        'bitrate': 8.0,
    }),
    ('mpeg2_22050hz_vbr.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 22050,
        'duration': 0.156734693877551,
        'filesize': 364,
        'bitrate': 7.9625,
    }),
    ('mpeg2_24khz_vbr.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 24000,
        'duration': 0.168,
        'filesize': 360,
        'bitrate': 7.999999999999999,
    }),
    ('mpeg25_id3v1.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 12000,
        'duration': 0.24,
        'filesize': 560,
        'bitrate': 8.0,
        'title': 'some title',
    }),
    ('mpeg25_id3v2.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 12000,
        'duration': 0.24,
        'filesize': 560,
        'bitrate': 8.0,
        'title': 'some title',
    }),
    ('mpeg25_8khz_vbr.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 8000,
        'duration': 0.288,
        'filesize': 576,
        'bitrate': 8.000000000000002,
    }),
    ('mpeg25_11025hz_vbr.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 11025,
        'duration': 0.2089795918367347,
        'filesize': 416,
        'bitrate': 7.9625,
    }),
    ('mpeg25_12khz_vbr.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 12000,
        'duration': 0.24,
        'filesize': 432,
        'bitrate': 8.0,
    }),
    ('mpeg1_id3v1.mp2', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.10448979591836735,
        'filesize': 5143,
        'bitrate': 384.0,
        'title': 'some title',
    }),
    ('mpeg1_id3v2.mp2', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.10448979591836735,
        'filesize': 6070,
        'bitrate': 384.0,
        'title': 'some title',
    }),
    ('mpeg1_32khz.mp2', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 32000,
        'duration': 0.108,
        'filesize': 5184,
        'bitrate': 384.0,
    }),
    ('mpeg1_44_1khz.mp2', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.10448979591836735,
        'filesize': 5015,
        'bitrate': 384.0,
    }),
    ('mpeg1_48khz.mp2', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 48000,
        'duration': 0.12,
        'filesize': 5760,
        'bitrate': 384.0,
    }),
    ('mpeg2_id3v1.mp2', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 24000,
        'duration': 0.144,
        'filesize': 3008,
        'bitrate': 160.0,
        'title': 'some title',
    }),
    ('mpeg2_id3v2.mp2', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 24000,
        'duration': 0.144,
        'filesize': 3935,
        'bitrate': 160.0,
        'title': 'some title',
    }),
    ('mpeg2_16khz.mp2', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 16000,
        'duration': 0.144,
        'filesize': 2880,
        'bitrate': 160.0,
    }),
    ('mpeg2_22050hz.mp2', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 22050,
        'duration': 0.10448979591836735,
        'filesize': 2089,
        'bitrate': 160.0,
    }),
    ('mpeg2_24khz.mp2', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 24000,
        'duration': 0.144,
        'filesize': 2880,
        'bitrate': 160.0,
    }),
    ('mpeg1_32khz.mp1', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 32000,
        'duration': 0.096,
        'filesize': 2688,
        'bitrate': 224.0,
    }),
    ('mpeg1_44_1khz.mp1', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.09578231292517007,
        'filesize': 2684,
        'bitrate': 224.0,
    }),
    ('mpeg1_48khz.mp1', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 48000,
        'duration': 0.096,
        'filesize': 2688,
        'bitrate': 224.0,
    }),
    ('empty.ogg', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'duration': 3.684716553287982,
        'filesize': 4328,
        'bitrate': 112.0,
        'samplerate': 44100,
        'channels': 2,
    }),
    ('multipage-setup.ogg', {
        'other': OtherFields({
            'transcoded': ['mp3;241'],
            'replaygain_album_gain': ['-10.29 dB'],
            'replaygain_album_peak': ['1.50579047'],
            'replaygain_track_peak': ['1.17979193'],
            'replaygain_track_gain': ['-10.02 dB'],
        }),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'genre': 'JRock',
        'duration': 4.128798185941043,
        'album': 'Timeless',
        'year': '2006',
        'title': 'Burst',
        'artist': 'UVERworld',
        'track': 7,
        'filesize': 76983,
        'bitrate': 160.0,
        'samplerate': 44100,
        'comment': 'SRCL-6240',
        'channels': 2,
    }),
    ('test.ogg', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'duration': 1.0,
        'album': 'the boss',
        'year': '2006',
        'title': 'the boss',
        'artist': 'james brown',
        'track': 1,
        'filesize': 7467,
        'bitrate': 160.0,
        'samplerate': 44100,
        'channels': 2,
        'comment': 'hello!',
    }),
    ('corrupt_metadata.ogg', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'filesize': 18648,
        'bitrate': 80.0,
        'duration': 2.132358276643991,
        'samplerate': 44100,
        'channels': 1,
    }),
    ('composer.ogg', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'filesize': 4480,
        'album': 'An Album',
        'artist': 'An Artist',
        'composer': 'some composer',
        'bitrate': 112.0,
        'duration': 3.684716553287982,
        'channels': 2,
        'genre': 'Some Genre',
        'samplerate': 44100,
        'title': 'A Title',
        'track': 2,
        'year': '2007',
        'comment': 'A Comment',
    }),
    ('ogg_with_image.ogg', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'channels': 1,
        'duration': 0.1,
        'filesize': 5759,
        'bitrate': 96.0,
        'samplerate': 44100,
        'artist': 'Sample Artist',
        'title': 'Sample Title',
    }),
    ('classical.ogg', {
        'other': OtherFields({
            'grouping': ['some grouping', 'some content group'],
            'work': ['some work'],
            'movement_name': ['some movement'],
            'movement': ['1'],
            'movement_total': ['2'],
            'show_movement': ['1']
        }),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'channels': 1,
        'duration': 0.1,
        'filesize': 4279,
        'bitrate': 96.0,
        'samplerate': 44100,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
        'composer': 'some composer',
        'genre': 'Classical',
        'year': '2025',
        'track': 1,
        'track_total': 2
    }),
    ('data_after_eos.ogg', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'duration': 3.684716553287982,
        'filesize': 4424,
        'bitrate': 112.0,
        'samplerate': 44100,
        'channels': 2,
    }),
    ('no_audio.ogg', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'duration': 0.0,
        'filesize': 2837,
        'samplerate': 8000,
        'channels': 2,
        'bitrate': 45.6,
    }),
    ('multi_stream.ogv', {
        'other': OtherFields({
            'encoder': ['Lavf62.3.100'],
        }),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'duration': 30.0,
        'filesize': 9344,
        'bitrate': 16.8,
        'samplerate': 8000,
        'channels': 1,
    }),
    ('negative_bitrate.ogg', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'duration': 7.6635,
        'filesize': 7224,
        'samplerate': 6000,
        'channels': 1,
    }),
    ('test.opus', {
        'other': OtherFields({
            'encoder': ['Lavc57.24.102 libopus'],
            'arrange': ['\u6771\u65b9'],
            'catalogid': ['ARCD0024'],
            'discid': ['A212230D'],
            'event': ['\u4f8b\u5927\u796d5'],
            'lyricist': ['Haruka'],
            'mastering': ['Hedonist'],
            'origin': ['\u6771\u65b9\u5e7b\u60f3\u90f7'],
            'originaltitle': ['Bad Apple!!'],
            'performer': ['Masayoshi Minoshima'],
            'vocal': ['nomico'],
        }),
        'mime_type': 'audio/ogg; codecs="opus"',
        'is_lossless': False,
        'albumartist': 'Alstroemeria Records',
        'samplerate': 48000,
        'channels': 2,
        'track': 1,
        'disc': 1,
        'title': 'Bad Apple!!',
        'duration': 0.9935,
        'bitrate': 51.5832913940614,
        'year': '2008.05.25',
        'filesize': 10000,
        'artist': 'nomico',
        'album': 'Exserens - A selection of Alstroemeria Records',
        'comment': 'ARCD0018 - Lovelight',
        'disc_total': 1,
        'track_total': 13,
    }),
    ('8khz_5s.opus', {
        'other': OtherFields({
            'encoder': ['opusenc from opus-tools 0.2']
        }),
        'mime_type': 'audio/ogg; codecs="opus"',
        'is_lossless': False,
        'filesize': 7251,
        'channels': 1,
        'samplerate': 48000,
        'duration': 5.0,
        'bitrate': 9.5952
    }),
    ('test_flac.oga', {
        'other': OtherFields({
            'copyright': ['test3'],
            'isrc': ['test4'],
            'lyrics': ['test7']
        }),
        'mime_type': 'audio/ogg; codecs="flac"',
        'is_lossless': True,
        'filesize': 9273,
        'album': 'test2',
        'artist': 'test6',
        'comment': 'test5',
        'bitrate': 19.912367802585194,
        'duration': 3.705034013605442,
        'channels': 2,
        'genre': 'Acoustic',
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'test1',
        'track': 5,
        'year': '2023',
    }),
    ('empty_file.ogg', {
        'other': OtherFields(),
        'filesize': 0,
    }),
    ('no_bitrate.spx', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="speex"',
        'is_lossless': False,
        'filesize': 7921,
        'channels': 1,
        'samplerate': 16000,
        'duration': 2.1445625,
        'artist': 'test1',
        'title': 'test2',
    }),
    ('bitrate_present.spx', {
        'other': OtherFields({
            'encoder': ['Lavc62.11.100 libspeex'],
        }),
        'mime_type': 'audio/ogg; codecs="speex"',
        'is_lossless': False,
        'filesize': 2304,
        'channels': 1,
        'samplerate': 8000,
        'bitrate': 15.0,
        'duration': 1.067,
        'artist': 'test1',
        'title': 'test2',
    }),
    ('zero_value_properties.ogg', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'filesize': 3979,
    }),
    ('silence.opus', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="opus"',
        'is_lossless': False,
        'filesize': 155,
        'duration': 0.1,
        'bitrate': 1.44,
        'samplerate': 48000,
        'channels': 2,
    }),
    ('zero_value_properties.opus', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="opus"',
        'is_lossless': False,
        'filesize': 155,
        'duration': 0.1065,
        'bitrate': 1.3521126760563382,
        'samplerate': 48000,
    }),
    ('zero_value_properties.spx', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="speex"',
        'is_lossless': False,
        'filesize': 2239,
    }),
    ('test.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'channels': 2,
        'duration': 1.0,
        'filesize': 176444,
        'bitrate': 1411.2,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('test3sMono.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'channels': 1,
        'duration': 3.0,
        'filesize': 264644,
        'bitrate': 705.6,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('test-tagged.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'channels': 2,
        'duration': 1.0,
        'filesize': 176688,
        'album': 'thealbum',
        'artist': 'theartisst',
        'bitrate': 1411.2,
        'genre': 'Acid',
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'thetitle',
        'track': 66,
        'comment': 'hello',
        'year': '2014',
    }),
    ('test-riff-tags.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'channels': 2,
        'duration': 1.0,
        'filesize': 176540,
        'artist': 'theartisst',
        'bitrate': 1411.2,
        'genre': 'Acid',
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'thetitle',
        'comment': 'hello',
        'year': '2014',
    }),
    ('silence-22khz-mono-1s.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'channels': 1,
        'duration': 0.9991836734693877,
        'filesize': 48160,
        'bitrate': 352.8,
        'samplerate': 22050,
        'bitdepth': 16,
    }),
    ('id3_header_with_a_zero_byte.wav', {
        'other': OtherFields({
            'title': ['Stacked'],
            'isft': ['Lavf58.20.100'],
        }),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'channels': 1,
        'duration': 1.0,
        'filesize': 44280,
        'bitrate': 352.8,
        'samplerate': 22050,
        'bitdepth': 16,
        'artist': 'Purpley',
        'title': 'Test000',
        'track': 17,
        'album': 'prototypes',
    }),
    ('adpcm.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="2"',
        'is_lossless': False,
        'channels': 1,
        'duration': 12.080136054421768,
        'filesize': 268686,
        'bitrate': 177.6721711022762,
        'samplerate': 44100,
        'bitdepth': 4,
        'artist': 'test artist',
        'title': 'test title',
        'track': 1,
        'album': 'test album',
        'comment': 'test comment',
        'genre': 'test genre',
        'year': '1990',
    }),
    ('riff_extra_zero.wav', {
        'other': OtherFields({
            'isft': ['Lavf59.16.100'],
        }),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'channels': 2,
        'duration': 0.11609977324263039,
        'filesize': 20670,
        'bitrate': 1411.2,
        'samplerate': 44100,
        'bitdepth': 16,
        'artist': 'B.O.S.E.',
        'title': 'Mission Bass',
        'album': '808 Bass Express',
        'genre': 'Hip-Hop/Rap',
        'year': '1996',
        'track': 3,
    }),
    ('riff_extra_zero_2.wav', {
        'other': OtherFields({
            'isft': ['Lavf59.16.100'],
        }),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'channels': 2,
        'duration': 0.11609977324263039,
        'filesize': 20682,
        'bitrate': 1411.2,
        'samplerate': 44100,
        'bitdepth': 16,
        'artist': 'The Jimmy Castor Bunch',
        'title': 'It\'s Just Begun',
        'album': 'The Perfect Beats, Vol. 4',
        'genre': 'Pop Electronica',
        'track': 7,
    }),
    ('wav_invalid_track_number.wav', {
        'other': OtherFields({
            '_disc': ['garbage'],
        }),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'filesize': 8908,
        'bitrate': 705.6,
        'duration': 0.1,
        'samplerate': 44100,
        'channels': 1,
        'bitdepth': 16,
    }),
    ('gsm_6_10.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="31"',
        'is_lossless': False,
        'bitrate': 72.8,
        'channels': 1,
        'duration': 0.1,
        'filesize': 1246,
        'samplerate': 44100,
        'album': 'album',
        'artist': 'artist',
        'title': 'track',
        'track': 99,
        'year': '2010',
        'comment': 'some comment here',
        'genre': 'Bass',
    }),
    ('wav_with_image.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'channels': 1,
        'duration': 2.144625,
        'filesize': 22902,
        'bitrate': 64.0,
        'samplerate': 8000,
        'bitdepth': 8,
    }),
    ('xmp_data.wav', {
        'other': OtherFields({
            'xmp': [
                "<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>\n"
                "<x:xmpmeta xmlns:x='adobe:ns:meta/' x:xmptk='Image::ExifTool "
                "13.55'>\n<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf"
                "-syntax-ns#'>\n\n <rdf:Description rdf:about=''\n  xmlns:xmp="
                "'http://ns.adobe.com/xap/1.0/'>\n  <xmp:CreateDate>2026-06-03"
                "T00:00:00</xmp:CreateDate>\n </rdf:Description>\n</rdf:RDF>\n"
                "</x:xmpmeta>"
            ]
        }),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'artist': 'some artist',
        'title': 'some title',
        'album': 'some album',
        'filesize': 11752,
        'samplerate': 44100,
        'duration': 0.1,
        'channels': 1,
        'bitrate': 705.6,
        'bitdepth': 16,
    }),
    ('32bit_float.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="3"',
        'is_lossless': True,
        'bitrate': 512.0,
        'channels': 2,
        'duration': 0.1,
        'filesize': 6488,
        'samplerate': 8000,
        'bitdepth': 32,
    }),
    ('24bit_pcm.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'bitrate': 384.0,
        'channels': 2,
        'duration': 0.1,
        'filesize': 4844,
        'samplerate': 8000,
        'bitdepth': 24,
    }),
    ('24bit_pcm_extended.wav', {
        'other': OtherFields({
            'isft': ['Lavf61.7.100'],
        }),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'bitrate': 384.0,
        'channels': 2,
        'duration': 0.128,
        'filesize': 6246,
        'samplerate': 8000,
        'bitdepth': 24,
    }),
    ('32bit_pcm.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'bitrate': 512.0,
        'channels': 2,
        'duration': 0.1,
        'filesize': 6444,
        'samplerate': 8000,
        'bitdepth': 32,
    }),
    ('32bit_pcm_extended.wav', {
        'other': OtherFields({
            'isft': ['Lavf61.7.100'],
        }),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'bitrate': 512.0,
        'channels': 2,
        'duration': 0.128,
        'filesize': 8294,
        'samplerate': 8000,
        'bitdepth': 32,
    }),
    ('adpcm_no_byterate.wav', {
        'other': OtherFields({
            'isft': ['Lavf61.7.100'],
        }),
        'mime_type': 'audio/wav; codecs="2"',
        'is_lossless': False,
        'bitrate': 64.7588932806324,
        'channels': 2,
        'duration': 0.1265,
        'filesize': 1148,
        'samplerate': 8000,
        'bitdepth': 4,
    }),
    ('no_audio_data_compressed.wav', {
        'other': OtherFields({
            'isft': ['Lavf61.7.100'],
        }),
        'mime_type': 'audio/wav; codecs="55"',
        'is_lossless': False,
        'channels': 2,
        'duration': 0.0,
        'filesize': 104,
        'samplerate': 8000,
    }),
    ('no_audio_data_uncompressed.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'channels': 2,
        'duration': 0.0,
        'filesize': 44,
        'samplerate': 8000,
        'bitdepth': 16,
        'bitrate': 256.0,
    }),
    ('8bit_pcm.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'bitrate': 128.0,
        'channels': 2,
        'duration': 0.1,
        'filesize': 1644,
        'samplerate': 8000,
        'bitdepth': 8,
    }),
    ('8bit_pcm_lavf.wav', {
        'other': OtherFields({
            'isft': ['Lavf61.7.100'],
        }),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'bitrate': 128.0,
        'channels': 2,
        'duration': 0.128,
        'filesize': 2126,
        'samplerate': 8000,
        'bitdepth': 8,
    }),
    ('16bit_pcm.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'bitrate': 256.0,
        'channels': 2,
        'duration': 0.1,
        'filesize': 3244,
        'samplerate': 8000,
        'bitdepth': 16,
    }),
    ('mp3_audio.wav', {
        'other': OtherFields({
            'isft': ['Lavf61.7.100'],
        }),
        'mime_type': 'audio/wav; codecs="55"',
        'is_lossless': False,
        'filesize': 4264,
        'samplerate': 44100,
        'duration': 1.0250566893424036,
        'channels': 1,
        'bitrate': 32.46649706890831,
    }),
    ('empty_file.wav', {
        'other': OtherFields(),
        'filesize': 0,
    }),
    ('zero_value_properties.wav', {
        'other': OtherFields(),
        'mime_type': 'audio/wav',
        'filesize': 1644,
    }),
    ('flac1sMono.flac', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'genre': 'Avantgarde',
        'album': 'alb',
        'year': '2014',
        'duration': 1.0,
        'title': 'track',
        'track': 23,
        'artist': 'art',
        'channels': 1,
        'filesize': 26632,
        'bitrate': 211.48,
        'samplerate': 44100,
        'bitdepth': 16,
        'comment': 'hello',
    }),
    ('flac453sStereo.flac', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'channels': 2,
        'duration': 453.51473922902494,
        'filesize': 84236,
        'bitrate': 1.33982856,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('flac1.5sStereo.flac', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'channels': 2,
        'album': 'alb',
        'year': '2014',
        'duration': 1.4995238095238095,
        'title': 'track',
        'track': 23,
        'artist': 'art',
        'filesize': 59868,
        'bitrate': 318.34639568116864,
        'genre': 'Avantgarde',
        'samplerate': 44100,
        'bitdepth': 16,
        'comment': 'hello',
    }),
    ('flac_application.flac', {
        'other': OtherFields({
            'replaygain_track_peak': ['0.9976'],
            'musicbrainz_albumartistid': [
                'e5c7b94f-e264-473c-bb0f-37c85d4d5c70'
            ],
            'musicbrainz_trackid': ['e65fb332-0c1e-4172-85e0-59cd37e5669e'],
            'replaygain_album_gain': ['-8.14 dB'],
            'labelid': ['RTRADLP480'],
            'musicbrainz_albumid': ['359a91e9-3bb3-4b60-a823-8aaa4bad1e36'],
            'artistsort': ['Belle and Sebastian'],
            'replaygain_track_gain': ['-8.08 dB'],
            'replaygain_album_peak': ['1.0000'],
        }),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'channels': 2,
        'track_total': 11,
        'album': 'Belle and Sebastian Write About Love',
        'year': '2010-10-11',
        'duration': 273.64,
        'title': 'I Want the World to Stop',
        'track': 4,
        'artist': 'Belle and Sebastian',
        'filesize': 13000,
        'bitrate': 0.0023973103347463822,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('no-tags.flac', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'channels': 2,
        'duration': 3.684716553287982,
        'filesize': 4692,
        'bitrate': 1.0985919653406853,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('variable-block.flac', {
        'other': OtherFields({
            'discid': ['AA0B360B'],
            'japanese title': ['アップルシード オリジナル・サウンドトラック'],
            'organization': ['Sony Music Records (SRCP-371)'],
            'ripper': ['Exact Audio Copy 0.99pb5'],
            'replaygain_album_gain': ['-8.68 dB'],
            'replaygain_album_peak': ['1.000000'],
            'replaygain_track_gain': ['-9.61 dB'],
            'replaygain_track_peak': ['1.000000'],
        }),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'channels': 2,
        'album': 'Appleseed Original Soundtrack',
        'year': '2004',
        'duration': 261.68,
        'title': 'DIVE FOR YOU',
        'track': 1,
        'track_total': 11,
        'artist': 'Boom Boom Satellites',
        'filesize': 10240,
        'bitrate': 0.06040966065423418,
        'disc': 1,
        'genre': 'Anime Soundtrack',
        'samplerate': 44100,
        'bitdepth': 16,
        'disc_total': 2,
        'comment': 'Original Soundtrack',
        'composer': 'Boom Boom Satellites (Lyrics)',
    }),
    ('106-invalid-streaminfo.flac', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'filesize': 4692,
        'bitrate': 1.0985919653406853,
        'channels': 2,
        'duration': 3.684716553287982,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('106-short-picture-block-size.flac', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'filesize': 4692,
        'bitrate': 1.0985919653406853,
        'channels': 2,
        'duration': 3.684716553287982,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('with_padded_id3_header.flac', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'filesize': 16070,
        'album': 'album',
        'artist': 'artist',
        'bitrate': 261.74231999999995,
        'channels': 1,
        'duration': 0.45351473922902497,
        'genre': 'genre',
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'title',
        'track': 1,
        'year': '2018',
        'comment': 'comment',
    }),
    ('with_padded_id3_header2.flac', {
        'other': OtherFields({
            'tlen': ['297666'],
            'encoded_by': ['Exact Audio Copy   (Sicherer Modus)'],
            'encoder_settings': [
                'flac.exe -T "artist=Unbekannter Künstler" '
                '-T "title=Track01" -T "album=Unbekannter Titel" '
                '-T "date=" -T "tracknumber=01" -T "genre=" -5'
            ],
            'artist': ['artist'],
            'album': ['album'],
            'title': ['title'],
        }),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'filesize': 19522,
        'album': 'Unbekannter Titel',
        'artist': 'Unbekannter Künstler',
        'bitrate': 261.74231999999995,
        'channels': 1,
        'disc': 1,
        'disc_total': 1,
        'duration': 0.45351473922902497,
        'genre': 'genre',
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'Track01',
        'track': 1,
        'track_total': 5,
        'year': '2018',
        'comment': 'comment',
    }),
    ('flac_invalid_track_number.flac', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'filesize': 235,
        'bitrate': 1.92,
        'channels': 1,
        'duration': 0.1,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('multiple_values_images.flac', {
        'other': OtherFields({
            'artist': ['artist 2', 'artist 3'],
            'genre': ['genre 2'],
            'album': ['album 2'],
            'disc': ['2', '3'],
            'disc_total': ['2', '3'],
            'track': ['2', '3'],
            'track_total': ['2', '3'],
            'url': ['https://example.com'],
        }),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'filesize': 4749,
        'album': 'album 1',
        'artist': 'artist 1',
        'bitrate': 1.92,
        'channels': 1,
        'duration': 0.1,
        'genre': 'genre 1',
        'samplerate': 44100,
        'bitdepth': 16,
        'disc': 1,
        'disc_total': 1,
        'track': 1,
        'track_total': 1,
    }),
    ('unsynced_lyrics.flac', {
        'other': OtherFields({
            'lyrics': ['some lyrics here\nnew line']
        }),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'channels': 2,
        'duration': 3.684716553287982,
        'filesize': 4777,
        'bitrate': 1.0985919653406853,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('empty_file.flac', {
        'other': OtherFields(),
        'filesize': 0,
    }),
    ('invalid_second_streaminfo.flac', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'filesize': 273,
        'bitrate': 1.92,
        'channels': 1,
        'duration': 0.1,
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'title',
    }),
    ('invalid_block_sizes.flac', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'filesize': 295,
        'bitrate': 1.92,
        'channels': 1,
        'duration': 0.1,
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'some title',
        'artist': 'some artist',
        'track': 1,
        'album': 'some album',
    }),
    ('zero_value_properties.flac', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'filesize': 235,
        'channels': 1,
        'bitdepth': 1,
    }),
    ('test2.wma', {
        'other': OtherFields({
            '_track': ['0'],
            'mediaprimaryclassid': ['{D1607DBC-E323-4BE2-86A1-48A42A28441E}'],
            'encodingtime': ['128861118183900000'],
            'wmfsdkversion': ['11.0.5721.5145'],
            'wmfsdkneeded': ['0.0.0.0000'],
            'isvbr': ['1'],
            'peakvalue': ['30369'],
            'averagelevel': ['7291'],
            'deviceconformancetemplate': ['L2'],
        }),
        'mime_type': 'application/vnd.ms-asf; codecs="161"',
        'is_lossless': False,
        'samplerate': 44100,
        'album': 'The Colour and the Shape',
        'title': 'Doll',
        'bitrate': 64.04,
        'filesize': 5800,
        'track': 1,
        'albumartist': 'Foo Fighters',
        'artist': 'Foo Fighters',
        'duration': 83.406,
        'year': '1997',
        'genre': 'Alternative',
        'composer': 'Foo Fighters',
        'channels': 2,
        'bitdepth': 16,
    }),
    ('lossless.wma', {
        'other': OtherFields(),
        'mime_type': 'application/vnd.ms-asf; codecs="163"',
        'is_lossless': True,
        'samplerate': 44100,
        'bitrate': 667.296,
        'filesize': 2500,
        'bitdepth': 16,
        'duration': 43.133,
        'channels': 2,
    }),
    ('wma_invalid_track_number.wma', {
        'other': OtherFields({
            'encoder_settings': ['Lavf60.16.100']
        }),
        'mime_type': 'application/vnd.ms-asf; codecs="161"',
        'is_lossless': False,
        'filesize': 3940,
        'bitrate': 128.0,
        'duration': 2.1409999999999996,
        'samplerate': 44100,
        'bitdepth': 16,
        'channels': 1,
    }),
    ('grouping.wma', {
        'other': OtherFields({
            'grouping': ['some grouping'],
            'work': ['some work'],
        }),
        'mime_type': 'application/vnd.ms-asf; codecs="161"',
        'is_lossless': False,
        'filesize': 4070,
        'bitrate': 128.0,
        'duration': 2.1409999999999996,
        'samplerate': 44100,
        'bitdepth': 16,
        'channels': 1,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
        'year': '2025',
    }),
    ('xmp_data.wma', {
        'other': OtherFields({
            'xmp': [
                '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>\n<x:'
                'xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Exempi + XMP Core 6'
                '.0.0">\n <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf'
                '-syntax-ns#">\n  <rdf:Description rdf:about=""\n    xmlns:xmp'
                '="http://ns.adobe.com/xap/1.0/"\n    xmlns:dc="http://purl.or'
                'g/dc/elements/1.1/"\n    xmlns:asf="http://ns.adobe.com/asf/1'
                '.0/"\n   xmp:CreateDate="1970-01-01T00:00:00Z"\n   dc:test="v'
                'alue"\n   asf:NativeDigest="0,1,2,3,4;97E16F15A2F14D88FB93680'
                'F9D2428A1">\n   <dc:title>\n    <rdf:Alt>\n     <rdf:li xml:l'
                'ang="x-default">some title</rdf:li>\n    </rdf:Alt>\n   </dc:'
                'title>\n   <dc:creator>\n    <rdf:Seq>\n     <rdf:li>some art'
                'ist</rdf:li>\n    </rdf:Seq>\n   </dc:creator>\n  </rdf:Descr'
                'iption>\n </rdf:RDF>\n</x:xmpmeta>\n<?xpacket end="r"?>'
            ],
            'encoder_settings': ['Lavf60.16.100'],
        }),
        'mime_type': 'application/vnd.ms-asf; codecs="161"',
        'is_lossless': False,
        'filesize': 4723,
        'bitrate': 128.0,
        'duration': 2.1409999999999996,
        'samplerate': 44100,
        'bitdepth': 16,
        'channels': 1,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
    }),
    ('empty_file.wma', {
        'other': OtherFields(),
        'filesize': 0,
    }),
    ('invalid_object_size.wma', {
        'other': OtherFields(),
        'mime_type': 'application/vnd.ms-asf',
        'filesize': 2500,
    }),
    ('zero_value_properties.wma', {
        'other': OtherFields(),
        'mime_type': 'application/vnd.ms-asf',
        'filesize': 2500,
        'duration': 0.0,
    }),
    ('silence.wma', {
        'other': OtherFields({
            'encoder_settings': ['Lavf62.12.102'],
        }),
        'mime_type': 'application/vnd.ms-asf; codecs="161"',
        'is_lossless': False,
        'samplerate': 8000,
        'bitrate': 128.0,
        'filesize': 3744,
        'bitdepth': 16,
        'duration': 0.10000000000000009,
        'channels': 2,
    }),
    ('multiple_values_images.wma', {
        'other': OtherFields({
            'album': ['another album', 'some album'],
            'artist': ['another artist', 'some artist'],
            'title': ['another title', 'some title'],
            'comment': [
                'almost there...', 'greatness takes time',
                'the hex editor is my best friend'
            ],
            'copyright': ['even more nothing', 'more nothing', 'nothing'],
            'encoder_settings': ['Lavf62.12.102'],
        }),
        'mime_type': 'application/vnd.ms-asf; codecs="161"',
        'is_lossless': False,
        'samplerate': 8000,
        'bitrate': 128.0,
        'filesize': 8384,
        'bitdepth': 16,
        'duration': 0.10000000000000009,
        'channels': 2,
        'album': 'yet another album',
        'artist': 'yet another artist',
        'title': 'yet another title',
        'genre': 'Jungle',
        'year': '1960',
        'comment': 'dreaming in bytes',
    }),
    ('mp3_audio.asf', {
        'other': OtherFields({
            'encoder_settings': ['Lavf61.7.100'],
        }),
        'mime_type': 'application/vnd.ms-asf; codecs="55"',
        'is_lossless': False,
        'samplerate': 44100,
        'filesize': 6906,
        'duration': 2.145,
        'channels': 1,
    }),
    ('test.m4a', {
        'other': OtherFields({
            'itunsmpb': [
                ' 00000000 00000840 000001DC 0000000000D3E9E4 00000000'
                ' 00000000 00000000 00000000 00000000 00000000 00000000'
                ' 00000000'
            ],
            'itunnorm': [
                ' 00000358 0000032E 000020AE 000020D9 0003A228 00032A28'
                ' 00007E20 00007E90 00007BFD 00009293'
            ],
            'itunes_cddb_ids': ['11++'],
            'ufidhttp://www.cddb.com/id3/taginfo1.html': [
                '3CD3N48Q241232290U3387DD249F72E6B082B283425ADB9B0F324P1'
            ],
            'bpm': ['0'],
            'encoded_by': ['iTunes 10.5'],
            'cpil': ['0'],
            'pgap': ['0'],
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'samplerate': 44100,
        'duration': 314.97868480725623,
        'bitrate': 256.0,
        'channels': 2,
        'genre': 'Pop',
        'year': '2011',
        'title': 'Nothing',
        'album': 'Only Our Hearts To Lose',
        'track_total': 11,
        'track': 11,
        'artist': 'Marian',
        'filesize': 61432,
    }),
    ('mpeg4_with_image.m4a', {
        'other': OtherFields({
            'publisher': ['test7'],
            'bpm': ['1'],
            'encoded_by': ['Lavf60.3.100']
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'artist': 'test1',
        'composer': 'test8',
        'filesize': 9419,
        'samplerate': 8000,
        'duration': 1.294,
        'channels': 1,
        'bitrate': 27.887,
    }),
    ('alac_file.m4a', {
        'other': OtherFields({
            'copyright': ['© Hyperion Records Ltd, London'],
            'lyrics': ['Album notes:'],
            'upc': ['0034571177380']
        }),
        'mime_type': 'audio/mp4; codecs="alac"',
        'is_lossless': True,
        'artist': 'Howard Shelley',
        'filesize': 20000,
        'composer': 'Clementi, Muzio (1752-1832)',
        'title': 'Clementi: Piano Sonata in D major, Op 25 No 6 - Movement 2: '
                 'Un poco andante',
        'album': 'Clementi: The Complete Piano Sonatas, Vol. 4',
        'year': '2009',
        'track': 14,
        'track_total': 27,
        'disc': 1,
        'disc_total': 1,
        'samplerate': 44100,
        'duration': 166.62639455782312,
        'genre': 'Classical',
        'albumartist': 'Howard Shelley',
        'channels': 2,
        'bitrate': 436.743,
        'bitdepth': 16,
    }),
    ('mpeg4_desc_cmt.m4a', {
        'other': OtherFields({
            'description': ['test description'],
            'encoded_by': ['Lavf59.27.100']
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'filesize': 32006,
        'bitrate': 101.038,
        'channels': 2,
        'comment': 'test comment',
        'duration': 2.36,
        'samplerate': 44100,
    }),
    ('mpeg4_xa9des.m4a', {
        'other': OtherFields({
            'description': ['test description']
        }),
        'mime_type': 'audio/mp4',
        'filesize': 2639,
        'comment': 'test comment',
        'duration': 727.1066666666667,
    }),
    ('test2.m4a', {
        'other': OtherFields({
            'publisher': ['test7'],
            'bpm': ['99999'],
            'encoded_by': ['Lavf60.3.100']
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'artist': 'test1',
        'composer': 'test8',
        'filesize': 6260,
        'samplerate': 8000,
        'duration': 1.294,
        'channels': 1,
        'bitrate': 27.887,
    }),
    ('mvhd_version_1.m4a', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4; codecs="mp4a.40.5"',
        'is_lossless': False,
        'title': '64-bit test',
        'filesize': 2048,
        'samplerate': 44100,
        'duration': 123251.6585941043,
        'channels': 2,
    }),
    ('multi_value.m4a', {
        'other': OtherFields({
            'artist': ['another artist', 'yet another artist'],
            'composer': [
                'another composer', 'yet another composer', 'last composer'
            ],
            'custom': ['value1', 'value2', 'value3'],
            'encoded_by': ['Lavf61.7.100'],
            'grouping': ['grouping', 'second grouping']
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'artist': 'some artist',
        'title': 'some title',
        'album': 'some album',
        'composer': 'some composer',
        'filesize': 1995,
        'samplerate': 44100,
        'duration': 0.524,
        'channels': 1,
        'bitrate': 1.666,
    }),
    ('mixed_case_atoms.m4a', {
        'other': OtherFields({
            'plid': ['1'],
            'atid': ['2'],
            'cnid': ['3'],
            'pgap': ['1'],
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'filesize': 1995,
        'samplerate': 44100,
        'duration': 0.524,
        'channels': 1,
        'bitrate': 1.666,
    }),
    ('classical.m4a', {
        'other': OtherFields({
            'grouping': ['some grouping'],
            'work': ['some work'],
            'movement_name': ['some movement'],
            'movement': ['1'],
            'movement_total': ['2'],
            'show_movement': ['1'],
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'filesize': 1995,
        'samplerate': 44100,
        'duration': 0.524,
        'channels': 1,
        'bitrate': 1.666,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
        'composer': 'some composer',
        'genre': 'Classical',
        'year': '2025',
        'track': 1,
        'track_total': 2,
    }),
    ('mp4_extended_size.m4a', {
        'other': OtherFields({
            'description': ['test description'],
            'encoded_by': ['Lavf59.27.100']
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'comment': 'test comment',
        'filesize': 32014,
        'samplerate': 44100,
        'duration': 2.36,
        'channels': 2,
        'bitrate': 101.038,
    }),
    ('mp4_extended_size_truncated.m4a', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4',
        'filesize': 39
    }),
    ('mp4_invalid_size_zero.m4a', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4',
        'filesize': 152
    }),
    ('xmp_data.m4a', {
        'other': OtherFields({
            'xmp': [
                "<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>\n"
                "<x:xmpmeta xmlns:x='adobe:ns:meta/' x:xmptk='Image::ExifTool "
                "13.55'>\n<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf"
                "-syntax-ns#'>\n\n <rdf:Description rdf:about=''\n  xmlns:xmp="
                "'http://ns.adobe.com/xap/1.0/'>\n  <xmp:CreateDate>2026-06-03"
                "T00:00:00</xmp:CreateDate>\n </rdf:Description>\n</rdf:RDF>\n"
                "</x:xmpmeta>"
            ],
            'encoded_by': ['Lavf61.7.100']
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'artist': 'some artist',
        'title': 'some title',
        'album': 'some album',
        'filesize': 4826,
        'samplerate': 44100,
        'duration': 0.524,
        'channels': 1,
        'bitrate': 1.666,
    }),
    ('xmp_empty.m4a', {
        'other': OtherFields({
            'encoded_by': ['Lavf61.7.100']
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'artist': 'some artist',
        'title': 'some title',
        'album': 'some album',
        'filesize': 2019,
        'samplerate': 44100,
        'duration': 0.524,
        'channels': 1,
        'bitrate': 1.666,
    }),
    ('8bit_pcm_to_als.mp4', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4; codecs="mp4a.40.36"',
        'is_lossless': True,
        'bitrate': 19.76,
        'channels': 2,
        'duration': 0.1,
        'filesize': 928,
        'samplerate': 8000,
    }),
    ('8bit_pcm_lavf_to_als.mp4', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4; codecs="mp4a.40.36"',
        'is_lossless': True,
        'bitrate': 0.125,
        'channels': 2,
        'duration': 0.128,
        'filesize': 719,
        'samplerate': 8000,
    }),
    ('16bit_pcm_to_als.mp4', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4; codecs="mp4a.40.36"',
        'is_lossless': True,
        'bitrate': 23.6,
        'channels': 2,
        'duration': 0.1,
        'filesize': 976,
        'samplerate': 8000,
    }),
    ('24bit_pcm_to_als.mp4', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4; codecs="mp4a.40.36"',
        'is_lossless': True,
        'bitrate': 23.84,
        'channels': 2,
        'duration': 0.1,
        'filesize': 979,
        'samplerate': 8000,
    }),
    ('24bit_pcm_extended_to_als.mp4', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4; codecs="mp4a.40.36"',
        'is_lossless': True,
        'bitrate': 134.812,
        'channels': 2,
        'duration': 0.128,
        'filesize': 2899,
        'samplerate': 8000,
    }),
    ('32bit_pcm_to_als.mp4', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4; codecs="mp4a.40.36"',
        'is_lossless': True,
        'bitrate': 0.16,
        'channels': 2,
        'duration': 0.1,
        'filesize': 683,
        'samplerate': 8000,
    }),
    ('32bit_pcm_extended_to_als.mp4', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4; codecs="mp4a.40.36"',
        'is_lossless': True,
        'bitrate': 262.187,
        'channels': 2,
        'duration': 0.128,
        'filesize': 4937,
        'samplerate': 8000,
    }),
    ('32bit_float_to_als.mp4', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4; codecs="mp4a.40.36"',
        'is_lossless': True,
        'bitrate': 0.64,
        'channels': 2,
        'duration': 0.1,
        'filesize': 736,
        'samplerate': 8000,
    }),
    ('mp3_audio.m4a', {
        'other': OtherFields({
            'encoded_by': ['Lavf61.7.100']
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.6B"',
        'is_lossless': False,
        'filesize': 4922,
        'samplerate': 44100,
        'duration': 1.025,
        'channels': 1,
        'bitrate': 32.48,
    }),
    ('empty_file.m4a', {
        'other': OtherFields(),
        'filesize': 0,
    }),
    ('empty_custom_field.m4a', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4',
        'filesize': 72,
    }),
    ('zero_value_properties.m4a', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4',
        'filesize': 1995,
    }),
    ('alac_silence.m4a', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4; codecs="alac"',
        'is_lossless': True,
        'filesize': 1124,
        'samplerate': 8000,
        'duration': 0.1,
        'channels': 2,
        'bitrate': 256.0,
        'bitdepth': 16,
    }),
    ('zero_value_properties_alac.m4a', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4; codecs="alac"',
        'is_lossless': True,
        'filesize': 1124,
    }),
    ('mp3_audio_no_btrt_atom.m4a', {
        'other': OtherFields({
            'encoded_by': ['Lavf62.12.102']
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.6B"',
        'is_lossless': False,
        'filesize': 4895,
        'samplerate': 44100,
        'duration': 1.045,
        'channels': 1,
        'bitrate': 31.85,
    }),
    ('mp3_audio_dec_config_last.m4a', {
        'other': OtherFields({
            'encoded_by': ['Lavf62.12.102']
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.6B"',
        'is_lossless': False,
        'filesize': 4889,
        'samplerate': 44100,
        'duration': 1.045,
        'channels': 1,
        'bitrate': 31.85,
    }),
    ('test-tagged.aiff', {
        'other': OtherFields(),
        'mime_type': 'audio/aiff; codecs="NONE"',
        'is_lossless': True,
        'channels': 2,
        'duration': 1.0,
        'filesize': 177620,
        'artist': 'theartist',
        'bitrate': 1411.2,
        'genre': 'Acid',
        'samplerate': 44100,
        'bitdepth': 16,
        'track': 1,
        'title': 'thetitle',
        'album': 'thealbum',
        'comment': 'hello',
        'year': '2014',
    }),
    ('test.aiff', {
        'other': OtherFields({
            'copyright': ['℗ 1992 Ace Records']
        }),
        'mime_type': 'audio/aiff; codecs="NONE"',
        'is_lossless': True,
        'channels': 2,
        'duration': 0.0,
        'filesize': 164,
        'samplerate': 44100,
        'bitdepth': 16,
        'bitrate': 1411.2,
        'title': 'Go Out and Get Some',
        'comment': 'Millie Jackson - Get It Out \'cha System - 1978',
    }),
    ('pluck-pcm8.aiff', {
        'other': OtherFields(),
        'mime_type': 'audio/aiff; codecs="NONE"',
        'is_lossless': True,
        'channels': 2,
        'duration': 0.2999546485260771,
        'filesize': 6892,
        'artist': 'Serhiy Storchaka',
        'title': 'Pluck',
        'album': 'Python Test Suite',
        'bitrate': 176.4,
        'samplerate': 11025,
        'bitdepth': 8,
        'comment': 'Audacity Pluck + Wahwah',
        'year': '2013',
    }),
    ('M1F1-mulawC-AFsp.afc', {
        'other': OtherFields({
            'comment': ['user: kabal@CAPELLA', 'program: CopyAudio']
        }),
        'mime_type': 'audio/aiff; codecs="ulaw"',
        'is_lossless': False,
        'channels': 2,
        'duration': 2.936625,
        'filesize': 47148,
        'bitrate': 256.0,
        'samplerate': 8000,
        'bitdepth': 16,
        'comment': 'AFspdate: 2003-01-30 03:28:34 UTC',
    }),
    ('invalid_sample_rate.aiff', {
        'other': OtherFields(),
        'mime_type': 'audio/aiff; codecs="NONE"',
        'is_lossless': True,
        'channels': 1,
        'filesize': 4096,
        'bitdepth': 16,
    }),
    ('aiff_extra_tags.aiff', {
        'other': OtherFields({
            'copyright': ['test'],
            'isrc': ['CC-XXX-YY-NNNNN']
        }),
        'mime_type': 'audio/aiff; codecs="NONE"',
        'is_lossless': True,
        'channels': 1,
        'duration': 2.176,
        'filesize': 18532,
        'bitrate': 64.0,
        'samplerate': 8000,
        'bitdepth': 8,
        'title': 'song title',
        'artist': 'artist 1;artist 2',
    }),
    ('aiff_with_image.aiff', {
        'other': OtherFields(),
        'mime_type': 'audio/aiff; codecs="NONE"',
        'is_lossless': True,
        'channels': 1,
        'duration': 2.176,
        'filesize': 21044,
        'bitrate': 64.0,
        'samplerate': 8000,
        'bitdepth': 8,
        'title': 'image',
    }),
    ('xmp_data.aiff', {
        'other': OtherFields({
            'xmp': [
                '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>\n<x:'
                'xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Exempi + XMP Core 6'
                '.0.0">\n   <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-r'
                'df-syntax-ns#">\n      <rdf:Description rdf:about=""\n       '
                '     xmlns:dc="http://purl.org/dc/elements/1.1/"\n           '
                ' xmlns:xmpDM="http://ns.adobe.com/xmp/1.0/DynamicMedia/">\n  '
                '       <dc:title>\n            <rdf:Alt>\n               <rdf'
                ':li xml:lang="x-default">Pluck</rdf:li>\n            </rdf:Al'
                't>\n         </dc:title>\n         <dc:creator>\n            '
                '<rdf:Bag>\n               <rdf:li>Serhiy Storchaka</rdf:li>\n'
                '            </rdf:Bag>\n         </dc:creator>\n         <dc:'
                'test>value</dc:test>\n         <xmpDM:logComment>Audacity Plu'
                'ck + Wahwah</xmpDM:logComment>\n      </rdf:Description>\n   '
                '</rdf:RDF>\n</x:xmpmeta>'
            ]
        }),
        'mime_type': 'audio/aiff; codecs="NONE"',
        'is_lossless': True,
        'channels': 2,
        'duration': 0.2999546485260771,
        'filesize': 9612,
        'artist': 'Serhiy Storchaka',
        'title': 'Pluck',
        'bitrate': 176.4,
        'samplerate': 11025,
        'bitdepth': 8,
        'comment': 'Audacity Pluck + Wahwah',
    }),
    ('no_audio.aiff', {
        'other': OtherFields(),
        'mime_type': 'audio/aiff; codecs="NONE"',
        'is_lossless': True,
        'channels': 2,
        'duration': 0.0,
        'filesize': 54,
        'samplerate': 8000,
        'bitdepth': 16,
        'bitrate': 256.0,
    }),
    ('empty_file.aiff', {
        'other': OtherFields(),
        'filesize': 0,
    }),
    ('zero_value_properties.aiff', {
        'other': OtherFields(),
        'mime_type': 'audio/aiff; codecs="NONE"',
        'is_lossless': True,
        'filesize': 4096,
    }),
    ('magic_bytes_only_id3.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 3,
    }),
    ('detect_mp3_id3v2.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.47020408163265304,
        'album': 'I Can Walk On Water I Can Fly',
        'year': '2007',
        'title': 'I Can Walk On Water I Can Fly',
        'artist': 'Basshunter',
        'track': 1,
        'filesize': 8186,
        'bitrate': 127.99548611111112,
        'genre': 'Dance',
        'comment': 'Ripped by THSLIVE',
    }),
    ('detect_mp3_id3v1.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'genre': 'Darkwave',
        'duration': 3.7355102040816326,
        'album': 'Quod Libet Test Data',
        'year': '2004',
        'title': 'Silence',
        'artist': 'piman',
        'track': 2,
        'filesize': 15070,
        'bitrate': 32.0,
    }),
    ('detect_mp3_mpeg1.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 3.7355102040816326,
        'filesize': 14942,
        'bitrate': 32.0,
    }),
    ('detect_mp3_mpeg2.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 16000,
        'duration': 0.18,
        'filesize': 468,
        'bitrate': 8.0,
    }),
    ('detect_mp3_mpeg25.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 8000,
        'duration': 0.288,
        'filesize': 576,
        'bitrate': 8.000000000000002,
    }),
    ('detect_mp2_mpeg1.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.10448979591836735,
        'filesize': 5015,
        'bitrate': 384.0,
    }),
    ('detect_mp2_mpeg2.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 16000,
        'duration': 0.144,
        'filesize': 2880,
        'bitrate': 160.0,
    }),
    ('detect_mp1_mpeg1.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'channels': 2,
        'samplerate': 32000,
        'duration': 0.096,
        'filesize': 2688,
        'bitrate': 224.0,
    }),
    ('magic_bytes_only_mp3.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 2,
    }),
    ('detect_ogg.x', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'filesize': 4480,
        'album': 'An Album',
        'artist': 'An Artist',
        'composer': 'some composer',
        'bitrate': 112.0,
        'duration': 3.684716553287982,
        'channels': 2,
        'genre': 'Some Genre',
        'samplerate': 44100,
        'title': 'A Title',
        'track': 2,
        'year': '2007',
        'comment': 'A Comment',
    }),
    ('magic_bytes_only_ogg.x', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg',
        'filesize': 5,
    }),
    ('detect_wav.x', {
        'other': OtherFields({
            'isft': ['Lavf58.20.10'],
        }),
        'mime_type': 'audio/wav; codecs="1"',
        'is_lossless': True,
        'channels': 1,
        'duration': 0.0,
        'filesize': 120,
        'bitrate': 352.8,
        'samplerate': 22050,
        'bitdepth': 16,
        'artist': 'Purpley',
        'title': 'Test000',
        'album': 'prototypes',
    }),
    ('magic_bytes_only_wav.x', {
        'other': OtherFields(),
        'mime_type': 'audio/wav',
        'filesize': 12,
    }),
    ('detect_flac.x', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'is_lossless': True,
        'channels': 2,
        'duration': 3.684716553287982,
        'filesize': 120,
        'bitrate': 0.2605356439543127,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('magic_bytes_only_flac.x', {
        'other': OtherFields(),
        'mime_type': 'audio/flac',
        'filesize': 4,
    }),
    ('detect_asf.x', {
        'other': OtherFields(),
        'mime_type': 'application/vnd.ms-asf',
        'filesize': 120,
        'artist': 'Foo Fighters',
        'title': 'Doll',
    }),
    ('magic_bytes_only_asf.x', {
        'other': OtherFields(),
        'mime_type': 'application/vnd.ms-asf',
        'filesize': 30,
    }),
    ('detect_mp4_m4a.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4',
        'filesize': 120,
        'duration': 167.78739229024944,
    }),
    ('magic_bytes_only_mp4.x', {
        'other': OtherFields(),
        'mime_type': 'audio/mp4',
        'filesize': 8,
    }),
    ('detect_aiff.x', {
        'other': OtherFields({
            'copyright': ['℗ 1992 Ace Records']
        }),
        'mime_type': 'audio/aiff; codecs="NONE"',
        'is_lossless': True,
        'channels': 2,
        'duration': 0.0,
        'filesize': 164,
        'samplerate': 44100,
        'bitdepth': 16,
        'bitrate': 1411.2,
        'title': 'Go Out and Get Some',
        'comment': 'Millie Jackson - Get It Out \'cha System - 1978',
    }),
    ('magic_bytes_only_aiff.x', {
        'other': OtherFields(),
        'mime_type': 'audio/aiff',
        'filesize': 12,
    }),
    ('chapters_id3v24.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 8743,
        'duration': 4.176,
        'channels': 1,
        'bitrate': 16.0,
        'samplerate': 8000,
        'artist': 'Test Author',
        'title': 'Test Episode',
    }),
    ('chapters_id3v23.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 8547,
        'duration': 4.176,
        'channels': 1,
        'bitrate': 16.0,
        'samplerate': 8000,
        'title': 'Legacy Episode',
    }),
    ('chapters_id3_no_ctoc.mp3', {
        'other': OtherFields(),
        'mime_type': 'audio/mpeg',
        'is_lossless': False,
        'filesize': 8478,
        'duration': 4.176,
        'channels': 1,
        'bitrate': 16.0,
        'samplerate': 8000,
        'title': 'Linear Episode',
    }),
    ('chapters_vorbis.ogg', {
        'other': OtherFields(),
        'mime_type': 'audio/ogg; codecs="vorbis"',
        'is_lossless': False,
        'filesize': 5447,
        'duration': 4.0,
        'channels': 1,
        'bitrate': 22.4,
        'samplerate': 8000,
        'artist': 'Test Author',
        'title': 'Test Episode',
    }),
    ('chapters_mp4.m4a', {
        'other': OtherFields({
            'encoded_by': ['Lavf62.3.100'],
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'filesize': 10006,
        'duration': 4.0,
        'channels': 1,
        'bitrate': 16.25,
        'samplerate': 8000,
    }),
    ('chapters_mp4_track.m4a', {
        'other': OtherFields({
            'encoded_by': ['Lavf62.3.100'],
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'filesize': 9943,
        'duration': 4.0,
        'channels': 1,
        'bitrate': 16.25,
        'samplerate': 8000,
    }),
    ('chapters_mp4_chpl_only.m4a', {
        'other': OtherFields({
            'encoded_by': ['Lavf62.3.100'],
        }),
        'mime_type': 'audio/mp4; codecs="mp4a.40.2"',
        'is_lossless': False,
        'filesize': 9467,
        'duration': 4.0,
        'channels': 1,
        'bitrate': 16.25,
        'samplerate': 8000,
    }),
])

IMAGE_TEST_FILES: dict[str, ExpectedImages] = dict([
    ('image-text-encoding.mp3', {
        'other': OtherImages(),
        'front_cover': Image(
            name='front_cover',
            mime_type='image/jpeg',
            description='cover',
            size=5708,
            data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x02\x00\x00d\x00d'
        ),
    }),
    ('id3v22_with_image.mp3', {
        'other': OtherImages(),
        'front_cover': Image(
            name='front_cover',
            mime_type='image/jpeg',
            description='some image ë',
            size=1220,
            data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H'
        ),
    }),
    ('id3v22_with_image_stray_null.mp3', {
        'other': OtherImages(),
        'front_cover': Image(
            name='front_cover',
            mime_type='image/jpeg',
            description='some image ë',
            size=1220,
            data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H'
        ),
    }),
    ('multiple_images.mp3', {
        'other': OtherImages({
            'front_cover': [
                Image(
                    name='front_cover',
                    mime_type='image/png',
                    description='second image',
                    size=1552,
                    data=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\xf4'
                ),
                Image(
                    name='front_cover',
                    mime_type='image/png',
                    description='third image',
                    size=1552,
                    data=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\xf4'
                )
            ],
            'artist': [
                Image(
                    name='artist',
                    mime_type='image/jpeg',
                    description='first artist image',
                    size=1220,
                    data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H'
                ),
                Image(
                    name='artist',
                    mime_type='image/jpeg',
                    description='second artist image',
                    size=1220,
                    data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H'
                ),
                Image(
                    name='artist',
                    mime_type='image/png',
                    description='third artist image',
                    size=1552,
                    data=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\xf4'
                )
            ],
            'conductor': [
                Image(
                    name='conductor',
                    description='empty image',
                    size=0,
                    data=b''
                )
            ]
        }),
        'front_cover': Image(
            name='front_cover',
            mime_type='image/jpeg',
            description='first image',
            size=1220,
            data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H'
        ),
    }),
    ('ogg_with_image.ogg', {
        'other': OtherImages({
            'bright_colored_fish': [
                Image(
                    name='bright_colored_fish',
                    mime_type='image/jpeg',
                    description='some image ë',
                    size=1220,
                    data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H'
                )
            ],
        }),
    }),
    ('wav_with_image.wav', {
        'other': OtherImages(),
        'front_cover': Image(
            name='front_cover',
            mime_type='image/jpeg',
            description='some image ë',
            size=4627,
            data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01'
        ),
    }),
    ('multiple_values_images.flac', {
        'other': OtherImages({
            'bright_colored_fish': [
                Image(
                    name='bright_colored_fish',
                    mime_type='image/jpeg',
                    description='some image ë',
                    size=1220,
                    data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H'
                )
            ],
            'front_cover': [
                Image(
                    name='front_cover',
                    mime_type='image/png',
                    description='another image',
                    size=1552,
                    data=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\xf4'
                ),
                Image(
                    name='front_cover',
                    mime_type='image/gif',
                    description='yet another image',
                    size=61,
                    data=b'GIF87a\x1e\x00\x1e\x00\x80\x01\x00\x00\x00\x00\xff'
                )
            ],
        }),
        'front_cover': Image(
            name='front_cover',
            mime_type='image/jpeg',
            description='some image ë',
            size=1220,
            data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H'
        ),
    }),
    ('invalid_block_sizes.flac', {
        'other': OtherImages(),
        'front_cover': Image(
            name='front_cover',
            mime_type='image/gif',
            size=61,
            data=b'GIF87a\x1e\x00\x1e\x00\x80\x01\x00\x00\x00\x00\xff\xff'
        ),
    }),
    ('mpeg4_with_image.m4a', {
        'other': OtherImages({
            'front_cover': [
                Image(
                    name='front_cover',
                    mime_type='image/bmp',
                    size=1870,
                    data=b'BMN\x07\x00\x00\x00\x00\x00\x00F\x00\x00\x008\x00'
                ),
                Image(
                    name='front_cover',
                    mime_type='image/gif',
                    size=61,
                    data=b'GIF87a\x1e\x00\x1e\x00\x80\x01\x00\x00\x00\x00\xff'
                )
            ],
        }),
        'front_cover': Image(
            name='front_cover',
            mime_type='image/jpeg',
            size=1220,
            data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H'
        ),
    }),
    ('aiff_with_image.aiff', {
        'other': OtherImages({
            'generic': [
                Image(
                    name='generic',
                    mime_type='image/jpeg',
                    description='some image ë',
                    size=1220,
                    data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H'
                )
            ],
            'composer': [
                Image(
                    name='composer',
                    mime_type='image/jpeg',
                    description='some image ë',
                    size=1220,
                    data=b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H'
                )
            ],
        }),
    }),
])

SAMPLE_FOLDER = os.path.join(os.path.dirname(__file__), 'samples')


class TestAll(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # Use utf-8 encoding for debug print()
        if isinstance(stdout, TextIOWrapper):
            stdout.reconfigure(encoding='utf-8')
        # Show full assertion error diff
        cls.maxDiff = None

    def compare_tag(self,
                    results: ExpectedTag,
                    expected: ExpectedTag) -> None:
        self.assertEqual(set(results), set(expected))

        for path, result_val in results.items():
            expected_val = expected[path]
            if isinstance(expected_val, OtherFields):
                assert isinstance(result_val, OtherFields)
                self.assertEqual(set(result_val), set(expected_val))

                for other_key, other_result_val in result_val.items():
                    other_expected_val = expected_val[other_key]
                    if other_key in {'lyrics', 'xmp'}:
                        # Only check start of value
                        self.assertEqual(
                            len(other_result_val), len(other_expected_val)
                        )
                        for index, val in enumerate(other_expected_val):
                            self.assertEqual(
                                other_result_val[index][:len(val)],
                                val
                            )
                    else:
                        self.assertEqual(other_result_val, other_expected_val)
                continue
            if isinstance(expected_val, float):
                assert isinstance(result_val, float)
                self.assertAlmostEqual(result_val, expected_val)
                continue
            self.assertEqual(result_val, expected_val)

    def compare_images(self,
                       results: ExpectedImages,
                       expected: ExpectedImages) -> None:
        def assert_images_match(result_val: Image,
                                expected_val: Image) -> None:
            self.assertEqual(result_val.name, expected_val.name)
            self.assertEqual(result_val.size, expected_val.size)
            self.assertEqual(result_val.mime_type, expected_val.mime_type)
            self.assertEqual(result_val.description, expected_val.description)
            self.assertEqual(
                result_val.data[:len(expected_val.data)],
                expected_val.data
            )

        self.assertEqual(results.keys(), expected.keys())

        for path, result_val in results.items():
            expected_val = expected[path]
            if isinstance(expected_val, OtherImages):
                assert isinstance(result_val, OtherImages)
                self.assertEqual(set(result_val), set(expected_val))

                for other_key, other_result_val in result_val.items():
                    for index, image in enumerate(other_result_val):
                        assert_images_match(
                            image, expected_val[other_key][index]
                        )
                continue
            assert isinstance(result_val, Image)
            assert_images_match(result_val, expected_val)

    def test_file_reading_all(self) -> None:
        for testfile, expected in TEST_FILES.items():
            with self.subTest(testfile=testfile, expected=expected):
                filename = os.path.join(SAMPLE_FOLDER, testfile)
                tag = TinyTag.get(
                    filename, tags=True, duration=True, image=True)
                results = {
                    key: val for key, val in tag.__dict__.items()
                    if not key.startswith('_') and key != 'filename'
                    and val is not None and not isinstance(val, Images)
                }
                self.compare_tag(results, expected)

    def test_file_reading_tags(self) -> None:
        for testfile, expected in TEST_FILES.items():
            with self.subTest(testfile=testfile, expected=expected):
                filename = os.path.join(SAMPLE_FOLDER, testfile)
                excluded_attrs = {
                    'bitdepth', 'bitrate', 'channels', 'duration',
                    'is_lossless', 'samplerate'
                }
                tag = TinyTag.get(filename, tags=True, duration=False)
                results = {
                    key: val for key, val in tag.__dict__.items()
                    if not key.startswith('_') and key != 'filename'
                    and val is not None and not isinstance(val, Images)
                }
                filtered_expected = {
                    key: val for key, val in expected.items()
                    if key not in excluded_attrs
                }
                if 'mime_type' in filtered_expected:
                    filtered_expected['mime_type'] = (
                        str(filtered_expected['mime_type'])
                        .split(';', maxsplit=1)[0]
                    )
                self.compare_tag(results, filtered_expected)
                assert tag.images.any is None

    def test_file_reading_duration(self) -> None:
        for testfile, expected in TEST_FILES.items():
            with self.subTest(testfile=testfile, expected=expected):
                filename = os.path.join(SAMPLE_FOLDER, testfile)
                allowed_attrs = {
                    'bitdepth', 'bitrate', 'channels', 'duration', 'filesize',
                    'is_lossless', 'mime_type', 'samplerate'
                }
                tag = TinyTag.get(filename, tags=False, duration=True)
                results = {
                    key: val for key, val in tag.__dict__.items()
                    if not key.startswith('_') and key != 'filename'
                    and val is not None and not isinstance(val, Images)
                    and not isinstance(val, OtherFields)
                }
                filtered_expected = {
                    key: val for key, val in expected.items()
                    if key in allowed_attrs
                }
                self.compare_tag(results, filtered_expected)
                assert tag.images.any is None

    def test_file_reading_images(self) -> None:
        for testfile, expected in IMAGE_TEST_FILES.items():
            with self.subTest(testfile=testfile, expected=expected):
                filename = os.path.join(SAMPLE_FOLDER, testfile)
                tag = TinyTag.get(filename, image=True)
                results = {
                    key: val
                    for key, val in tag.images.__dict__.items()
                    if val is not None
                }
                self.compare_images(results, expected)

    def test_pathlib_compatibility(self) -> None:
        testfile = next(iter(TEST_FILES.keys()))
        filename = Path(SAMPLE_FOLDER) / testfile
        TinyTag.get(filename)
        self.assertTrue(TinyTag.is_supported(filename))

    def test_file_obj_compatibility(self) -> None:
        testfile = next(iter(TEST_FILES.keys()))
        filename = os.path.join(SAMPLE_FOLDER, testfile)
        with open(filename, 'rb') as file_handle:
            tag = TinyTag.get(file_obj=file_handle)
            file_handle.seek(0)
            tag_bytesio = TinyTag.get(file_obj=BytesIO(file_handle.read()))
            self.assertEqual(tag.filesize, tag_bytesio.filesize)

    @skipIf(
        system() == 'Windows' and python_implementation() == 'PyPy',
        reason='PyPy on Windows not supported'
    )
    def test_binary_path_compatibility(self) -> None:
        binary_file_path = os.path.join(
            SAMPLE_FOLDER, 'non_ascii_filename_äää.mp3').encode('utf-8')
        tag = TinyTag.get(binary_file_path)
        self.assertEqual(tag.samplerate, 44100)
        self.assertEqual(tag.other['encoder_settings'], ['Lavf58.20.100'])

    def test_unsupported_extension(self) -> None:
        bogus_file = os.path.join(SAMPLE_FOLDER, 'there_is_no_such_ext.bogus')
        with self.assertRaises(UnsupportedFormatError) as context:
            TinyTag.get(bogus_file)
        self.assertIsInstance(context.exception, TinyTagException)

    def test_unsupported_magic_bytes(self) -> None:
        bogus_file = os.path.join(SAMPLE_FOLDER, 'detect_none.x')
        with self.assertRaises(UnsupportedFormatError) as context:
            TinyTag.get(bogus_file)
        self.assertIsInstance(context.exception, TinyTagException)

    def test_override_encoding(self) -> None:
        chinese_id3 = os.path.join(SAMPLE_FOLDER, 'chinese_id3.mp3')
        tag = TinyTag.get(chinese_id3, encoding='gbk')
        self.assertEqual(tag.artist, '苏云')
        self.assertEqual(tag.album, '角落之歌')

    def test_invalid_file(self) -> None:
        for path, cls in (
            ('invalid_file.m4a', _MP4),
            ('invalid_file.flac', _Flac),
            ('invalid_file.ogg', _Ogg),
            ('invalid_file.wav', _Wave),
            ('invalid_file.asf', _ASF),
            ('invalid_file.aiff', _Aiff),
        ):
            with self.subTest(path=path, cls=cls):
                with self.assertRaises(ParseError) as context:
                    cls.get(os.path.join(SAMPLE_FOLDER, path))
                self.assertIsInstance(context.exception, TinyTagException)

    def test_image_construction(self) -> None:
        name = 'front_cover'
        mime_type = 'image/jpeg'
        description = 'cover'
        size = 5708
        data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x02\x00\x00d\x00d'
        image = Image(
            name=name, mime_type=mime_type, description=description, size=size,
            data=data
        )
        self.assertEqual(image.name, name)
        self.assertEqual(image.mime_type, mime_type)
        self.assertEqual(image.description, description)
        self.assertEqual(image.size, size)
        self.assertEqual(image.data, data)

    def test_images_any(self) -> None:
        tag = TinyTag.get(
            os.path.join(SAMPLE_FOLDER, 'multiple_values_images.flac'),
            image=True
        )
        image = tag.images.any
        manual_image = tag.images.front_cover
        assert image is not None
        assert manual_image is not None
        assert image.data is not None
        self.assertEqual(image.name, 'front_cover')
        self.assertEqual(image.size, 1220)
        self.assertEqual(image.data, manual_image.data)
        self.assertTrue(tag.images.other)
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(image.data, tag.get_image())

    def test_images_any_other(self) -> None:
        tag = TinyTag.get(
            os.path.join(SAMPLE_FOLDER, 'ogg_with_image.ogg'), image=True)
        image = tag.images.any
        manual_image = tag.images.other['bright_colored_fish'][0]
        assert image is not None
        assert manual_image is not None
        assert image.data is not None
        self.assertEqual(image.name, 'bright_colored_fish')
        self.assertEqual(image.size, 1220)
        self.assertEqual(image.data, manual_image.data)
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(image.data, tag.get_image())

    def test_detect_magic_bytes(self) -> None:
        for testfile, expected in (
            ('detect_mp3_id3v2.x', _ID3),
            ('detect_mp3_id3v1.x', _ID3),
            ('detect_mp3_mpeg1.x', _MPEG),
            ('detect_mp3_mpeg2.x', _MPEG),
            ('detect_mp3_mpeg25.x', _MPEG),
            ('detect_mp2_mpeg1.x', _MPEG),
            ('detect_mp2_mpeg2.x', _MPEG),
            ('detect_mp1_mpeg1.x', _MPEG),
            ('detect_ogg.x', _Ogg),
            ('detect_wav.x', _Wave),
            ('detect_flac.x', _Flac),
            ('detect_asf.x', _ASF),
            ('detect_mp4_m4a.x', _MP4),
            ('detect_aiff.x', _Aiff),
        ):
            with self.subTest(testfile=testfile, expected=expected):
                filename = os.path.join(SAMPLE_FOLDER, testfile)
                tag = TinyTag.get(filename)
                self.assertIsInstance(tag, expected)

            with self.subTest(testfile=testfile, expected=expected):
                filename = os.path.join(SAMPLE_FOLDER, testfile)
                with self.assertRaises(UnsupportedFormatError) as context:
                    TinyTag.get(filename, check_magic_bytes=False)
                self.assertIsInstance(context.exception, TinyTagException)

    def test_show_hint_for_wrong_usage(self) -> None:
        with self.assertRaises(ValueError) as context:
            TinyTag.get()
        self.assertIsInstance(context.exception, ValueError)
        self.assertEqual(
            str(context.exception),
            'Either filename or file_obj argument is required'
        )

    def test_unimplemented_load(self) -> None:
        class IncompleteTag(TinyTag):  # pylint: disable=abstract-method
            def load(self,
                     file_handle: BinaryIO | None,
                     tags: bool,
                     duration: bool) -> None:
                self.filesize = 1
                self._filehandler = file_handle
                self._load(tags=tags, duration=duration)
        tag = IncompleteTag()
        with self.assertRaises(ValueError):
            tag.load(file_handle=None, tags=True, duration=True)
        with self.assertRaises(NotImplementedError):
            tag.load(file_handle=BytesIO(), tags=True, duration=False)
        with self.assertRaises(NotImplementedError):
            tag.load(file_handle=BytesIO(), tags=False, duration=True)

    def test_deprecations(self) -> None:
        file_path = os.path.join(SAMPLE_FOLDER, 'multiple_values_images.flac')
        with self.assertWarns(DeprecationWarning):
            TinyTag.get(filename=file_path, image=True, ignore_errors=True)
        with self.assertWarns(DeprecationWarning):
            tag = TinyTag.get(
                filename=file_path, image=True, ignore_errors=False)
        with self.assertWarns(DeprecationWarning):
            assert tag.audio_offset is None
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(str(tag.extra), "{}")
        with self.assertWarns(DeprecationWarning):
            assert tag.images.any is not None
            self.assertEqual(tag.get_image(), tag.images.any.data)

    def test_str_vars(self) -> None:
        tag = TinyTag.get(
            os.path.join(SAMPLE_FOLDER, 'multiple_values_images.flac'),
            image=True
        )
        vars_str = str(vars(tag))
        self.assertIn(
            "multiple_values_images.flac', 'filesize': 4749, "
            "'mime_type': 'audio/flac', 'is_lossless': True, 'duration': 0.1, "
            "'channels': 1, 'bitrate': 1.92, 'bitdepth': 16, "
            "'samplerate': 44100, 'artist': 'artist 1', "
            "'albumartist': None, 'composer': None, 'album': 'album 1', "
            "'disc': 1, 'disc_total': 1, 'title': None, 'track': 1, "
            "'track_total': 1, 'genre': 'genre 1', 'year': None, "
            "'comment': None, 'images': <tinytag.tinytag.Images "
            "object at ",
            vars_str
        )
        self.assertIn(
            "'other': {'artist': ['artist 2', 'artist 3'], "
            "'album': ['album 2'], 'genre': ['genre 2'], "
            "'url': ['https://example.com'], 'track': ['2', '3'], "
            "'disc_total': ['2', '3'], 'disc': ['2', '3'], "
            "'track_total': ['2', '3']}",
            vars_str
        )
        self.assertEqual(
            str(vars(tag.images)),
            "{'front_cover': Image(name='front_cover', size=1220, data="
            "b'\\xff\\xd8\\xff\\xe0\\x00\\x10JFIF\\x00\\x01\\x01\\x01\\x00H"
            "\\x00H\\x00\\x00\\xff\\xe2\\x02\\xb0ICC_PROFILE\\x00\\x01\\x01"
            "\\x00\\x00\\x02\\xa0lcm..', mime_type='image/jpeg', description="
            "'some image ë'), 'back_cover': None, 'media': None, 'other': "
            "{'bright_colored_fish': [Image(name='bright_colored_fish', "
            "size=1220, data=b'\\xff\\xd8\\xff\\xe0\\x00\\x10JFIF\\x00\\x01"
            "\\x01\\x01\\x00H\\x00H\\x00\\x00\\xff\\xe2\\x02\\xb0ICC_PROFILE"
            "\\x00\\x01\\x01\\x00\\x00\\x02\\xa0lcm..', mime_type="
            "'image/jpeg', description='some image ë')], 'front_cover': "
            "[Image(name='front_cover', size=1552, data=b'\\x89PNG\\r\\n\\x1a"
            "\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x01\\xf4\\x00\\x00\\x01"
            "\\xf4\\x08\\x02\\x00\\x00\\x00D\\xb4H\\xdd\\x00\\x00\\x00\\x01"
            "sRGB\\x01\\xd9\\xc9,..', mime_type='image/png', description="
            "'another image'), Image(name='front_cover', size=61, data="
            "b'GIF87a\\x1e\\x00\\x1e\\x00\\x80\\x01\\x00\\x00\\x00\\x00\\xff"
            "\\xff\\xff,\\x00\\x00\\x00\\x00\\x1e\\x00\\x1e\\x00\\x00\\x02"
            "\\x1c\\x84\\x8f\\xa9\\xcb\\xed\\x0f\\xa3\\x9c\\xb4\\xda\\x8b"
            "\\xb3\\xde\\xbc..', mime_type='image/gif', description="
            "'yet another image')]}}"
        )

    def test_str_flat_dict(self) -> None:
        tag = TinyTag.get(
            os.path.join(SAMPLE_FOLDER, 'multiple_values_images.flac'),
            image=True
        )
        self.assertIn(
            "multiple_values_images.flac', 'filesize': 4749, "
            "'mime_type': 'audio/flac', 'is_lossless': True, 'duration': 0.1, "
            "'channels': 1, 'bitrate': 1.92, 'bitdepth': 16, "
            "'samplerate': 44100, 'artist': ['artist 1', "
            "'artist 2', 'artist 3'], 'album': ['album 1', 'album 2'], "
            "'disc': ['1', '2', '3'], 'disc_total': ['1', '2', '3'], "
            "'track': ['1', '2', '3'], 'track_total': ['1', '2', '3'], "
            "'genre': ['genre 1', 'genre 2'], 'url': ['https://example.com']}",
            str(tag.as_dict())
        )
        self.assertEqual(
            str(tag.images.as_dict()),
            "{'front_cover': [Image(name='front_cover', size=1220, data=b'"
            "\\xff\\xd8\\xff\\xe0\\x00\\x10JFIF\\x00\\x01\\x01\\x01\\x00H"
            "\\x00H\\x00\\x00\\xff\\xe2\\x02\\xb0ICC_PROFILE\\x00\\x01\\x01"
            "\\x00\\x00\\x02\\xa0lcm..', mime_type='image/jpeg', description="
            "'some image ë'), Image(name='front_cover', size=1552, data="
            "b'\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x01"
            "\\xf4\\x00\\x00\\x01\\xf4\\x08\\x02\\x00\\x00\\x00D\\xb4H\\xdd"
            "\\x00\\x00\\x00\\x01sRGB\\x01\\xd9\\xc9,..', "
            "mime_type='image/png', description='another image'), "
            "Image(name='front_cover', size=61, data=b'GIF87a\\x1e\\x00\\x1e"
            "\\x00\\x80\\x01\\x00\\x00\\x00\\x00\\xff\\xff\\xff,\\x00\\x00"
            "\\x00\\x00\\x1e\\x00\\x1e\\x00\\x00\\x02\\x1c\\x84\\x8f\\xa9"
            "\\xcb\\xed\\x0f\\xa3\\x9c\\xb4\\xda\\x8b\\xb3\\xde\\xbc..', "
            "mime_type='image/gif', description='yet another image')], "
            "'bright_colored_fish': [Image(name='bright_colored_fish', "
            "size=1220, data=b'\\xff\\xd8\\xff\\xe0\\x00\\x10JFIF\\x00\\x01"
            "\\x01\\x01\\x00H\\x00H\\x00\\x00\\xff\\xe2\\x02\\xb0ICC_PROFILE"
            "\\x00\\x01\\x01\\x00\\x00\\x02\\xa0lcm..', "
            "mime_type='image/jpeg', description='some image ë')]}"
        )


CHAPTER_FILES: dict[str, list[tuple[str | None, float, float]]] = {
    'chapters_id3v24.mp3': [
        ('Chapter One', 0.0, 1.2),
        ('Chapter Two', 1.2, 3.0),
        ('Chapter Three', 3.0, 4.0),
    ],
    'chapters_id3v23.mp3': [
        ('First Part', 0.0, 2.0),
        ('Second Part', 2.0, 4.0),
    ],
    'chapters_id3_no_ctoc.mp3': [
        ('Linear A', 0.5, 1.5),
        (None, 1.5, 3.0),
    ],
    'chapters_vorbis.ogg': [
        ('Opening', 0.0, 1.5),
        ('Middle', 1.5, 3.0),
        ('Closing', 3.0, 4.0),
    ],
    'chapters_mp4.m4a': [
        ('Intro', 0.0, 1.0),
        ('Main Part', 1.0, 2.5),
        ('Outro', 2.5, 4.0),
    ],
    'chapters_mp4_track.m4a': [
        ('Intro', 0.0, 1.0),
        ('Main Part', 1.0, 2.5),
        ('Outro', 2.5, 4.0),
    ],
    'chapters_mp4_chpl_only.m4a': [
        ('Intro', 0.0, 1.0),
        ('Main Part', 1.0, 2.5),
        ('Outro', 2.5, 4.0),
    ],
}


class TestChapters(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        if isinstance(stdout, TextIOWrapper):
            stdout.reconfigure(encoding='utf-8')
        cls.maxDiff = None

    def get_tag(self, filename: str) -> TinyTag:
        return TinyTag.get(os.path.join(SAMPLE_FOLDER, filename))

    def compare_chapters(self,
                         chapters: Chapters,
                         expected: list[tuple[str | None, float, float]],
                         ) -> None:
        self.assertEqual(len(chapters), len(expected))
        for index, (chapter, values) in enumerate(zip(chapters, expected)):
            title, start, end = values
            self.assertIsInstance(chapter, Chapter)
            self.assertEqual(chapter.index, index)
            self.assertEqual(chapter.title, title)
            self.assertAlmostEqual(chapter.start, start)
            assert chapter.end is not None
            self.assertAlmostEqual(chapter.end, end)
            assert chapter.duration is not None
            self.assertAlmostEqual(chapter.duration, end - start)

    def test_chapters_id3v24(self) -> None:
        tag = self.get_tag('chapters_id3v24.mp3')
        self.compare_chapters(
            tag.chapters, CHAPTER_FILES['chapters_id3v24.mp3'])
        self.assertEqual(tag.chapter_warnings, [])
        self.assertIsInstance(tag.chapters, Chapters)
        self.assertEqual(len(tag.chapters.as_list()), 3)
        self.assertEqual(
            tag.chapters.as_list()[0],
            {'title': 'Chapter One', 'start': 0.0, 'end': 1.2, 'index': 0}
        )

    def test_chapters_id3v23(self) -> None:
        tag = self.get_tag('chapters_id3v23.mp3')
        self.compare_chapters(
            tag.chapters, CHAPTER_FILES['chapters_id3v23.mp3'])
        self.assertEqual(tag.chapter_warnings, [])

    def test_chapters_id3_no_ctoc(self) -> None:
        tag = self.get_tag('chapters_id3_no_ctoc.mp3')
        self.compare_chapters(
            tag.chapters, CHAPTER_FILES['chapters_id3_no_ctoc.mp3'])
        self.assertEqual(tag.chapter_warnings, [])

    def test_chapters_vorbis(self) -> None:
        tag = self.get_tag('chapters_vorbis.ogg')
        self.compare_chapters(
            tag.chapters, CHAPTER_FILES['chapters_vorbis.ogg'])
        self.assertEqual(tag.chapter_warnings, [])

    def test_chapters_mp4(self) -> None:
        tag = self.get_tag('chapters_mp4.m4a')
        self.compare_chapters(
            tag.chapters, CHAPTER_FILES['chapters_mp4.m4a'])
        self.assertEqual(tag.chapter_warnings, [])

    def test_chapters_mp4_track(self) -> None:
        tag = self.get_tag('chapters_mp4_track.m4a')
        self.compare_chapters(
            tag.chapters, CHAPTER_FILES['chapters_mp4_track.m4a'])
        self.assertEqual(tag.chapter_warnings, [])

    def test_chapters_mp4_chpl_only(self) -> None:
        tag = self.get_tag('chapters_mp4_chpl_only.m4a')
        self.compare_chapters(
            tag.chapters, CHAPTER_FILES['chapters_mp4_chpl_only.m4a'])
        self.assertEqual(tag.chapter_warnings, [])

    def test_chapters_mp4_truncated(self) -> None:
        tag = self.get_tag('chapters_mp4_truncated.m4a')
        self.assertIsInstance(tag, _MP4)
        # The truncated Nero chapter atom is rejected, and the QuickTime
        # chapter track is used instead.
        self.assertEqual(len(tag.chapters), 3)
        self.assertIn('truncated chpl atom', tag.chapter_warnings)

    def test_chapters_id3_broken(self) -> None:
        tag = self.get_tag('chapters_id3_broken.mp3')
        # Duplicate CHAP IDs and truncated frames do not abort parsing.
        self.assertEqual(len(tag.chapters), 2)
        self.assertIn("duplicate chapter ID 'x'", tag.chapter_warnings)
        self.assertIn("truncated CHAP frame 'z'", tag.chapter_warnings)
        self.assertIn('circular CTOC reference', ' '.join(
            tag.chapter_warnings))
        self.assertIn('ends before it starts', ' '.join(
            tag.chapter_warnings))
        self.assertIn('out of order', ' '.join(tag.chapter_warnings))
        # The inverted end time is ignored; the end falls back to the audio
        # duration since the next chapter starts earlier.
        assert tag.duration is not None
        assert tag.chapters[0].end is not None
        self.assertAlmostEqual(tag.chapters[0].end, tag.duration)

    def test_chapters_vorbis_broken(self) -> None:
        tag = self.get_tag('chapters_vorbis_broken.ogg')
        self.assertEqual(len(tag.chapters), 3)
        self.assertIn('invalid chapter timestamp', ' '.join(
            tag.chapter_warnings))
        self.assertIn('out of order', ' '.join(tag.chapter_warnings))

    def test_no_chapters(self) -> None:
        for filename in ('cbr.mp3', 'test.ogg', 'test.m4a', 'test.wav'):
            with self.subTest(filename=filename):
                tag = self.get_tag(filename)
                self.assertEqual(tag.chapters, [])
                self.assertEqual(tag.chapter_warnings, [])
                self.assertNotIn('chapters', tag.as_dict())

    def test_chapters_without_tags(self) -> None:
        for filename in CHAPTER_FILES:
            with self.subTest(filename=filename):
                tag = TinyTag.get(
                    os.path.join(SAMPLE_FOLDER, filename),
                    tags=False, duration=True)
                self.assertEqual(tag.chapters, [])

    def test_chapters_without_duration(self) -> None:
        for filename, expected in CHAPTER_FILES.items():
            with self.subTest(filename=filename):
                tag = TinyTag.get(
                    os.path.join(SAMPLE_FOLDER, filename),
                    tags=True, duration=False)
                self.assertEqual(len(tag.chapters), len(expected))
                # Without a duration, formats that do not store an explicit
                # chapter end cannot derive one for the last chapter.
                if filename.endswith(('.ogg', '.m4a')):
                    if filename == 'chapters_vorbis.ogg':
                        self.assertIsNone(tag.chapters[-1].end)

    def test_chapter_equality_and_repr(self) -> None:
        chapter = Chapter('Title', 1.0, 2.0, 3)
        self.assertEqual(chapter, Chapter('Title', 1.0, 2.0, 3))
        self.assertNotEqual(chapter, Chapter('Other', 1.0, 2.0, 3))
        self.assertEqual(chapter.duration, 1.0)
        self.assertEqual(hash(chapter), hash(Chapter('Title', 1.0, 2.0, 3)))
        self.assertIn("title='Title'", repr(chapter))
        self.assertEqual(
            chapter.as_dict(),
            {'title': 'Title', 'start': 1.0, 'end': 2.0, 'index': 3}
        )

    def test_chapter_file_object(self) -> None:
        path = os.path.join(SAMPLE_FOLDER, 'chapters_id3v24.mp3')
        with open(path, 'rb') as file_handle:
            tag = TinyTag.get(file_obj=file_handle)
        self.assertEqual(len(tag.chapters), 3)
        self.assertEqual(tag.chapters[0].title, 'Chapter One')

    def test_chapter_parsing_helpers(self) -> None:
        # Chapter subframe helpers are reused by the ID3 parser.
        self.assertEqual(
            _ID3._read_chapter_string(b'abc\x00rest'), ('abc', 4))
        self.assertEqual(
            _ID3._read_chapter_string(b'abc'), (None, 0))
        parser = _ID3()
        # ID3v2.4 text subframes use synchsafe sizes
        subframes = list(parser._parse_subframes(
            b'TIT2\x00\x00\x00\x06\x00\x00\x03Hello', 4))
        self.assertEqual(subframes, [(b'TIT2', b'\x03Hello')])
        self.assertIsNone(parser._decode_text_subframe(b''))
        self.assertIsNone(parser._decode_text_subframe(b'\x09bad'))
        self.assertEqual(
            parser._decode_text_subframe(b'\x03Text'), 'Text')

    def test_chapters_beyond_audio(self) -> None:
        # A chapter starting past the end of the audio is kept, but
        # flagged so callers know the timestamp is inconsistent.
        parser = _ID3()
        parser.duration = 1.0
        parser._chap_frames = [
            _ChapterFrame('a', 0, 500, 'Start'),
            _ChapterFrame('b', 5000, 9000, 'Far away'),
        ]
        parser._resolve_id3_chapters()
        parser._finalize_chapters()
        self.assertEqual(len(parser.chapters), 2)
        self.assertIn('chapter 1 starts beyond the audio',
                      parser.chapter_warnings)
        self.assertIn('chapter 1 ends beyond the audio',
                      parser.chapter_warnings)

    def test_chapters_unknown_end(self) -> None:
        parser = _ID3()
        parser.duration = None
        parser._chap_frames = [
            _ChapterFrame('a', 1000, None, 'No end'),
        ]
        parser._resolve_id3_chapters()
        parser._finalize_chapters()
        self.assertEqual(len(parser.chapters), 1)
        self.assertIsNone(parser.chapters[0].end)
        self.assertIsNone(parser.chapters[0].duration)

    def test_chapter_v21_v22_frames(self) -> None:
        # ID3v2.2 CHAP/CTOC frames are not defined by the spec; tinytag
        # ignores them rather than failing.
        parser = _ID3()
        parser._parse_chapter_frame(
            b'CHAP', b'\x00' * 4, id3version=2)
        self.assertEqual(parser.chapters, [])

    def test_chapter_duplicate_toc(self) -> None:
        parser = _ID3()
        parser.duration = 10.0
        parser._chap_frames = [
            _ChapterFrame('a', 0, 1000, 'A'),
            _ChapterFrame('b', 1000, 2000, 'B'),
        ]
        parser._ctoc_frames = [
            _ChapterTOC('toc', True, ['a', 'b'], 'TOC'),
            _ChapterTOC('toc', False, ['a'], 'Duplicate'),
        ]
        parser._resolve_id3_chapters()
        parser._finalize_chapters()
        self.assertEqual(len(parser.chapters), 2)
        self.assertIn("duplicate CTOC ID 'toc'", parser.chapter_warnings)

    def test_chapter_missing_from_toc(self) -> None:
        parser = _ID3()
        parser.duration = 10.0
        parser._chap_frames = [
            _ChapterFrame('a', 0, 1000, 'A'),
        ]
        parser._ctoc_frames = [
            _ChapterTOC('toc', True, ['missing', 'a'], 'TOC'),
        ]
        parser._resolve_id3_chapters()
        parser._finalize_chapters()
        self.assertEqual(len(parser.chapters), 1)
        self.assertEqual(parser.chapters[0].title, 'A')
        self.assertIn("chapter 'missing' is missing",
                      parser.chapter_warnings)

    def test_chapter_toc_without_top_level(self) -> None:
        parser = _ID3()
        parser.duration = 10.0
        parser._chap_frames = [
            _ChapterFrame('a', 0, 1000, 'A'),
            _ChapterFrame('b', 1000, 2000, 'B'),
        ]
        parser._ctoc_frames = [
            _ChapterTOC('toc', False, ['b', 'a'], 'TOC'),
        ]
        parser._resolve_id3_chapters()
        parser._finalize_chapters()
        self.assertEqual(
            [chapter.title for chapter in parser.chapters], ['B', 'A'])
        self.assertIn('no top-level CTOC frame found',
                      parser.chapter_warnings)

    def test_vorbis_timestamp_parsing(self) -> None:
        self.assertEqual(
            _Ogg._parse_vorbis_timestamp('00:00:01.500'), 1.5)
        self.assertEqual(_Ogg._parse_vorbis_timestamp('01:02:03'), 3723.0)
        self.assertEqual(_Ogg._parse_vorbis_timestamp('1:30'), 90.0)
        self.assertEqual(_Ogg._parse_vorbis_timestamp('2.5'), 2.5)
        self.assertIsNone(_Ogg._parse_vorbis_timestamp(''))
        self.assertIsNone(_Ogg._parse_vorbis_timestamp('abc'))
        self.assertIsNone(_Ogg._parse_vorbis_timestamp('1:2:3:4'))

    def test_vorbis_chapter_without_name(self) -> None:
        chapters, warnings = _Ogg._build_vorbis_chapters(
            {1: '00:00:00.000', 2: '00:00:05.000'},
            {2: 'Second'},
        )
        self.assertEqual(len(chapters), 2)
        self.assertIsNone(chapters[0].title)
        self.assertEqual(chapters[1].title, 'Second')
        self.assertEqual(warnings, [])

    def test_vorbis_name_without_timestamp(self) -> None:
        chapters, warnings = _Ogg._build_vorbis_chapters(
            {1: '00:00:00.000'}, {1: 'First', 2: 'Orphan'})
        self.assertEqual(len(chapters), 1)
        self.assertEqual(
            warnings, ['chapter 2 has a name but no timestamp'])

    def test_chapter_as_dict_excludes_chapters(self) -> None:
        tag = self.get_tag('chapters_mp4.m4a')
        self.assertEqual(tag.chapters.as_list()[0]['title'], 'Intro')
        self.assertNotIn('chapters', tag.as_dict())
        self.assertNotIn('chapter_warnings', tag.as_dict())


class _FailingFile(BytesIO):
    def seek(self, *args: object) -> int:
        raise OSError('seek failed')


class TestChapterParsingHelpers(TestCase):

    def test_index_atoms(self) -> None:
        atom = b'\x00\x00\x00\x0cmoov\x00\x00\x00\x00'
        self.assertEqual(_MP4._index_atoms(atom), {b'moov': b'\x00' * 4})
        # Truncated atom header
        self.assertEqual(_MP4._index_atoms(b'\x00\x00'), {})
        # 64-bit atom size, complete
        extended = (b'\x00\x00\x00\x01moov'
                    + (20).to_bytes(8, 'big') + b'\x00' * 4)
        self.assertEqual(
            _MP4._index_atoms(extended), {b'moov': b'\x00' * 4})
        # 64-bit atom size, truncated header
        self.assertEqual(
            _MP4._index_atoms(b'\x00\x00\x00\x01moov'), {})
        # Size smaller than the header
        self.assertEqual(_MP4._index_atoms(b'\x00\x00\x00\x04moov'), {})
        # Size larger than the data
        self.assertEqual(
            _MP4._index_atoms(b'\x00\x00\x00\x10moov\x00\x00'), {})

    def test_iter_atoms(self) -> None:
        data = (b'\x00\x00\x00\x08free'
                + b'\x00\x00\x00\x0ctrakDATA')
        self.assertEqual(list(_MP4._iter_atoms(data, b'trak')), [b'DATA'])
        self.assertEqual(
            list(_MP4._iter_atoms(b'\x00\x00\x00\x01trak', b'trak')), [])
        self.assertEqual(
            list(_MP4._iter_atoms(b'\x00\x00\x00\x04trak', b'trak')), [])
        extended = b'\x00\x00\x00\x01trak' + b'\x00' * 8
        self.assertEqual(list(_MP4._iter_atoms(extended, b'trak')), [])

    def test_parse_table_helpers(self) -> None:
        self.assertEqual(_MP4._parse_stsc(b''), [])
        self.assertEqual(_MP4._parse_stsc(b'\x00' * 8), [])
        stsc = b'\x00' * 4 + b'\x00\x00\x00\x02'
        stsc += b'\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\x01'
        stsc += b'\x00\x00\x00\x05\x00\x00\x00\x01\x00\x00\x00\x01'
        self.assertEqual(
            _MP4._parse_stsc(stsc), [(1, 3), (5, 1)])
        # Truncated entry stops parsing
        self.assertEqual(
            _MP4._parse_stsc(stsc[:-12]), [(1, 3)])
        self.assertEqual(_MP4._parse_stco(b''), [])
        stco = b'\x00' * 4 + b'\x00\x00\x00\x02'
        stco += b'\x00\x00\x00\x2c\x00\x00\x01\x00'
        self.assertEqual(_MP4._parse_stco(stco), [44, 256])
        self.assertEqual(_MP4._parse_stco(stco[:-4]), [44])
        self.assertEqual(_MP4._parse_stts(b''), [])
        stts = b'\x00' * 4 + b'\x00\x00\x00\x02'
        stts += b'\x00\x00\x00\x01\x00\x00\x03\xe8'
        stts += b'\x00\x00\x00\x02\x00\x00\x01\xf4'
        self.assertEqual(_MP4._parse_stts(stts), [1000, 500, 500])
        self.assertEqual(_MP4._parse_stts(stts[:-4]), [1000])
        self.assertEqual(_MP4._parse_stsz(b''), [])
        uniform = b'\x00' * 4 + b'\x00\x00\x00\x0a' + b'\x00\x00\x00\x03'
        self.assertEqual(_MP4._parse_stsz(uniform), [10, 10, 10])
        sizes = b'\x00' * 4 + b'\x00\x00\x00\x00' + b'\x00\x00\x00\x02'
        sizes += b'\x00\x00\x00\x13\x00\x00\x00\x17'
        self.assertEqual(_MP4._parse_stsz(sizes), [19, 23])
        self.assertEqual(_MP4._parse_stsz(sizes[:-4]), [19])

    def test_parse_mdhd_timescale(self) -> None:
        self.assertEqual(_MP4._parse_mdhd_timescale(b''), 0)
        version0 = b'\x00' * 12 + b'\x00\x00\x03\xe8' + b'\x00' * 4
        self.assertEqual(_MP4._parse_mdhd_timescale(version0), 1000)
        version1 = (b'\x01' + b'\x00' * 19 + b'\x00\x00\x03\xe8'
                    + b'\x00' * 4)
        self.assertEqual(_MP4._parse_mdhd_timescale(version1), 1000)
        self.assertEqual(
            _MP4._parse_mdhd_timescale(b'\x01' + b'\x00' * 19), 0)
        self.assertEqual(
            _MP4._parse_mdhd_timescale(b'\x02' + b'\x00' * 19), 0)

    def test_read_chapter_title(self) -> None:
        fh = BytesIO(b'\x00' * 4 + b'\x00\x03abc\x0cloudy')
        self.assertEqual(_MP4._read_chapter_title(fh, 4, 6), 'abc')
        # Zero-length title
        self.assertEqual(_MP4._read_chapter_title(BytesIO(b'\x00\x00'), 0,
                                                  2), None)
        # Empty sample
        self.assertEqual(_MP4._read_chapter_title(BytesIO(), 0, 0), None)
        # Length exceeds the sample
        self.assertEqual(
            _MP4._read_chapter_title(BytesIO(b'\x00\x05ab'), 0, 4), None)
        # File handle errors are ignored
        self.assertEqual(
            _MP4._read_chapter_title(_FailingFile(b'ab'), 0, 2), None)

    def test_read_moov_errors(self) -> None:
        self.assertIsNone(_MP4._read_moov(_FailingFile()))
        # Missing moov atom
        self.assertIsNone(_MP4._read_moov(BytesIO(
            b'\x00\x00\x00\x08free')))
        # Truncated header
        self.assertIsNone(_MP4._read_moov(BytesIO(b'\x00\x00')))
        # Extended size, truncated
        self.assertIsNone(_MP4._read_moov(BytesIO(b'\x00\x00\x00\x01moov')))
        # Extended size, valid: 8 byte header, 8 byte size, 4 byte payload
        data = (b'\x00\x00\x00\x01moov'
                + (20).to_bytes(8, 'big') + b'\x00' * 4)
        self.assertEqual(_MP4._read_moov(BytesIO(data)), b'\x00' * 4)
        # Extended size pointing past the end of the file
        data = (b'\x00\x00\x00\x01moov'
                + (100).to_bytes(8, 'big') + b'\x00' * 4)
        self.assertIsNone(_MP4._read_moov(BytesIO(data)))
        # Invalid size
        self.assertIsNone(_MP4._read_moov(BytesIO(b'\x00\x00\x00\x04moov')))
        # Sanity limit
        self.assertIsNone(_MP4._read_moov(BytesIO(
            b'\x00\x00\x00\x01moov' + b'\x00' * 7 + b'\x01' + b'\x00')))
        # A trailing atom header too short to contain a full size/type
        self.assertIsNone(_MP4._read_moov(BytesIO(
            b'\x00\x00\x00\x0cfree' + b'\x00' * 4 + b'\x00' * 4)))
        # An atom header shorter than its declared 8 bytes
        self.assertIsNone(_MP4._read_moov(BytesIO(
            b'\x00\x00\x00\x08free' + b'\x00' * 8)))
        # End of file without moov
        self.assertIsNone(_MP4._read_moov(BytesIO(
            b'\x00\x00\x00\x08free')))

    def test_chapters_from_trak_malformed(self) -> None:
        self.assertEqual(_MP4._chapters_from_trak(b''), [])
        # Missing mdia
        self.assertEqual(_MP4._chapters_from_trak(
            b'\x00\x00\x00\x08free'), [])
        # mdia without a text handler
        hdlr = b'\x00' * 8 + b'soun' + b'\x00' * 4
        mdia = (b'\x00\x00\x00\x08hdlr' + b'\x00' * 12)
        trak = b'\x00\x00\x00\x14mdia' + mdia
        self.assertEqual(_MP4._chapters_from_trak(trak), [])
        # A short handler
        trak = (b'\x00\x00\x00\x0chdlr' + b'\x00\x00')
        mdia = b'\x00\x00\x00\x10mdia' + trak
        trak = b'\x00\x00\x00\x18trak' + mdia
        self.assertEqual(_MP4._chapters_from_trak(trak), [])
        self.assertEqual(_MP4._chapters_from_trak(
            b'\x00\x00\x00\x08mdia'), [])

    def test_parse_chpl_malformed(self) -> None:
        def parse(data: bytes) -> list[tuple[str, object]]:
            return list(_MP4._parse_chpl(data))

        def header(count: int, version: int = 1) -> bytes:
            # version/flags (4), reserved (4), chapter count (1)
            return (bytes([version]) + b'\x00' * 7
                    + bytes([count]))

        self.assertEqual(
            parse(b'\x01'), [('chapter_warning', 'truncated chpl atom')])
        self.assertEqual(
            parse(header(0, version=2)),
            [('chapter_warning', 'unknown chpl version 2')])
        # Chapter count says 3, only one entry present
        self.assertIn(
            ('chapter_warning', 'truncated chpl chapter entry'),
            parse(header(3) + b'\x00' * 8 + b'\x01I'))
        # Title length exceeds the data
        self.assertEqual(
            parse(header(1) + b'\x00' * 8 + b'\x09I'),
            [('chapter_warning', 'truncated chpl chapter title')])
        # A zero chapter count produces no chapters
        self.assertEqual(parse(header(0)), [])
        # A valid entry
        self.assertEqual(
            parse(header(1) + b'\x00' * 8 + b'\x03abc'),
            [('chapters', [Chapter('abc', 0.0, None, 0)])])

    def test_parse_chapter_frame_malformed(self) -> None:
        parser = _ID3()
        parser._parse_chapter_frame(b'CHAP', b'no terminator')
        self.assertIn('truncated CHAP frame', parser.chapter_warnings)
        parser = _ID3()
        parser._parse_chapter_frame(b'CTOC', b'id\x00\x03')
        self.assertIn("truncated CTOC frame 'id'", parser.chapter_warnings)
        parser = _ID3()
        parser._parse_chapter_frame(b'CTOC', b'id\x00\x03\x02child')
        self.assertIn("truncated CTOC frame 'id'", parser.chapter_warnings)
        parser = _ID3()
        parser._parse_chapter_frame(
            b'CHAP', b'id\x00' + b'\xff' * 16)
        self.assertIn("CHAP frame 'id' has no start time",
                      parser.chapter_warnings)
        self.assertEqual(parser.chapters, [])

    def test_parse_subframes_v22_and_truncated(self) -> None:
        parser = _ID3()
        v22 = parser._parse_subframes(b'TIT\x00\x00\x03\x03Hi', 2)
        self.assertEqual(list(v22), [(b'TIT', b'\x03Hi')])
        v23 = parser._parse_subframes(b'TIT2\x00\x00\x00\x03\x00\x00Hi!', 4)
        self.assertEqual(list(v23), [(b'TIT2', b'Hi!')])
        # Truncated subframe (size exceeds data)
        self.assertEqual(
            list(parser._parse_subframes(
                b'TIT2\x00\x00\x00\x09\x00\x00Hi', 4)), [])
        # Empty subframe ID terminates parsing
        self.assertEqual(
            list(parser._parse_subframes(b'\x00' * 10, 4)), [])

    def test_update_copies_chapters(self) -> None:
        source = _ID3()
        source._chapters = Chapters([
            Chapter('One', 0.0, 1.0, 0)])
        source._chapter_warnings = ['warning']
        target = _ID3()
        target._update(source)
        self.assertEqual(len(target.chapters), 1)
        self.assertEqual(target.chapter_warnings, ['warning'])

    def test_finalize_negative_duration_and_times(self) -> None:
        parser = _ID3()
        parser.duration = -1.0
        parser._chapters = Chapters([
            Chapter('Negative', -1.0, 1.0, 0),
            Chapter('Overlap', 0.5, 0.9, 1),
        ])
        parser._finalize_chapters()
        self.assertIn('chapter 0 starts before the audio',
                      parser.chapter_warnings)
        self.assertIn('chapter 1 overlaps the previous chapter',
                      parser.chapter_warnings)

    def test_quicktime_chapter_track_edge_cases(self) -> None:
        def atom(atom_type: bytes, payload: bytes) -> bytes:
            return (len(payload) + 8).to_bytes(4, 'big') + atom_type + payload

        def table(count: int, *values: int) -> bytes:
            return (b'\x00' * 4 + count.to_bytes(4, 'big')
                    + b''.join(value.to_bytes(4, 'big')
                               for value in values))

        hdlr = atom(b'hdlr', b'\x00' * 8 + b'text' + b'\x00' * 4)
        mdhd = atom(b'mdhd', b'\x00' * 12 + (1000).to_bytes(4, 'big')
                    + b'\x00' * 4)
        mdhd_zero = atom(b'mdhd', b'\x00' * 20)
        stts = atom(b'stts', table(1, 1, 1000))
        stsz = atom(b'stsz', table(0, 1, 5))
        empty_stsz = atom(b'stsz', table(0, 0, 0))

        def stbl(inner: bytes) -> bytes:
            return atom(b'stbl', inner)

        def minf(inner: bytes) -> bytes:
            return atom(b'minf', inner)

        def chapters(inner: bytes) -> Chapters:
            return _MP4._chapters_from_trak(atom(b'mdia', inner))

        # A track without a minf atom
        self.assertEqual(chapters(hdlr + mdhd), [])
        # A minf atom without stbl
        self.assertEqual(chapters(hdlr + mdhd + minf(b'')), [])
        # Missing mdhd
        self.assertEqual(chapters(hdlr + minf(stbl(b''))), [])
        # Missing time scale
        self.assertEqual(
            chapters(hdlr + mdhd_zero + minf(stbl(stts + stsz))), [])
        # Durations missing
        self.assertEqual(chapters(hdlr + mdhd + minf(stbl(stsz))), [])
        # Empty sample table
        self.assertEqual(
            chapters(hdlr + mdhd + minf(stbl(stts + empty_stsz))), [])
        # Valid track without a file handle: titles are left unset
        result = chapters(hdlr + mdhd + minf(stbl(stts + stsz)))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].start, 0.0)
        self.assertIsNone(result[0].title)
        # Non-text tracks are ignored
        sound_hdlr = atom(b'hdlr', b'\x00' * 8 + b'soun' + b'\x00' * 4)
        self.assertEqual(
            chapters(sound_hdlr + mdhd + minf(stbl(stts + stsz))), [])
        # Empty chunk tables
        fh = BytesIO(b'\x00' * 4)
        self.assertEqual(
            _MP4._read_chapter_titles(fh, b'', b'', [5]), [None])
        self.assertEqual(
            _MP4._read_chapter_titles(fh, table(1, 1, 1), table(0, 0), [5]),
            [None])
        # More samples than chunks: trailing titles stay unset
        titles = _MP4._read_chapter_titles(
            fh, table(1, 1, 1), table(1, 0), [2, 2])
        self.assertEqual(titles, [None, None])
        # More per-chunk samples than expected stops at the sample count
        titles = _MP4._read_chapter_titles(
            fh, table(1, 1, 5), table(1, 0), [2])
        self.assertEqual(titles, [None])
        # Each text sample is a 2 byte length plus the title. The second
        # chunk mapping entry is used for the second chunk.
        data = b'\x00\x02ab\x00\x02cd'
        stsc = table(2, 1, 1, 1, 2, 1, 1)  # (first, per_chunk, desc)
        titles = _MP4._read_chapter_titles(
            BytesIO(data), stsc, table(2, 0, 4), [4, 4])
        self.assertEqual(titles, ['ab', 'cd'])
        # A chunk map that describes more samples than the sample table
        # stops reading, and missing trailing titles are padded with None.
        titles = _MP4._read_chapter_titles(
            fh, table(1, 1, 9, 1), table(1, 0), [4])
        self.assertEqual(titles, [None])
        titles = _MP4._read_chapter_titles(
            fh, table(1, 1, 1, 1), table(1, 0), [4, 4, 4])
        self.assertEqual(titles, [None, None, None])

    def test_parse_chapter_track_no_moov(self) -> None:
        parser = _MP4()
        parser._filehandler = BytesIO(b'\x00\x00\x00\x08free')
        parser._parse_chapter_track(parser._filehandler)
        self.assertEqual(parser.chapters, [])
        parser._filehandler = _FailingFile()
        parser._parse_chapter_track(parser._filehandler)
        self.assertEqual(parser.chapters, [])
        # A moov without any trak atom is ignored
        moov = b'\x00\x00\x00\x08free'
        parser._filehandler = BytesIO(
            (len(moov) + 8).to_bytes(4, 'big') + b'moov' + moov)
        parser._parse_chapter_track(parser._filehandler)
        self.assertEqual(parser.chapters, [])

    def test_toc_duplicate_entry_and_expanded_node(self) -> None:
        parser = _ID3()
        parser.duration = 10.0
        parser._chap_frames = [
            _ChapterFrame('a', 0, 1000, 'A'),
            _ChapterFrame('b', 1000, 2000, 'B'),
        ]
        parser._ctoc_frames = [
            _ChapterTOC('toc', True, ['a', 'a', 'part'], 'TOC'),
            _ChapterTOC('part', False, ['b'], 'Part'),
            _ChapterTOC('other', True, ['part'], 'Other'),
        ]
        parser._resolve_id3_chapters()
        self.assertIn("duplicate CTOC entry 'a'", parser.chapter_warnings)
        # The second root referencing an already expanded TOC is skipped.
        self.assertEqual(len(parser.chapters), 2)

    def test_flac_vorbis_chapters(self) -> None:
        # FLAC stores Vorbis comments the same way as Ogg.
        path = os.path.join(SAMPLE_FOLDER, 'unsynced_lyrics.flac')
        tag = TinyTag.get(path)
        self.assertEqual(tag.chapters, [])
        self.assertEqual(tag.chapter_warnings, [])

    def test_chapter_duration_without_end(self) -> None:
        self.assertIsNone(Chapter('No end', 1.0).duration)
        self.assertNotEqual(Chapter('A', 0.0), object())

    def test_flac_chapter_warnings_and_images(self) -> None:
        import struct as _struct

        def block(block_type: int, payload: bytes) -> bytes:
            return bytes([block_type]) + len(payload).to_bytes(3, 'big') \
                + payload

        # A Vorbis comment block with a bad timestamp and a picture block.
        comments = [b'CHAPTER001=garbage', b'CHAPTER001NAME=Bad']
        vorbis = _struct.pack('<I', 0) + _struct.pack('<I', len(comments))
        for comment in comments:
            vorbis += _struct.pack('<I', len(comment)) + comment
        # FLAC Vorbis comment blocks have no framing bit.
        picture = (_struct.pack('>I', 3)
                   + _struct.pack('>I', 9) + b'image/png'
                   + _struct.pack('>I', 0)
                   + _struct.pack('>IIII', 1, 1, 24, 0)
                   + _struct.pack('>I', 4) + b'PNG!')
        stream = (b'fLaC' + block(0x04, vorbis)
                  + block(0x86, picture) + b'\x00' * 8)
        tag = _Flac.get(file_obj=BytesIO(stream), image=True)
        self.assertEqual(tag.chapters, [])
        self.assertIn("invalid chapter timestamp 'garbage'",
                      tag.chapter_warnings)
        self.assertIsNotNone(tag.images.any)
        # A picture embedded in a Vorbis comment block is exposed too.
        import base64
        encoded = base64.b64encode(picture)
        comments = [b'METADATA_BLOCK_PICTURE=' + encoded]
        vorbis = _struct.pack('<I', 0) + _struct.pack('<I', len(comments))
        for comment in comments:
            vorbis += _struct.pack('<I', len(comment)) + comment
        stream = (b'fLaC' + block(0x84, vorbis) + b'\x00' * 8)
        tag = _Flac.get(file_obj=BytesIO(stream), image=True)
        self.assertEqual(tag.chapters, [])
        self.assertIsNotNone(tag.images.any)

    def test_chapter_values_from_atom_tree(self) -> None:
        class ChapterTreeTag(_MP4):
            @classmethod
            def _build_combined_tree(cls) -> Any:
                return {b'chap': cls._chapter_test_parser}

            @classmethod
            def _chapter_test_parser(cls, data: bytes) -> Any:
                yield 'chapters', Chapters([Chapter('One', 0.0, 1.0, 0)])
                yield 'chapter_warning', 'test warning'

        # A top-level atom is parsed by the callable leaf.
        stream = BytesIO(b'\x00\x00\x00\x08chap')
        tag = ChapterTreeTag.get(file_obj=stream)
        self.assertEqual(len(tag.chapters), 1)
        self.assertEqual(tag.chapters[0].title, 'One')
        self.assertEqual(tag.chapter_warnings, ['test warning'])

    def test_read_moov_defensive_limits(self) -> None:
        class _ShortReadFile(BytesIO):
            def read(self, size: int | None = -1) -> bytes:
                return b'\x00' * 4

            def seek(self, offset: int, whence: int = 0) -> int:
                if whence == 2:
                    return 64
                return super().seek(offset, whence)

        class _HugeFile(BytesIO):
            def __init__(self) -> None:
                # Declared size is just above the 64 MiB sanity limit.
                super().__init__(
                    (9 + (1 << 26)).to_bytes(4, 'big') + b'moov')

            def seek(self, offset: int, whence: int = 0) -> int:
                if whence == 2:
                    return 9 + (1 << 26)
                return super().seek(offset, whence)

        # A file handle that never returns a full atom header.
        self.assertIsNone(_MP4._read_moov(_ShortReadFile()))
        # A moov atom larger than the sanity limit is not read into memory.
        huge = _HugeFile()
        self.assertEqual(huge.seek(0, 2), 9 + (1 << 26))
        self.assertIsNone(_MP4._read_moov(huge))

    def test_flac_with_chapter_comments(self) -> None:
        # FLAC reuses the Vorbis comment parser, including chapters.
        import struct as _struct
        vorbis_block = _struct.pack('<I', 0)  # vendor length
        comments = [b'CHAPTER001=00:00:00.000', b'CHAPTER001NAME=One',
                    b'CHAPTER002=00:00:01.000', b'CHAPTER002NAME=Two']
        vorbis_block += _struct.pack('<I', len(comments))
        for comment in comments:
            vorbis_block += _struct.pack('<I', len(comment)) + comment
        header = b'fLaC'
        header += bytes([0x84]) + (len(vorbis_block)).to_bytes(3, 'big')
        stream = header + vorbis_block + b'\x00' * 64
        tag = TinyTag.get(file_obj=BytesIO(stream))
        self.assertIsInstance(tag, _Flac)
        self.assertEqual(len(tag.chapters), 2)
        self.assertEqual(tag.chapters[0].title, 'One')
        self.assertEqual(tag.chapters[1].start, 1.0)
