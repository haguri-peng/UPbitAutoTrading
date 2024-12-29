# 업비트(UPbit) 자동 매매

- 업비트에서 자동 매매할 수 있도록 Python 코드를 작성하였습니다.
- 스케줄 및 매매전략은 각자의 입맛에 맞게 수정하여 적용하시면 됩니다.
- AI(ChatGPT, Cluade 등)에게 미리 작성한 코드([<mark>trading_strategy.py</mark>](/trading/trading_strategy.py))와 생각하고 있던
  <mark>매매전략</mark>을 던져주시면 입맛에 맞게 코드를 수정해주니 활용하시면 됩니다. 그래도 직접 코드 검증 및 백테스팅은 해봐야 합니다.
- 보다 쉽게 사용할 수 있는 `pyupbit`라는 라이브러리가 있으나 업비트에서 직접 제공하는 API를 통해 구현하였습니다.

## 매매전략

제가 차트를 보면서 임의로 설정한 것이라 매매전략은 크게 특별한 건 아닙니다.
차트로 다 맞출 수 없습니다. <u>'대개 이렇다'</u>는 것이지 뭐가 됐든 절대적인 건 없다고 생각해야 합니다.

### `공통`

- 동시다발적으로 여러 코인을 매매하는 것이 아니라 특정 코인만을 직접 정하여 매매
- 원화 마켓(e.g. KRW-DOGE)에서 매매. 마켓은 파라미터를 통해 얼마든지 변경 가능.
- 매매 시 분할로 하지 않으며, 시장가로 처리
- `15분`봉을 기준으로 사용
- 캔들 정보는 5번(건당 200개) 연속 호출하여 가져온 1,000개의 데이터로 매매 전략을 판단
- `RSI`, `MACD`, `볼린저밴드`, `거래량`을 지표로 활용
- **50MA, 200MA**로 시장 상황 판단 (<u>상승장: 50MA가 더 큼, 하락장: 200MA가 더 큼</u>)

### `매수(Buy)`

1. 매수는 15분 단위로 진행합니다. (0/15/30/45)
2. 업비트는 원화(KRW) 마켓 거래 수수료가 `0.05%`이기 때문에 주문금액을 현재 원화 잔고(balance)에서 어림잡아 `0.1%` 차감하여 주문합니다.

#### `상승장` 📈

- 최근 25번(25개의 15분 봉) 이내에 RSI가 25 이하  
  (RSI는 floor를 적용하여 소수점 부분을 절사)
- MACD 히스토그램이 양전하고 방향이 바뀌는 시점

#### `하락장` 📉

- RSI가 25 이하(최근 100번의 데이터를 확인)로 쌍바닥(2건 이상이면 됨)
- MACD 히스토그램이 양전하고 방향이 바뀌는 시점

### `매도(Sell)`

1. 매수와 마찬가지로 15분 봉으로 판단하나 매분마다 매도 타이밍을 체크합니다.
2. 손절매(2% 손실)인 경우 매도합니다.

#### `상승장` 📈

- RSI가 한번이라도 72를 넘는 시점이 존재
- MACD가 하향 교차

#### `하락장` 📉

- 이전 캔들이 거래량과 볼린저밴드의 상단을 돌파하는 지 확인하여 판단
- 거래량은 20MA 이동 평균을 기준으로 하여 이보다 많은지 확인
- 볼린저밴드는 이전 캔들의 종가가 볼린저밴드의 상단을 돌파하는 지 확인

## 스케줄러

- APScheduler의 BackgroundScheduler 적용
- 매분 선언한 `auto_trading` 함수를 실행하도록 interval 설정

## 업비트 Open API 키

1. PC 페이지 로그인 > 마이 페이지 > Open API 관리 > 정보 입력 후 키 발급
2. `Access Key`와 `Secret Key` 확인
3. [.env](/.env) 파일에 정보 입력

## 알림

- 매매 시 SMTP로 메일(Gmail)을 전송합니다.  
  (Gmail > Forwarding and POP/IMAP > IMAP access > <u>**Enable IMAP**</u>)
- 현재 사용하고 있는 Google 계정이 아니라 다른 계정(Google)을 하나 더 생성해서 세팅하는 걸 추천합니다.
- 송/수신자 정보는 [.env](/.env) 파일에 작성하면 됩니다.

## 로그 파일

- 설정 파일: `logging.conf`
- 경로: logs/
- 로그 파일: my_log.log
- 로그 레벨: console - DEBUG / file - INFO
- suffix: yyyy-MM-dd

로그 폴더가 반드시 있어야 실행됩니다. 로그는 매일 자정을 기준으로 새로 생성되며, 최대 60일 동안 보관합니다.  
(단, 설정 파일 내용에서 로그 파일의 Path는 <mark>절대경로</mark>로 지정해야 함)

## 개발 환경 및 테스트

- Python Version: 3.9.6
- Mac에서 작업하고 이 프로그램 소스를 가지고 윈도우(Python 3.13.1)에서 정상적으로 실행하고 있습니다.

## Tree

```shell
.
├── account
│   └── my_account.py
├── logs
│   └── my_log.log
├── trading
│   ├── trade.py
│   └── trading_strategy.py
├── upbit_data
│   └── candle.py
├── utils
│   └── email_utils.py
├── .env
├── .gitignore
├── README.md
├── logging.conf
├── main.py
└── requirements.txt

6 directories, 12 files
```

## 참조

- [클래스 101 - 버리니 님 파이썬 코인 자동매매](https://class101.page.link/aB74)
- [업비트 개발자센터 - API Reference](https://docs.upbit.com/reference/)
