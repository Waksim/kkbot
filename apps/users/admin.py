from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from .models import TelegramUser, Deck, UserActivity


class DeckInline(admin.TabularInline):
    """Встраиваемая админ-модель для отображения колод пользователя."""
    model = Deck
    extra = 0  # Не показывать пустые формы для добавления
    fields = ('deck_code', 'created_at',)
    readonly_fields = ('deck_code', 'created_at',)
    can_delete = False
    show_change_link = True  # Ссылка на страницу редактирования колоды

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


class UserActivityInline(admin.TabularInline):
    """Встраиваемая админ-модель для отображения активности пользователя."""
    model = UserActivity
    extra = 0
    fields = ('created_at', 'activity_type', 'details',)
    readonly_fields = ('created_at', 'activity_type', 'details',)
    can_delete = False
    ordering = ('-created_at',)

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    """Админ-панель для модели TelegramUser."""
    list_display = ('user_id', 'username', 'first_name', 'deck_count', 'created_at')
    search_fields = ('user_id', 'username', 'first_name')
    list_filter = ('created_at',)
    readonly_fields = ('user_id', 'created_at',)
    inlines = [DeckInline, UserActivityInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        # Оптимизация: предзагружаем количество колод
        return super().get_queryset(request).prefetch_related('decks')


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    """Админ-панель для модели Deck."""
    list_display = ('deck_code', 'owner_link', 'created_at')
    search_fields = ('deck_code', 'owner__username', 'owner__user_id')
    list_filter = ('created_at', 'owner')
    readonly_fields = ('deck_code', 'owner', 'created_at', 'character_card_ids', 'action_card_ids')

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Админ-панель для модели UserActivity."""
    list_display = ('user', 'activity_type', 'created_at')
    search_fields = ('user__username', 'user__user_id', 'details')
    list_filter = ('activity_type', 'created_at')
    readonly_fields = ('user', 'activity_type', 'details', 'created_at')

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False