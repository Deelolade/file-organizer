"""Generate a simple folder app icon (app.ico) used for the packaged exe."""
from PIL import Image, ImageDraw

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

back = (37, 99, 235, 255)    # blue-600
front = (59, 130, 246, 255)  # blue-500
tab = (96, 165, 250, 255)    # blue-400

# Tab
d.rounded_rectangle([40, 52, 132, 96], radius=10, fill=tab)
# Folder body (back)
d.rounded_rectangle([40, 76, 216, 204], radius=18, fill=back)
# Folder front panel
d.rounded_rectangle([40, 100, 216, 204], radius=16, fill=front)

img.save(
    "app.ico",
    format="ICO",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
print("wrote app.ico")
