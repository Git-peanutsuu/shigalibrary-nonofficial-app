# 検討の末、Bookテーブル削除
# class Book(models.Model):
#     title = models.CharField(max_length=255)
#     author = models.CharField(max_length=255)
#     isbn_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
#     title_code = models.CharField(max_length=50, blank=True, null=True)
#     def __str__(self):
#         return self.title
# 高速: JOIN不要でクエリが速い。
# 個人特化: ユーザーごとの本が独立して分かりやすい。
# SEARCH:なぜJOINが不要だとクエリ画速いのか。
# books/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
class User(AbstractUser):
    line_id = models.CharField(max_length=100, unique=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)  # 必須フィールド
    name = models.CharField(max_length=255)

    USERNAME_FIELD = 'line_id'  # line_idでログイン
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.name

class UserBook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default='Untitled')
    author = models.CharField(max_length=255, blank=True)
    isbn_id = models.CharField(max_length=50, blank=True, null=True)
    is_want_to_read = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    is_reading = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.user.name} - {self.title}"