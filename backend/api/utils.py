import random
import string
from collections import defaultdict
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from django.db import models

from recipes.models import RecipeIngredient, RecipeShortLink
from django.conf import settings
from .constants import DEFAULT_SHORT_CODE_LENGTH


def generate_short_code(length=DEFAULT_SHORT_CODE_LENGTH):
    characters = f"{string.ascii_letters}{string.digits}"
    return ''.join(random.choice(characters) for _ in range(length))


def get_or_create_short_link(recipe):
    short_link, created = RecipeShortLink.objects.get_or_create(
        recipe=recipe,
        defaults={'short_code': generate_short_code()}
    )
    return short_link


def get_shopping_list_ingredients(user):
    return RecipeIngredient.objects.filter(
        recipe__shopping_cart__user=user
    ).values(
        'ingredient__name',
        'ingredient__measurement_unit'
    ).annotate(
        total_amount=models.Sum('amount')
    ).order_by('ingredient__name')


def format_shopping_list(ingredients):
    if not ingredients:
        return 'Ваш список покупок пуст.'
    
    shopping_list = "Список покупок:\n\n"
    for ingredient in ingredients:
        name = ingredient['ingredient__name']
        unit = ingredient['ingredient__measurement_unit']
        amount = ingredient['total_amount']
        shopping_list += f"• {name} ({unit}) — {amount}\n"
    
    return shopping_list


def generate_shopping_list_txt(user):
    ingredients = get_shopping_list_ingredients(user)
    return format_shopping_list(ingredients)
    