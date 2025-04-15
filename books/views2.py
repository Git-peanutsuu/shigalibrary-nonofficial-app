# Create your views here.
import requests
import logging
# from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from django.http import HttpResponse
from django.conf import settings
# Djangoのプラクティスで、settings.pyをインポートする
# from .models import User
# from .models import UserBook

# システムIDをリストするAPIがあれば、以下のようにリクエストを送ります
list_url = "https://api.calil.jp/librarysystemlist?appkey={settings.CALIL_APPLICATION_KEY}&systemid=Shiga_Pref&isbn=4798044857"
response = requests.get(list_url)

# レスポンスを解析
library_systems = response.json()

# 取得したシステムIDを表示
print(library_systems)


# def search_book(request):
    # query = request.GET.get('query', '')
    # if not query:
    #     context = {
    #         'error_message': '検索キーワードを入力してください。',
    #     }
    #     return render(request, 'books/search_book.html', context)
    # try:
    #     # 楽天ブックスAPIに変更
    #     api_url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?applicationId={settings.RAKUTEN_APPLICATION_ID}&hits=15&title={query}"
    #     response = requests.get(api_url)
    #     response.raise_for_status()
    #     books = response.json().get('Items', [])
    #     print(books[5] if len(books) > 5 else books)  # デバッグ用
    #     if not books:
    #         context = {
    #             'error_message': '検索結果が見つかりませんでした。',
    #             'query': query,
    #         }
    #         return render(request, 'books/search_book.html', context)
    #     context = {
    #         'books': [
    #             {
    #                 'title': b['Item'].get('title', 'N/A'),
    #                 'author': b['Item'].get('author', 'N/A'),
    #                 'isbn': b['Item'].get('isbn', 'N/A'),  # 楽天はISBNを直接返す
    #                 'image_link': b['Item'].get('largeImageUrl', '').replace('http://', 'https://'),
    #             } for b in books
    #         ],
    #         'query': query,
    #     }
    #     return render(request, 'books/search_book.html', context)
    # except requests.exceptions.RequestException as e:
    #     context = {
    #         'error_message': '楽天ブックスとの接続に問題が発生しました。再度お試しください。',
    #         'query': query,
    #     }
    #     return render(request, 'books/search_book.html', context)
    # except ValueError:
    #     context = {
    #         'error_message': '検索結果の取得に失敗しました。再度お試しください。',
    #         'query': query,
    #     }
    #     return render(request, 'books/search_book.html', context)
