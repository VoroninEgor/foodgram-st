from django.contrib import admin
from django.db.models import Count, Prefetch

from api.constants import MIN_INGREDIENT_AMOUNT

from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = MIN_INGREDIENT_AMOUNT
    min_num = MIN_INGREDIENT_AMOUNT


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'author', 'cooking_time', 'created', 'favorites_count'
    )
    list_filter = (
        'created',
        'author',
        ('author__username', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = ('name',) 
    ordering = ('-created',)
    inlines = (RecipeIngredientInline,)
    readonly_fields = ('favorites_count',)
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('author').prefetch_related(
            'ingredients',
            Prefetch(
                'recipe_ingredients',
                queryset=RecipeIngredient.objects.select_related('ingredient')
            )
        ).annotate(
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
