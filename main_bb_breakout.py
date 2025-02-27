import sys, os, math, time
import logging.config
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

# 현재 스크립트의 디렉토리 경로를 얻습니다.
current_dir = os.path.dirname(os.path.abspath(__file__))

# account, upbit_data, trading, utils 디렉토리의 경로를 생성
account_dir = os.path.join(current_dir, 'account')
upbit_data_dir = os.path.join(current_dir, 'upbit_data')
trading_dir = os.path.join(current_dir, 'trading')
utils_dir = os.path.join(current_dir, 'utils')

# sys.path에 디렉토리를 추가
sys.path.append(account_dir)
sys.path.append(upbit_data_dir)
sys.path.append(trading_dir)
sys.path.append(utils_dir)

# import
from account.my_account import get_my_exchange_account
from upbit_data.candle import get_min_candle_data
from trading.bollinger_band_breakout import trading_strategy
from trading.trade import buy_market, sell_market, get_open_order
from utils.email_utils import send_email

# 로그파일 경로
log_dir = os.path.join(current_dir, 'logs')

# 로그 폴더가 없으면 진행하지 않음
if not os.path.exists(log_dir):
    print('로그 폴더(/logs)가 존재하지 않습니다. 생성 후 다시 실행해주세요.')
    sys.exit(1)

logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)


def get_account_info():
    logger.info('========== get_account_info ==========')

    # get my account
    my_account = get_my_exchange_account()

    # 도지코인(DOGE) 기준으로 확인합니다.
    doge_ticker = 'DOGE'
    is_doge_in_account = False
    doge_balance = '0'
    doge_avg_buy_price = 0.0

    if 'currency' not in my_account.columns:
        raise ValueError('[currency] 컬럼이 존재하지 않습니다.')

    if doge_ticker in my_account['currency'].values:
        is_doge_in_account = True
        doge_balance = my_account[my_account['currency'] == doge_ticker]['balance'].values[0]
        doge_avg_buy_price = float(my_account[my_account['currency'] == doge_ticker]['avg_buy_price'].values[0])

    logger.debug(f'is_doge_in_account : {is_doge_in_account}')
    logger.debug(f'doge_balance : {doge_balance}')
    logger.debug(f'doge_avg_buy_price : {doge_avg_buy_price}')

    # 원화 잔고 확인
    krw_amount = 0.0
    krw_ticker = 'KRW'
    if krw_ticker in my_account['currency'].values:
        my_account['balance'] = my_account['balance'].astype(float)
        krw_amount = my_account[my_account['currency'] == krw_ticker]['balance'].values[0]

    logger.debug(f'krw_amount : {krw_amount}')

    # 투자 가능한 원화 계산
    # 거래 수수료는 원화(KRW) 마켓에서는 0.05%이나 실제 매수 시 전체 금액에서 0.1%를 제한 금액으로 투자를 진행
    krw_invest_amount = 0
    if krw_amount > 0:
        krw_invest_amount = math.floor(krw_amount * 0.999)

    logger.debug(f'krw_invest_amount : {krw_invest_amount}')

    return {
        'is_doge': is_doge_in_account,
        'doge_balance': doge_balance,
        'doge_buy_price': doge_avg_buy_price,
        'krw_balance': krw_amount,
        'krw_available': krw_invest_amount
    }


def mod5_curr_min():
    # 현재 시간 가져오기 - 로컬 PC의 시간이 기준
    current_time = datetime.now()

    # 현재 분(minute) 추출
    current_minute = current_time.minute

    # 나머지
    remainder_of_mod5 = current_minute % 5

    logger.debug(f'current_time : {current_time}, current_minute : {current_minute}')
    logger.debug(f'remainder_of_mod5 : {remainder_of_mod5}')

    return remainder_of_mod5


def get_data():
    # 도지코인(KRW-DOGE) 5분봉 가져오기
    doge_5min_data = get_min_candle_data('KRW-DOGE', 5)

    return doge_5min_data


