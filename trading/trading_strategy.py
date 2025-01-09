# import math
import pandas as pd
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
    - 50MA, 200MA로 시장 상황 판단 [상승장(50MA > 200MA), 하락장(50MA < 200MA)]
    - 분할 매수/매도 하지 않고, 전 금액(KRW)로 매수하고 매도 시에도 한번에 전체를 매도합니다.
    - 매매는 10분(5/15/25/35/45/55) 간격으로 판단 (단, 매도는 매분 타이밍을 확인합니다.)
    - RSI, MACD, 볼린저밴드, 거래량 지표를 활용
    - 골든 크로스 / 데드 크로스 상황에 따라 매수/매도 처리
    - 손절매 조건 (1.69420% 손실)

    ## 상승장 전략
    - 매수는 이전 캔들이 볼린저밴드 하단 아래로 내려가고 최종 캔들이 양봉인 경우 진행
    - 매도는 RSI가 한번이라도 72을 넘어서고, MACD가 하향 교차되는 경우 진행

    ## 하락장 전략
    - 매수는 RSI가 25 이하로 쌍바닥이 나오고 MACD 히스토그램이 양전환. 상승장과 다르게 최근 100번의 데이터를 확인
      (50MA 기울기가 양수로 한번이라도 전환되기 전까지는 매수 금지)
    - 매도는 이전 캔들(종가 기준)이 볼린저밴드 상단을 돌파하고 거래량이 20일 이동평균을 초과하는 경우

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

    # 최소 200개 데이터 필요 (MA200 계산을 위해)
    if len(df) < 200:
        print('데이터가 부족합니다 (최소 200개 필요).')
        return {
            "signal": "",
            "message": ""
        }

    # 이동평균선 계산
    df['MA50'] = df['close'].rolling(window=50).mean()
    df['MA200'] = df['close'].rolling(window=200).mean()

    # 50MA 기울기 계산
    df['MA50_slope'] = df['MA50'].diff()  # diff() 함수를 사용하여 기울기 계산

    # 골든 크로스 / 데드 크로스 확인
    golden_cross = (df['MA50'].iloc[-2] < df['MA200'].iloc[-2]) and (df['MA50'].iloc[-1] > df['MA200'].iloc[-1])
    dead_cross = (df['MA50'].iloc[-2] > df['MA200'].iloc[-2]) and (df['MA50'].iloc[-1] < df['MA200'].iloc[-1])

    # 시장 상황 판단 (50MA와 200MA 비교)
    is_bull_market = df['MA50'].iloc[-1] > df['MA200'].iloc[-1]

    print(f'is_bull_market : {is_bull_market}')

    # RSI 계산
    rsi_indicator = RSIIndicator(df['close'], window=14)
    df['RSI'] = rsi_indicator.rsi()

    # MACD 계산
    macd = MACD(df['close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_histogram'] = macd.macd_diff()

    # 볼린저 밴드 계산
    bollinger = BollingerBands(df['close'])
    df['BB_upper'] = bollinger.bollinger_hband()
    df['BB_lower'] = bollinger.bollinger_lband()

    # 매수 가능
    if position == 0:
        # 50MA가 200MA보다 작은 구간의 DataFrame 추출
        under_50ma_df = df[df['MA50'] < df['MA200']].tail(100)  # 최근 100개만 확인

        # 해당 구간에서 50MA 기울기가 0보다 큰 적이 있는지 확인
        ma50_slope_positive_after_dead_cross = (under_50ma_df['MA50_slope'] > 0).any()

        # 데드 크로스 발생 후 50MA 기울기가 양수로 한번이라도 전환되기 전까지는 매수 금지
        if not is_bull_market and not ma50_slope_positive_after_dead_cross:
            print('데드 크로스 발생 후 50MA 기울기가 양수로 한번이라도 전환되기 전까지 매수 대기')
            return {
                "signal": "",
                "message": ""
            }

        # 골든 크로스 발생 시 매수
        if golden_cross:
            print('buy_signal - 골든 크로스 발생!')
            return {
                "signal": "buy",
                "message": "골든 크로스 발생"
            }
        elif is_bull_market:
            # 상승장 매수 조건
            recent_df: pd.DataFrame = df.tail(25)

            # 이전 캔들이 볼린저 밴드 하단 아래로 내려갔는지 확인
            prev_candle_below_bb = recent_df['close'].iloc[-2] <= recent_df['BB_lower'].iloc[-2]

            # 최종 캔들이 양봉인지 확인
            current_candle_is_positive = recent_df['close'].iloc[-1] >= recent_df['open'].iloc[-1]

            buy_condition = prev_candle_below_bb and current_candle_is_positive
        else:
            # 하락장 매수 조건
            recent_df_100: pd.DataFrame = df.tail(100)
            rsi_series = recent_df_100['RSI']
            rsi_valleys = []

            # RSI 저점 찾기
            for i in range(1, len(rsi_series) - 1):
                if (rsi_series.iloc[i] <= 25 and
                        rsi_series.iloc[i] < rsi_series.iloc[i - 1] and
                        rsi_series.iloc[i] < rsi_series.iloc[i + 1]):
                    rsi_valleys.append(i)

            # RSI 쌍바닥 확인
            has_double_bottom = len(rsi_valleys) >= 2

            # MACD 히스토그램 양전환 확인
            macd_turned_positive = (
                    recent_df_100['MACD_histogram'].iloc[-1] > recent_df_100['MACD_histogram'].iloc[-2] and
                    recent_df_100['MACD_histogram'].iloc[-1] > 0 > recent_df_100['MACD_histogram'].iloc[-2]
            )

            print(f'len(rsi_valleys) : {len(rsi_valleys)}')
            print(f'has_double_bottom : {has_double_bottom}')
            print(f'macd_turned_positive : {macd_turned_positive}')

            buy_condition = has_double_bottom and macd_turned_positive

        if buy_condition:
            print(f'buy_signal!! ({"상승장" if is_bull_market else "하락장"})')
            return {
                "signal": "buy",
                "message": f"{'상승장' if is_bull_market else '하락장'} 매수 조건에 부합"
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

        # 데드 크로스 발생 시 매도
        if dead_cross:
            print('sell_signal - 데드 크로스 발생!')
            return {
                "signal": "sell",
                "message": "데드 크로스 발생"
            }

        # 손절매 조건 (1.69420% 손실)
        current_price = df['close'].iloc[-1]
        if current_price < buy_price * 0.983058:
            print('sell_signal - 손절매!!')
            return {
                "signal": "sell",
                "message": "손절매!!"
            }

        # 20일 거래량 이동평균 계산 추가
        df['Volume_MA20'] = df['volume'].rolling(window=20).mean()

        # 'datetime' 데이터 만들기
        df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        buy_datetime = pd.to_datetime(buy_time)

        after_buy_df = df[df['datetime'] > buy_datetime]

        print(f'len(after_buy_df) : {len(after_buy_df)}')

        # 최소 2개의 캔들이 있어야 인덱싱 가능
        if len(after_buy_df) >= 2:
            if is_bull_market:
                # 상승장 매도 조건: RSI 72 초과 후 MACD 하향 교차
                rsi_above_72 = (after_buy_df['RSI'] > 72).any()

                # MACD 하향 교차 검증
                macd_cross_down = (
                        after_buy_df['MACD'].iloc[-1] < after_buy_df['MACD_signal'].iloc[-1] and
                        after_buy_df['MACD'].iloc[-2] >= after_buy_df['MACD_signal'].iloc[-2]
                )

                print(f'rsi_above_72 : {rsi_above_72}')
                print(f'macd_cross_down : {macd_cross_down}')

                if rsi_above_72 and macd_cross_down:
                    print('sell_signal - [상승장] RSI > 72 once and MACD cross down')
                    return {
                        "signal": "sell",
                        "message": "[상승장] RSI > 72 once and MACD cross down"
                    }
            else:
                # 하락장 매도 조건 (거래량 + 볼린저 밴드 상단 돌파)
                prev_candle = after_buy_df.iloc[-2]

                print(f'prev_candle["close"] : {prev_candle["close"]}')
                print(f'prev_candle["BB_upper"] : {prev_candle["BB_upper"]}')
                print(f'prev_candle["volume"] : {prev_candle["volume"]}')
                print(f'prev_candle["Volume_MA20"] : {prev_candle["Volume_MA20"]}')

                # 이전 캔들 기준으로 계산
                # 이전 캔들의 종가가 볼린저밴드 상단을 돌파 and 거래량이 20일 이동평균을 초과
                if (prev_candle['close'] >= prev_candle['BB_upper'] and
                        prev_candle['volume'] > prev_candle['Volume_MA20']):
                    print('sell_signal - [하락장] 이전 캔들이 볼린저 밴드 상단 돌파 및 거래량 증가')
                    return {
                        "signal": "sell",
                        "message": "[하락장] 이전 캔들이 볼린저 밴드 상단 돌파 및 거래량 증가"
                    }

    return {
        "signal": "",
        "message": ""
    }
