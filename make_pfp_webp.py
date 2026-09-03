
import urllib.request
from PIL import Image

url = 'https://fonts.gstatic.com/s/e/notoemoji/latest/1f480/512.webp'
urllib.request.urlretrieve(url, '1f480.webp')

skull = Image.open('1f480.webp').convert('RGBA')
# Discord soft grey background
bg = Image.new('RGBA', (600, 600), (49, 51, 56, 255))
x = (600 - skull.width) // 2
y = (600 - skull.height) // 2
bg.paste(skull, (x, y), skull)
bg.save('bot_pfp_discord.png')
print('Done!')

