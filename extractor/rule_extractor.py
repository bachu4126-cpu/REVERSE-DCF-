"""
규칙 기반 재무 계정 추출기.
Claude API 없이 키워드 매칭으로 DART 재무제표에서 계정값을 추출한다.
"""

# ──────────────────────────────────────────────────────────────
# 키워드 딕셔너리
# ──────────────────────────────────────────────────────────────

INCOME_KEYWORDS = {
    "매출액": [
        "매출액", "수익(매출액)", "영업수익", "매출(수익)", "매출및수익",
        "영업수입", "서비스수익", "총매출", "매출합계",
        "영업수익(매출액)", "매출액(수익)",
        "매출",  # KT&G 등 단순 표기 기업 (exclude로 원가·총이익 제외)
    ],
    "매출원가": [
        "매출원가", "매출비용", "영업비용(매출원가)",
        "제품매출원가", "상품매출원가", "서비스원가",
        "용역원가", "공사원가", "제조원가",
    ],
    "판매비와관리비": [
        "판매비와관리비", "판매관리비", "판관비", "영업비용(판매비",
        "판매비및관리비", "판매비 및 관리비",
    ],
    "영업이익": [
        "영업이익", "영업손익", "영업이익(손실)",
        "영업손실", "영업이익(영업손실)", "영업이익또는손실",
    ],
    "법인세차감전순이익": [
        "법인세차감전", "법인세비용차감전", "세전이익", "세전순이익",
        "법인세차감전계속사업이익", "법인세차감전손익",
        "세전계속사업이익",
    ],
    "법인세비용": [
        "법인세비용", "법인세수익비용", "법인세비용(수익)",
        "당기법인세비용", "법인세부담액", "법인세비용(이익)",
    ],
    "당기순이익_지배": [
        "지배기업 소유주에 귀속", "지배지분 순이익", "지배주주귀속",
        "지배기업의 소유주", "모회사 소유주에 귀속",
        "지배기업소유주귀속당기순이익",
        "지배주주에 귀속되는 당기순이익",
        "지배기업 지분의 당기순이익",
        "지배기업지분 당기순이익",
        "지배기업 주주에 귀속",
        "지배기업 소유주지분",  # KT&G: 귀속 섹션 하위 "지배기업 소유주지분" 행
    ],
}

CASHFLOW_KEYWORDS = {
    "주식보상비용": [
        "주식보상비용", "주식기준보상", "종업원주식보상", "주식결제형",
        "주식기준보상비용", "종업원주식선택권비용",
        "주식매입선택권비용", "주식보상거래",
        "종업원급여(주식기준보상)",
    ],
    "자산부채_변동": [
        "자산·부채의 변동", "자산부채의 변동", "운전자본의 변동",
        "영업활동으로 인한 자산·부채", "영업활동으로인한자산부채",
        "영업활동의 자산·부채", "영업활동의 자산부채",
        "자산 및 부채의 변동",
        "자산과 부채의 변동", "자산,부채의 변동",
        "영업활동과관련된자산부채의변동",
        "영업자산과부채의변동", "유동자산부채의변동",
        "운전자본변동", "영업관련자산부채변동",
    ],
    "유형자산_취득": [
        "유형자산의 취득", "유형자산취득", "유형자산 취득",
        "유형자산 매입", "유형자산의취득",
        "유형자산의 구입", "유형자산구입", "설비자산취득",
        "유형고정자산취득", "유형자산의 증가",
    ],
    "무형자산_취득": [
        "무형자산의 취득", "무형자산취득", "무형자산 취득",
        "무형자산 매입", "개발비의 취득", "개발비 지출",
        "무형자산의 구입", "소프트웨어의 취득", "소프트웨어취득",
        "특허권의 취득", "개발비의지출", "무형자산의 증가",
    ],
    "차입금_유입": [
        "차입금의 증가", "차입금 유입", "장단기차입금의 증가",
        "단기차입금의 증가", "장기차입금의 증가", "차입금차입",
        "차입금의 차입",
        "단기차입금차입", "장기차입금차입",
        "금융기관차입", "차입금의증가",
        "단기금융부채의 증가", "장기금융부채의 증가",
        "전환사채의 증가", "전환사채의 발행",
        "신주인수권부사채의 발행", "신주인수권부사채의 증가",
        "사채의 발행", "교환사채의 발행",
    ],
    "차입금_상환": [
        "차입금의 감소", "차입금 상환", "장단기차입금의 감소",
        "단기차입금의 감소", "장기차입금의 감소", "차입금상환",
        "차입금의 상환",
        "단기차입금상환", "장기차입금상환",
        "금융기관차입금상환", "차입금의감소",
        "단기금융부채의 감소", "장기금융부채의 감소",
        "사채의 상환", "전환사채의 상환",
        "신주인수권부사채의 상환",
        "복합금융상품 상환", "복합금융상품상환",
    ],
}

