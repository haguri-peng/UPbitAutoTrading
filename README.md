# 업비트(UPbit) 자동 매매

- 업비트에서 자동 매매할 수 있도록 Python 코드를 작성하였습니다.
- 스케줄 및 매매전략은 각자의 입맛에 맞게 수정하여 적용하시면 됩니다.
- AI(ChatGPT, Cluade 등)에게 미리 작성한 코드([<mark>trading_strategy.py</mark>](/trading/trading_strategy.py))와 생각하고 있던
  <mark>매매전략</mark>을 던져주시면 입맛에 맞게 코드를 수정해주니 활용하시면 됩니다. 그래도 직접 코드 검증 및 백테스팅은 해봐야 합니다.
- 보다 쉽게 사용할 수 있는 `pyupbit`라는 라이브러리가 있으나 업비트에서 직접 제공하는 API를 통해 구현하였습니다.

## 진행사항

- 현재 추가로 [매매전략](/trading/trading_strategy2.py)을 추가해서 테스트를 진행하고 있습니다.
- 기존 전략으로 수익이 잘 나지 않아 다른 전략으로 바꿨는데, 테스트하면서 10% 더 날라갔네요. 😂

## 매매전략

제가 차트를 보면서 임의로 설정한 것이라 매매전략은 크게 특별한 건 아닙니다.
차트로 다 맞출 수 없습니다. <u>'대개 이렇다'</u>는 것이지 뭐가 됐든 절대적인 건 없다고 생각해야 합니다.  
매매전략을 직접 해보시면 생각보다 쉽지 않다는 것을 알게 되는데요. 원하는 매매전략을 세워서 실행하시면 됩니다.

### `공통`

- 동시다발적으로 여러 코인을 매매하는 것이 아니라 특정 코인만을 직접 정하여 매매
- 원화 마켓(e.g. KRW-DOGE)에서 매매. 마켓은 파라미터를 통해 얼마든지 변경 가능.
- 매매 시 분할로 하지 않으며, 시장가로 처리
- 캔들 정보는 5번(건당 200개) 연속 호출하여 가져온 1,000개의 데이터로 매매 전략을 판단
- `RSI`, `MACD`, `볼린저밴드` 등을 지표로 활용
- **20MA, 200MA**로 시장 상황 판단 (20MA는 기울기 포함. 20MA가 200MA보다 더 크면 `Bull Market`으로 설정)

### `매수(Buy)`

1. 조건에 맞는지 확인하고 매수를 진행합니다.
2. 업비트는 원화(KRW) 마켓 거래 수수료가 `0.05%`이기 때문에 주문금액을 현재 원화 잔고(balance)에서 어림잡아 `0.1%` 차감하여 주문합니다.

#### 매수 - 1차 조건

- 불마켓인 경우, 시작(open) 값이 20MA 보다 작고, 종료(close) 값이 20MA를 돌파
- 불마켓이 아닌 경우, RSI가 30 미만이 된 이후에 MACD 히스토그램이 양전환

#### 매수 - 2차 조건

- 거래량이 20일 이동평균 초과
- 시작(open) 값이 볼린저밴드 중간 아래이고, 종료(close) 값이 볼린저밴드 상단을 돌파

### `매도(Sell)`

1. 매분마다 매도 타이밍을 체크합니다.
2. 손절매(0.69% 손실)인 경우 매도합니다.
3. 불마켓인 경우, 한 번이라도 볼린저밴드 상단을 돌파한 이후에 중심선 아래로 하락 시 매도
4. 불마켓이 아닌 경우, 이전 캔들이 볼린저밴드 상단을 돌파한 경우 매도

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

- Python Version: 3.13.1 (3.9 버전에서도 정상적으로 동작합니다.)
- Mac에서 작업하고 이 프로그램 소스를 가지고 윈도우(Python 3.13.1)에서 정상적으로 실행하고 있습니다.

```shell
# 프로그램 실행
# 단, 실행하기 전에 venv 세팅과 관련 라이브러리가 다운로드 된 상태여야 합니다.
python main.py
```

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
│   └── trading_strategy2.py
├── upbit_data
│   └── candle.py
├── utils
│   └── email_utils.py
├── .env
├── .gitignore
├── CHANGELOG.md
├── README.md
├── logging.conf
├── main.py
└── requirements.txt

6 directories, 14 files
```

## 참조

- [클래스 101 - 버리니 님 파이썬 코인 자동매매](https://class101.page.link/aB74)
- [업비트 개발자센터 - API Reference](https://docs.upbit.com/reference/)
