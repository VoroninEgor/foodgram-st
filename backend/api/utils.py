import random
import string
from collections import defaultdict
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

from recipes.models import RecipeIngredient, RecipeShortLink
from django.conf import settings
from .constants import DEFAULT_SHORT_CODE_LENGTH


def generate_short_code(length=DEFAULT_SHORT_CODE_LENGTH):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def get_or_create_short_link(recipe):
    short_link, created = RecipeShortLink.objects.get_or_create(
        recipe=recipe,
        defaults={'short_code': generate_short_code()}
    )
    return short_link


def generate_shopping_list_txt(user):
    shopping_cart = user.shopping_cart.all()
    if not shopping_cart:
        return HttpResponse(
            'Ваш список покупок пуст.',
            content_type='text/plain; charset=utf-8'
        )
    
    ingredients = defaultdict(int)
    
    for cart_item in shopping_cart:
        recipe_ingredients = RecipeIngredient.objects.filter(
            recipe=cart_item.recipe
        ).select_related('ingredient')
        
        for recipe_ingredient in recipe_ingredients:
            ingredient = recipe_ingredient.ingredient
            key = f"{ingredient.name} ({ingredient.measurement_unit})"
            ingredients[key] += recipe_ingredient.amount
    
    shopping_list = "Список покупок:\n\n"
    for ingredient, amount in sorted(ingredients.items()):
        shopping_list += f"• {ingredient} — {amount}\n"
    
    response = HttpResponse(
        shopping_list,
        content_type='text/plain; charset=utf-8'
    )
    response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
    return response
    