# 응축형 현금흐름(간접법 요약) 기업에서 영업창출현금흐름 탐지용
CONDENSED_OCF_KEYWORDS = [
    "영업으로부터 창출된 현금흐름",
    "영업으로부터의 현금흐름",
    "영업활동으로부터 창출된 현금",
    "영업으로부터창출된현금흐름",
    "영업에서 창출된 현금",   # KT&G
    "영업으로부터창출된현금",
]

DA_KEYWORDS = {
    "감가상각비": [
        "감가상각비", "유형자산감가상각", "감가상각 및 상각비",
        "감가상각비(유형자산)", "유형자산의 감가상각비",
        "감가상각비와 상각비",   # 유형+무형 합산 공시 기업
        "감가상각비 및 상각비",
        "유형자산상각비", "유형자산의상각비",
        "감가상각비 및 무형자산 상각",  # SK하이닉스: 유형+무형 합산 계상
    ],
    "무형자산상각비": [
        "무형자산상각비", "무형자산의 상각", "무형자산상각",
        "무형자산의 상각비", "기타무형자산상각비",
        "무형자산의 감가상각", "개발비상각비", "개발비의 상각",
        "소프트웨어상각비", "특허권상각비",
        "산업재산권상각비", "영업권상각비",
        "기술가치상각", "무형고정자산상각비",
    ],
}

EPS_KEYWORDS = {
    "희석_순이익": [
        "희석효과를 포함한",
        "희석효과 반영 후 당기순이익", "희석순이익",
        "희석효과를 고려한 당기순이익", "희석효과 포함 당기순이익",
        "희석주당이익 계산에 사용된 당기순이익",
        "희석효과를 반영한 당기순이익",
        "희석법 적용 당기순이익", "희석조정 당기순이익",
        "희석효과가 반영된 당기순이익",
        "희석주당순이익 계산에 사용된 당기순이익",
        "희석당기순이익",                   # SK하이닉스: "지배기업소유주지분 희석당기순이익"
        "지배기업소유주지분희석당기순이익",  # 공백 제거 변형
    ],
    "희석_주식수": [
        "가중평균희석유통보통주식수",
        "희석평균유통보통주식수", "희석주당이익 계산에 사용된 가중평균",
        "희석효과 반영 후 가중평균주식수", "가중평균유통보통주식수(희석)",
        "가중평균유통보통주식수희석", "희석효과 반영후 가중평균",
        "유통보통주식수(희석)",
        "희석조정 가중평균주식수", "희석법 가중평균주식수",
        "희석주당이익계산에사용된가중평균유통보통주식수",
        "희석효과반영가중평균유통보통주식수",
        "가중평균유통주식수(희석)", "희석주당순이익계산주식수",
    ],
}

# 희석 미공시 시 기본(Basic) 값으로 대체하기 위한 fallback 키워드 (notes 내 동일 시트 검색)
EPS_BASIC_FALLBACK = {
    "희석_순이익": [
        "지배기업의 보통주에 귀속되는 당기순이익",
        "지배기업 보통주에 귀속되는 당기순이익",
        "지배기업소유주에귀속되는당기순이익",
        "지배기업소유주귀속당기순이익",
        "지배주주에귀속되는당기순이익",
        "지배기업 소유주에 귀속되는 당기순이익",
        "지배기업의 소유주에게 귀속되는 당기순이익",  # KT&G EPS 주석
        "지배기업의 소유주에게 귀속될",  # KT&G: "계속영업손익 귀속될" 표현
        "지배주주에게 귀속되는 당기순이익",  # LS머트리얼즈: "지배주주에게" 표현
    ],
    "희석_주식수": [
        "가중평균유통보통주식수",
        "기본주당이익 계산에 사용된 가중평균유통보통주식수",
        "가중평균발행보통주식수", "가중평균보통주식수",
        "유통보통주식수(기본)", "기본법 가중평균주식수",
    ],
}

