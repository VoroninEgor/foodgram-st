from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from djoser.views import UserViewSet as DjoserUserViewSet
from django.contrib.auth.models import AnonymousUser
from django.db.models import Count
from django.http import HttpResponse

from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeShortLink, ShoppingCart
)
from users.models import Subscription
from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPageNumberPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    CustomUserSerializer, IngredientSerializer, RecipeCreateSerializer,
    RecipeListSerializer, RecipeMinifiedSerializer, RecipeShortLinkSerializer,
    SetAvatarSerializer, SubscriptionSerializer, UserWithRecipesSerializer
)
from .utils import generate_shopping_list_txt, get_or_create_short_link
from http import HTTPStatus

User = get_user_model()


def short_link_redirect(request, short_code):
    short_link = get_object_or_404(RecipeShortLink, short_code=short_code)
    return redirect(f'/recipes/{short_link.recipe.id}/')


class CustomUserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = CustomPageNumberPagination
    
    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def avatar(self, request):
        user = request.user
        
        if request.method == 'PUT':
            serializer = SetAvatarSerializer(data=request.data)
            if serializer.is_valid():
                user.avatar = serializer.validated_data['avatar']
                user.save()
                return Response(
                    {'avatar': request.build_absolute_uri(user.avatar.url)},
                    status=HTTPStatus.OK
                )
            return Response(
                serializer.errors, 
                status=HTTPStatus.BAD_REQUEST
            )
        
        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
            return Response(status=HTTPStatus.NO_CONTENT)
    
    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        subscriptions = Subscription.objects.filter(user=request.user)
        authors = User.objects.filter(
            id__in=subscriptions.values_list('author_id', flat=True)
        ).annotate(recipes_count=Count('recipes'))
        
        page = self.paginate_queryset(authors)
        if page is not None:
            serializer = UserWithRecipesSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = UserWithRecipesSerializer(
            authors, many=True, context={'request': request}
        )
        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id) # Проверка на существование автора нужна и при удалении в постман тестах
        
        if request.method == 'POST':
            if request.user == author:
                return Response(
                    {'errors': 'Нельзя подписаться на самого себя.'},
                    status=HTTPStatus.BAD_REQUEST
                )
            
            subscription, created = Subscription.objects.get_or_create(
                user=request.user, author=author
            )
            
            if not created:
                return Response(
                    {'errors': 'Вы уже подписаны на этого пользователя.'},
                    status=HTTPStatus.BAD_REQUEST
                )
            
            serializer = UserWithRecipesSerializer(
                author, context={'request': request}
            )
            return Response(serializer.data, status=HTTPStatus.CREATED)
        
        elif request.method == 'DELETE':
            deleted, _ = Subscription.objects.filter(
                user=request.user, author=author
            ).delete()
            
            if not deleted:
                return Response(
                    {'errors': 'Вы не подписаны на этого пользователя.'},
                    status=HTTPStatus.BAD_REQUEST
                )
            
            return Response(status=HTTPStatus.NO_CONTENT)

    @action(detail=False, methods=['get', 'put', 'patch', 'delete'],
            permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        if isinstance(request.user, AnonymousUser):
            return Response(status=HTTPStatus.UNAUTHORIZED)
        return super().me(request, *args, **kwargs)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = CustomPageNumberPagination
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateSerializer
        return RecipeListSerializer
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(
        detail=True,
        methods=['get'],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = get_or_create_short_link(recipe)
        serializer = RecipeShortLinkSerializer(
            short_link, context={'request': request}
        )
        return Response(serializer.data)
    
    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        
        if request.method == 'POST':
            favorite, created = Favorite.objects.get_or_create(
                user=request.user, recipe=recipe
            )
            
            if not created:
                return Response(
                    {'errors': 'Рецепт уже добавлен в избранное.'},
                    status=HTTPStatus.BAD_REQUEST
                )
            
            serializer = RecipeMinifiedSerializer(recipe)
            return Response(serializer.data, status=HTTPStatus.CREATED)
        
        elif request.method == 'DELETE':
            deleted, _ = Favorite.objects.filter(
                user=request.user, recipe=recipe
            ).delete()
            
            if not deleted:
                return Response(
                    {'errors': 'Рецепт не найден в избранном.'},
                    status=HTTPStatus.BAD_REQUEST
                )
            
            return Response(status=HTTPStatus.NO_CONTENT)
    
    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        
        if request.method == 'POST':
            cart_item, created = ShoppingCart.objects.get_or_create(
                user=request.user, recipe=recipe
            )
            
            if not created:
                return Response(
                    {'errors': 'Рецепт уже добавлен в список покупок.'},
                    status=HTTPStatus.BAD_REQUEST
                )
            
            serializer = RecipeMinifiedSerializer(recipe)
            return Response(serializer.data, status=HTTPStatus.CREATED)
        
        elif request.method == 'DELETE':
            deleted, _ = ShoppingCart.objects.filter(
                user=request.user, recipe=recipe
            ).delete()
            
            if not deleted:
                return Response(
                    {'errors': 'Рецепт не найден в списке покупок.'},
                    status=HTTPStatus.BAD_REQUEST
                )
            
            return Response(status=HTTPStatus.NO_CONTENT)
    
    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        shopping_list = generate_shopping_list_txt(request.user)
        response = HttpResponse(
            shopping_list,
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response
