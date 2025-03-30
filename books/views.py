from django.shortcuts import render
# Create your views here.
import requests

from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings
# Djangoのプラクティスで、settings.pyをインポートする
from .models import User
import logging

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
    print(f"Profile: {profile}")  # ターミナル確認
    try:
        user, created = User.objects.get_or_create(
            line_id=profile['userId'],
            defaults={'name': profile['displayName']}
        )
        print(f"User saved: {user}, Created: {created}")#ログ出力
        # ログイン処理（仮に名前表示）
        return HttpResponse(f"ようこそ、{user.name}さん！")
    except Exception as e:
        return HttpResponse(f"エラー: {e}", status=400)