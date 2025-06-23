from collections import Counter
from typing import List, Set
from apps.cards.models import Card

RESONANCE_TAGS: Set[str] = {
    # Элементы
    "Cryo", "Pyro", "Hydro", "Electro", "Anemo", "Geo", "Dendro",
    # Регионы
    "Mondstadt", "Liyue", "Inazuma", "Sumeru", "Fontaine", "Natlan",
    # Фракции
    "Fatui", "The Eremites", "Monster", "Hilichurl",
}


def calculate_resonances(character_cards: List[Card]) -> List[str]:
    """
    Вычисляет элементальные, региональные и фракционные резонансы
    на основе карт персонажей.

    Функция намеренно синхронная, так как она работает с данными,
    которые уже должны быть предзагружены в память (через `prefetch_related`),
    и не выполняет I/O-операций.
    """
    if not character_cards or len(character_cards) < 2:
        return []

    all_tags: List[str] = []
    for card in character_cards:
        # Используем предзагруженные через `prefetch_related` теги.
        # Это синхронная операция, которая не требует дополнительных запросов к БД в цикле.
        tags = [tag.name for tag in card.tags.all()]
        all_tags.extend(tags)

    tag_counter = Counter(all_tags)
    resonances: List[str] = []

    for tag in RESONANCE_TAGS:
        if tag_counter.get(tag, 0) >= 2:
            resonances.append(tag)

    # Сортируем для предсказуемого порядка на изображении и в тестах.
    return sorted(resonances)