# 법인세비용 추출 시 '법인세비용차감전순이익' 매칭 방지, 장기차입금의 오매칭 방지
INCOME_EXCLUDES = {
    "법인세비용": ["차감전"],
    # "매출" 키워드가 매출원가·매출총이익·매출채권 등에 오매칭되지 않도록 제외
    "매출액": ["원가", "총이익", "채권", "비용", "반품"],
}

BALANCE_EXCLUDES = {
    "장기차입금": ["유동성", "기타"],
}

BALANCE_KEYWORDS = {
    "부채총계": [
        "부채총계", "부채합계", "총부채",
    ],
    "자기자본_지배": [
        "지배기업의 소유주에게 귀속되는 자본",
        "지배기업 소유주에 귀속되는 자본", "지배기업 소유주에게 귀속되는 자본", "지배지분합계",
        "지배기업지분합계", "지배기업 소유주지분합계",
        "모회사 소유주에 귀속되는 자본",
        "지배기업소유주귀속자본", "지배주주지분합계",
        "지배기업지분자본합계", "지배주주에귀속되는자본",
        "지배기업 주주지분",
        "지배기업의 소유지분",   # SK하이닉스
        "지배기업소유지분",      # 공백 제거 변형
        "지배기업 소유주지분",   # KT&G
        "지배기업의 소유주지분", # LG전자: 조사 "의" 포함 변형
    ],
    "현금": [
        "현금및현금성자산", "현금 및 현금성자산",
        "현금및현금등가물",
        "현금과현금성자산", "현금및단기예금",
    ],
    "단기차입금": [
        "단기차입금",
        "단기금융기관차입금", "단기은행차입금",
        "단기금융부채(차입금)",
    ],
    "유동성장기부채": [
        "유동성 장기부채", "유동성장기차입금",
        "유동성장기부채", "유동성 장기차입금",
        "유동성장기사채", "1년이내상환장기차입금",
        "유동성전환사채", "유동장기차입금",
        "1년내만기도래장기차입금",
    ],
    "장기차입금": [
        "장기차입금",
        "비유동차입금", "장기금융기관차입금",
        "장기은행차입금", "장기금융부채(차입금)",
    ],
    "사채_유동": ["사채"],
    "사채_비유동": ["사채"],
}


# ──────────────────────────────────────────────────────────────
# 핵심 매칭 함수
# ──────────────────────────────────────────────────────────────

def _match(account_str: str, keywords: list[str]) -> bool:
    a = account_str.replace(' ', '').replace('·', '').replace('(', '').replace(')', '')
    for kw in keywords:
        k = kw.replace(' ', '').replace('·', '').replace('(', '').replace(')', '')
        if k in a:
            return True
    return False


def _find_sum(rows: list[dict], keywords: list[str], years: list[str],
             abs_val: bool = False) -> dict | None:
    """keywords에 매칭되는 모든 행의 값을 연도별로 합산."""
    matched_labels: list[str] = []
    year_totals = {yr: 0 for yr in years}
    year_has_data = {yr: False for yr in years}
    any_matched = False

    for row in rows:
        if _match(row['account'], keywords):
            any_matched = True
            for yr in years:
                v = row.get(f'fy{yr}')
                if v is not None:
                    year_totals[yr] += abs(v) if abs_val else v
                    year_has_data[yr] = True
            if row['account'] not in matched_labels:
                matched_labels.append(row['account'])

    if not any_matched:
        return None

    result: dict = {f'fy{yr}': (year_totals[yr] if year_has_data[yr] else None) for yr in years}
    result['matched_label'] = ', '.join(matched_labels[:4])
    return result


def _find_first(rows: list[dict], keywords: list[str], years: list[str],
                skip_zero: bool = False, exclude: list[str] | None = None) -> dict | None:
    """
    rows에서 keywords 매칭 첫 행 반환.
    skip_zero=True → 모든 값이 None인 행(DART 빈값 블록) 건너뜀.
    """
    for row in rows:
        if _match(row['account'], keywords):
            if exclude and _match(row['account'], exclude):
                continue
            val = {f'fy{yr}': row.get(f'fy{yr}') for yr in years}
            if skip_zero and all(v == 0 for v in val.values() if v is not None):
                continue
            val['matched_label'] = row['account']
            return val
    return None


