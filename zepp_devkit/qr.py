"""QR codes for the Zepp app's scanner (`zpkd1://<host>/<path>.zpk` installs, or a preview URL)."""
from pathlib import Path

import qrcode


def make(out, url, colour="#14223A"):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    qr.make_image(fill_color=colour, back_color="white").save(out)
    return out
