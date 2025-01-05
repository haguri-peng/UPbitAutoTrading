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

# sys.path에 account 디렉토리를 추가
sys.path.append(account_dir)
sys.path.append(upbit_data_dir)
sys.path.append(trading_dir)
sys.path.append(utils_dir)

# import
from account.my_account import get_my_exchange_account
from upbit_data.candle import get_min_candle_data
from trading.trading_strategy import trading_strategy
from trading.trade import buy_market, sell_market, get_open_order
from utils.email_utils import send_email

# 전역변수
buy_time = None  # 매수시간
krw_balance = 0  # 계좌잔고(KRW)

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


def check_time():
    # 현재 시간 가져오기 - 로컬 PC의 시간이 기준
    current_time = datetime.now()

    # 현재 분(minute) 추출
    current_minute = current_time.minute

    # 현재 분(minute)이 5분으로 끝나는지 확인
    is_reminder_of_five = current_minute % 10 == 5

    logger.debug(f'current_time : {current_time}, current_minute : {current_minute}')
    logger.debug(f'is_reminder_of_five : {is_reminder_of_five}')

    return is_reminder_of_five


def get_data():
    # 도지코인(KRW-DOGE) 10분봉 가져오기
    doge_10min_data = get_min_candle_data('KRW-DOGE', 10)

    return doge_10min_data


def auto_trading():
    try:
        # 계좌정보 확인
        account_info = get_account_info()

        # 시간 확인
        reminder_of_five = check_time()

        # 포지션 확인 (0: 매수 가능, 1: 매도 가능)
        # 현재 계좌에 매수된 코인 정보가 없으면 '매수 가능(0)', 있으면 매도 가능(1)입니다.
        current_position = 1 if account_info['is_doge'] else 0

        logger.debug(f'current_position : {current_position}')

        # 전역변수 사용
        global buy_time, krw_balance

        # 현재 계좌잔고(KRW) 세팅
        krw_balance = math.floor(account_info['krw_balance'])

        # 매수
        if current_position == 0:
            # 매수는 현재 시간(분)의 끝 자리가 5(분)이면 진행
            if reminder_of_five:
                trade_strategy_result = trading_strategy(get_data(), current_position)

                logger.debug(f'trade_strategy_result : {trade_strategy_result}')

                if trade_strategy_result['signal'] == 'buy':
                    buy_result = buy_market('KRW-DOGE', account_info['krw_available'])
                    if buy_result['uuid'].notnull()[0]:
                        # 시장가로 주문하기 때문에 uuid 값이 있으면 정상적으로 처리됐다고 가정한다.
                        # 매수하면서 전역변수인 매수시간을 세팅한다.
                        buy_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        logger.info(f'[KRW-DOGE] {account_info["krw_available"]}원 매수 하였습니다.')

                        send_email('[KRW-DOGE] 시장가 매수', trade_strategy_result['message'])
                    else:
                        logger.error('매수가 정상적으로 처리되지 않았습니다.')

        # 매도
        elif current_position == 1:
            trade_strategy_result = trading_strategy(get_data(), current_position, buy_time,
                                                     account_info['doge_buy_price'])

            logger.debug(f'trade_strategy_result : {trade_strategy_result}')

            if trade_strategy_result['signal'] == 'sell':
                sell_result = sell_market('KRW-DOGE', account_info['doge_balance'])
                if sell_result['uuid'].notnull()[0]:
                    while True:
                        open_order_df = get_open_order('KRW-DOGE', 'wait')
                        print(open_order_df)

                        time.sleep(5)  # 5초 대기

                        # wait 중인 거래가 없으면 반복 중단
                        if len(open_order_df) == 0:
                            break

                    # 매도하면서 전역변수인 매수시간을 초기화한다.
                    buy_time = None

                    # 매도 이후에 매매수익을 확인하기 위해 계좌정보를 다시 조회
                    after_sell_account = get_my_exchange_account()
                    print(after_sell_account)

                    # 원화 잔고 확인
                    trade_result = 0
                    if 'KRW' in after_sell_account['currency'].values:
                        after_sell_krw_bal = math.floor(
                            after_sell_account[after_sell_account['currency'] == 'KRW']['balance'].values[0])
                        trade_result = math.floor(after_sell_krw_bal - krw_balance)

                    logger.info(f'[KRW-DOGE] {account_info["doge_balance"]} 매도 하였습니다.')
                    logger.info(f'매매수익은 {trade_result} 입니다.')

                    send_email('[KRW-DOGE] 시장가 매도', f'{trade_strategy_result["message"]}\n매매수익은 {trade_result} 입니다.')
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
    scheduler.add_job(auto_trading, 'interval', minutes=1)  # 매분 체크
    scheduler.start()

    try:
        while True:
            # 프로그램이 종료되지 않게 대기하도록 설정
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
