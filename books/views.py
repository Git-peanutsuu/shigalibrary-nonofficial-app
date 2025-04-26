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

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache

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
    """ISBNから書籍の画像URLを取得（Google Books APIを使用）-->URLを返す"""
    # キャッシュキーを作成（例: "book_image_9784315523539"）
    cache_key = f"book_image_{isbn}"
    
    # キャッシュから取得を試みる
    cached_image = cache.get(cache_key)
    if cached_image is not None:
        return cached_image

    # Google Books APIのエンドポイント
    api_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    # APIキーが設定されている場合に追加（settings.pyにGOOGLE_BOOKS_API_KEYが必要）
    if hasattr(settings, 'GOOGLE_BOOKS_API_KEY'):
        api_url += f"&key={settings.GOOGLE_BOOKS_API_KEY}"
    try:
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()

        # 画像URLを抽出
        if 'items' in data and data['items']:
            volume_info = data['items'][0]['volumeInfo']
            image_url = volume_info.get('imageLinks', {}).get('thumbnail')
            if image_url:
                # HTTPSに変換（Google Books APIはHTTPで返す場合がある）
                image_url = image_url.replace("http://", "https://")
                # キャッシュに保存（保存期間: 1日）
                cache.set(cache_key, image_url, timeout=86400)
                return image_url
        return None
    except RequestException as e:
        logger.error(f'Google Books APIエラー: {str(e)} in get_book_image()')
        return None
    except (KeyError, IndexError) as e:
        logger.error(f'データ解析エラー: {str(e)} in get_book_image()')
        return None
    except Exception as e:
        logger.error(f'予期せぬエラー: {str(e)} in get_book_image()')
        return None
    
def paginate_items(request, items, per_page):
    """
    リストをページネーションする汎用関数。
    Args:
        request: HTTPリクエスト（ページ番号を取得するため）
        items: ページネーション対象のリスト
        per_page: 1ページあたりの表示数
    Returns:
        page_obj: 現在のページデータ（PaginatorのPageオブジェクト）
    When:
        HOMEとserach_book内で記述
    """
    paginator = Paginator(items, per_page)
    page = request.GET.get('page', 1)
    
    # 全角数字を半角数字に変換
    if isinstance(page, str):
        # 全角数字（１２３）を半角数字(123)に変換
        zen_to_han = str.maketrans('１２３４５６７８９０', '1234567890')
        page = page.translate(zen_to_han)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        # ページ番号が整数でない場合、1ページ目を返す
        page_obj = paginator.page(1)
    except EmptyPage:
        # ページ番号が範囲外の場合、最後のページを返す
        page_obj = paginator.page(paginator.num_pages)
    return page_obj
   
def home(request):
    if not request.user.is_authenticated:
        return render(request, 'books/index.html', {'message': 'ログインして,本を管理してみませんか'})
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

            # 並び順（新しい順/古い順）
            sort = request.GET.get('sort', 'oldest')  # デフォルトは古い順
            if sort == 'oldest':
                books = books.order_by('id')  # 古い順（id昇順）
            else:
                books = books.order_by('-id')  # 新しい順（id降順）

            book_list = []
            for book in books:
                image_link = get_book_image(book.isbn_id)
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

            # ページネーション（1ページあたり15件）
            page_obj = paginate_items(request, book_list, per_page=15)
            context = {
                "page_obj": page_obj,  # テンプレートでページ情報を利用
                "current_status": status,
                'sort': sort,
            }
            return render(request, "books/home.html", context)
        except UserBook.DoesNotExist:
            logger.error("UserBookが見つかりません。")
            return render(request, "books/home.html", {
                "error": "本が見つかりませんでした。検索して新しい本を追加してみてください。"
            })
        except RequestException as e:
            logger.error(f"外部APIエラー: {str(e)}")
            return render(request, "books/home.html", {
                "error": "外部サービスとの通信に失敗しました。ページを再読み込みしてください。問題が続く場合は、管理者（example@support.com）までご連絡ください。"
            })
        except Exception as e:
            logger.error(f"予期しないエラー: {str(e)}")
            return render(request, "books/home.html", {
                "error": "予期しないエラーが発生しました。ページを再読み込みしてください。問題が続く場合は、管理者（example@support.com）までご連絡ください。"
            })

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

def judge_search(request):#from home.html and search_book.html
    query = request.GET.get('query', '')
    source = request.GET.get('source', 'google')  # デフォルトはGoogle

    if source == 'rakuten':
        return search_by_rakuten(request, query)
    return search_by_google(request, query)

