# Create your views here.
import requests
from requests.exceptions import RequestException

import logging
import json
# from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from django.db import IntegrityError

from django.http import HttpResponse
from django.http import JsonResponse
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
        logger.error("認証エラー: codeがありません")
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
    token_data = response.json()

    if "access_token" not in token_data or "id_token" not in token_data:
        logger.error(f"トークン取得失敗: {token_data}")
        return HttpResponse("トークン取得失敗", status=400)
    

    # IDトークン検証
    verify_url = "https://api.line.me/oauth2/v2.1/verify"
    verify_data = {
        "id_token": token_data["id_token"],
        "client_id": settings.LINE_CHANNEL_ID,
    }
    verify_response = requests.post(verify_url, data=verify_data)
    if verify_response.status_code != 200:
        logger.error(f'IDトークン検証失敗{verify_response.json()}')
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
        logger.info(f"User saved: {user}, Created: {created}")

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

def get_book_image(isbn):
    """ISBNから書籍の画像URLを取得（楽天APIを使用）book_list()でused"""
    url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
    params = {
        "applicationId": settings.RAKUTEN_APPLICATION_ID,
        "isbn": isbn,
        "format": "json"
    }
    # 9784896329537
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("Items"):
            book = data["Items"][0]["Item"]
            print(book.get("mediumImageUrl", ""))
            return book.get("mediumImageUrl", "")
        return None
    except RequestException as e:
        logger.error(f'楽天APIエラー: {str(e)} in get_book_image()')
        return None
    except (KeyError, IndexError) as e:
        logger.error(f'データ解析エラー: {str(e)}in get_book_image()')
        return None
    except Exception as e:
        logger.error(f'予期せぬエラー: {str(e)}in get_book_image()')
        return None
def home(request):
    if request.user.is_authenticated:
        # Fetch books associated with the logged-in user
        # TODO:著者だけでなく、いろんなことも標示されている。
        user_books = UserBook.objects.filter(user=request.user, is_reading=True).exclude(isbn_id__isnull=True)
        context = {
            'message': "ログイン中です。",
            'user': request.user,  # Userオブジェクト
            'books': user_books,  # UserBookのリスト
        }
        return render(request, 'books/home.html', context)
    else:
        return render(request, 'books/index.html', {'message': "ログインしてください"})

@login_required(login_url='line_login')
    # TODO:画像表示
def book_list(request):
    # user = User.objects.get(line_id=request.user)
    try:
        status = request.GET.get('status', 'all')
        books = UserBook.objects.filter(user=request.user).exclude(isbn_id__isnull=True)
        if status == 'want':
            books = books.filter(is_want_to_read=True)
        elif status == 'reading':
            books = books.filter(is_reading=True)
        elif status == 'read':
            books = books.filter(is_read=True)
        book_list = []
        for book in books:
            image_link = get_book_image(book.isbn_id)
            print('image_link ->>',image_link)
            book_list.append({
                'title': book.title,
                'author': book.author,
                'isbn_id': book.isbn_id,
                'is_want_to_read': book.is_want_to_read,
                'is_reading': book.is_reading,
                'is_read': book.is_read,
                'is_added': True,
                'image_link': image_link if image_link else '',
                'calil_link': f"https://calil.jp/book/{book.isbn_id}/search?nearby=滋賀県立図書館",
            })
        context = {"books": book_list, "current_status": status}
        return render(request, "books/book_list.html", context)
    except Exception as e:
        logger.error(f"Error in book_list: {str(e)}")
        return render(request, "books/book_list.html", {"error": "本の取得に失敗しました。"})
