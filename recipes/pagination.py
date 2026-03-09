from rest_framework.pagination import PageNumberPagination


class RecipePagination(PageNumberPagination):
    """Погинация для рецептов"""

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class SmallPagination(PageNumberPagination):
    """Малая пагинация"""

    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 50
