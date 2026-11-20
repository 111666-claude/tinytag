#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 tinytag Contributors
# SPDX-License-Identifier: MIT

"""Generate small, fixed chapter fixtures for tinytag tests.

The base audio is a 4 second 8 kHz mono sine wave, encoded as MP3,
Vorbis (OGG) and AAC (M4A). Chapter metadata is written by hand so the
expected times are exact and independent of ffmpeg's muxer defaults.
"""
import os
import struct
import subprocess
import sys

OUT = sys.argv[1]


def synchsafe(n):
    return bytes([(n >> 21) & 0x7f, (n >> 14) & 0x7f,
                  (n >> 7) & 0x7f, n & 0x7f])


def id3_frame(frame_id, body, version=4):
    if version == 4:
        size = synchsafe(len(body))
    else:
        size = struct.pack('>I', len(body))
    return frame_id.encode() + size + b'\x00\x00' + body


def id3_text(value, encoding=3):
    if encoding == 0:
        return b'\x00' + value.encode('latin-1')
    if encoding == 1:
        return b'\x01' + value.encode('utf-16')
    return b'\x03' + value.encode('utf-8')


def id3_chap(element_id, start_ms, end_ms, title, version=4,
             encoding=3, offsets=(0xFFFFFFFF, 0xFFFFFFFF)):
    body = element_id.encode() + b'\x00'
    body += struct.pack('>II', start_ms, end_ms)
    body += struct.pack('>II', *offsets)
    if title is not None:
        body += id3_frame('TIT2', id3_text(title, encoding), version)
    return id3_frame('CHAP', body, version)


def id3_ctoc(element_id, children, title, top_level=True, ordered=True,
             version=4):
    flags = (0x02 if top_level else 0) | (0x01 if ordered else 0)
    body = element_id.encode() + b'\x00' + bytes([flags, len(children)])
    for child in children:
        body += child.encode() + b'\x00'
    if title is not None:
        body += id3_frame('TIT2', id3_text(title, 3), version)
    return id3_frame('CTOC', body, version)


def wrap_id3(frames, version=4):
    tag = b''.join(frames) + b'\x00' * 16
    return b'ID3' + bytes([version, 0, 0]) + synchsafe(len(tag)) + tag


def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


def ogg_crc(page):
    crc = 0
    for value in page:
        crc ^= value << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc


def parse_ogg_pages(data):
    pages = []
    offset = 0
    while offset < len(data):
        if data[offset:offset + 4] != b'OggS':
            raise SystemExit('unexpected Ogg layout')
        header = bytearray(data[offset:offset + 27])
        segment_count = header[26]
        segments = bytes(data[offset + 27:offset + 27 + segment_count])
        body_start = offset + 27 + segment_count
        body_size = sum(segments)
        body = bytes(data[body_start:body_start + body_size])
        pages.append((header, segments, body))
        offset = body_start + body_size
    return pages


def render_ogg_page(serial, packet, granule, sequence, header_type):
    segments = []
    remaining = len(packet)
    while remaining >= 255:
        segments.append(255)
        remaining -= 255
    segments.append(remaining)
    page: bytearray = bytearray(27 + len(segments))
    page[0:4] = b'OggS'
    page[4] = 0
    page[5] = header_type
    page[6:14] = struct.pack('<q', granule)
    page[14:18] = serial
    page[18:22] = struct.pack('<I', sequence)
    page[22:26] = b'\x00\x00\x00\x00'
    page[26] = len(segments)
    page[27:27 + len(segments)] = segments
    page.extend(packet)
    page[22:26] = struct.pack('<I', ogg_crc(page))
    return bytes(page)


def rewrite_ogg_serial(data, serial):
    """Rewrite the serial number of every Ogg page, keeping packets."""
    rebuilt = b''
    for page in parse_ogg_pages(data):
        header, segments, body = page
        page_data = bytearray(header) + segments + body
        page_data[14:18] = serial
        page_data[22:26] = b'\x00\x00\x00\x00'
        page_data[22:26] = struct.pack('<I', ogg_crc(page_data))
        rebuilt += bytes(page_data)
    return rebuilt