# 楽天＋図書館
    # def search_book(request):
    # query = request.GET.get('query', '')
    
    # # 検索キーワードがない場合
    # if not query:
    #     context = {
    #         'error_message': '検索キーワードを入力してください。',
    #     }
    #     return render(request, 'books/search_book.html', context)
    
    # try:
    #     # 楽天APIのURL作成
    #     api_url = f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404?applicationId={settings.RAKUTEN_APPLICATION_ID}&hits=15&title={query}"
    #     response = requests.get(api_url)
    #     response.raise_for_status()
        
    #     # 楽天APIレスポンスの取得
    #     books = response.json().get('Items', [])
    #     # print(books[0] if books else "No books found")  # デバッグ用
        
    #     # 検索結果がない場合
    #     if not books:
    #         context = {
    #             'error_message': '検索結果が見つかりませんでした。',
    #             'query': query,
    #         }
    #         return render(request, 'books/search_book.html', context)
        
    #     # 本の情報を整形
    #     books_info = [
    #         {
    #             'title': b['Item'].get('title', 'N/A'),
    #             'author': b['Item'].get('author', 'N/A'),
    #             'isbn': b['Item'].get('isbn', 'N/A'),
    #             'image_link': b['Item'].get('largeImageUrl', '').replace('http://', 'https://'),
    #         } for b in books
    #     ]
        
    #     # 各本のISBNを使って、Calil APIで蔵書確認を行う
    #     for book in books_info:
    #         isbn = book['isbn']
    #         print(f"Processing book: {book}")
            
    #         if isbn != 'N/A':  # ISBNがある場合にのみ確認
    #             # Calil APIのURLを作成
    #             calil_api_url = f"https://api.calil.jp/check?appkey={settings.CALIL_APPLICATION_KEY}&systemid=Shiga_Pref&isbn={isbn}"
                
    #             try:
    #                 # Calil APIにリクエスト
    #                 calil_response = requests.get(calil_api_url)
    #                 calil_response.raise_for_status()  # レスポンスのエラーがあれば例外を発生させる
                    
    #                 # Calil APIレスポンスのデータを確認
    #                 print(f"Raw API Response: {calil_response.text}")  # 生のレスポンスを表示
                    
    #                 # レスポンスが空か確認
    #                 if not calil_response.text:
    #                     print(f"Error: No response received for ISBN {isbn}")
    #                     book['availability'] = 'APIレスポンスなし'
    #                     continue
                    
    #                 # Calil APIレスポンスをJSON形式で解析
    #                 calil_data = calil_response.json()
    #                 print(f"Calil API Response: {calil_data}")  # デバッグ用
                    
    #                 # hits が 1 以上なら蔵書あり
    #                 if calil_data.get('hits', 0) > 0:
    #                     # Shiga_Pref の情報を確認
    #                     book_info = calil_data.get('books', {}).get(isbn, {}).get('Shiga_Pref', {})
    #                     status = book_info.get('status', '')
                        
    #                     # "OK"なら正常、"Running"は処理中
    #                     if status == 'OK':
    #                         # libkey の情報を使って貸出状況を設定
    #                         libkey = book_info.get('libkey', {})
                            
    #                         # 図書館ごとの貸出状況を確認
    #                         availability = []
    #                         for library, status in libkey.items():
    #                             if status == "貸出可":
    #                                 availability.append(f"{library} 貸出可")
    #                             elif status == "貸出中":
    #                                 availability.append(f"{library} 貸出中")
    #                             elif status == "館内のみ":
    #                                 availability.append(f"{library} 館内のみ")
                            
    #                         # availabilityがあれば設定
    #                         if availability:
    #                             book['availability'] = ', '.join(availability)
    #                         else:
    #                             book['availability'] = '蔵書なし'
    #                     elif status == 'Running':
    #                         book['availability'] = '処理中'  # 処理中の場合
    #                     else:
    #                         book['availability'] = '利用不可'  # 他の状態は利用不可
    #                 else:
    #                     book['availability'] = '利用不可'  # hitsが0なら利用不可
    #             except requests.exceptions.RequestException as e:
    #                 print(f"Error with API request for ISBN {isbn}: {e}")
    #                 book['availability'] = 'API接続エラー'  # APIの接続エラーが発生した場合
    #             except ValueError as e:
    #                 print(f"Error processing response for ISBN {isbn}: {e}")
    #                 book['availability'] = 'APIレスポンスエラー'  # レスポンスの形式に問題があった場合
    #         else:
    #             book['availability'] = 'ISBNなし'  # ISBNがない場合

    #     print('after processing:', books_info)  # デバッグ用


    #     # 検索結果と状態をcontextに設定
    #     context = {
    #         'books': books_info,
    #         'query': query,
    #     }

    #     return render(request, 'books/search_book.html', context)

    # except requests.exceptions.RequestException as e:
    #     context = {
    #         'error_message': '楽天ブックスとの接続に問題が発生しました。再度お試しください。',
    #         'query': query,
    #     }
    #     return render(request, 'books/search_book.html', context)

    # except ValueError:
    #     context = {
    #         'error_message': '検索結果の取得に失敗しました。再度お試しください。',
    #         'query': query,
    #     }
    #     return render(request, 'books/search_book.html', context)


# #
def search_book_with_google(request):
    # Example book title to search for
    search_query = "Python"  # You can dynamically change this based on user input
    google_book_api = f"https://www.googleapis.com/books/v1/volumes?q={search_query}"

    try:
        response = requests.get(google_book_api)
        print(f"Status Code: {response.status_code}")
        print(f"Response Content (first 500 chars): {response.text[750:1500]}")
        if response.status_code == 200:
            books_data = response.json()

            # Extract relevant book details from the API response
            books_info = [
                        {
                            'title': item_info.get('title', 'N/A'),
                            'authors': item_info.get('authors', ['N/A']),
                            'publisher': item_info.get('publisher', 'N/A'),
                            'published_date': item_info.get('publishedDate', 'N/A'),
                            'description': item_info.get('description', 'No description available.'),
                            'image_link': item_info.get('imageLinks', {}).get('thumbnail', ''),
                        }
                        for item in books_data.get('items', [])
                        if (item_info := item.get('volumeInfo'))  # Using assignment expression (walrus operator)
                    ]


            return render(request, 'books/search_book_with_google.html', {'books_info': books_info})

        else:
            return render(request, 'books/search_book_with_google.html', {'error': f'API request failed with status {response.status_code}'})

    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return render(request, 'books/search_book_with_google.html', {'error': 'API request error'})


@login_required(login_url='line_login')
# TODO:change func to add specific library list via CALIL to avoid too many Google API use.
def demo_search_book(request):
    # library_system_id = 'Shiga_Pref' 
    # open_url = (
    #     f"https://api.calil.jp/check?appkey={settings.CALIL_APPLICATION_KEY}&systemid={library_system_id}"
    #     )
    book_title = "疲労"
    from urllib.parse import quote
    encoded_title = quote(book_title) # URL-encode the book title
    open_url = f"https://api.calil.jp/openurl?rft.btitle={encoded_title}"
    open_url = 'https://api.calil.jp/openurl?rft.isbn=4103534222'
