from PIL import Image
import sys

# Original Logo-Bild
img = Image.open(r"C:\Users\jarvi\.openclaw\media\inbound\file_76---f50c940c-593d-40a3-9eb3-cafd0e924f85.jpg")

# Logo ist im linken Bereich - crop auf Icon
# Ungefähr Koordinaten (anpassen falls nötig)
logo_crop = img.crop((50, 80, 650, 680))

# Resize auf saubere Größe
logo_crop = logo_crop.resize((512, 512), Image.Resampling.LANCZOS)

# Speichern
logo_crop.save(r"C:\Jarvix\vera-office\static\vera-logo-real.png", "PNG")
print("Logo extrahiert: vera-logo-real.png")
