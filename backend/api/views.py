from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from http import HTTPStatus
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
)
from users.models import Subscription

from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPageNumberPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    CustomUserSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeListSerializer,
    RecipeMinifiedSerializer,
    RecipeShortLinkSerializer,
    SetAvatarSerializer,
    SubscriptionSerializer,
    UserWithRecipesSerializer,
)
from .utils import generate_shopping_list_txt

User = get_user_model()


def short_link_redirect(request, short_code):
    recipe = get_object_or_404(Recipe, short_link=short_code)
    return redirect(f'/recipes/{recipe.id}/')


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
        author = get_object_or_404(User, id=id)
        
        if request.method == 'POST':
            serializer = SubscriptionSerializer(
                data={'user': request.user.id, 'author': id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                UserWithRecipesSerializer(author, context={'request': request}).data,
                status=HTTPStatus.CREATED
            )
        
        elif request.method == 'DELETE':
            deleted_count, _ = Subscription.objects.filter(
                user=request.user,
                author=author
            ).delete()

            if not deleted_count:
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
    queryset = Recipe.objects.select_related('author').prefetch_related(
        Prefetch(
            'recipe_ingredients',
            queryset=RecipeIngredient.objects.select_related('ingredient')
        )
    ).all()
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
        serializer = RecipeShortLinkSerializer(
            recipe, context={'request': request}
        )
        return Response(serializer.data)
    
    def _handle_recipe_action(self, request, recipe, model_class, error_message, success_message):
        '''Общий метод для обработки добавления/удаления рецепта в избранное или корзину.'''
        if request.method == 'POST':
            item, created = model_class.objects.get_or_create(
                user=request.user, recipe=recipe
            )
            
            if not created:
                return Response(
                    {'errors': error_message},
                    status=HTTPStatus.BAD_REQUEST
                )
            
            serializer = RecipeMinifiedSerializer(recipe)
            return Response(serializer.data, status=HTTPStatus.CREATED)
        
        elif request.method == 'DELETE':
            deleted, _ = model_class.objects.filter(
                user=request.user, recipe=recipe
            ).delete()
            
            if not deleted:
                return Response(
                    {'errors': success_message},
                    status=HTTPStatus.BAD_REQUEST
                )
            
            return Response(status=HTTPStatus.NO_CONTENT)
    
    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        return self._handle_recipe_action(
            request=request,
            recipe=recipe,
            model_class=Favorite,
            error_message='Рецепт уже добавлен в избранное.',
            success_message='Рецепт не найден в избранном.'
        )
    
    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        return self._handle_recipe_action(
            request=request,
            recipe=recipe,
            model_class=ShoppingCart,
            error_message='Рецепт уже добавлен в список покупок.',
            success_message='Рецепт не найден в списке покупок.'
        )
    
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
