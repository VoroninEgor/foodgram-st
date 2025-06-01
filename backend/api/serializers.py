import base64
import uuid
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers
from djoser.serializers import UserCreateSerializer, UserSerializer

from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeIngredient, 
    RecipeShortLink, ShoppingCart
)
from users.models import Subscription

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(
                base64.b64decode(imgstr), 
                name=f'{uuid.uuid4()}.{ext}'
            )
        return super().to_internal_value(data)


class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password'
        )


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True)
    
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 
            'is_subscribed', 'avatar'
        )
    
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user, author=obj
            ).exists()
        return False


class SetAvatarSerializer(serializers.Serializer):
    avatar = Base64ImageField()


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')
    
    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    
    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeListSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    
    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        return False
    
    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ShoppingCart.objects.filter(
                user=request.user, recipe=obj
            ).exists()
        return False


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientCreateSerializer(many=True)
    image = Base64ImageField()
    
    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'image', 'name', 'text', 'cooking_time'
        )
    
    def validate(self, data):
        required_fields = ['ingredients', 'name', 'text', 'cooking_time', 'image']
        if self.instance is not None:
            missing_fields = []
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if missing_fields:
                errors = {}
                for field in missing_fields:
                    errors[field] = 'Это поле обязательно.'
                raise serializers.ValidationError(errors)
        elif 'ingredients' not in data:
            raise serializers.ValidationError({
                'ingredients': 'Это поле обязательно.'
            })
        
        return data
    
    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Нужно добавить хотя бы один ингредиент.'
            )
        
        ingredient_ids = [item['id'] for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )
        
        existing_ingredients = Ingredient.objects.filter(
            id__in=ingredient_ids
        ).values_list('id', flat=True)
        
        non_existing_ids = set(ingredient_ids) - set(existing_ingredients)
        if non_existing_ids:
            raise serializers.ValidationError(
                f'Ингредиенты с id {list(non_existing_ids)} не существуют.'
            )
        
        for item in value:
            if item['amount'] < 1:
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть больше 0.'
                )
        
        return value
    
    def create_ingredients(self, recipe, ingredients):
        recipe_ingredients = []
        for ingredient_data in ingredients:
            try:
                ingredient = Ingredient.objects.get(id=ingredient_data['id'])
                recipe_ingredients.append(
                    RecipeIngredient(
                        recipe=recipe,
                        ingredient=ingredient,
                        amount=ingredient_data['amount']
                    )
                )
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    f'Ингредиент с id {ingredient_data["id"]} не существует.'
                )
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
    
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        try:
            self.create_ingredients(recipe, ingredients)
        except serializers.ValidationError:
            recipe.delete()
            raise
        return recipe
    
    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        
        instance.recipe_ingredients.all().delete()
        self.create_ingredients(instance, ingredients)
        
        return super().update(instance, validated_data)
    
    def to_representation(self, instance):
        return RecipeListSerializer(
            instance, context=self.context
        ).data


class UserWithRecipesSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )
    
    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = None
        if request:
            recipes_limit = request.query_params.get('recipes_limit')
        
        recipes = obj.recipes.all()
        if recipes_limit:
            try:
                recipes = recipes[:int(recipes_limit)]
            except ValueError:
                pass
        
        return RecipeMinifiedSerializer(recipes, many=True).data
    
    def get_recipes_count(self, obj):
        return obj.recipes.count()


class RecipeShortLinkSerializer(serializers.ModelSerializer):
    short_link = serializers.SerializerMethodField(source='short-link')
    
    class Meta:
        model = RecipeShortLink
        fields = ('short_link',)
    
    def get_short_link(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/s/{obj.short_code}/')
        return f'/s/{obj.short_code}/'
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'short_link' in data:
            data['short-link'] = data.pop('short_link')
        return data


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ('user', 'author')
    
    def validate(self, data):
        user = data['user']
        author = data['author']
        
        if user == author:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.'
            )
        
        if Subscription.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя.'
            )
        
        return data 