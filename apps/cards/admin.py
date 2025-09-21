import logging
import os
import tempfile
import threading
from io import BytesIO
from pathlib import Path
from typing import Tuple

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.db.models import QuerySet, Q
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import path
from django.conf import settings
from django.utils.html import format_html
from django_select2.forms import Select2MultipleWidget

from .models import Card, Tag
from .services.db_updater import run_card_update
from .services.translation_importer import export_cards_to_excel, get_translation_diff, apply_translations_from_excel

logger = logging.getLogger(__name__)


class TranslationUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Excel-файл для импорта (.xlsx)",
        help_text="Файл должен содержать колонки: card_id, name_ru, title_ru, description_ru.",
        required=True
    )


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
    list_display = ('image_preview', 'card_id', 'name_en', 'name_ru', 'card_type', 'display_tags', 'is_new')
    list_display_links = ('card_id', 'name_en', 'name_ru',)
    list_filter = ('card_type', 'is_new', 'tags')
    search_fields = ('name_en', 'name_ru', 'card_id')
    ordering = ('-card_id',)
    list_per_page = 30
    readonly_fields = ('card_id', 'image_preview_large')
    actions = ('export_as_excel',)
    fieldsets = (
        ("Основная информация (EN)", {"fields": ('name_en', 'title_en', 'description_en')}),
        ("Основная информация (RU)", {"fields": ('name_ru', 'title_ru', 'description_ru')}),
        ("Общие данные", {"fields": ('card_id', 'card_type', 'is_new', 'cost_info', 'hp')}),
        ("Изображение", {"fields": ('image_preview_large', 'upload_image')}),
        ("Связи и теги", {"fields": ('related_card', 'tags')}),
    )
    change_list_template = "admin/cards/card/change_list.html"

    @admin.action(description='Export selected cards to Excel for translation')
    def export_as_excel(self, request: HttpRequest, queryset: QuerySet):
        file_stream = export_cards_to_excel(queryset)
        response = HttpResponse(file_stream,
                                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=card_translations.xlsx'
        return response

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
                 name="cards_card_update_from_api"),
            path("import-translations/", self.admin_site.admin_view(self.import_translations_view),
                 name="cards_card_import_translations"),
        ]
        return custom_urls + urls

    def import_translations_view(self, request: HttpRequest):
        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta

        if request.method == "POST":
            # Step 2: Apply confirmed changes
            if 'apply_changes' in request.POST:
                temp_file_path = request.session.get('uploaded_excel_path')
                if not temp_file_path or not os.path.exists(temp_file_path):
                    self.message_user(request, "Temporary file not found or session expired. Please upload again.", messages.ERROR)
                    return HttpResponseRedirect(".")

                with open(temp_file_path, 'rb') as f:
                    file_stream = BytesIO(f.read())

                errors = apply_translations_from_excel(file_stream)

                if errors:
                    for error in errors:
                        self.message_user(request, f"Error applying changes: {error}", messages.ERROR)
                else:
                    self.message_user(request, "Translations applied successfully.", messages.SUCCESS)

                # Clean up the temporary file and session
                os.remove(temp_file_path)
                del request.session['uploaded_excel_path']
                return HttpResponseRedirect("../")

            # Step 1: Handle file upload and show diff
            form = TranslationUploadForm(request.POST, request.FILES)
            if form.is_valid():
                excel_file = request.FILES['excel_file']

                # Use a temporary file instead of session storage for the file content
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_f:
                    for chunk in excel_file.chunks():
                        temp_f.write(chunk)
                    request.session['uploaded_excel_path'] = temp_f.name

                with open(temp_f.name, 'rb') as f:
                    file_stream = BytesIO(f.read())

                diff = get_translation_diff(file_stream)

                context.update({
                    'updates': diff['updates'],
                    'errors': diff['errors'],
                })
                return render(request, 'admin/cards/card/translation_diff.html', context)

        # Initial view (GET request)
        form = TranslationUploadForm()
        context['form'] = form
        return render(request, 'admin/cards/card/translation_import.html', context)

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