def search_by_google(request, query):
    query = request.GET.get('query', '')
    source = request.GET.get('source', 'google')  # デフォルトはGoogle
    if not query:
        context = {
            'error_message': '検索キーワードを入力してください。',
        }
        return render(request, 'books/google_search_result.html', context)
    # ページ番号からstartIndexを計算（1ページ15件）
    page = request.GET.get('page', '1')
    try:
        page_num = int(page)
    except ValueError:
        page_num = 1
    items_per_page = 15
    start_index = (page_num - 1) * items_per_page  # 例: 2ページ目ならstartIndex=15

    # Google Books APIで検索（現在のページの15件のみ取得）
    books = []
    total_items = 0
    try:
        google_url = f"https://www.googleapis.com/books/v1/volumes?q={query}&startIndex={start_index}&maxResults={items_per_page}"
        if hasattr(settings, 'GOOGLE_BOOKS_API_KEY'):
            google_url += f"&key={settings.GOOGLE_BOOKS_API_KEY}"
        response = requests.get(google_url, timeout=5)
        response.raise_for_status()
        google_data = response.json()
        total_items = min(google_data.get('totalItems', 0), 1000)  # 取得可能な最大件数に制限
        logger.info(f'Google Books APIデータ取得：{google_data.get("totalItems")}')
        items = google_data.get('items', [])
        
        for item in items:
            volume_info = item.get('volumeInfo', {})
            isbn = None
            identifiers = volume_info.get('industryIdentifiers', [])
            for identifier in identifiers:
                if identifier.get('type') == 'ISBN_13':
                    isbn = identifier.get('identifier')
                    break
                elif identifier.get('type') == 'OTHER':
                    logger.info(f"ISBNなし、PKEY発見: PKEY:{identifier.get('identifier')} for title {volume_info.get('title')}")
            
            books.append({
                'title': volume_info.get('title', 'N/A'),
                'author': ', '.join(volume_info.get('authors', ['N/A'])),
                'isbn': isbn,
                'image_link': get_book_image(isbn) if isbn else None,
                'calil_link': f"https://calil.jp/book/{isbn}/search?nearby=滋賀県立図書館" if isbn else None,
            })
    except RequestException as e:
        logger.error(f'Google Books APIエラー: {str(e)}')
        books = []

    # ISBNがある本だけ先に抽出（カーリルAPIの処理を最適化）
    books_with_isbn = [book for book in books if book['isbn'] is not None]
    calil_data = {}
    if books_with_isbn:
        try:
            isbns = [b['isbn'] for b in books_with_isbn]
            calil_url = f"https://api.calil.jp/check?appkey={settings.CALIL_APPLICATION_KEY}&systemid=Shiga_Pref&isbn={','.join(isbns)}&format=json"
            calil_response = requests.get(calil_url, timeout=5)
            calil_response.raise_for_status()
            response_text = calil_response.text
            if response_text.startswith('callback('):
                response_text = response_text[9:-2]
            calil_data = json.loads(response_text).get('books', {})
        except RequestException as e:
            logger.info(f"カーリルエラー: {str(e)}")
        except ValueError as e:
            logger.info(f"カーリルJSONパースエラー: {str(e)}")

    # ユーザーの本リストとステータスを反映
    if request.user.is_authenticated:
        user_books = set(UserBook.objects.filter(user=request.user).values_list('isbn_id', flat=True))
        def get_book_status(isbn):
            return UserBook.objects.filter(user=request.user, isbn_id=isbn).first()
    else:
        user_books = set()
        def get_book_status(isbn):
            return None

    processed_books = [
        {
            'title': book['title'],
            'author': book['author'],
            'isbn': book['isbn'] if book['isbn'] else 'N/A',
            'image_link': book['image_link'],
            'availability': calil_data.get(book['isbn'], {}).get('Shiga_Pref', {}) if book['isbn'] else {},
            'calil_link': book['calil_link'] if book['isbn'] else None,
            'is_added': book['isbn'] in user_books,
            'status': get_book_status(book['isbn'])
        }
        for book in books if book['isbn'] is not None
    ]

    # 取得できなかった件数を計算
    fetched_books_count = len(books)  # Google Books APIで取得した件数
    displayed_books_count = len(processed_books)  # 表示している件数（ISBNあり）
    not_displayed_count = fetched_books_count - displayed_books_count  # 取得できなかった件数

    # ページネーション情報（カスタム）
    total_pages = (total_items + items_per_page - 1) // items_per_page  # 総ページ数を計算
    has_next = start_index + items_per_page < total_items  # 次のページがあるか
    has_previous = page_num > 1  # 前のページがあるか

    # 前後3件のページ番号を計算
    page_range = range(max(1, page_num - 3), min(total_pages + 1, page_num + 4))

    context = {
        'books': processed_books,
        'query': query,
        'total_items': total_items,
        'page_num': page_num,
        'total_pages': total_pages,
        'has_next': has_next,
        'has_previous': has_previous,
        'page_range': page_range,
        'not_displayed_count': not_displayed_count,  # 取得できなかった件数
    }
    return render(request, 'books/google_search_result.html', context)