# open_url = 'https://api.calil.jp/openurl?rft.isbn=4103534222'
 
    try:
        response = requests.get(open_url)
        print(f"Status Code: {response.status_code}")
        print(f"{response.headers['Content-type']}")
        if response.status_code == 200:
            if 'text/html' in response.headers['Content-Type']:
                # soup = BeautifulSoup(response.text, 'html.parser')
                # books_data  = soup.find_all('div', id='result')
                print(f'Received HTML response instead of JSON.')
                # return render(request, 
                #                   'books/demo_search_book.html', 
                #                   {'books': response.text}
                #                   )
                return HttpResponse(response.text)
            else:
                return render(request, 
                                'books/demo_search_book.html', 
                                {'books': response.text}
                                )
        else:
            return render(request, 
                          'books/demo_search_book.html', 
                          {'error': f'API request failed with status {response.status_code}'}
                          )
    except requests.exceptions.RequestException as e:
        # If there's an exception (e.g., network error), handle it here
        print(f"Error during API request: {e}")
        return render(request, 'books/demo_search_book.html', {'error': 'API request error'})


# @login_required(login_url='/login/')
# def scan_barcode(request):
# エラー連発のためやめた
# # かなり読み取りができず、
#     if request.method == 'POST':
#         isbn = request.POST.get('isbn')
#         if not isbn or not isbn.isdigit() or len(isbn) != 13:
#             return JsonResponse({"status": "error", "message": "バーコードが正しく読み取れませんでした。もう一度お試しください。"})

#         # 楽天APIで検索
#         url = "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
#         params = {
#             "applicationId": settings.RAKUTEN_APPLICATION_ID,
#             "isbn": isbn,
#             "format": "json"
#         }
#         try:
#             response = requests.get(url, params=params, timeout=5)
#             response.raise_for_status()  # 4xx, 5xxエラーで例外
#             data = response.json()
#         except RequestException as e:
#             logger.error(f'楽天APIエラー: {str(e)}')
#             return JsonResponse({"status": "error", "message": f"楽天APIへの接続に失敗しました: {str(e)}。ネットワークを確認してください。"})

#         if not data.get("Items"):
#             return JsonResponse({"status": "error", "message": "このISBNの本は見つかりませんでした。別の本を試してください。"})
#         logger.info(f'楽天APIデータ取得：{data}')
#         book = data["Items"][0]["Item"]

#         # カーリルAPIで蔵書チェック
#         calil_url = "http://api.calil.jp/check"
#         calil_params = {
#             "appkey": settings.CALIL_APPLICATION_KEY,
#             "isbn": isbn,
#             "systemid": "Shiga_Pref",
#             "format": "json",
#             "callback": ""
#         }
#         try:
#             calil_response = requests.get(calil_url, params=calil_params, timeout=5)
#             calil_response.raise_for_status()
#             # レスポンス内容をログに出力
#             logger.info(f'カーリルAPIレスポンス: {calil_response.text}')
#             # レスポンスが空か確認
#             if not calil_response.text.strip():
#                 logger.info(f'カーリルAPIレスポンスのパースエラー: {str(json_err)}')                
#                 raise ValueError("カーリルAPIから空のレスポンスが返されました")
#             try:
#                 calil_data = calil_response.json()
#             except json.JSONDecodeError as json_err:
#                 logger.error(f'カーリルAPIレスポンスのパースエラー: {str(json_err)}')
#                 raise ValueError(f"カーリルAPIレスポンスが不正な形式です: {calil_response.text}")
#         except RequestException as e:
#             calil_data = {}  # カーリル失敗でも楽天の結果は使える
#             logger.error(f'カーリルAPIエラー: {str(e)}')
#             error_message = f"図書館情報の取得に失敗しました: {str(e)}"

#         context = {
#             "book": {
#                 "title": book.get("title", "N/A"),
#                 "author": book.get("author", "N/A"),
#                 "isbn": isbn,
#                 "image_link": book.get("largeImageUrl", "").replace("http://", "https://"),
#                 "availability": calil_data.get("books", {}).get(isbn, {}).get("Shiga_Pref", {}),
#                 "calil_link": f"https://calil.jp/book/{isbn}/search?nearby=滋賀県立図書館",
#                 "is_added": UserBook.objects.filter(user=request.user, isbn_id=isbn).exists(),
#                 "status": UserBook.objects.filter(user=request.user, isbn_id=isbn).first(),
#             },
#             "error_message": locals().get("error_message", "")
#         }
#         if "error_message" in locals():
#             context["error_message"] = error_message
#         return render(request, "books/scan_result.html", context)
#     logger.info('NOT POST METHOD')
#     return render(request, "books/scan_indexpage.html")
#確認用
# def example_url(request):#if you use it as test, access to example_url/
#     library_system_id = 'Shiga_Pref' 
#     open_url = (
#         f"https://api.calil.jp/check?appkey={settings.CALIL_APPLICATION_KEY}&systemid={library_system_id}"
#         )
#     response = request.get(open_url)
#     return render(request, 'books/example_url.html',request)
