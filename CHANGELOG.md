# ChangeLog

## 2025-01 (2)

- 전반적으로 매매전략 변경
- 기준 변경 (3분봉)
- 매수 체크 타이밍을 (3n + 1)로 변경. 즉, 3으로 나눴을 때 1이 남은 경우(1/4/7/10/13...)  
  (아무래도 캔들의 중반 부에 체크한다는 의미)
- 손절매 기준 변경 (1% 손실 시 손절매)
- 매도 조건 추가  
  (매수 시점 이후에 한 번이라도 볼린저밴드의 상단을 돌파하는 경우가 있다면, 현재가가 볼린저밴드 중심 아래로 떨어지면 즉시 매도)
- MA 기준 변경 (50MA -> 20MA)

## 2025-01

- 기준 변경 (15분봉 -> 10분봉)
- 매도 시, 매매 결과까지 알리도록 설정
- 매도 중에 'wait' 거래가 있으면 계속 대기했다가 다음 로직을 수행하도록 처리
- 골든 크로스, 데드 크로스에 대한 전략 추가

## 2024-12

- initial commit
