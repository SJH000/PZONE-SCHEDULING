# 02. Data Scope and Cleaning

## 데이터 범위
| table        |   dump_rows_seen |   rows_loaded |
|:-------------|-----------------:|--------------:|
| prc_hist_tb  |             5830 |          5830 |
| prc_trns_tb  |           846932 |        846916 |
| prc_oee_tb   |            34265 |         34265 |
| strg_buf_in  |              187 |           187 |
| strg_buf_out |               76 |            76 |
| strg_fns_in  |               42 |            42 |
| strg_fns_out |               42 |            42 |
| std_eqpmn_tb |               16 |            15 |
| std_strg_cd  |                9 |             9 |
| std_prdct_tb |                5 |             4 |

## 정상 route 기준
- 전체 serial: `324`
- 정상 route 또는 prefix serial: `294`
- 제외 serial: `30`

## Clean 기준
Clean 지표는 원본 로그에서 분석 왜곡 가능성이 큰 값을 제외한 지표다.

제외/flag 대상:
- `STR` 없이 `END`만 있는 기록
- `END` 없이 `STR`만 있는 기록
- 음수 처리시간 또는 음수 대기시간
- 설비별 `Q3 + 1.5*IQR` 초과 처리시간
- 기본 상한을 초과하는 장시간 처리/대기/점유 로그

Raw는 데이터 품질과 이상 상황 확인용이고, 병목 판단은 clean 기준을 우선한다.