@login_required(login_url='line_login')
def add_book(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '404-Sorry!-Page-Not-Found'})
    # EXPLAIN: POSTメソッドでフォームから送信されるが、JSがpreventDefault（）で横取り
    # fetch() が /add/（= Djangoの add_book()）へPOSTリクエスト送信 title, author, isbn_id, status
    # add_book()でデータベースにisbn_idの有無を確認 json reuturnで -> JSの.then(response => response.json()) で受け取る
    # 受け取ったstatusをbasedonで分岐
    isbn_id = request.POST.get('isbn_id')
    if UserBook.objects.filter(user=request.user, isbn_id=isbn_id).exists():
        return JsonResponse({'status': 'exists'})
    try:
        user_book = UserBook.objects.create(
            user=request.user,
            title=request.POST.get('title'),
            author=request.POST.get('author'),
            isbn_id=isbn_id,
            # 初期ステータスを1つだけ設定
            is_want_to_read=(request.POST.get('status') == 'want'),
            is_reading=(request.POST.get('status') == 'reading'),
            is_read=(request.POST.get('status') == 'read')
        )
        return JsonResponse({'status': 'added', 'isbn': isbn_id, 'current_status': request.POST.get('status')})
    except IntegrityError:
        # unique 制約に反した場合のエラー処理
        logger.error(f"IntegrityError: {isbn_id} already exists for user {request.user}")
        return JsonResponse({'status': 'exists', 'message': 'この本は既に追加されています'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required(login_url='/login/')
def update_book_status(request, isbn):  # isbn_id → isbn
    if request.method == 'POST':
        try:
            user_book = UserBook.objects.get(user=request.user, isbn_id=isbn)  # isbn_idはモデルのフィールド名なのでOK
        except UserBook.DoesNotExist:
            return JsonResponse({"status": "error", "message": "指定された本が見つかりません"}, status=404)

        status = request.POST.get('status')
        if status not in ['want', 'reading', 'read']:
            return JsonResponse({"status": "error", "message": "無効なステータスです"}, status=400)

        # すべてのブールフィールドをFalseにリセット
        user_book.is_want_to_read = False
        user_book.is_reading = False
        user_book.is_read = False
        # 選択されたステータスに応じて対応するフィールドをTrueに
        if status == 'want':
            user_book.is_want_to_read = True
        elif status == 'reading':
            user_book.is_reading = True
        elif status == 'read':
            user_book.is_read = True
        user_book.save()
        return JsonResponse({"status": "updated", "isbn": isbn, "current_status": status})
    return JsonResponse({"status": "error", "message": "無効なリクエストです"}, status=400)

@login_required(login_url='/login/')
def delete_book(request, isbn):
    if request.method == 'POST':
        try:
            user_book = UserBook.objects.get(user=request.user, isbn_id=isbn)#.first()は最初の1件のオブジェクト（または存在しなければ Noneどっちでも
            user_book.delete()
            return JsonResponse({"status": "deleted"})
        except UserBook.DoesNotExist:
            return JsonResponse({"status": "error", "message": "指定された本が見つかりません"}, status=404)
    return JsonResponse({"status": "error", "message": "無効なリクエストです"}, status=400)

def search_book(request):
    query = request.GET.get('query', '')
    if not query:
        context = {
            'error_message': '検索キーワードを入力してください。',
        }
        return render(request, 'books/search_book.html', context)
    
    # 楽天ブックスAPI
    try:
        api_url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?applicationId={settings.RAKUTEN_APPLICATION_ID}&hits=15&title={query}"
        response = requests.get(api_url)
        response.raise_for_status()
        books = response.json().get('Items', [])
        # logger.info(books[5] if len(books) > 5 else books)  # デバッグ用
        if not books:
            context = {
                'error_message': '楽天ブックスで検索結果が見つかりませんでした。',
                'query': query,
            }
            return render(request, 'books/search_book.html', context)
    except requests.exceptions.RequestException as e:
        context = {
            'error_message': f'楽天ブックスとの接続に問題が発生しました: {str(e)}',
            'query': query,
        }
        return render(request, 'books/search_book.html', context)

    # カーリルAPI
    try:
        isbns = [b['Item'].get('isbn', 'N/A') for b in books if b['Item'].get('isbn') != 'N/A']
        if not isbns:
            calil_data = {}
        else:
            calil_url = f"https://api.calil.jp/check?appkey={settings.CALIL_APPLICATION_KEY}&systemid=Shiga_Pref&isbn={','.join(isbns)}&format=json"
            calil_response = requests.get(calil_url)
            calil_response.raise_for_status()
            # JSONP対策: callback(...)を剥がしてJSONに
            response_text = calil_response.text
            if response_text.startswith('callback('):
                response_text = response_text[9:-2]  # 'callback('と');'を削除
            calil_data = json.loads(response_text).get('books', {})
            logger.info("カーリルデータ:", calil_data)  # デバッグ用
    except requests.exceptions.RequestException as e:
        calil_data = {}
        logger.info(f"カーリルエラー: {str(e)}")
    except ValueError as e:
        calil_data = {}
        logger.info(f"カーリルJSONパースエラー: {str(e)}")

    # Login true ->追加を下かどうかを確認, not true -> 空のまま表示
    if request.user.is_authenticated:
        user_books = set(UserBook.objects.filter(user=request.user).values_list('isbn_id', flat=True))
    else:
        user_books = set()
    # TODO:後悔,,,モデルにそもそもstatusとかを＿
    context = {
    'books': [
        {
            'title': b['Item'].get('title', 'N/A'),
            'author': b['Item'].get('author', 'N/A'),
            'isbn': b['Item'].get('isbn', 'N/A'),
            'image_link': b['Item'].get('largeImageUrl', '').replace('http://', 'https://'),
            'availability': calil_data.get(b['Item'].get('isbn', 'N/A'), {}).get('Shiga_Pref', {}),
            'calil_link': f"https://calil.jp/book/{b['Item'].get('isbn', 'N/A')}/search?nearby=滋賀県立図書館",
            'is_added': b['Item'].get('isbn', 'N/A') in user_books,
            'status': UserBook.objects.filter(user=request.user, isbn_id=b['Item'].get('isbn', 'N/A')).first()  # firstで一意に
        } for b in books if b['Item'].get('isbn') != 'N/A'
    ],
    'query': query,
    }
    for book in context['books']:
        logger.info(f"Book: {book['title']}, Is Added: {book['is_added']}")

    return render(request, 'books/search_book.html', context)
# ----------
# ---scan---
@login_required(login_url='/login/')
def display_scan_page(request):
    if request.method == 'GET':
        return render(request, "books/scan_indexpage.html")
    return redirect('display_scan_page')

@login_required(login_url='/login/')
def extract_isbn(request):
    if request.method == 'POST':
        barcode_data = request.POST.get('barcode')
        # 仮のバーコード処理（実際はJavaScriptでバーコードを読み取る）
        # ここではbarcode_dataがISBNそのものと仮定
        isbn = barcode_data
        if not isbn or not isbn.isdigit() or len(isbn) != 13:
            return JsonResponse({"status": "error", "message": "バーコードが正しく読み取れませんでした。もう一度お試しください。"}, status=400)
        return JsonResponse({"status": "success", "isbn": isbn})
    return redirect('display_scan_page')

@login_required(login_url='/login/')
def search_book_by_isbn(request):
    if request.method == 'POST':
        isbn = request.POST.get('isbn')
        if not isbn or not isbn.isdigit() or len(isbn) != 13:
            context = {"error_message": "バーコードが正しく読み取れませんでした。もう一度お試しください。"}
            return render(request, "books/scan_result.html", context)

        # 楽天APIで検索
        url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
        params = {
            "applicationId": settings.RAKUTEN_APPLICATION_ID,
            "isbn": isbn,
            "format": "json"
        }
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
        except RequestException as e:
            logger.error(f'楽天APIエラー: {str(e)}')
            context = {"error_message": f"楽天APIへの接続に失敗しました: {str(e)}。ネットワークを確認してください。"}
            return render(request, "books/scan_result.html", context)

        if not data.get("Items"):
            context = {"error_message": "このISBNの本は見つかりませんでした。別の本を試してください。"}
            return render(request, "books/scan_result.html", context)

        book = data["Items"][0]["Item"]
        logger.info(f'楽天APIデータ取得：{book}')

        # カーリルAPIで蔵書チェック
        calil_url = "http://api.calil.jp/check"
        calil_params = {
            "appkey": settings.CALIL_APPLICATION_KEY,
            "isbn": isbn,
            "systemid": "Shiga_Pref",
            "format": "json",
            "callback": ""  # JSONP形式を無効化
        }
        try:
            logger.info(f'カーリルAPIリクエスト: {calil_params}')
            calil_response = requests.get(calil_url, params=calil_params, timeout=5)
            calil_response.raise_for_status()
            logger.info(f'カーリルAPIレスポンス: {calil_response.text}')
            if not calil_response.text.strip():
                raise ValueError("カーリルAPIから空のレスポンスが返されました")

            # JSONP形式のレスポンスを処理
            logger.info(json.loads(calil_response.text[1:-2]).get('books', {}))
            # calil_data = calil_response.json()変な文が代入されているため、はがす
            calil_data = json.loads(calil_response.text[1:-2])#textなのでjsonで辞書に変換, 余計なもの'();'をはがす。
            # ー＞{"session": "123djdjioj", "continue": 0, "books": {"9784315523539": {"Shiga_Pref": {"status": "Cache", "libkey": {"図書館": "貸出中"}, "reserveurl": "https://www.shiga-pref-library.jp/wo/opc_srh/srh_detail/4779008"}}}}
            # 後にavailabilityに代入し、bookだけを取得
        except (RequestException, ValueError, json.JSONDecodeError) as e:
            logger.error(f'カーリルAPIエラー: {str(e)}')
            calil_data = {}
            error_message = f"図書館情報の取得に失敗しました: {str(e)}"

        context = {
            "book": {
                "title": book.get("title", "N/A"),
                "author": book.get("author", "N/A"),
                "isbn": isbn,
                "image_link": book.get("largeImageUrl", "").replace("http://", "https://"),
                "availability": calil_data.get("books", {}).get(isbn, {}).get("Shiga_Pref", {}),
                "calil_link": f"https://calil.jp/book/{isbn}/search?nearby=滋賀県立図書館",
                "is_added": UserBook.objects.filter(user=request.user, isbn_id=isbn).exists(),
                "status": UserBook.objects.filter(user=request.user, isbn_id=isbn).first()
            },
            "error_message": locals().get("error_message", "")
        }
        return render(request, "books/scan_result.html", context)
    return redirect('display_scan_page')
@login_required(login_url='/login/')
def example_url(request):
    if not request.user.is_authenticated:
        return render(request, 'books/index.html',{'message':'あなたはまだログインしていません。'})
    else:
        try:
            status = request.GET.get('status', 'all')
            books = UserBook.objects.filter(user=request.user).exclude(isbn_id__isnull=True)
            if status == 'want':
                books = books.filter(is_want_to_read=True)
            elif status == 'reading':
                books = books.filter(is_reading=True)
            elif status == 'read':
                books = books.filter(is_read=True)
            book_list = []
            for book in books:
                image_link = get_book_image(book.isbn_id)
                print('image_link ->>',image_link)
                book_list.append({
                    'title': book.title,
                    'author': book.author,
                    'isbn_id': book.isbn_id,
                    'is_want_to_read': book.is_want_to_read,
                    'is_reading': book.is_reading,
                    'is_read': book.is_read,
                    'is_added': True,
                    'image_link': image_link if image_link else '',
                    'calil_link': f"https://calil.jp/book/{book.isbn_id}/search?nearby=滋賀県立図書館",
                })
            context = {"books": book_list, "current_status": status}
            return render(request, "books/example_url.html", context)
        except Exception as e:
            logger.error(f"Error in book_list: {str(e)}")
            return render(request, "books/example_url.html", {"error": "本の取得に失敗しました。"})

# TODO:共有機能　API実装: Django REST Framework
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from .models import UserBook
# @api_view(['GET'])
# def share_books(request):
#     books = UserBook.objects.filter(user__line_id=request.session['line_id'])
#     data = [{'title': b.title, 'author': b.author, 'isbn_id': b.isbn_id} for b in books]
#     return Response(data)