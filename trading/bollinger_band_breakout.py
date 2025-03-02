import pandas as pd
from ta.volatility import BollingerBands


def trading_strategy(
        df: pd.DataFrame,
        position: int,
) -> dict:
    """
    코인 트레이딩 전략 함수 - Bollinger Band Breakout

    Args:
        df (pd.DataFrame): 가격 데이터프레임
        position (int): 현재 포지션 (0: 매수 가능, 1: 매도 가능)

    Returns:
        str: 트레이딩 액션 ('buy', 'sell', '')

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
            "bull_market": "",
            "message": ""
        }

    # # 이동평균선 계산
    # df['MA20'] = df['close'].rolling(window=20).mean()
    # df['MA50'] = df['close'].rolling(window=50).mean()
    #
    # # 20MA 기울기 계산
    # df['MA20_slope'] = df['MA20'].diff()  # diff() 함수를 사용하여 기울기 계산

    # EMA 계산
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()

    # 시장 상황 판단 (50EMA와 200EMA 비교)
    is_bull_market = df['EMA50'].iloc[-1] > df['EMA200'].iloc[-1]

    print(f'is_bull_market : {is_bull_market}')

    # 볼린저밴드 계산
    bollinger = BollingerBands(df['close'])
    df['BB_upper'] = bollinger.bollinger_hband()
    df['BB_mid'] = bollinger.bollinger_mavg()
    df['BB_lower'] = bollinger.bollinger_lband()

    # 최근 20개의 DataFrame 추출
    recent_df: pd.DataFrame = df.tail(20)

    # 이전 캔들이 볼린저밴드 하단을 돌파한 음봉(-)인지 확인
    bb_lower_breakout = (
            recent_df['open'].iloc[-2] > recent_df['close'].iloc[-2] and
            recent_df['close'].iloc[-2] < recent_df['BB_lower'].iloc[-2]
    )

    print(f'position : {position}')
    print(f'bb_lower_breakout : {bb_lower_breakout}')

    # 매수 가능
    if position == 0 and bb_lower_breakout:
        # 현재 캔들이 양봉이면 매수
        is_recent_positive_candle = recent_df['open'].iloc[-1] < recent_df['close'].iloc[-1]

        if is_recent_positive_candle:
            buy_msg = '이전 캔들이 볼린저밴드 하단을 돌파한 음봉이고, 현재 캔들이 양봉'

            print(f'buy_signal! - {buy_msg}')
            return {
                "signal": "buy",
                "bull_market": is_bull_market,
                "message": f"매수 조건에 부합 - {buy_msg}"
            }

    # 매도 가능
    elif position == 1:
        # 이전 캔들이 볼린저밴드 상단을 돌파한 양봉(+)인지 확인
        bb_upper_breakout = (
                recent_df['open'].iloc[-2] < recent_df['close'].iloc[-2] and
                recent_df['close'].iloc[-2] > recent_df['BB_upper'].iloc[-2]
        )

        print(f'bb_upper_breakout : {bb_upper_breakout}')

        if bb_upper_breakout:
            sell_msg = '이전 캔들이 볼린저밴드 상단을 돌파한 양봉'

            print(f'buy_signal! - {sell_msg}')
            return {
                "signal": "sell",
                "bull_market": is_bull_market,
                "message": f"매도 조건에 부합 - {sell_msg}"
            }

    return {
        "signal": "",
        "bull_market": is_bull_market,
        "message": ""
    }
