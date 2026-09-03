
import urllib.request
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from PIL import Image

url = 'https://raw.githubusercontent.com/jdecked/twemoji/master/assets/svg/1f480.svg'
urllib.request.urlretrieve(url, '1f480.svg')

drawing = svg2rlg('1f480.svg')
# svglib default drawing size is whatever the SVG is (twemoji svgs are usually 36x36)
renderPM.drawToFile(drawing, 'skull_raw.png', fmt='PNG', dpi=72, bg=None)

# Open it and resize it carefully
raw_skull = Image.open('skull_raw.png').convert('RGBA')

# To get a high res, let's scale the drawing object before rendering
drawing.scale(12, 12)
drawing.width *= 12
drawing.height *= 12
renderPM.drawToFile(drawing, 'skull_hires.png', fmt='PNG', dpi=72, bg=None)

skull = Image.open('skull_hires.png').convert('RGBA')
# Twemoji is usually square. Let's make a 512x512 canvas
bg = Image.new('RGBA', (512, 512), (49, 51, 56, 255)) # Discord grey
# Paste centered
x = (512 - skull.width) // 2
y = (512 - skull.height) // 2
bg.paste(skull, (x, y), skull)
bg.save('bot_pfp_twemoji.png')
print('Done!')

