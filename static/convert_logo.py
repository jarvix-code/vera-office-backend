from cairosvg import svg2png

svg2png(url="C:/Jarvix/vera-office/static/vera-logo-official.svg",
        write_to="C:/Jarvix/vera-office/static/vera-logo-official-512.png",
        output_width=512, output_height=512)

svg2png(url="C:/Jarvix/vera-office/static/vera-logo-official.svg",
        write_to="C:/Jarvix/vera-office/static/vera-logo-official-256.png",
        output_width=256, output_height=256)

svg2png(url="C:/Jarvix/vera-office/static/vera-logo-official.svg",
        write_to="C:/Jarvix/vera-office/static/vera-logo-official-128.png",
        output_width=128, output_height=128)

print("✅ PNG-Versionen erstellt: 512px, 256px, 128px")
