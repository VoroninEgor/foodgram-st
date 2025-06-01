from rest_framework.pagination import PageNumberPagination

from .constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class CustomPageNumberPagination(PageNumberPagination):
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = MAX_PAGE_SIZE 