def write_vorbis_chapters(source, target, metadata):
    """Add chapter comments to an Ogg Vorbis file deterministically.

    Only the Vorbis comment page is replaced; all audio pages and their
    packet boundaries are preserved verbatim.
    """
    with open(source, 'rb') as file_handle:
        pages = parse_ogg_pages(file_handle.read())

    comment = b'\x03vorbis'
    comment += struct.pack('<I', len(b'tinytag test')) + b'tinytag test'
    comment += struct.pack('<I', len(metadata))
    for key, value in metadata:
        entry = f'{key}={value}'.encode('utf-8')
        comment += struct.pack('<I', len(entry)) + entry
    comment += b'\x01'

    output = b''
    replaced = False
    for header, segments, body in pages:
        if not replaced and body.startswith(b'\x03vorbis'):
            # The comment page may also hold the setup packet, so split
            # it into packets and replace only the comment packet.
            packets = []
            pending = b''
            offset = 0
            for segment in segments:
                pending += body[offset:offset + segment]
                offset += segment
                if segment < 255:
                    packets.append(pending)
                    pending = b''
            packets[0] = comment
            combined = b''.join(packets)
            segment_sizes = bytearray()
            for packet in packets:
                remaining = len(packet)
                while remaining >= 255:
                    segment_sizes.append(255)
                    remaining -= 255
                segment_sizes.append(remaining)
            page_data = bytearray(header)
            page_data[26] = len(segment_sizes)
            page_data = page_data + bytes(segment_sizes) + combined
            page_data[22:26] = b'\x00\x00\x00\x00'
            page_data[22:26] = struct.pack('<I', ogg_crc(page_data))
            output += bytes(page_data)
            replaced = True
            continue
        page_data = bytearray(header) + segments + body
        output += bytes(page_data)
    with open(target, 'wb') as file_handle:
        file_handle.write(output)


