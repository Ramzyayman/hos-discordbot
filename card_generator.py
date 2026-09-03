import os
import io
import textwrap
from datetime import datetime
from urllib.request import urlopen, Request
from PIL import Image, ImageDraw, ImageFont, ImageChops
from pilmoji import Pilmoji

# Cyberpunk Neon Mode Color Palette
BG_COLOR = (15, 15, 19, 255)       # #0f0f13
USER_COLOR = (242, 243, 245, 255)  # #F2F3F5
TIME_COLOR = (148, 155, 164, 255)  # #949BA4
TEXT_COLOR = (219, 222, 225, 255)  # #DBDEE1
BORDER_COLOR = (255, 0, 85, 255)   # #ff0055 Neon Pink/Red

def download_fonts():
    """Downloads Roboto fonts for consistent, HD text rendering."""
    fonts = {
        "Roboto-Regular.ttf": "https://cdn.jsdelivr.net/gh/googlefonts/roboto/src/hinted/Roboto-Regular.ttf",
        "Roboto-Medium.ttf": "https://cdn.jsdelivr.net/gh/googlefonts/roboto/src/hinted/Roboto-Medium.ttf",
        "Roboto-Black.ttf": "https://cdn.jsdelivr.net/gh/googlefonts/roboto/src/hinted/Roboto-Black.ttf"
    }
    for name, url in fonts.items():
        if not os.path.exists(name):
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(req, timeout=10) as response:
                    with open(name, 'wb') as f:
                        f.write(response.read())
            except Exception:
                pass

def get_font(size: int, weight: str = "regular"):
    download_fonts()
    font_file = "Roboto-Regular.ttf"
    if weight == "medium":
        font_file = "Roboto-Medium.ttf"
    elif weight == "black":
        font_file = "Roboto-Black.ttf"
        
    try:
        return ImageFont.truetype(font_file, size)
    except IOError:
        # Fallback if download failed
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

def create_circular_avatar(avatar_image: Image.Image, size: int = 40) -> Image.Image:
    """Resize and crop an image into a smooth circle."""
    avatar = avatar_image.convert("RGBA").resize((size * 3, size * 3), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size * 3, size * 3), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size * 3, size * 3), fill=255)
    avatar.putalpha(mask)
    return avatar.resize((size, size), Image.Resampling.LANCZOS)

def create_stamp(text: str = "CAUGHT IN 4K") -> Image.Image:
    """Create a high-quality, neon rectangular rubber stamp."""
    stamp_w = 320
    stamp_h = 80
    stamp = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(stamp)

    neon_color = (255, 0, 85, 200) # Semi-transparent neon
    bg_color = (255, 0, 85, 20)    # Very faint background tint

    # Background tint
    draw.rounded_rectangle([4, 4, stamp_w - 4, stamp_h - 4], radius=12, fill=bg_color)
    
    # Outer borders
    draw.rounded_rectangle([4, 4, stamp_w - 4, stamp_h - 4], radius=12, outline=neon_color, width=4)
    draw.rounded_rectangle([12, 12, stamp_w - 12, stamp_h - 12], radius=6, outline=(255, 0, 85, 120), width=1)

    title_font = get_font(32, weight="black")

    # Measure texts
    t_bbox = draw.textbbox((0, 0), text, font=title_font)
    t_w = t_bbox[2] - t_bbox[0]
    t_h = t_bbox[3] - t_bbox[1]

    # Center text vertically and horizontally
    start_y = (stamp_h - t_h) // 2 - 8
    draw.text(((stamp_w - t_w) // 2, start_y), text, fill=(255, 0, 85, 230), font=title_font)

    # Rotate
    return stamp.rotate(12, expand=True, resample=Image.Resampling.BICUBIC)

def create_default_avatar(username: str, size: int = 40) -> Image.Image:
    """Generate a clean Discord-like placeholder avatar."""
    img = Image.new("RGBA", (size * 3, size * 3), (88, 101, 242)) # Blurple
    draw = ImageDraw.Draw(img)
    initial = (username[:1] or "?").upper()
    font = get_font(size * 1.5, weight="medium")
    
    bbox = draw.textbbox((0, 0), initial, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((size * 3 - w) // 2, (size * 3 - h) // 2 - (size*0.2)), initial, fill=(255, 255, 255), font=font)
    
    mask = Image.new("L", (size * 3, size * 3), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 3, size * 3), fill=255)
    img.putalpha(mask)
    return img.resize((size, size), Image.Resampling.LANCZOS)

def generate_shame_card(
    author_name: str,
    message_text: str,
    timestamp: datetime = None,
    avatar_url: str = None,
    attachment_url: str = None,
    card_width: int = 700,
) -> io.BytesIO:
    """Renders a pixel-perfect Discord Dark Mode screenshot."""
    if timestamp is None:
        timestamp = datetime.now()
    time_str = timestamp.strftime("Today at %I:%M %p").replace(" 0", " ") # e.g. Today at 8:42 PM

    # Layout Metrics
    avatar_size = 40
    padding_x = 16
    padding_y = 16
    text_x = padding_x + avatar_size + 16 # 72
    
    # Fonts
    name_font = get_font(16, weight="medium")
    time_font = get_font(12, weight="regular")
    body_font = get_font(16, weight="regular")

    # Fetch avatar
    if avatar_url:
        try:
            req = Request(avatar_url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=5) as response:
                raw_avatar = Image.open(io.BytesIO(response.read()))
                avatar = create_circular_avatar(raw_avatar, avatar_size)
        except Exception:
            avatar = create_default_avatar(author_name, avatar_size)
    else:
        avatar = create_default_avatar(author_name, avatar_size)

    # Fetch attachment
    attachment_img = None
    if attachment_url:
        try:
            req = Request(attachment_url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=6) as response:
                raw_attachment = Image.open(io.BytesIO(response.read())).convert("RGBA")
                # Max bounds for Discord image attachments
                raw_attachment.thumbnail((400, 300), Image.Resampling.LANCZOS)
                attachment_img = raw_attachment
        except Exception:
            attachment_img = None

    # Text wrapping
    content_width_px = card_width - text_x - 32 # Leave right padding
    wrap_chars = max(30, int(content_width_px / 7.8))
    
    lines = []
    for paragraph in (message_text or "").split("\n"):
        if not paragraph.strip():
            lines.append("")
        else:
            lines.extend(textwrap.wrap(paragraph, width=wrap_chars))

    if not lines and attachment_img:
        lines = []

    # Heights
    line_height = 22 # 1.375 * 16px
    text_block_height = len(lines) * line_height
    
    content_y_start = padding_y + 24 # Name takes up ~24px height
    card_height = content_y_start + text_block_height
    
    if attachment_img:
        card_height += attachment_img.height + 12

    # Add bottom padding
    card_height += 16
    
    # Generate the neon stamp first so we know its exact rotated size
    stamp = create_stamp("CAUGHT IN 4K")
    
    # Minimum height to fit the stamp perfectly without cutting it off
    card_height = max(card_height, stamp.height + 32)

    # Create Base Canvas
    card = Image.new("RGBA", (card_width, card_height), BG_COLOR)
    draw = ImageDraw.Draw(card)

    # Draw Subtle Border / Inner Box
    draw.rectangle([0, 0, card_width - 1, card_height - 1], outline=BORDER_COLOR, width=1)

    # Paste Avatar
    card.paste(avatar, (padding_x, padding_y), avatar)

    # We use Pilmoji for all text rendering so that emojis in names or messages render natively!
    with Pilmoji(card) as pilmoji:
        # Draw Author Name
        pilmoji.text((text_x, padding_y), author_name, fill=USER_COLOR, font=name_font)
        
        # Draw Timestamp
        name_bbox = draw.textbbox((text_x, padding_y), author_name, font=name_font)
        time_x = name_bbox[2] + 8
        pilmoji.text((time_x, padding_y + 4), time_str, fill=TIME_COLOR, font=time_font)
    
        # Draw Message Body
        curr_y = content_y_start
        for line in lines:
            pilmoji.text((text_x, curr_y), line, fill=TEXT_COLOR, font=body_font, emoji_position_offset=(0, 4))
            curr_y += line_height

    # Draw Attachment
    if attachment_img:
        if lines:
            curr_y += 4
        att_mask = Image.new("L", attachment_img.size, 0)
        mask_draw = ImageDraw.Draw(att_mask)
        mask_draw.rounded_rectangle([0, 0, attachment_img.width, attachment_img.height], radius=8, fill=255)
        card.paste(attachment_img, (text_x, curr_y), att_mask)

    # Apply Stamp with Alpha Blending safely inside bounds
    stamp_x = card_width - stamp.width - 20
    # Pin stamp to bottom right corner with 16px padding
    stamp_y = card_height - stamp.height - 16
    
    stamp_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    stamp_layer.paste(stamp, (stamp_x, stamp_y))
    card = Image.alpha_composite(card, stamp_layer)

    # Convert to RGB
    final_card = card.convert("RGB")

    # Output to BytesIO
    output_buffer = io.BytesIO()
    final_card.save(output_buffer, format="PNG", optimize=True)
    output_buffer.seek(0)
    
    # OPTIMIZATION: Manually close PIL images to instantly free memory and prevent Discloud OOM kills
    card.close()
    stamp.close()
    stamp_layer.close()
    final_card.close()
    avatar.close()
    if attachment_img:
        attachment_img.close()
        
    import gc
    gc.collect()

    return output_buffer
