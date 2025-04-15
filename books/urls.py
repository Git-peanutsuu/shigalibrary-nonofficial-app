from django.urls import path
from . import views

# homeが定義されていないということなので修正した。しかし、サイトに飛ぶといきなり、ログインをしなくとも、本('Untitle'に設定した本が表示されている。）ルーティングのおかしさはおいておいて、本がユーザーに関係なく、みれるようになっている気がする。
# 修正した。
urlpatterns = [
    path('list/', views.book_list, name='book_list'),
    path('', views.home, name='home'),
    path('add/', views.add_book, name='add_book'),# ここだけだとエラー htmlもないし、views.pyもない
    path('scan/', views.display_scan_page, name='display_scan_page'),
    path('extract-isbn/', views.extract_isbn, name='extract_isbn'),
    path('search-book/', views.search_book_by_isbn, name='search_book_by_isbn'),
    path('search/', views.search_book, name='search_book'),
    path('update/<str:isbn>/', views.update_book_status, name='update_book_status'),
    path('delete/<str:isbn>/', views.delete_book, name='delete_book'),
    path('example_url/',views.example_url, name = 'example_url'),
    # path('search_book_with_google/',views.search_book_with_google, name ='search_book_with_google')
    # path('demo_search_book/', views.demo_search_book, name = 'demo_search_book'),

]