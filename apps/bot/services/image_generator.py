import io
import logging
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from apps.cards.models import Card

# --- Константы для отрисовки ---
BG_SIZE = (801, 1430)
CHAR_CARD_SIZE = (150, 250)
ACTION_CARD_SIZE = (105, 168)
Y_CHAR = 80
# ИЗМЕНЕНИЕ: Опускаем резонансы ниже для лучшего центрирования
Y_RESONANCE = Y_CHAR + CHAR_CARD_SIZE[1] + 55
Y_ACTION_START = Y_RESONANCE + 60
CHAR_SPACING = 25
ACTION_X_SPACING = 15
ACTION_Y_SPACING = 15
CARDS_PER_ROW = 6
RESONANCE_TEXT_COLOR = (80, 56, 30)
NO_RESONANCE_TEXT = "No Resonance"
DEFAULT_RESONANCE_COLOR = (128, 128, 128)  # Цвет для неизвестных резонансов

# ИЗМЕНЕНИЕ: Возвращаем словарь с цветами
RESONANCE_COLORS = {
    # Элементы
    "Cryo": (155, 203, 255), "Pyro": (255, 128, 88), "Hydro": (0, 112, 255),
    "Electro": (187, 127, 255), "Anemo": (128, 255, 183), "Geo": (255, 212, 93),
    "Dendro": (97, 209, 60),
    # Регионы
    "Mondstadt": (70, 180, 160), "Liyue": (250, 190, 80), "Inazuma": (160, 130, 220),
    "Sumeru": (60, 170, 90), "Fontaine": (80, 150, 240), "Natlan": (230, 100, 70),
    # Фракции
    "Fatui": (80, 100, 120), "The Eremites": (220, 160, 100),
    "Monster": (160, 80, 45), "Hilichurl": (200, 180, 140),
}

# Пути к ассетам
ASSETS_DIR: Path = settings.BASE_DIR / "core" / "static" / "bot"
BG_PATH = ASSETS_DIR / "images" / "background.png"
BORDER_PATH = ASSETS_DIR / "images" / "border.png"
FONT_PATH = ASSETS_DIR / "fonts" / "gi_font.ttf"


# Папки и словари с иконками/эмодзи удалены


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Загружает шрифт или возвращает шрифт по умолчанию."""
    try:
        return ImageFont.truetype(str(FONT_PATH), size)
    except IOError:
        logging.warning(f"Не удалось загрузить шрифт: {FONT_PATH}.")
        return ImageFont.load_default(size)


def _paste_card(
        base_image: Image.Image, card: Card, position: tuple[int, int],
        size: tuple[int, int], border_img: Image.Image
) -> None:
    """Вставляет изображение карты с рамкой на основное изображение."""
    card_path = card.local_image_path
    if not card_path.exists():
        logging.warning(f"Изображение для карты '{card.name}' ({card.card_id}) не найдено: {card_path}")
        return

    with Image.open(card_path).convert("RGBA") as card_img:
        card_resized = card_img.resize(size, Image.Resampling.LANCZOS)
        border_resized = border_img.resize(size, Image.Resampling.LANCZOS)
        card_resized.paste(border_resized, (0, 0), border_resized)
        base_image.paste(card_resized, position, card_resized)


def create_deck_image(
        character_cards: List[Card], action_cards: List[Card], resonances: List[str]
) -> io.BytesIO:
    """Создает изображение колоды и возвращает его в виде байтового потока."""
    try:
        bg_image = Image.open(BG_PATH).convert("RGBA")
        border_image = Image.open(BORDER_PATH).convert("RGBA")
    except FileNotFoundError as e:
        logging.error(f"Не найдены базовые ассеты: {e}")
        bg_image = Image.new("RGB", BG_SIZE, "grey")
        border_image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    draw = ImageDraw.Draw(bg_image)
    center_x = bg_image.width // 2

    # 2. Отрисовка карт персонажей
    unique_character_cards = list({card.card_id: card for card in character_cards}.values())
    total_chars_width = len(unique_character_cards) * CHAR_CARD_SIZE[0] + (
                len(unique_character_cards) - 1) * CHAR_SPACING
    start_x_char = center_x - total_chars_width // 2
    for i, char_card in enumerate(unique_character_cards):
        x = start_x_char + i * (CHAR_CARD_SIZE[0] + CHAR_SPACING)
        _paste_card(bg_image, char_card, (x, Y_CHAR), CHAR_CARD_SIZE, border_image)

    # 3. Отрисовка резонансов (метод с цветными кружками)
    font_res = _get_font(22)
    spacing_res = 35
    circle_text_gap = 12
    circle_diameter = 20

    res_list = resonances if resonances else [NO_RESONANCE_TEXT]
    items_to_draw = []
    total_res_width = 0

    for res_name in res_list:
        text = res_name.upper()
        color = RESONANCE_COLORS.get(res_name) if res_name != NO_RESONANCE_TEXT else None

        text_width = draw.textbbox((0, 0), text, font=font_res)[2]
        item_width = text_width + (circle_diameter + circle_text_gap if color else 0)

        items_to_draw.append({"color": color, "text": text, "width": item_width})
        total_res_width += item_width

    total_res_width += (len(items_to_draw) - 1) * spacing_res
    current_x = center_x - total_res_width // 2

    for item in items_to_draw:
        y_pos = Y_RESONANCE

        if item["color"]:
            # Координаты для кружка
            y_circle_start = y_pos - circle_diameter // 2
            x_circle_end = current_x + circle_diameter
            y_circle_end = y_circle_start + circle_diameter

            draw.ellipse(
                (current_x, y_circle_start, x_circle_end, y_circle_end),
                fill=item["color"],
                outline=(50, 50, 50, 100),  # тонкая темная обводка
                width=1
            )
            current_x += circle_diameter + circle_text_gap

        draw.text((current_x, y_pos), item["text"], font=font_res, fill=RESONANCE_TEXT_COLOR, anchor="lm")
        current_x += item["width"] - (circle_diameter + circle_text_gap if item["color"] else 0) + spacing_res

    # 4. Отрисовка карт действий
    total_row_width = CARDS_PER_ROW * ACTION_CARD_SIZE[0] + (CARDS_PER_ROW - 1) * ACTION_X_SPACING
    start_x_action = center_x - total_row_width // 2
    for i, action_card in enumerate(action_cards):
        row = i // CARDS_PER_ROW
        col = i % CARDS_PER_ROW
        x = start_x_action + col * (ACTION_CARD_SIZE[0] + ACTION_X_SPACING)
        y = Y_ACTION_START + row * (ACTION_CARD_SIZE[1] + ACTION_Y_SPACING)
        _paste_card(bg_image, action_card, (x, y), ACTION_CARD_SIZE, border_image)

    # 5. Сохранение в байтовый поток
    image_bytes = io.BytesIO()
    bg_image.convert("RGB").save(image_bytes, format='JPEG', quality=90)
    image_bytes.seek(0)
    return image_bytes