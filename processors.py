import io
import base64
from PIL import Image, ImageEnhance, ImageOps, ImageFilter, ImageDraw

def image_to_base64(img):
    """Конвертация PIL Image в base64 строку для отправки в браузер."""
    buf = io.BytesIO()
    # Автоматически сохраняем PNG если есть прозрачность, иначе JPEG
    if img.mode == 'RGBA':
        img.save(buf, format="PNG")
    else:
        img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def resize_for_preview(img, max_width=800):
    """Создание легкой копии для быстрого предпросмотра."""
    ratio = min(max_width/img.width, 1.0)
    if ratio >= 1: return img.copy()
    return img.resize((int(img.width*ratio), int(img.height*ratio)), Image.Resampling.LANCZOS)

def apply_vignette(img, intensity):
    """Создает виньетку с учетом прозрачности."""
    if intensity <= 0: return img
    
    # Создаем черный слой
    black_layer = Image.new('RGB', img.size, (0,0,0))
    
    # Создаем маску овала
    mask_w, mask_h = img.size[0] // 2, img.size[1] // 2
    if mask_w < 10: mask_w = 10
    if mask_h < 10: mask_h = 10
    
    mask = Image.new('L', (mask_w, mask_h), 0)
    draw = ImageDraw.Draw(mask)
    
    x_radius = mask_w * (0.75 - 0.4 * intensity)
    y_radius = mask_h * (0.75 - 0.4 * intensity)
    cx, cy = mask_w // 2, mask_h // 2
    
    draw.ellipse((cx - x_radius, cy - y_radius, cx + x_radius, cy + y_radius), fill=255)
    
    # Размываем и растягиваем маску
    blur_radius = min(mask_w, mask_h) * 0.4
    mask = mask.filter(ImageFilter.GaussianBlur(blur_radius))
    mask = mask.resize(img.size, Image.Resampling.LANCZOS)
    
    return Image.composite(img, black_layer, mask)

def apply_filters(img, params):
    """Основной конвейер обработки."""
    # 1. Геометрия
    rot = params.get('rotation', 0)
    if rot != 0:
        # expand=True важен для сохранения углов при повороте
        img = img.rotate(-rot, expand=True)
        
    if params.get('flip_x'): img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if params.get('flip_y'): img = img.transpose(Image.FLIP_TOP_BOTTOM)

    # 2. Сохранение альфа-канала
    alpha = None
    if img.mode == 'RGBA':
        alpha = img.getchannel('A')
        img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # 3. RGB Баланс
    r_fac = float(params.get('color_r', 1.0))
    g_fac = float(params.get('color_g', 1.0))
    b_fac = float(params.get('color_b', 1.0))
    
    if abs(r_fac - 1.0) > 0.01 or abs(g_fac - 1.0) > 0.01 or abs(b_fac - 1.0) > 0.01:
        bands = img.split()
        if len(bands) >= 3:
            r, g, b = bands[0], bands[1], bands[2]
            if r_fac != 1.0: r = ImageEnhance.Brightness(r).enhance(r_fac)
            if g_fac != 1.0: g = ImageEnhance.Brightness(g).enhance(g_fac)
            if b_fac != 1.0: b = ImageEnhance.Brightness(b).enhance(b_fac)
            img = Image.merge('RGB', (r, g, b))

    # 4. Цветовые эффекты
    if params.get('sepia'):
        sepia_matrix = (0.393, 0.769, 0.189, 0, 0.349, 0.686, 0.168, 0, 0.272, 0.534, 0.131, 0)
        img = img.convert("RGB", sepia_matrix)

    if params.get('negative'): img = ImageOps.invert(img)
    if params.get('grayscale'): img = ImageOps.grayscale(img).convert("RGB")

    # 5. Базовая коррекция
    enhancements = [
        (ImageEnhance.Brightness, 'brightness'),
        (ImageEnhance.Contrast, 'contrast'),
        (ImageEnhance.Color, 'saturation'),
        (ImageEnhance.Sharpness, 'sharpness')
    ]
    for Enhancer, key in enhancements:
        val = float(params.get(key, 1.0))
        if val != 1.0: img = Enhancer(img).enhance(val)

    # 6. Финальные эффекты
    blur_val = float(params.get('blur', 0))
    if blur_val > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_val))

    vig_val = float(params.get('vignette', 0))
    if vig_val > 0:
        img = apply_vignette(img, vig_val)

    # 7. Восстановление прозрачности
    if alpha:
        if alpha.size != img.size:
            alpha = alpha.resize(img.size)
        img.putalpha(alpha)

    return img