from django.urls import path
from . import views

# homeが定義されていないということなので修正した。しかし、サイトに飛ぶといきなり、ログインをしなくとも、本('Untitle'に設定した本が表示されている。）ルーティングのおかしさはおいておいて、本がユーザーに関係なく、みれるようになっている気がする。
# 修正した。
urlpatterns = [
    path('list/', views.book_list, name='book_list'),
    path('', views.home, name='home'),
    path('add/', views.add_book, name='add_book'),
]