def auto_trading():
    logger.debug('##### Bollinger Band Breakout #####')

    try:
        # 시간 확인
        remainder = mod5_curr_min()

        # 계좌정보 확인
        account_info = get_account_info()

        # 현재 계좌잔고(KRW) 확인
        krw_balance: float = math.floor(account_info['krw_balance'])

        # 포지션 확인 (0: 매수 가능, 1: 매도 가능, 9: 매수/매도 모두 불가)
        current_position = 9
        if remainder == 4 and krw_balance > 10000:
            current_position = 0
        elif remainder == 0 and account_info['is_doge']:
            current_position = 1

        logger.debug(f'remainder : {remainder}')
        logger.debug(f'krw_balance : {krw_balance}')
        logger.debug(f'current_position : {current_position}')

        if current_position == 0 or current_position == 1:
            # 캔들 정보 가져오기
            doge_data = get_data()

            krw_trade_amount = 10000  # 1만원씩 매매
            formatted_trade_amount = '{:,}'.format(krw_trade_amount)
            trade_strategy_result = trading_strategy(doge_data, current_position)

            logger.debug(f'trade_strategy_result : {trade_strategy_result}')

            if trade_strategy_result['signal'] == 'buy':
                # 매수
                buy_result = buy_market('KRW-DOGE', krw_trade_amount)
                if buy_result['uuid'].notnull()[0]:
                    # 시장가로 주문하기 때문에 uuid 값이 있으면 정상
                    logger.info(f'[KRW-DOGE] {formatted_trade_amount}원 매수 하였습니다.')

                    buy_msg = f"{trade_strategy_result['message']}" + \
                              f"[KRW-DOGE] {formatted_trade_amount}원 매수 하였습니다."
                    send_email('[KRW-DOGE] 시장가 매수', buy_msg)
                else:
                    logger.error('매수가 정상적으로 처리되지 않았습니다.')
                    send_email('매수 중 에러 발생', '매수 중 에러가 발생하였습니다. 확인해주세요.')

            elif trade_strategy_result['signal'] == 'sell':
                current_price: float = doge_data['close'].iloc[-1]
                doge_balance = float(account_info['doge_balance'])
                doge_to_krw = current_price * doge_balance

                # 원화 환산 금액이 2만원이 넘으면 1만원씩 매도
                if doge_to_krw > 20000:
                    sell_doge_amount = 10000 / current_price
                # 2만원 미만인 경우 전체 매도
                else:
                    sell_doge_amount = doge_balance

                logger.info(f'current_price : {current_price}')
                logger.info(f'doge_balance : {doge_balance}')
                logger.info(f'doge_to_krw : {doge_to_krw}')
                logger.info(f'sell_doge_amount : {sell_doge_amount}')

                # 매도
                sell_result = sell_market('KRW-DOGE', str(sell_doge_amount))
                if sell_result['uuid'].notnull()[0]:
                    while True:
                        open_order_df = get_open_order('KRW-DOGE', 'wait')
                        # print(open_order_df)

                        time.sleep(5)  # 5초 대기

                        # wait 중인 거래가 없으면 반복 중단
                        if len(open_order_df) == 0:
                            break

                    logger.info(f'[KRW-DOGE] {sell_doge_amount} 매도 하였습니다.')

                    sell_msg = f"{trade_strategy_result['message']}" + \
                               f"[KRW-DOGE] {sell_doge_amount} 매도 하였습니다."
                    send_email('[KRW-DOGE] 시장가 매도', sell_msg)
                else:
                    logger.error('매도가 정상적으로 처리되지 않았습니다.')
                    send_email('매도 중 에러 발생', '매도 중 에러가 발생하였습니다. 확인해주세요.')

    except ValueError as ve:
        logger.error(f'ValueError : {ve}')
    except Exception as e:
        logger.error(f'예상치 못한 오류 발생 : {e}')


# main 작업 실행
if __name__ == '__main__':
    logger.info('++++++++++ apscheduler starts. ++++++++++')

    # 현재 시간
    scheduler_start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f'scheduler_start_time : {scheduler_start_time}')

    # Background Scheduler 세팅
    scheduler = BackgroundScheduler()
    scheduler.add_job(auto_trading, 'cron', second=50)  # 매분 50초에 실행
    scheduler.start()

    try:
        while True:
            # 프로그램이 종료되지 않게 대기하도록 설정
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
