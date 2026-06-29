# ========================================
# ГЕНЕРАЦИЯ QR-КОДА (БЕЗ ЛИШНЕЙ ХУЙНИ)
# ========================================

import qrcode
from PIL import Image
from io import BytesIO

async def generate(data, logo_path=None):
    # Создаем объект QR
    qr = qrcode.QRCode(
        version=3,                                   # Размер матрицы
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # Чтоб лого не сломал
        box_size=10,                                 # Размер одного пикселя
        border=2,                                    # Отступ от края
    )
    qr.add_data(data)      # Кидаем ссылку внутрь
    qr.make(fit=True)      # Строим матрицу

    # Рисуем черно-белую картинку
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    # Если прилетел логотип - вставляем по центру
    if logo_path:
        try:
            logo = Image.open(logo_path).convert("RGBA")  # Открываем картинку
            size = img.size[0] // 5                       # Сжимаем до 1/5 QR
            logo.thumbnail((size, size), Image.Resampling.LANCZOS)
            x = (img.size[0] - logo.width) // 2           # Координата X по центру
            y = (img.size[1] - logo.height) // 2          # Координата Y по центру
            img.paste(logo, (x, y), logo)                 # Вставляем
        except:
            pass  # Если картинка кривая - хуй с ней, пропускаем
    
    # Сохраняем в память (чтобы отправить в Telegram)
    bio = BytesIO()
    bio.name = 'qr.png'
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio