# Copyright (c) 2026 Rickard Längkvist
"""Build-only dependency: qrcode[pil]. No network service or runtime dependency."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from donations import SWISH_PAYLOAD, QR_FILE


def build():
    import qrcode
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=8, border=4)
    qr.add_data(SWISH_PAYLOAD)
    qr.make(fit=True)
    qr.make_image(fill_color='black', back_color='white').save(QR_FILE)


if __name__ == '__main__':
    build()
