from django.shortcuts import render

# Create your views here.
import requests

from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings
# Djangoのプラクティスで、settings.pyをインポートする
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
        f"redirect_uri={settings.LINE_REDIRECT_URI}&state=12345&scope=profile&ui_locales=ja"
    )
    # TODO:stateをランダムに生成
    
    return redirect(auth_url)

def line_callback(request):
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
    print(f"レスポンス内容: {response.text}")
    token_data = response.json()

    if "access_token" not in token_data:
        return HttpResponse("トークン取得失敗", status=400)
    

    # プロフィール取得
    profile_url = "https://api.line.me/v2/profile"
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    profile = requests.get(profile_url, headers=headers).json()

    # ログイン処理（仮に名前表示）
    return HttpResponse(f"ようこそ、{profile['displayName']}さん！")