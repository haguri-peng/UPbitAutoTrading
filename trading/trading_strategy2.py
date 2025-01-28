# import math
import pandas as pd
from typing import Optional
from ta.trend import MACD


def trading_strategy(
        df: pd.DataFrame,
        position: int,
        buy_time: Optional[str] = None,
        buy_price: Optional[float] = None
) -> dict:
    """
    코인 트레이딩 전략 함수 - 시장 상황(상승장/하락장)에 따른 차별화된 전략 적용

    Args:
        df (pd.DataFrame): 가격 데이터프레임
        position (int): 현재 포지션 (0: 매수 가능, 1: 매도 가능)
        buy_time (str, optional): 매수 시간
        buy_price (float, optional): 매수 가격

    Returns:
        str: 트레이딩 액션 ('buy', 'sell', '')

    ===============================================================================================
    # 매수/매도 플랜 설명
    - EMA5가 EMA20을 상향 교차하는 경우 매수
    - STOPLOSS는 매수 시점 바로 이전의 최종 3개의 캔들의 시작(open)에서 최솟값
    - STOPLOSS를 제외하고 매수 이후에 캔들 1개 정도의 시간이 흐른 뒤 체크
    - EMA5이 EMA10에 하향 교차 시 매도

    # 계산에 사용될 df 설명
    - close: 종가
    - open: 시가
    - high: 고가
    - low: 저가
    - volume: 거래량
    """

    # DataFrame 필수 데이터 검증
    required_columns = ['close', 'date', 'time', 'volume']
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"DataFrame은 {required_columns} 컬럼을 포함해야 합니다.")

    # 최소 200개 데이터 필요
    if len(df) < 200:
        print('데이터가 부족합니다 (최소 200개 필요).')
        return {
            "signal": "",
            "message": ""
        }

    # EMA 계산
    df['EMA5'] = df['close'].ewm(span=5, adjust=False).mean()
    df['EMA10'] = df['close'].ewm(span=10, adjust=False).mean()
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()

    # EMA 기울기 계산
    df['EMA10_slope'] = df['EMA10'].diff()  # diff() 함수를 사용하여 기울기 계산

    # MACD 계산
    macd = MACD(df['close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_histogram'] = macd.macd_diff()

    # 매수 가능
    if position == 0:
        buy_condition = False
        buy_msg = ''

        # # MACD 히스토그램 양전환 확인
        # # -0.05 수치까진 허용
        # macd_turned_positive = (
        #         df['MACD_histogram'].iloc[-2] > df['MACD_histogram'].iloc[-3] and
        #         df['MACD_histogram'].iloc[-2] > -0.05
        # )

        # EMA5가 EMA20을 상향 교차
        ema_cross_up = (
                df['EMA5'].iloc[-3] < df['EMA20'].iloc[-3] and
                df['EMA5'].iloc[-2] >= df['EMA20'].iloc[-2]
        )

        # print(f'macd_turned_positive : {macd_turned_positive}')
        print(f'ema_cross_up : {ema_cross_up}')
        print(f"EMA5 : {df['EMA5'].iloc[-2]}")
        print(f"EMA20 : {df['EMA20'].iloc[-2]}")

        # if macd_turned_positive and ema_cross_up:
        if ema_cross_up:
            buy_condition = True
            buy_msg = 'EMA5가 EMA20을 상향 교차'

        if buy_condition:
            print(f'buy_signal! - {buy_msg}')
            return {
                "signal": "buy",
                "message": f"매수 조건에 부합 - {buy_msg}"
            }

    # 매도 가능
    elif position == 1:
        # 필수 입력값 검증
        if not buy_time or not buy_price:
            print('매수 시간 또는 가격 정보가 없습니다.')
            return {
                "signal": "",
                "message": ""
            }

        # 'datetime' 데이터 만들기
        df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        buy_datetime = pd.to_datetime(buy_time)

        # 매수시점 이후의 캔들만 가져오기
        after_buy_df = df[df['datetime'] >= buy_datetime]

        print(f'len(after_buy_df) : {len(after_buy_df)}')

        if len(after_buy_df) >= 2:
            # STOPLOSS
            # STOPLOSS는 매수 시점 바로 이전의 최종 3개의 캔들의 시작(open)에서 최솟값
            # stop_loss_price = after_buy_df['open'].iloc[0]
            last3_df: pd.Series = df['open'].tail(4).iloc[:-1]
            stop_loss_price = last3_df.min()
            current_price = df['close'].iloc[-1]

            print(f'stop_loss_price : {stop_loss_price}')
            print(f'current_price : {current_price}')

            if current_price < stop_loss_price:
                print('sell_signal - STOPLOSS')
                return {
                    "signal": "sell",
                    "message": "STOPLOSS"
                }

            # # 해당 구간에서 10EMA 기울기가 꺾이는지 확인
            # ema10_slope_negative = (after_buy_df['EMA10_slope'] < 0).any()
            #
            # print(f'ema10_slope_negative : {ema10_slope_negative}')
            #
            # # 매수 이후에 캔들 1개 정도의 시간이 흐른 뒤 체크
            # if len(after_buy_df) >= 3 and ema10_slope_negative:
            #     print('sell_signal - 10EMA 기울기가 음(-)으로 전환')
            #     return {
            #         "signal": "sell",
            #         "message": "10EMA 기울기가 음(-)으로 전환"
            #     }

            # EMA5이 EMA10에 하향 교차
            if len(after_buy_df) >= 3 and df['EMA5'].iloc[-1] < df['EMA10'].iloc[-1]:
                print('sell_signal - EMA5이 EMA10에 하향 교차')
                return {
                    "signal": "sell",
                    "message": "EMA5이 EMA10에 하향 교차"
                }
        else:
            print('매수 이후 데이터 부족')
            return {
                "signal": "",
                "message": "매수 이후 데이터 부족"
            }

    return {
        "signal": "",
        "message": ""
    }
