# Create your views here.
import requests
import logging
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from django.http import HttpResponse
from django.conf import settings
# Djangoのプラクティスで、settings.pyをインポートする
from .models import User
from .models import UserBook

# ロガーの設定
logger = logging.getLogger('books')

def line_login(request):
        # デバッグ情報を追加
    logger.info("LINE認証URLにリダイレクト開始")
    
    # LINE認証URLにリダイレクト
    auth_url = (
        "https://access.line.me/oauth2/v2.1/authorize?"
        f"response_type=code&client_id={settings.LINE_CHANNEL_ID}&"
        f"redirect_uri={settings.LINE_REDIRECT_URI}&state=12345&scope=profile%20openid&ui_locales=ja"
    )
    # TODO:stateをランダムに生成
    
    return redirect(auth_url)

@login_required(login_url='line_login')
def logout_view(request):
    # セッションをリセット（削除）
    logout(request)
    return redirect('home')

def line_callback(request):
    # LINE認証コールバック ライン側でcodeを取得をしている
    code = request.GET.get('code')
    if not code:
        return HttpResponse("認証エラー: codeがありません", status=400)

    # アクセストークン取得
    token_url = "https://api.line.me/oauth2/v2.1/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.LINE_REDIRECT_URI,
        "client_id": settings.LINE_CHANNEL_ID,
        "client_secret": settings.LINE_CHANNEL_SECRET,
    }
    response = requests.post(token_url, data=data)
        # レスポンスの詳細をログに出力
    print(f"LINE APIレスポンス: {response.status_code}")
    # print(f"レスポンス内容: {response.text}")
    token_data = response.json()

    if "access_token" not in token_data or "id_token" not in token_data:
        return HttpResponse("トークン取得失敗", status=400)
    

    # IDトークン検証
    verify_url = "https://api.line.me/oauth2/v2.1/verify"
    verify_data = {
        "id_token": token_data["id_token"],
        "client_id": settings.LINE_CHANNEL_ID,
    }
    verify_response = requests.post(verify_url, data=verify_data)
    if verify_response.status_code != 200:
        return HttpResponse(f"IDトークン検証失敗: {verify_response.json()}", status=400)
    
    
    # プロフィール取得
    profile_url = "https://api.line.me/v2/profile"
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    profile = requests.get(profile_url, headers=headers).json()

    # Model
    # print(f"Profile: {profile}")  ターミナル確認
    try:
        user, created = User.objects.get_or_create(
            line_id=profile['userId'],
            defaults={'name': profile['displayName']}
        )
        print(f"User saved: {user}, Created: {created}")

        if created:
            user.set_unusable_password()  # パスワード不要に
            user.save()
        # ログイン処理（仮に名前表示）
        # return HttpResponse(f"ようこそ、{user.name}さん！")
        from django.contrib.auth import login
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')  # バックエンド指定
        return redirect('home')
    except Exception as e:
        return HttpResponse(f"エラー: {e}", status=400)

def home(request):
    if request.user.is_authenticated:
        # Fetch books associated with the logged-in user
        print('LOG IN 200')
        user_books = UserBook.objects.filter(user=request.user)
        user = UserBook.objects.filter(user=request.user)
        context = {
            'message': "ログイン中です。",
            'user': request.user,  # Userオブジェクト
            'books': user_books,  # UserBookのリスト
        }
        return render(request, 'books/home.html', context)
    else:
        return render(request, 'books/index.html', {'message': "ログインしてください"})

@login_required(login_url='line_login')
def book_list(request):
    # user = User.objects.get(line_id=request.user.line_id)
    books = UserBook.objects.filter(user=request.user)
    # ERROR:might happen
    print(books)
    return render(request, 'books/book_list.html', {'books': books})

@login_required(login_url='line_login')
def add_book(request):
    if request.method == 'POST':
        title = request.POST['title']
        author = request.POST['author']
        isbn_id = request.POST.get('isbn_id', '')
        status = request.POST['status']
        user_book = UserBook.objects.create(
                user=request.user, 
                title=title,
                author=author,
                isbn_id=isbn_id
            )
        if status == 'want':
            user_book.is_want_to_read = True
        elif status == 'read':
            user_book.is_read = True
        elif status == 'reading':
            user_book.is_reading = True
        user_book.save()
        return redirect('book_list')
    return render(request, 'books/add_book.html')

@login_required(login_url='line_login')
def update_book_status(request, isbn_id):
    #   CHECK:isbn_idでいいのか
    if request.method == 'POST':
        book = get_object_or_404(UserBook, id=isbn_id, user=request.user.line_id)
        
        # Update status based on form data
        book.is_read = bool(request.POST.get('is_read', False))
        book.is_reading = bool(request.POST.get('is_reading', False))
        book.is_want_to_read = bool(request.POST.get('is_want_to_read', False))
        
        book.save()
        return redirect('book_list')
@login_required(login_url='line_login')
def delete_book(request, isbn_id):
    book = get_object_or_404(UserBook, id=isbn_id, user=request.user.line_id)
    book.delete()
    return redirect('book_list')
# TODO:共有機能　API実装: Django REST Framework
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from .models import UserBook
# @api_view(['GET'])
# def share_books(request):
#     books = UserBook.objects.filter(user__line_id=request.session['line_id'])
#     data = [{'title': b.title, 'author': b.author, 'isbn_id': b.isbn_id} for b in books]
#     return Response(data)

# 関数renderにおける辞書の意味はとは何？
# path('', views.home, name='home'),のnameの意味は？
# なぜ    if 'line_id' not in request.session:
#         return redirect('line_login')
#     user = User.objects.get(line_id=request.session['line_id'])
#     books = Book.objects.all()でline_idを参照することができるのか？Pythonは関数ごとにスコープ範囲が決められていますよね？
# TODO:本の表示だけはしたい。つまり、本の登録をすべてやるのではなく、本を検索したりして、登録する際に絶対に必要だと思う。
# 問題はあります。違う観点で話すため一度置いておきます。
# 借りるというのは私が想定しているのは、登録した本が他のユーザーによって借りられなくする図書館システムではありません。私の目的は「図書館の非公式サブアプリ」を作ることであり、借りている本や読みたい本を、検索または自動で画像検索、登録し、本の記録をすることです。そのため、借りるというのは「借りられている本を表示