def _na_reason(rows: list[dict], keywords: list[str],
               exclude: list[str] | None = None) -> str:
    """N/A 진단: 계정 자체 없음 vs 계정은 있지만 값 미공시."""
    for row in rows:
        if _match(row['account'], keywords):
            if exclude and _match(row['account'], exclude):
                continue
            return f'계정 존재하나 해당 기간 값 미공시 ({row["account"]})'
    return '계정 없음 (키워드 매칭 실패)'


def _abs_result(result: dict | None, years: list[str]) -> dict | None:
    if result is None:
        return None
    for yr in years:
        k = f'fy{yr}'
        if result.get(k) is not None:
            result[k] = abs(result[k])
    return result


def _na_result(years: list[str], note: str = '') -> dict:
    result = {f'fy{yr}': None for yr in years}
    result['matched_label'] = 'N/A'
    result['note'] = note
    return result


def _zero_result(years: list[str], note: str = '') -> dict:
    """값이 없는 항목을 0으로 처리 (FCFE 계산에서 무시됨)."""
    result = {f'fy{yr}': 0 for yr in years}
    result['matched_label'] = '해당 없음'
    result['note'] = note
    return result


# ──────────────────────────────────────────────────────────────
# 사채 유동/비유동 분리
# ──────────────────────────────────────────────────────────────

def _find_bonds(rows: list[dict], years: list[str]) -> tuple[dict | None, dict | None]:
    current_section = 'unknown'
    bond_current = None
    bond_noncurrent = None

    for row in rows:
        acct = row['account'].replace(' ', '')
        if '유동부채' in acct and '비유동' not in acct:
            current_section = 'current'
        elif '비유동부채' in acct:
            current_section = 'noncurrent'

        if _match(row['account'], ['사채']):
            val = {f'fy{yr}': row.get(f'fy{yr}') for yr in years}
            val['matched_label'] = row['account']
            if current_section == 'current' and bond_current is None:
                bond_current = val
            elif current_section == 'noncurrent' and bond_noncurrent is None:
                bond_noncurrent = val

    return bond_current, bond_noncurrent


def _find_loans_by_section(rows: list[dict], years: list[str]) -> tuple[dict | None, dict | None]:
    """
    유동/비유동 섹션 컨텍스트로 bare '차입금' 행을 단기/장기로 분리.
    '단기차입금'/'장기차입금' 키워드 매칭 실패 시 fallback으로 호출 (SK하이닉스 패턴).
    """
    section = 'unknown'
    cur = None
    noncur = None
    for row in rows:
        acct = row['account'].replace(' ', '')
        if '유동부채' in acct and '비유동' not in acct:
            section = 'current'
        elif '비유동부채' in acct:
            section = 'noncurrent'
        if (_match(row['account'], ['차입금'])
                and not _match(row['account'], ['단기', '장기', '유동성', '기타', '상환'])):
            val = {f'fy{yr}': row.get(f'fy{yr}') for yr in years}
            val['matched_label'] = row['account']
            if section == 'current' and cur is None:
                cur = val
            elif section == 'noncurrent' and noncur is None:
                noncur = val
    return cur, noncur


# ──────────────────────────────────────────────────────────────
# 섹션별 추출 함수
# ──────────────────────────────────────────────────────────────

def extract_income(rows: list[dict], years: list[str]) -> dict:
    result = {}
    for key, kws in INCOME_KEYWORDS.items():
        exclude = INCOME_EXCLUDES.get(key)
        found = _find_first(rows, kws, years, exclude=exclude)
        result[key] = found or _na_result(years, _na_reason(rows, kws, exclude=exclude))
    return result


def extract_cashflow(rows: list[dict], years: list[str]) -> dict:
    result = {}
    for key, kws in CASHFLOW_KEYWORDS.items():
        if key in ('차입금_유입', '차입금_상환'):
            # 전환사채·사채 등 여러 항목 합산
            abs_val = (key == '차입금_상환')
            found = _find_sum(rows, kws, years, abs_val=abs_val)
        else:
            found = _find_first(rows, kws, years)
            if key in ('유형자산_취득', '무형자산_취득'):
                found = _abs_result(found, years)

        if found is None:
            if key == '주식보상비용':
                result[key] = _zero_result(
                    years,
                    '현금흐름표에 별도 행 없음. 0으로 처리 (타사에는 존재 가능)'
                )
            else:
                result[key] = _na_result(years, _na_reason(rows, kws))
        else:
            result[key] = found
    return result


