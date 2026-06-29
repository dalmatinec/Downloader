# ========================================
# ГЕНЕРАЦИЯ QR-КОДА
# ========================================

import qrcode
from PIL import Image
from io import BytesIO

async def generate(data, logo_path=None):
    # Создаем объект QR
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Рисуем черно-белую картинку
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    # Если есть лого - вставляем по центру
    if logo_path:
        try:
            logo = Image.open(logo_path).convert("RGBA")
            size = img.size[0] // 5
            logo.thumbnail((size, size), Image.Resampling.LANCZOS)
            x = (img.size[0] - logo.width) // 2
            y = (img.size[1] - logo.height) // 2
            img.paste(logo, (x, y), logo)
        except:
            pass
    
    # Сохраняем в память
    bio = BytesIO()
    bio.name = 'qr.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio