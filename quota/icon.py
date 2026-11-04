"""The Quota app icon, drawn in pure Python (no image library) and returned as PNG bytes."""
import math
import struct
import zlib

_CACHE = {}
PURPLE = (0x62, 0x50, 0xD6)


def _cover(d):
    """Pixel coverage from a signed distance in pixels (negative = inside)."""
    return max(0.0, min(1.0, 0.5 - d))


def png(size):
    """A square RGBA PNG of the logo: a white open ring and dot on a rounded purple tile."""
    if size in _CACHE:
        return _CACHE[size]
    s = size / 32.0  # the logo is drawn on a 32 x 32 grid
    c = 16 * s
    radius, ring_r, half_w, dot_r = 9 * s, 10 * s, 1.6 * s, 2.6 * s
    cap_a, cap_b = (16 * s, 6 * s), (26 * s, 16 * s)  # ends of the ring
    rows = []
    for y in range(size):
        row = bytearray([0])
        py = y + 0.5
        for x in range(size):
            px = x + 0.5
            qx, qy = abs(px - c) - (c - radius), abs(py - c) - (c - radius)  # rounded tile
            d_tile = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - radius
            alpha = _cover(d_tile)
            if alpha <= 0:
                row += b"\x00\x00\x00\x00"
                continue
            dx, dy = px - c, py - c
            r = math.hypot(dx, dy)
            d = min(math.hypot(px - cap_a[0], py - cap_a[1]), math.hypot(px - cap_b[0], py - cap_b[1])) - half_w
            if not (dx > 0 and dy < 0):  # the ring is open in the top-right quarter
                d = min(d, abs(r - ring_r) - half_w)
            white = max(_cover(d), _cover(r - dot_r))
            row += bytes([round(PURPLE[i] + (255 - PURPLE[i]) * white) for i in range(3)] + [round(255 * alpha)])
        rows.append(bytes(row))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    out = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))
    _CACHE[size] = out
    return out