def main():
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, '_tmp')
    os.makedirs(tmp, exist_ok=True)
    wav = os.path.join(tmp, 'tone.wav')
    # 4 seconds of 440 Hz, 8 kHz mono, 16 bit PCM
    frames = bytearray()
    import math
    for i in range(8000 * 4):
        value = int(12000 * math.sin(2 * math.pi * 440 * i / 8000))
        frames += struct.pack('<h', value)
    with open(wav, 'wb') as file_handle:
        data_size = len(frames)
        file_handle.write(b'RIFF' + struct.pack('<I', 36 + data_size)
                          + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 1, 1,
                                                      8000, 16000, 2, 16)
                          + b'data' + struct.pack('<I', data_size) + frames)

    mp3 = os.path.join(tmp, 'base.mp3')
    ogg = os.path.join(tmp, 'base.ogg')
    m4a = os.path.join(tmp, 'base.m4a')
    run(['ffmpeg', '-y', '-i', wav, '-c:a', 'libmp3lame', '-b:a', '16k',
         '-write_xing', '0', '-id3v2_version', '0', '-map_metadata', '-1',
         mp3])
    run(['ffmpeg', '-y', '-i', wav, '-c:a', 'libvorbis', '-q:a', '-1',
         '-map_metadata', '-1', ogg])
    # ffmpeg picks a random Ogg stream serial. Give the base file a
    # fixed serial so the fixtures are reproducible byte-for-byte.
    with open(ogg, 'rb') as file_handle:
        ogg_data = file_handle.read()
    with open(ogg, 'wb') as file_handle:
        file_handle.write(rewrite_ogg_serial(
            ogg_data, b'\x07\x07\x07\x07'))
    run(['ffmpeg', '-y', '-i', wav, '-c:a', 'aac', '-b:a', '16k',
         '-map_metadata', '-1', '-movflags', '+faststart', m4a])

    with open(mp3, 'rb') as file_handle:
        mp3_audio = file_handle.read()
    with open(ogg, 'rb') as file_handle:
        ogg_audio = file_handle.read()

    # --- ID3v2.4, nested ordered CTOC, CHAP frames stored out of order.
    frames = [
        id3_frame('TIT2', id3_text('Test Episode')),
        id3_frame('TPE1', id3_text('Test Author')),
        id3_ctoc('toc', ['part1', 'part2'], 'Episode'),
        id3_ctoc('part1', ['chapter1', 'chapter2'], 'Part One',
                 top_level=False),
        id3_ctoc('part2', ['chapter3'], 'Part Two', top_level=False),
        id3_chap('chapter3', 3000, 4000, 'Chapter Three'),
        id3_chap('chapter1', 0, 1200, 'Chapter One'),
        id3_chap('chapter2', 1200, 3000, 'Chapter Two'),
    ]
    with open(os.path.join(OUT, 'chapters_id3v24.mp3'), 'wb') as fh:
        fh.write(wrap_id3(frames, 4) + mp3_audio)

    # --- ID3v2.3, linear CTOC, UTF-16 titles.
    frames = [
        id3_frame('TIT2', id3_text('Legacy Episode'), 3),
        id3_ctoc('toc', ['a', 'b'], None, version=3),
        id3_chap('a', 0, 2000, 'First Part', version=3, encoding=1),
        id3_chap('b', 2000, 4000, 'Second Part', version=3, encoding=1),
    ]
    with open(os.path.join(OUT, 'chapters_id3v23.mp3'), 'wb') as fh:
        fh.write(wrap_id3(frames, 3) + mp3_audio)

    # --- No CTOC: non-ordered, CHAPTERxxx style linear fallback.
    frames = [
        id3_frame('TIT2', id3_text('Linear Episode')),
        id3_chap('c', 500, 1500, 'Linear A'),
        id3_chap('d', 1500, 3000, None),
    ]
    with open(os.path.join(OUT, 'chapters_id3_no_ctoc.mp3'), 'wb') as fh:
        fh.write(wrap_id3(frames, 4) + mp3_audio)

    # --- Broken: cyclic CTOC, duplicate CHAP ID, inverted times,
    # truncated CHAP frame, and missing title.
    frames = [
        id3_ctoc('toc', ['x', 'loop'], 'Broken'),
        id3_ctoc('loop', ['toc'], 'Loop', top_level=False),
        id3_chap('x', 3000, 1000, 'Inverted'),
        id3_chap('x', 0, 500, 'Duplicate'),
        id3_chap('y', 500, 1200, None),
    ]
    broken = id3_frame('CHAP', b'z\x00' + struct.pack('>II', 0, 1000))
    broken += b'\x00' * 12
    frames.append(broken)
    with open(os.path.join(OUT, 'chapters_id3_broken.mp3'),
              'wb') as fh:
        fh.write(wrap_id3(frames, 4) + mp3_audio)

    # --- Ogg Vorbis: CHAPTERxxx / CHAPTERxxxNAME pairs
    write_vorbis_chapters(ogg, os.path.join(OUT, 'chapters_vorbis.ogg'), [
        ('TITLE', 'Test Episode'),
        ('ARTIST', 'Test Author'),
        ('CHAPTER001', '00:00:00.000'),
        ('CHAPTER001NAME', 'Opening'),
        ('CHAPTER002', '00:00:01.500'),
        ('CHAPTER002NAME', 'Middle'),
        ('CHAPTER003', '00:00:03.000'),
        ('CHAPTER003NAME', 'Closing'),
    ])

    # --- Ogg Vorbis: broken variants
    write_vorbis_chapters(
        ogg, os.path.join(OUT, 'chapters_vorbis_broken.ogg'), [
            ('CHAPTER001', 'garbage'),
            ('CHAPTER001NAME', 'Bad time'),
            ('CHAPTER002', '00:00:02.000'),
            ('CHAPTER002NAME', 'Second'),
            ('CHAPTER003', '00:00:00.500'),
            ('CHAPTER003NAME', 'Out of order'),
            ('CHAPTER004', '00:00:03.000'),
        ])

    # --- MP4 with Nero chpl atom (and a QuickTime chapter track)
    chapter_files = os.path.join(tmp, 'chapters.txt')
    with open(chapter_files, 'w', encoding='utf-8') as fh:
        fh.write(';FFMETADATA1\n')
        for title, start, end in (('Intro', 0, 1000),
                                  ('Main Part', 1000, 2500),
                                  ('Outro', 2500, 4000)):
            fh.write('[CHAPTER]\nTIMEBASE=1/1000\n'
                     f'START={start}\nEND={end}\ntitle={title}\n')
    mp4 = os.path.join(OUT, 'chapters_mp4.m4a')
    run(['ffmpeg', '-y', '-i', m4a, '-i', chapter_files,
         '-map_metadata', '1', '-map', '0', '-c', 'copy',
         '-movflags', '+faststart', mp4])

    # --- MP4 with only a QuickTime chapter track (no chpl)
    mp4_track = os.path.join(OUT, 'chapters_mp4_track.m4a')
    run(['ffmpeg', '-y', '-i', m4a, '-i', chapter_files,
         '-map_metadata', '1', '-map', '0', '-c', 'copy',
         '-movflags', '+faststart+disable_chpl', mp4_track])

    # --- MP4 with a truncated chpl atom: keep only the header bytes
    with open(mp4, 'rb') as file_handle:
        data = file_handle.read()
    index = data.find(b'chpl')
    start = index - 4
    size = struct.unpack_from('>I', data, start)[0]
    payload = data[start + 8:start + size]
    short_payload = payload[:6]  # version, flags, reserved, count, partial
    new_atom = (struct.pack('>I', 8 + len(short_payload)) + b'chpl'
                + short_payload)
    truncated = data[:start] + new_atom + data[start + size:]
    # Update all enclosing atom sizes from 'moov' to the file root.
    moov_start = truncated.find(b'moov') - 4
    moov_size = struct.unpack_from('>I', truncated, moov_start)[0]
    delta = len(new_atom) - size
    truncated = (truncated[:moov_start]
                 + struct.pack('>I', moov_size + delta)
                 + truncated[moov_start + 4:])
    with open(os.path.join(OUT, 'chapters_mp4_truncated.m4a'),
              'wb') as fh:
        fh.write(truncated)

    # --- MP4 with only the Nero chpl atom, chapter track stripped
    with open(mp4, 'rb') as file_handle:
        data = file_handle.read()
    moov_offset = data.find(b'moov') - 4
    moov_size = struct.unpack_from('>I', data, moov_offset)[0]
    moov_payload = data[moov_offset + 8:moov_offset + moov_size]
    children = []
    position = 0
    while position + 8 <= len(moov_payload):
        child_size = struct.unpack_from('>I', moov_payload, position)[0]
        child_type = moov_payload[position + 4:position + 8]
        children.append((child_type, position, child_size))
        position += child_size
    text_traks = [child for child in children if child[0] == b'trak']
    # The second trak is the QuickTime text chapter track.
    if len(text_traks) > 1:
        _type, trak_offset, trak_size = text_traks[1]
        new_payload = (moov_payload[:trak_offset]
                       + moov_payload[trak_offset + trak_size:])
        chpl_only = (data[:moov_offset]
                     + struct.pack('>I', 8 + len(new_payload)) + b'moov'
                     + new_payload
                     + data[moov_offset + moov_size:])
        with open(os.path.join(OUT, 'chapters_mp4_chpl_only.m4a'),
                  'wb') as fh:
            fh.write(chpl_only)

    for name in os.listdir(OUT):
        if name.startswith('_tmp'):
            continue
        path = os.path.join(OUT, name)
        if os.path.isfile(path):
            print(f'{name}: {os.path.getsize(path)} bytes')


if __name__ == '__main__':
    main()
