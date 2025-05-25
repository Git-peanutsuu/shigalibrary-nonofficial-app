from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('add/', views.add_book, name='add_book'),# ここだけだとエラー htmlもないし、views.pyもない
    # path('scan/', views.display_scan_page, name='display_scan_page'),
    path('extract-isbn/', views.extract_isbn, name='extract_isbn'),
    path('search-book/', views.search_book_by_isbn, name='search_book_by_isbn'),
    path('search/', views.judge_search, name='search'),
    path('update/<str:isbn>/', views.update_book_status, name='update_book_status'),
    path('delete/<str:isbn>/', views.delete_book, name='delete_book'),
    # path('example_url/',views.example_url, name = 'example_url'),

]