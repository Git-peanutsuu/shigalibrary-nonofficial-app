from django.contrib import admin
from .models import User, Book, UserBook

admin.site.register(User)
admin.site.register(Book)
admin.site.register(UserBook)