def extract_da(rows: list[dict], years: list[str]) -> dict:
    """성격별 비용 주석(D834300/D834310)에서 D&A 추출.
    DART 형식상 빈값 블록이 먼저 나오므로 skip_zero=True 사용.
    주의: D834310(판관비 내역)만 있는 경우 매출원가 내 D&A는 포함되지 않음.
    """
    result = {}
    for key, kws in DA_KEYWORDS.items():
        found = _find_first(rows, kws, years, skip_zero=True)
        if found:
            for yr in years:
                k = f'fy{yr}'
                if found.get(k) is not None:
                    found[k] = abs(found[k])
            result[key] = found
        else:
            result[key] = _na_result(years, _na_reason(rows, kws))

    # 합산 계상 감지 — 두 가지 케이스 처리
    dep = result.get('감가상각비', {})
    amor = result.get('무형자산상각비', {})
    dep_label = dep.get('matched_label', '').replace(' ', '')
    amor_label = amor.get('matched_label', '')

    # Case 1: 합산 표현 레이블 + 무형자산상각비 별도 없음 (한미반도체 패턴)
    if ('와상각비' in dep_label or '및상각비' in dep_label) and amor_label == 'N/A':
        result['무형자산상각비'] = _zero_result(years, '감가상각비와 합산 계상 (별도 없음, 이중계산 방지)')

    # Case 2: 동일 행이 양쪽에 매칭 → 무형 = 0 (SK하이닉스 패턴)
    elif (dep.get('matched_label') and amor_label not in ('N/A', '해당 없음')
          and dep.get('matched_label') == amor_label):
        result['무형자산상각비'] = _zero_result(
            years, f'감가상각비와 동일 행 매칭 → 이중계산 방지 ({amor_label})'
        )

    return result


def extract_eps(rows: list[dict], years: list[str]) -> dict:
    """희석 EPS 추출. 특정 연도 희석 미공시 시 동일 시트 기본값(Basic)으로 대체."""
    result = {}
    for key, kws in EPS_KEYWORDS.items():
        found = _find_first(rows, kws, years, skip_zero=True)

        if found is None:
            # 희석 행 자체가 없을 때 기본(Basic) 행으로 전면 대체
            fallback_kws = EPS_BASIC_FALLBACK.get(key, [])
            if fallback_kws:
                fb = _find_first(rows, fallback_kws, years, skip_zero=True)
                if fb:
                    fb['note'] = '희석 미공시 → 기본값 사용'
                    result[key] = fb
                    continue
            result[key] = _na_result(years, _na_reason(rows, kws))
            continue

        # 연도별 None → 같은 시트 내 기본(Basic) fallback
        fallback_kws = EPS_BASIC_FALLBACK.get(key, [])
        fallback_applied = []
        if fallback_kws:
            fb = _find_first(rows, fallback_kws, years, skip_zero=True)
            if fb:
                for yr in years:
                    if found.get(f'fy{yr}') is None and fb.get(f'fy{yr}') is not None:
                        found[f'fy{yr}'] = fb[f'fy{yr}']
                        fallback_applied.append(yr)

        if fallback_applied:
            yrs_str = ', '.join(f'FY{y}' for y in fallback_applied)
            found['note'] = f'{yrs_str}: 희석 미공시 → 기본값(지배) 사용'

        result[key] = found
    return result


_BALANCE_DEBT_KEYS = {'단기차입금', '유동성장기부채', '장기차입금'}

