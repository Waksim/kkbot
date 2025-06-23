import logging
import threading
from pathlib import Path
from typing import Tuple

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.db.models import QuerySet, Q
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path
from django.conf import settings
from django.utils.html import format_html
from django_select2.forms import Select2MultipleWidget

from .models import Card, Tag
from .services.db_updater import run_card_update

logger = logging.getLogger(__name__)


class CardAdminForm(forms.ModelForm):
    upload_image = forms.ImageField(
        label="Заменить изображение",
        help_text="Загрузите новое изображение в формате .webp. Оно заменит текущее.",
        required=False
    )

    class Meta:
        model = Card
        fields = '__all__'
        widgets = {"tags": Select2MultipleWidget}


@admin.register(Card)
class CardAdmin(ModelAdmin):
    form = CardAdminForm
    list_display = ('image_preview', 'card_id', 'name', 'card_type', 'display_tags', 'is_new')
    list_display_links = ('card_id', 'name',)
    list_filter = ('card_type', 'is_new', 'tags')
    search_fields = ('name', 'card_id')
    ordering = ('-card_id',)
    list_per_page = 30
    readonly_fields = ('card_id', 'image_preview_large')
    fieldsets = (
        ("Основная информация", {"fields": ('card_id', 'name', 'card_type', 'is_new', 'title')}),
        ("Изображение", {"fields": ('image_preview_large', 'upload_image')}),
        ("Игровые данные", {"fields": ('description', 'cost_info', 'hp')}),
        ("Связи и теги", {"fields": ('related_card', 'tags')}),
    )
    change_list_template = "admin/cards/card/change_list.html"

    def get_search_results(self, request: HttpRequest, queryset: QuerySet, search_term: str) -> Tuple[QuerySet, bool]:
        """
        Переопределяем стандартный поиск для включения поиска по именам тегов.
        """
        # Выполняем стандартный поиск по `search_fields` (`name`, `card_id`).
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term,
        )

        # Если поисковый запрос не пустой, дополнительно ищем совпадения в именах связанных тегов.
        if search_term:
            queryset |= self.model.objects.filter(tags__name__icontains=search_term)
            # Используем `distinct()` для удаления дубликатов, которые могут возникнуть,
            # если карта найдена и по имени, и по тегу (например, поиск "Pyro").
            queryset = queryset.distinct()

        return queryset, True

    def get_urls(self) -> list:
        urls = super().get_urls()
        custom_urls = [
            path("update-from-api/", self.admin_site.admin_view(self.update_cards_view),
                 name="cards_card_update_from_api")
        ]
        return custom_urls + urls

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).prefetch_related('tags')

    def _get_image_url(self, obj: Card) -> str | None:
        if obj.local_image_path.exists():
            relative_path = obj.local_image_path.relative_to(settings.MEDIA_ROOT)
            timestamp = obj.local_image_path.stat().st_mtime
            return f"{settings.MEDIA_URL}{relative_path}?v={timestamp}"
        return None

    @admin.display(description="Изображение")
    def image_preview(self, obj: Card) -> str:
        url = self._get_image_url(obj)
        if url:
            return format_html('<img src="{}" style="width: 50px; height: auto;" />', url)
        return "Нет фото"

    @admin.display(description="Текущее изображение")
    def image_preview_large(self, obj: Card) -> str:
        url = self._get_image_url(obj)
        if url:
            return format_html('<img src="{}" style="max-width: 200px; height: auto;" />', url)
        return "Нет фото"

    @admin.display(description="Теги")
    def display_tags(self, obj: Card) -> str:
        tags = [tag.name for tag in obj.tags.all()]
        return ", ".join(sorted(tags)) if tags else "—"

    def save_model(self, request: HttpRequest, obj: Card, form: CardAdminForm, change: bool) -> None:
        super().save_model(request, obj, form, change)
        uploaded_file = request.FILES.get('upload_image')

        if not uploaded_file:
            return

        destination_path: Path = obj.local_image_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(destination_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            self.message_user(request, f"Изображение для карты '{obj.name}' успешно заменено.", messages.SUCCESS)
        except IOError as e:
            logger.error(f"Ошибка IOError при записи файла изображения для карты {obj.card_id}: {e}", exc_info=True)
            self.message_user(request, f"Ошибка при сохранении изображения: {e}", messages.ERROR)

    def update_cards_view(self, request: HttpRequest) -> HttpResponseRedirect:
        try:
            # Запускаем тяжелую задачу в отдельном потоке, чтобы не блокировать основной процесс Django.
            thread = threading.Thread(target=run_card_update, daemon=True)
            thread.start()
            self.message_user(
                request,
                "Процесс обновления карт запущен в фоновом режиме. "
                "Это может занять несколько минут.",
                messages.SUCCESS,
            )
        except Exception as e:
            self.message_user(request, f"Не удалось запустить процесс обновления: {e}", messages.ERROR)
        return HttpResponseRedirect("../")


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)