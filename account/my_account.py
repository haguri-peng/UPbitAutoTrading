import requests, jwt, uuid, os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

"""
# 전체 계좌 조회
URL: https://docs.upbit.com/reference/%EC%A0%84%EC%B2%B4-%EA%B3%84%EC%A2%8C-%EC%A1%B0%ED%9A%8C

[GET] https://api.upbit.com/v1/accounts

## Response
- currency: 화폐를 의미하는 영문 대문자 코드
- balance: 주문가능 금액/수량
- locked: 주문 중 묶여있는 금액/수량
- avg_buy_price: 매수평균가
- avg_buy_price_modified: 매수평균가 수정 여부
- unit_currency: 평단가 기준 화폐
"""
my_account_url = 'https://api.upbit.com/v1/accounts'

# Authorization
# Key: access_key, secret_key
access_key = os.getenv('ACCESS_KEY', '')
secret_key = os.getenv('SECRET_KEY', '')


# 내 계좌를 확인합니다.
def get_my_exchange_account():
    authorization = 'Bearer {}'.format(jwt.encode({'access_key': access_key, 'nonce': str(uuid.uuid4())}, secret_key))
    headers = {"Authorization": authorization}

    my_exchange_account = pd.DataFrame(requests.get(my_account_url, headers=headers).json())
    return my_exchange_account
