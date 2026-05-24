from PIL import Image

# Lade Logo-Varianten Bild
img = Image.open(r"C:\Jarvix\vera-office\Vera Logo\VERA-Logo-Varianten-1.jpg")

# Das Hauptlogo ist links oben im Header der App zu sehen
# Crop den Bereich mit dem Icon (geschätzte Koordinaten)
logo_icon = img.crop((60, 140, 280, 360))  # Icon allein
logo_icon.save(r"C:\Jarvix\vera-office\static\vera-logo-icon.png", "PNG")

# Wortbildmarke (Icon + Text) aus Visitenkarte unten links
logo_full = img.crop((50, 850, 350, 1050))  # Icon + "VERA Office" Text
logo_full.save(r"C:\Jarvix\vera-office\static\vera-logo-full.png", "PNG")

print("Logos extrahiert:")
print("- vera-logo-icon.png (nur Icon)")
print("- vera-logo-full.png (Icon + Text)")
