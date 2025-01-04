import requests, jwt, uuid, hashlib, os
import pandas as pd
from urllib.parse import urlencode, unquote
from dotenv import load_dotenv

load_dotenv()

# Authorization
# Key: access_key, secret_key
access_key = os.getenv('ACCESS_KEY', '')
secret_key = os.getenv('SECRET_KEY', '')

"""
# 주문하기
URL: https://docs.upbit.com/reference/%EC%A3%BC%EB%AC%B8%ED%95%98%EA%B8%B0

[POST] https://api.upbit.com/v1/orders

## Request (* 항목은 필수)
- market*: 마켓 ID
- side*: 주문 종류 (bid - 매수, ask - 매도)
- volume*: 주문량 (지정가, 시장가 매도 시 필수)
- price*: 주문 가격 (지정가, 시장가 매수 시 필수)
- ord_type*: 주문 타입 [limit - 지정가주문, price - 시장가 주문(매수), market - 시장가 주문(매도), best: 최유리 주문]
- identifier: 조회용 사용자 지정값
- time_in_force: IOC, FOK 주문 설정 (ord_type이 best 혹은 limit 일 때만 지원)
                    IOC: Immediate or Cancel
                    FOK: Fill or Kill

## Response
- uuid: 주문의 고유 ID
- side: 주문 종류
- ord_type: 주문 방식
- price: 주문 당시 화폐 가격
- state: 주문 상태
- market: 마켓 ID
- created_at: 주문 생성 시간
- volume: 사용자가 입력한 주문의 양
- reserved_fee: 수수료로 예약된 비용
- remaining_fee: 남은 수수료
- paid_fee: 사용된 수수료
- locked: 거래에 사용중인 비용
- executed_volume: 체결된 양
- trades_count: 해당 주문에 걸린 체결 수
- time_in_force: IOD, FOK 설정
- identifier: 조회용 사용자 지정값
"""


def buy_market(market: str, price: int) -> pd.DataFrame:
    if not market or not price:
        raise ValueError(f'[market, price] 파라미터는 필수입니다.')

    buy_market_url = 'https://api.upbit.com/v1/orders'
    buy_market_params = {
        "market": market,
        "side": "bid",
        "ord_type": "price",  # 시장가 주문
        "price": price,
    }
    bm_query_string = unquote(urlencode(buy_market_params, doseq=True)).encode("utf-8")
    bm_hash = hashlib.sha512()
    bm_hash.update(bm_query_string)
    bm_query_hash = bm_hash.hexdigest()

    bm_payload = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
        "query_hash": bm_query_hash,
        "query_hash_alg": "SHA512"
    }

    bm_jwt_token = jwt.encode(bm_payload, secret_key)
    bm_authorization = 'Bearer {}'.format(bm_jwt_token)
    bm_headers = {
        "Authorization": bm_authorization
    }

    buy_market_order_data = pd.DataFrame.from_dict(
        requests.post(buy_market_url, json=buy_market_params, headers=bm_headers).json(), orient='index').T

    return buy_market_order_data


def sell_market(market: str, volume: str) -> pd.DataFrame:
    if not market or not volume:
        raise ValueError(f'[market, volume] 파라미터는 필수입니다.')

    sell_market_url = 'https://api.upbit.com/v1/orders'
    sell_market_params = {
        "market": market,
        "side": "ask",
        "ord_type": "market",  # 시장가 주문
        "volume": volume,
    }
    sm_query_string = unquote(urlencode(sell_market_params, doseq=True)).encode("utf-8")
    sm_hash = hashlib.sha512()
    sm_hash.update(sm_query_string)
    sm_query_hash = sm_hash.hexdigest()

    sm_payload = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
        "query_hash": sm_query_hash,
        "query_hash_alg": "SHA512"
    }

    sm_jwt_token = jwt.encode(sm_payload, secret_key)
    sm_authorization = 'Bearer {}'.format(sm_jwt_token)
    bm_headers = {
        "Authorization": sm_authorization
    }

    sell_market_order_data = pd.DataFrame.from_dict(
        requests.post(sell_market_url, json=sell_market_params, headers=bm_headers).json(), orient='index').T

    return sell_market_order_data


"""
# 체결 대기 주문 (Open Order) 조회
URL: https://docs.upbit.com/reference/%EB%8C%80%EA%B8%B0-%EC%A3%BC%EB%AC%B8-%EC%A1%B0%ED%9A%8C

[GET] https://api.upbit.com/v1/orders/open

## Request
- market: 마켓 ID
- state: 주문 상태 [wait - 체결 대기 (default), watch - 예약주문 대기]
- states[]: 주문 상태의 목록. state와 states는 동시에 사용할 수 없습니다. e.g., ['wait', 'watch']
- page: 페이지 수, default 1
- limit: 요청 개수, default 100, max 100
- order_by: 정렬 방식 [asc: 오름차순, desc: 내림차순 (default)]

## Response
- uuid: 주문의 고유 ID
- side: 주문 종류
- ord_type: 주문 방식
- price: 주문 당시 화폐 가격
- state: 주문 상태
- market: 마켓 ID
- created_at: 주문 생성 시간
- volume: 사용자가 입력한 주문의 양
- remaining_volume: 체결 후 남은 주문 양
- reserved_fee: 수수료로 예약된 비용
- remaining_fee: 남은 수수료
- paid_fee: 사용된 수수료
- locked: 거래에 사용중인 비용
- executed_volume: 체결된 양
- executed_funds: 현재까지 체결된 금액
- trades_count: 해당 주문에 걸린 체결 수
- time_in_force: IOD, FOK 설정
- identifier: 조회용 사용자 지정값
"""


def get_open_order(market: str, state: str) -> pd.DataFrame:
    if not market:
        raise ValueError(f'[market] 파라미터는 필수입니다.')

    # 기본값(wait - 체결 대기) 설정
    if not state:
        state = 'wait'

    open_order_url = 'https://api.upbit.com/v1/orders/open'
    open_order_params = {
        "market": market,
        "state": state
    }
    oo_query_string = unquote(urlencode(open_order_params, doseq=True)).encode("utf-8")
    oo_hash = hashlib.sha512()
    oo_hash.update(oo_query_string)
    oo_query_hash = oo_hash.hexdigest()

    oo_payload = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
        "query_hash": oo_query_hash,
        "query_hash_alg": "SHA512"
    }

    oo_jwt_token = jwt.encode(oo_payload, secret_key)
    oo_authorization = 'Bearer {}'.format(oo_jwt_token)
    oo_headers = {
        "Authorization": oo_authorization
    }

    open_order_data = pd.DataFrame(requests.get(open_order_url, json=open_order_params, headers=oo_headers).json())

    return open_order_data

# oo_result = get_open_order('KRW-DOGE', 'wait')
# print(oo_result)
