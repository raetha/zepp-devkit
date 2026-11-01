#!/usr/bin/env python3
"""A QR code PNG for the Zepp app's scanner.

  python3 qr.py <out.png> <url> [colour]
"""
import sys
from pathlib import Path

import qrcode

out, url = Path(sys.argv[1]), sys.argv[2]
colour = sys.argv[3] if len(sys.argv) > 3 else "#14223A"
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=3)
qr.add_data(url)
qr.make(fit=True)
out.parent.mkdir(parents=True, exist_ok=True)
qr.make_image(fill_color=colour, back_color="white").save(out)