def extract_balance(rows: list[dict], years: list[str]) -> dict:
    result = {}
    for key, kws in BALANCE_KEYWORDS.items():
        if key in ('사채_유동', '사채_비유동'):
            continue
        exclude = BALANCE_EXCLUDES.get(key)
        found = _find_first(rows, kws, years, exclude=exclude)
        if found is None:
            if key in _BALANCE_DEBT_KEYS:
                result[key] = _zero_result(years, '차입금 없음 (0으로 처리)')
            else:
                result[key] = _na_result(years, _na_reason(rows, kws, exclude=exclude))
        else:
            result[key] = found

    # bare '차입금' 섹션 컨텍스트 fallback (SK하이닉스 패턴)
    primary_miss = {k for k in _BALANCE_DEBT_KEYS
                    if result.get(k, {}).get('note', '').startswith('차입금 없음')}
    if '단기차입금' in primary_miss or '장기차입금' in primary_miss:
        loan_cur, loan_noncur = _find_loans_by_section(rows, years)
        if loan_cur and '단기차입금' in primary_miss:
            result['단기차입금'] = loan_cur
        if loan_noncur and '장기차입금' in primary_miss:
            result['장기차입금'] = loan_noncur

    bond_cur, bond_noncur = _find_bonds(rows, years)
    # 사채 없는 기업은 0으로 처리 (재무건전성 표에서 N/A 대신 0)
    result['사채_유동'] = bond_cur or _zero_result(years, '유동 사채 없음 (0으로 처리)')
    result['사채_비유동'] = bond_noncur or _zero_result(years, '비유동 사채 없음 (0으로 처리)')
    return result


# ──────────────────────────────────────────────────────────────
# 통합 추출
# ──────────────────────────────────────────────────────────────