def search_by_rakuten(request, query):
    if not query:
        context = {
            'error_message': '検索キーワードを入力してください。',
        }
        return render(request, 'books/rakuten_search_result.html', context)

    page = request.GET.get('page', '1')
    try:
        page_num = int(page)
    except ValueError:
        page_num = 1
    items_per_page = 15
    
    books = []
    total_items = 0
    try:
        rakuten_url = (
            f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
            f"?applicationId={settings.RAKUTEN_APPLICATION_ID}"
            f"&title={query}"
            f"&page={page_num}"
            f"&hits={items_per_page}"
            f"&format=json"
        )
        response = requests.get(rakuten_url, timeout=5)
        response.raise_for_status()
        rakuten_data = response.json()
        total_items = min(rakuten_data.get('count', 0), 1000)
        items = rakuten_data.get('Items', [])
        
        for item in items:
            book_info = item.get('Item', {})
            isbn = book_info.get('isbn')
            books.append({
                'title': book_info.get('title', 'N/A'),
                'author': book_info.get('author', 'N/A'),
                'isbn': isbn,
                'image_link': book_info.get('mediumImageUrl'),
                'calil_link': f"https://calil.jp/book/{isbn}/search?nearby=滋賀県立図書館" if isbn else None,
            })
    except RequestException as e:
        logger.error(f'楽天APIエラー: {str(e)}')
        books = []

    books_with_isbn = [book for book in books if book['isbn'] is not None]
    calil_data = {}
    if books_with_isbn:
        try:
            isbns = [b['isbn'] for b in books_with_isbn]
            calil_url = f"https://api.calil.jp/check?appkey={settings.CALIL_APPLICATION_KEY}&systemid=Shiga_Pref&isbn={','.join(isbns)}&format=json"
            calil_response = requests.get(calil_url, timeout=5)
            calil_response.raise_for_status()
            response_text = calil_response.text
            if response_text.startswith('callback('):
                response_text = response_text[9:-2]
            calil_data = json.loads(response_text).get('books', {})
        except RequestException as e:
            logger.info(f"カーリルエラー: {str(e)}")
        except ValueError as e:
            logger.info(f"カーリルJSONパースエラー: {str(e)}")

    if request.user.is_authenticated:
        user_books = set(UserBook.objects.filter(user=request.user).values_list('isbn_id', flat=True))
        def get_book_status(isbn):
            return UserBook.objects.filter(user=request.user, isbn_id=isbn).first()
    else:
        user_books = set()
        def get_book_status(isbn):
            return None

    processed_books = [
        {
            'title': book['title'],
            'author': book['author'],
            'isbn': book['isbn'] if book['isbn'] else 'N/A',
            'image_link': book['image_link'],
            'availability': calil_data.get(book['isbn'], {}).get('Shiga_Pref', {}) if book['isbn'] else {},
            'calil_link': book['calil_link'] if book['isbn'] else None,
            'is_added': book['isbn'] in user_books,
            'status': get_book_status(book['isbn'])
        }
        for book in books if book['isbn'] is not None
    ]

    fetched_books_count = len(books)
    displayed_books_count = len(processed_books)
    not_displayed_count = fetched_books_count - displayed_books_count

    total_pages = (total_items + items_per_page - 1) // items_per_page
    has_next = page_num < total_pages
    has_previous = page_num > 1
    page_range = range(max(1, page_num - 3), min(total_pages + 1, page_num + 4))

    context = {
        'books': processed_books,
        'query': query,
        'total_items': total_items,
        'page_num': page_num,
        'total_pages': total_pages,
        'has_next': has_next,
        'has_previous': has_previous,
        'page_range': page_range,
        'not_displayed_count': not_displayed_count,
        'source': 'rakuten',
    }
    return render(request, 'books/rakuten_search_result.html', context)
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
# @login_required(login_url='/login/')
# def example_url(request):


# TODO:共有機能　API実装: Django REST Framework
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from .models import UserBook
# @api_view(['GET'])
# def share_books(request):
#     books = UserBook.objects.filter(user__line_id=request.session['line_id'])
#     data = [{'title': b.title, 'author': b.author, 'isbn_id': b.isbn_id} for b in books]
#     return Response(data)