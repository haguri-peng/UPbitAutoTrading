import requests
import pandas as pd

headers = {"Accept": "application/json"}

"""
# 캔들 정보 조회 [분(Minutes) 기준]
URL: https://docs.upbit.com/reference/%EB%B6%84minute-%EC%BA%94%EB%93%A4-1

[GET] https://api.upbit.com/v1/candles/minutes/{unit}

## Path params
- unit: 분 단위 가능한 값: 1, 3, 5, 15, 10, 30, 60, 240)

## Request
- market: 조회할 시장 정보 (ex. 'KRW-BTC')
- to: 마지막 캔들 시각. 기본적으로 UTC 기준 시간이며, '2024-12-03T00:00:00+09:00' 과 같이 KST 시간으로 요청 가능
      비워서 요청한 경우 가장 최근 캔들 
- count: 캔들 개수 (최대 200개까지 가능)

## Response - 최신순으로 출력
- market: 종목코드
- candle_date_time_utc: 캔들 기준 시각 (UTC 기준). Format: yyyy-MM-dd'T'HH:mm:ss
- candle_date_time_kst: 캔들 기준 시각 (KST 기준). Format: yyyy-MM-dd'T'HH:mm:ss
- opening_price: 시가
- high_price: 고가
- low_price: 저가
- trade_price: 종가
- timestamp: 해당 캔들에서 마지막 틱이 저장된 시각
- candle_acc_trade_price: 누적 거래 금액
- candle_acc_trade_volume: 누적 거래량
- unit: 분 단위(유닛)
"""


# 분 기준 캔들정보 가져오기
def get_min_candle_data(market: str, minute: int):
    candle_min_url = f'https://api.upbit.com/v1/candles/minutes/{minute}'

    # 모든 캔들정보를 여기에 담는다.
    candle_all_data = None
    last_time = None

    # 5번 호출하여 1,000개의 데이터를 만든다.
    # 한번 호출 시, {minute}분 간격으로 200개씩 데이터를 가져온다.
    # 이 데이터는 {minute} X 200
    for i in range(5):
        if i == 0:
            candle_min_params = {
                "market": market,
                "count": 200
            }
        else:
            candle_min_params = {
                "market": market,
                "to": last_time,
                "count": 200
            }
        candle_min_data = pd.DataFrame(
            requests.get(candle_min_url, params=candle_min_params, headers=headers).json())

        if candle_min_data.empty or len(candle_min_data) == 0:
            raise ValueError('캔들정보가 비어 있습니다.')

        candle_min_data['date'] = candle_min_data.candle_date_time_kst.str.split('T').str[0]
        candle_min_data['time'] = candle_min_data.candle_date_time_kst.str.split('T').str[1]
        # candle_min_data.drop(['candle_date_time_utc', 'candle_date_time_kst', 'timestamp'], axis=1, inplace=True)

        # 라이브러리에서 활용할 수 있도록 컬럼 값 형태 변경
        candle_min_data['open'] = candle_min_data['opening_price']  # 시가
        candle_min_data['close'] = candle_min_data['trade_price']  # 종가
        candle_min_data['high'] = candle_min_data['high_price']  # 고가
        candle_min_data['low'] = candle_min_data['low_price']  # 저가
        candle_min_data['volume'] = candle_min_data['candle_acc_trade_volume']  # 거래량

        # 헷갈리지 않도록 변경 전 컬럼 값은 삭제
        candle_min_data.drop(['opening_price', 'trade_price', 'high_price', 'low_price', 'candle_acc_trade_volume'],
                             axis=1,
                             inplace=True)

        # last_time 설정
        # 순회하면서 다음 번 호출 시 파라미터의 'to'에 해당 값이 세팅됩니다.
        last_time = candle_min_data['candle_date_time_utc'].iloc[-1]

        if candle_all_data is None:
            candle_all_data = candle_min_data
        else:
            candle_all_data = pd.concat([candle_all_data, candle_min_data], ignore_index=True)

    # 데이터가 역순(최신순)이기 때문에 시간순으로 순서를 변경해야 한다.
    candle_all_data.sort_values(by='candle_date_time_kst', inplace=True)
    candle_all_data.drop_duplicates(subset=['candle_date_time_kst'], keep='last')  # 중복된 데이터 제거

    return candle_all_data
