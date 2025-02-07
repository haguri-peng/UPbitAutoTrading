import pandas as pd
import numpy as np
from typing import Optional
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands


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
    - 최근 캔들 중에서 볼린저밴드 하단 아래로 내려간 적이 있고, 5EMA 기울기가 양(+)으로 전환할 때 매소
    - 손절매는 0.5% 손실 시 진행
    - 매수 이후에 10EMA가 20EMA에 하향 교차하는 경우 매도

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

    # 이동평균선 계산
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['MA200'] = df['close'].rolling(window=200).mean()

    # # 시장 상황 판단 (20MA와 200MA 비교)
    # is_bull_market = df['MA20'].iloc[-2] > df['MA200'].iloc[-2]

    # EMA 계산
    df['EMA5'] = df['close'].ewm(span=5, adjust=False).mean()
    df['EMA10'] = df['close'].ewm(span=10, adjust=False).mean()
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()

    # 200MA 기울기 계산
    df['MA200_slope'] = df['MA200'].diff()  # diff() 함수를 사용하여 기울기 계산

    is_positive_200ma_slope = df['MA200_slope'].iloc[-2] > 0

    # RSI 계산
    rsi_indicator = RSIIndicator(df['close'], window=14)
    df['RSI'] = rsi_indicator.rsi()

    # MACD 계산
    macd = MACD(df['close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_histogram'] = macd.macd_diff()

    # 볼린저밴드 계산
    bollinger = BollingerBands(df['close'])
    df['BB_upper'] = bollinger.bollinger_hband()
    df['BB_mid'] = bollinger.bollinger_mavg()
    df['BB_lower'] = bollinger.bollinger_lband()

    # 볼린저밴드 영역 계산
    df['BB_range'] = df['BB_upper'] - df['BB_lower']

    # 양봉 캔들의 크기가 볼린저밴드 영역의 절반을 넘는지 확인
    df['candle_size'] = df['close'] - df['open']
    df['is_big_bull'] = (df['candle_size'] > df['BB_range'] / 2) & (df['close'] > df['open'])

    # 20일 거래량 이동평균 계산
    df['Volume_MA20'] = df['volume'].rolling(window=20).mean()

    # 최근 20개의 DataFrame 추출
    recent_df: pd.DataFrame = df.tail(20)

    # 20MA 기울기 계산
    diffs = recent_df['MA20'].diff()

    # 기울기가 음(-)인 경우와 양(+)인 경우 개수 세기
    negative_cnt = np.sum(np.where(diffs < 0, 1, 0))
    positive_cnt = np.sum(np.where(diffs > 0, 1, 0))

    is_positive_20ma_slope = positive_cnt > negative_cnt

    # 결과 출력
    print('[20MA, 200MA 기울기 확인]')
    print(f'음(-)인 기울기 개수 : {negative_cnt}')
    print(f'양(+)인 기울기 개수 : {positive_cnt}')
    print(f'is_positive_20ma_slope : {is_positive_20ma_slope}')
    print(f'is_positive_200ma_slope : {is_positive_200ma_slope}')

    # EMA 기울기 계산
    df['EMA5_slope'] = df['EMA5'].diff()
    df['EMA10_slope'] = df['EMA10'].diff()
    df['EMA20_slope'] = df['EMA20'].diff()

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

        print('[EMA 값 확인]')
        print(f"5EMA : {df['EMA5'].iloc[-2]}")
        print(f"10EMA : {df['EMA10'].iloc[-2]}")
        print(f"20EMA : {df['EMA20'].iloc[-2]}")

        # 최근 20개의 캔들(종가 기준) 중에서 볼린저밴드 하단 아래로 내려갔는지 확인
        recent_candle_below_bb = (recent_df['close'][:-1] < recent_df['BB_lower'][:-1]).any()

        # EMA 기울기가 양(+)으로 모두 바뀌었는지 확인
        is_positive_all_ema_slope = (
                df['EMA5_slope'].iloc[-2] > 0 and
                df['EMA10_slope'].iloc[-2] > 0 and
                df['EMA20_slope'].iloc[-2] > 0
        )

        # RSI 30 미만 확인
        rsi_under_30 = (recent_df['RSI'] < 30).any()

        print(f'recent_candle_below_bb : {recent_candle_below_bb}')
        print(f'is_positive_all_ema_slope : {is_positive_all_ema_slope}')
        print(f'rsi_under_30 : {rsi_under_30}')

        if recent_candle_below_bb and is_positive_all_ema_slope:
            if is_positive_200ma_slope:
                buy_condition = True
                buy_msg = '[상승장] 최근 캔들 중에서 볼린저밴드 하단 아래로 내려간 적이 있고, 10EMA 기울기가 양(+)으로 전환'
            else:
                if rsi_under_30:
                    buy_condition = True
                    buy_msg = '[하락장] 최근 캔들 중에서 볼린저밴드 하단 아래로 내려간 적이 있고, 10EMA 기울기가 양(+)으로 전환'

        if not buy_condition:
            # 최근 캔들이 큰 양봉인지 확인
            is_big_bull_candle = recent_df['is_big_bull'].iloc[-2]

            # 거래량이 20일 거래량 이동평균을 넘어서는지 확인
            is_over_20ma_vol = recent_df['volume'].iloc[-2] > recent_df['Volume_MA20'].iloc[-2]

            print(f'is_big_bull_candle : {is_big_bull_candle}')
            print(f'is_over_20ma_vol : {is_over_20ma_vol}')

            if is_big_bull_candle and is_over_20ma_vol:
                buy_condition = True
                buy_msg = '볼린저밴드 반을 넘는 거대한 양봉이고 거래량도 20일 평균을 넘어섬'

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
            # # STOPLOSS
            # # STOPLOSS는 매수 시점 바로 이전의 최종 3개의 캔들의 시작(open)에서 최솟값
            # last3_df: pd.Series = df['open'].tail(4).iloc[:-1]
            # stop_loss_price = last3_df.min()
            # current_price = df['close'].iloc[-1]
            #
            # print(f'stop_loss_price : {stop_loss_price}')
            # print(f'current_price : {current_price}')
            #
            # if current_price < stop_loss_price:
            #     print('sell_signal - STOPLOSS')
            #     return {
            #         "signal": "sell",
            #         "message": "STOPLOSS"
            #     }

            current_price = df['close'].iloc[-2]

            print(f'current_price : {current_price}')

            # 손절매 조건 (0.6942% 손실)
            if current_price < buy_price * 0.993058:
                print('sell_signal - 손절매!!')
                return {
                    "signal": "sell",
                    "message": "손절매(0.6942% 손실)!!"
                }

            # 이전 캔들의 EMA가 정배열(5, 10, 20이 순서대로)인지 확인
            is_bef_ema_ordered = (
                    df['EMA5'].iloc[-3] > df['EMA10'].iloc[-3] > df['EMA20'].iloc[-3]
            )

            print(f'is_bef_ema_ordered : {is_bef_ema_ordered}')

            # 5EMA가 10EMA에 하향 교차
            if (len(after_buy_df) >= 3 and
                    is_bef_ema_ordered and
                    df['EMA5'].iloc[-2] < df['EMA10'].iloc[-2]):
                print('sell_signal - 5EMA가 10EMA에 하향 교차')
                return {
                    "signal": "sell",
                    "message": "5EMA가 10EMA에 하향 교차"
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
