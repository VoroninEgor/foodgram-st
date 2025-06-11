import random
import string
from collections import defaultdict
from io import BytesIO

from django.conf import settings
from django.db import models
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from recipes.models import RecipeIngredient


def get_shopping_list_ingredients(user):
    return RecipeIngredient.objects.filter(
        recipe__shopping_cart__user=user
    ).values(
        'ingredient__name',
        'ingredient__measurement_unit'
    ).annotate(
        total_amount=models.Sum('amount')
    ).order_by('ingredient__name')


def generate_shopping_list_txt(user):
    ingredients = get_shopping_list_ingredients(user)
    
    shopping_list = ['Список покупок:\n']
    
    for ingredient in ingredients:
        shopping_list.append(
            f"{ingredient['ingredient__name']} - "
            f"{ingredient['total_amount']} "
            f"{ingredient['ingredient__measurement_unit']}"
        )
    
    return '\n'.join(shopping_list)
    