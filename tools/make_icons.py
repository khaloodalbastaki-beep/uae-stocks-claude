"""Generate PWA icons with zero dependencies (stdlib zlib+struct PNG encoder).
A brand gradient square with a subtle 'U' notch — good enough for an MVP home-screen
icon and avoids pulling in Pillow (keeps the toolchain light, Khalid's rule)."""
import struct
import zlib
from pathlib import Path


def _png(width, height, rgba_fn):
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0
        for x in range(width):
            raw.extend(rgba_fn(x, y, width, height))
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")


def pixel(x, y, w, h):
    # diagonal gradient between accent blue (#2f81f7) and teal (#11a37f)
    tx = (x + y) / (w + h)
    r = int(0x2f + (0x11 - 0x2f) * tx)
    g = int(0x81 + (0xa3 - 0x81) * tx)
    b = int(0xf7 + (0x7f - 0xf7) * tx)
    # rounded-corner alpha
    rad = w * 0.16
    a = 255
    for cx, cy in ((rad, rad), (w - rad, rad), (rad, h - rad), (w - rad, h - rad)):
        if (x < rad or x > w - rad) and (y < rad or y > h - rad):
            if ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 > rad:
                a = 0
    # 'U' glyph: two vertical bars + bottom bar, centered
    cx0, cx1 = w * 0.34, w * 0.62
    bw = w * 0.085
    top, bot = h * 0.32, h * 0.66
    in_left = abs(x - cx0) < bw and top < y < bot
    in_right = abs(x - cx1) < bw and top < y < bot
    in_bottom = (bot - bw) < y < (bot + bw) and cx0 - bw < x < cx1 + bw
    if in_left or in_right or in_bottom:
        return bytes((245, 248, 255, a))
    return bytes((r, g, b, a))


def main():
    out = Path(__file__).resolve().parent.parent / "web" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        data = _png(size, size, pixel)
        (out / f"icon-{size}.png").write_bytes(data)
        print(f"wrote icon-{size}.png ({len(data)} bytes)")


if __name__ == "__main__":
    main()
