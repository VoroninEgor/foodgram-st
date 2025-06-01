from django.contrib import admin
from django.db.models import Count

from .models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                     RecipeShortLink, ShoppingCart)
from api.constants import MIN_INGREDIENT_AMOUNT


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = MIN_INGREDIENT_AMOUNT
    min_num = MIN_INGREDIENT_AMOUNT


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    list_filter = ('measurement_unit',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'author', 'cooking_time', 'created', 'favorites_count'
    )
    list_filter = ('created', 'author')
    search_fields = ('name', 'author__username', 'author__email')
    ordering = ('-created',)
    inlines = (RecipeIngredientInline,)
    readonly_fields = ('favorites_count',)
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            favorites_count=Count('favorites')
        )
    
    def favorites_count(self, obj):
        return obj.favorites_count
    
    favorites_count.short_description = 'В избранном'
    favorites_count.admin_order_field = 'favorites_count'


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount')
    list_filter = ('ingredient',)
    search_fields = ('recipe__name', 'ingredient__name')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe', 'created')
    list_filter = ('created',)
    search_fields = ('user__username', 'recipe__name')
    ordering = ('-created',)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe', 'created')
    list_filter = ('created',)
    search_fields = ('user__username', 'recipe__name')
    ordering = ('-created',)


@admin.register(RecipeShortLink)
class RecipeShortLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'short_code', 'created')
    list_filter = ('created',)
    search_fields = ('recipe__name', 'short_code')
    ordering = ('-created',)
    readonly_fields = ('short_code',)