def extract_all_data(fs_data: dict, notes_data: dict, prev_notes_data: dict | None = None) -> dict:
    """재무제표 + 주석 데이터를 받아 모든 섹션 추출 결과 반환."""
    fs_years = fs_data.get('years', ['2025', '2024', '2023'])
    notes_years = notes_data.get('years', ['2025', '2024'])

    years = fs_years if len(fs_years) >= len(notes_years) else notes_years

    errors = []

    income = {}
    if fs_data.get('income_rows'):
        income = extract_income(fs_data['income_rows'], years)
    else:
        errors.append('손익계산서 시트를 찾지 못했습니다.')

    cashflow = {}
    if fs_data.get('cashflow_rows'):
        cashflow = extract_cashflow(fs_data['cashflow_rows'], years)
    else:
        errors.append('현금흐름표 시트를 찾지 못했습니다.')

    # 주식보상비용: 현금흐름표에 없을 때 D851100 주석에서 재탐색
    sbc = cashflow.get('주식보상비용', {})
    if '별도 행 없음' in sbc.get('note', '') and notes_data.get('sbp_rows'):
        found = _find_first(
            notes_data['sbp_rows'],
            CASHFLOW_KEYWORDS['주식보상비용'],
            years,
            skip_zero=True,
        )
        if found:
            found['note'] = 'D851100 주식기준보상 주석에서 추출'
            cashflow['주식보상비용'] = found

    # Fix 2 — SBC 연도별 fallback: 행은 매칭됐으나 특정 연도 값이 None인 경우
    sbc = cashflow.get('주식보상비용', {})
    if notes_data.get('sbp_rows') and '별도 행 없음' not in sbc.get('note', ''):
        missing_sbc = [yr for yr in years if sbc.get(f'fy{yr}') is None]
        if missing_sbc:
            sbp_found = _find_first(
                notes_data['sbp_rows'],
                CASHFLOW_KEYWORDS['주식보상비용'],
                years,
                skip_zero=True,
            )
            if sbp_found:
                applied = []
                for yr in missing_sbc:
                    v = sbp_found.get(f'fy{yr}')
                    if v is not None:
                        sbc[f'fy{yr}'] = v
                        applied.append(yr)
                if applied:
                    yrs_str = ', '.join(f'FY{y}' for y in applied)
                    old = sbc.get('note', '')
                    sbc['note'] = (old + f'  {yrs_str}: D851100 주석 대체').strip()

    da = {}
    if notes_data.get('da_rows'):
        # 전체 연도 기준으로 추출 (주석 미제공 연도는 None으로 채워짐)
        da = extract_da(notes_data['da_rows'], years)
    else:
        errors.append('성격별 비용 주석(D834300) 시트를 찾지 못했습니다. 현금흐름표에서 재시도합니다.')
        if fs_data.get('cashflow_rows'):
            da = {
                '감가상각비': _find_first(
                    fs_data['cashflow_rows'], DA_KEYWORDS['감가상각비'], years, skip_zero=True
                ) or _na_result(years, _na_reason(fs_data['cashflow_rows'], DA_KEYWORDS['감가상각비'])),
                '무형자산상각비': _find_first(
                    fs_data['cashflow_rows'], DA_KEYWORDS['무형자산상각비'], years, skip_zero=True
                ) or _na_result(years, _na_reason(fs_data['cashflow_rows'], DA_KEYWORDS['무형자산상각비'])),
            }

    # Fix 1 — D&A 연도별 현금흐름 fallback: 주석은 2년치만 제공하므로 누락 연도를 현금흐름표로 보완
    if da and fs_data.get('cashflow_rows'):
        cf_rows = fs_data['cashflow_rows']
        for key in ('감가상각비', '무형자산상각비'):
            acc = da.get(key)
            if acc is None:
                continue
            missing = [yr for yr in years if acc.get(f'fy{yr}') is None]
            if not missing:
                continue
            cf_found = _find_first(cf_rows, DA_KEYWORDS[key], years, skip_zero=True)
            if cf_found:
                applied = []
                for yr in missing:
                    v = cf_found.get(f'fy{yr}')
                    if v is not None:
                        acc[f'fy{yr}'] = abs(v)
                        applied.append(yr)
                if applied:
                    yrs_str = ', '.join(f'FY{y}' for y in applied)
                    old = acc.get('note', '')
                    acc['note'] = (old + f'  {yrs_str}: 현금흐름표 대체').strip()

    eps = {}
    if notes_data.get('eps_rows'):
        # 전체 연도 기준으로 추출 (주석 미제공 연도는 None)
        eps = extract_eps(notes_data['eps_rows'], years)
    else:
        errors.append('주당이익 주석(D838000) 시트를 찾지 못했습니다.')

    # ── EPS 크로스섹션 Fallback ──────────────────────────────
    # 주석 파일에 없는 연도(예: FY2023)는 손익계산서로 대체
    extra_years = [y for y in years if y not in notes_years]
    if extra_years and eps and income:
        ni_acc = eps.get('희석_순이익', {})
        sh_acc = eps.get('희석_주식수', {})
        income_ni = income.get('당기순이익_지배', {})

        # 손익계산서 주당이익 행 추출 — 주식수 역산용
        income_rows = fs_data.get('income_rows', [])
        eps_ps_diluted = _find_first(
            income_rows,
            ["희석주당이익", "희석 주당이익", "희석주당이익(손실)", "희석주당손익",
             "희석주당순이익", "희석주당순이익(손실)",
             "계속영업 희석주당이익", "희석주당손익합계"],  # KT&G
            years,
            skip_zero=True,  # [개요] 등 all-None 헤더 행 건너뜀
        )
        eps_ps_basic = _find_first(
            income_rows,
            ["기본주당이익", "기본 주당이익", "기본주당이익(손실)", "기본주당손익",
             "기본주당순이익", "기본주당순이익(손실)",
             "계속영업 기본주당이익", "기본주당손익합계"],  # KT&G
            years,
            skip_zero=True,  # [개요] 등 all-None 헤더 행 건너뜀
        )

        # DART 파일에 따라 희석/기본 레이블이 역전될 수 있음.
        # 주석에서 알려진 연도로 교차검증해 올바른 행을 선택한다.
        validated_row = None
        validated_label = None
        for ky in notes_years:
            known_sh = sh_acc.get(f'fy{ky}')
            known_ni = ni_acc.get(f'fy{ky}')
            if not (known_sh and known_ni):
                continue
            for cand_row, cand_label in [
                (eps_ps_diluted, '희석주당이익'),
                (eps_ps_basic,   '기본주당이익'),
            ]:
                if not cand_row:
                    continue
                ps = cand_row.get(f'fy{ky}')
                if ps and abs(round(known_ni / ps) - known_sh) / known_sh < 0.03:
                    validated_row = cand_row
                    validated_label = cand_label
                    break
            if validated_row:
                break
        if not validated_row:
            validated_row = eps_ps_diluted or eps_ps_basic
            validated_label = '희석주당이익' if eps_ps_diluted else '기본주당이익'

        for yr in extra_years:
            # 희석_순이익: 손익계산서 지배순이익으로 대체
            if ni_acc.get(f'fy{yr}') is None and income_ni.get(f'fy{yr}') is not None:
                ni_acc[f'fy{yr}'] = income_ni[f'fy{yr}']
                old = ni_acc.get('note', '')
                ni_acc['note'] = (old + f'  FY{yr}: 주석 미제공 → 손익계산서 지배순이익').strip()

            # 희석_주식수: 손익계산서 주당이익 역산 (지배순이익 ÷ 주당이익)
            if sh_acc.get(f'fy{yr}') is None:
                ni_val = ni_acc.get(f'fy{yr}')
                ps_val = validated_row.get(f'fy{yr}') if validated_row else None
                if ni_val and ps_val:
                    sh_acc[f'fy{yr}'] = round(ni_val / ps_val)
                    old = sh_acc.get('note', '')
                    sh_acc['note'] = (old + f'  FY{yr}: {validated_label} 역산').strip()
                else:
                    old = sh_acc.get('note', '')
                    sh_acc['note'] = (old + f'  FY{yr}: 주석 미제공 (대체 출처 없음)').strip()

    # Fix 5 — 전년도 주석에서 D&A 보완 (선택 파일 제공 시)
    if prev_notes_data and prev_notes_data.get('da_rows') and da:
        prev_da = extract_da(prev_notes_data['da_rows'], years)
        for key in ('감가상각비', '무형자산상각비'):
            acc = da.get(key)
            if acc is None or acc.get('matched_label') == '해당 없음':
                continue  # 이중계산 방지 0처리 중이면 건드리지 않음
            still_missing = [yr for yr in years if acc.get(f'fy{yr}') is None]
            if not still_missing:
                continue
            prev_val = prev_da.get(key, {})
            applied = []
            for yr in still_missing:
                v = prev_val.get(f'fy{yr}')
                if v is not None:
                    acc[f'fy{yr}'] = abs(v)
                    applied.append(yr)
            if applied:
                yrs_str = ', '.join(f'FY{y}' for y in applied)
                old = acc.get('note', '')
                acc['note'] = (old + f'  {yrs_str}: 전년도 주석에서 보완').strip()

    # Fix 3 — 응축형 현금흐름 자산부채_변동 역산
    # 자산부채_변동이 '계정 없음'이고 '영업으로부터 창출된 현금흐름' 행이 있으면 역산
    nwc = cashflow.get('자산부채_변동', {})
    if (nwc.get('matched_label') == 'N/A'
            and '계정 없음' in nwc.get('note', '')
            and fs_data.get('cashflow_rows')):
        ocf_row = _find_first(fs_data['cashflow_rows'], CONDENSED_OCF_KEYWORDS, years)
        if ocf_row:
            computed: dict = {}
            applied_yrs = []
            for yr in years:
                ocf_v = ocf_row.get(f'fy{yr}')
                ni_v  = income.get('당기순이익_지배', {}).get(f'fy{yr}')
                if ni_v is None:
                    ni_v = eps.get('희석_순이익', {}).get(f'fy{yr}')
                dep_v = da.get('감가상각비', {}).get(f'fy{yr}') or 0
                amor_v = da.get('무형자산상각비', {}).get(f'fy{yr}') or 0
                sbc_v  = cashflow.get('주식보상비용', {}).get(f'fy{yr}') or 0
                if ocf_v is not None and ni_v is not None:
                    computed[f'fy{yr}'] = ocf_v - ni_v - dep_v - amor_v - sbc_v
                    applied_yrs.append(yr)
                else:
                    computed[f'fy{yr}'] = None
            if applied_yrs:
                computed['matched_label'] = '역산 (영업창출CF - NI - D&A - SBC)'
                computed['note'] = '응축형 현금흐름 역산 근사값: 비현금 기타조정 항목(충당부채·외화환산 등) 포함됨'
                cashflow['자산부채_변동'] = computed

    balance = {}
    if fs_data.get('balance_rows'):
        balance = extract_balance(fs_data['balance_rows'], years)
    else:
        errors.append('재무상태표 시트를 찾지 못했습니다.')

    return {
        'company_name': fs_data.get('company_name') or notes_data.get('company_name') or '기업',
        'years': years,
        'notes_years': notes_years,
        'errors': errors,
        'sections': {
            'income': income,
            'cashflow': cashflow,
            'da': da,
            'eps': eps,
            'balance': balance,
        },
    }
