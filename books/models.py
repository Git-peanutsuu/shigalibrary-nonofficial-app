# books/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    line_id = models.CharField(max_length=100, unique=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    name = models.CharField(max_length=255)

    USERNAME_FIELD = 'line_id'
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

    class Meta:
        # ユーザーとISBNの組み合わせをユニークに
        unique_together = ('user', 'isbn_id')

    def save(self, *args, **kwargs):
        # ステータスが1つだけになるように制約
        statuses = [self.is_want_to_read, self.is_reading, self.is_read]
        if sum(statuses) > 1:  # 複数Trueならリセットして最新のを優先
            self.is_want_to_read = False
            self.is_read = False
            self.is_reading = False
            if 'is_read' in kwargs.get('update_fields', []):
                self.is_read = True
            elif 'is_reading' in kwargs.get('update_fields', []):
                self.is_reading = True
            elif 'is_want_to_read' in kwargs.get('update_fields', []):
                self.is_want_to_read = True
        super().save(*args, **kwargs)