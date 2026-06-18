# 03. Normal Routes

## 제품별 정상 route
| PRD_CD   | normal_route                                                               |   normal_serial_count |   serial_count_total |   normal_serial_ratio |
|:---------|:---------------------------------------------------------------------------|----------------------:|---------------------:|----------------------:|
| PRD1000  | C1_RAW_STORAGE > A1 > A2 > A4 > A5 > A6_KONA > A7 > A9_2 > A8 > A9_2 > A3  |                   124 |                  137 |              0.905109 |
| PRD2000  | C1_RAW_STORAGE > A1 > A2 > A4 > A5 > A6_TESLA > A7 > A9_2 > A8 > A9_2 > A3 |                    89 |                   95 |              0.936842 |
| PRD3001  | C1_RAW_STORAGE > A1 > A2 > A7 > A5 > A9_1 > A3                             |                    45 |                   53 |              0.849057 |
| PRD3002  | C1_RAW_STORAGE > A1 > A2 > A7 > A5 > A9_1 > A3                             |                    36 |                   39 |              0.923077 |

## 제외 route
정상 route에서 벗어난 전이는 분석에서 제외했다. 대표적으로 `A5 -> A3`는 제품별 정상 route에 없어서 제외됐다.

제외 route 예시:
| PRD_CD   | PRD_SRL_NO             | normalized_route                                                                | filter_reason                      |
|:---------|:-----------------------|:--------------------------------------------------------------------------------|:-----------------------------------|
| PRD1000  | PRD1000-260211039-0001 | C1_RAW_STORAGE > A1 > A2 > A4 > A5 > A7                                         | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260211040-0001 | C1_RAW_STORAGE > A1 > A2 > A4 > A5 > A6_KONA > A7 > A8 > A9_2                   | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260304001-0001 | C1_RAW_STORAGE > A1 > A2 > A4 > A6_KONA > A7 > A9_2 > A8 > A9_2 > A3            | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260331007-0001 | C1_RAW_STORAGE > A1 > A2 > A3 > A3                                              | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260331008-0001 | C1_RAW_STORAGE > A1 > A2 > A3                                                   | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260331009-0001 | C1_RAW_STORAGE > A1 > A2 > A3                                                   | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260402001-0001 | C1_RAW_STORAGE > A1 > A2 > A3 > A3                                              | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260402002-0001 | C1_RAW_STORAGE > A1 > A2 > A3 > A3                                              | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260407009-0001 | C1_RAW_STORAGE > A1 > A2 > A3 > A3                                              | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260407010-0001 | C1_RAW_STORAGE > A1 > A2 > A3                                                   | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260421001-0002 | C1_RAW_STORAGE > A1 > A2 > A3 > A3                                              | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260426001-0001 | C1_RAW_STORAGE > A1 > A2 > A3 > A3                                              | deviates_from_product_normal_route |
| PRD1000  | PRD1000-260504001-0003 | C1_RAW_STORAGE > A1 > A2 > A3 > A3                                              | deviates_from_product_normal_route |
| PRD2000  | PRD2000-260211034-0001 | C1_RAW_STORAGE > A1 > A2 > A4 > A6_TESLA                                        | deviates_from_product_normal_route |
| PRD2000  | PRD2000-260211037-0001 | C1_RAW_STORAGE > A1 > A2 > A4 > A5 > A3                                         | deviates_from_product_normal_route |
| PRD2000  | PRD2000-260212017-0001 | C1_RAW_STORAGE > A1 > A2 > A3 > A3                                              | deviates_from_product_normal_route |
| PRD2000  | PRD2000-260304006-0001 | C1_RAW_STORAGE > A1 > A2 > A4 > A5 > A6_TESLA > A7 > A9_2 > A3                  | deviates_from_product_normal_route |
| PRD2000  | PRD2000-260304010-0001 | C1_RAW_STORAGE > A1 > A2 > A4 > A6_TESLA > A7 > A9_2 > A8 > A9_2 > A3           | deviates_from_product_normal_route |
| PRD2000  | PRD2000-260316003-0001 | C1_RAW_STORAGE > A1 > A2 > A4 > A5 > A6_TESLA > A7 > A9_2 > A8 > A9_2 > A8 > A3 | deviates_from_product_normal_route |
| PRD3001  | PRD3001-260212007-0001 | C1_RAW_STORAGE > A1 > A2 > A3 > A3                                              | deviates_from_product_normal_route |

## 해석
- `PRD1000/PRD2000`은 핸들 계열이며 A4, A5, A6, A7, A9_2, A8 흐름을 가진다.
- `PRD3001/PRD3002`는 룸미러 계열이며 A7, A5, A9_1, A3 흐름을 가진다.
- 따라서 `A7 -> A5`는 룸미러 계열 정상 route이고, 예외가 아니다.
