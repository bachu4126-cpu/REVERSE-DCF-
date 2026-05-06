import re
import openpyxl


# DART 표준 시트 코드 (연결 기준)
INCOME_CODES = {'D431410', 'D431400', 'D431000', 'D431005', 'D310000', 'D310005'}
CASHFLOW_CODES = {'D520000', 'D521000', 'D522000'}
BALANCE_CODES = {'D210000', 'D211000', 'D212000'}
EPS_NOTE_CODES = {'D838000', 'D838010', 'D838100'}
DA_NOTE_CODES = {'D834300', 'D834310', 'D834305'}  # 성격별 비용 분류
SBP_NOTE_CODES = {'D851100', 'D851105'}             # 주식기준보상 주석

_YEAR_RE = re.compile(r'(\d{4})-\d{2}-\d{2}')


def load_workbook_safe(file_path: str):
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return openpyxl.load_workbook(file_path, data_only=True)


# ──────────────────────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────────────────────

def _merged_map(sheet) -> dict:
    """병합 셀 값 맵 반환: (row, col) → top-left 값"""
    m = {}
    for rng in sheet.merged_cells.ranges:
        top_val = sheet.cell(rng.min_row, rng.min_col).value
        for r in range(rng.min_row, rng.max_row + 1):
            for c in range(rng.min_col, rng.max_col + 1):
                if not (r == rng.min_row and c == rng.min_col):
                    m[(r, c)] = top_val
    return m


def _cell_val(sheet, merged_map, row_idx, col_idx):
    return merged_map.get((row_idx, col_idx),
                          sheet.cell(row_idx, col_idx).value)


def _find_sheet_by_codes(workbook, codes: set):
    upper = {c.upper() for c in codes}
    for name in workbook.sheetnames:
        if name.upper() in upper:
            return workbook[name], name
    return None, None


def _find_sheet_by_keyword(workbook, keywords: list, exclude: list = None):
    exclude = exclude or []
    candidates = [n for n in workbook.sheetnames
                  if any(k in n for k in keywords)
                  and not any(e in n for e in exclude)]
    if not candidates:
        return None, None
    for n in candidates:
        if '연결' in n:
            return workbook[n], n
    return workbook[candidates[0]], candidates[0]


def _extract_company_name(workbook) -> str:
    try:
        if '공시기본정보' in workbook.sheetnames:
            sheet = workbook['공시기본정보']
            for row in sheet.iter_rows(max_row=60, values_only=True):
                for i, cell in enumerate(row):
                    if cell and ('회사명' in str(cell) or '법인명' in str(cell)):
                        if i + 1 < len(row) and row[i + 1]:
                            return str(row[i + 1]).strip()
    except Exception:
        pass
    return ''


# ──────────────────────────────────────────────────────────────
# 연도 탐지
# ──────────────────────────────────────────────────────────────

def _detect_years(sheet, merged_map, max_header_rows: int = 12) -> list[str]:
    """
    헤더 행에서 연도(YYYY) 추출.
    "2025-01-01 ~ 2025-12-31" 형태에서 연도를 뽑아 내림차순 반환.
    """
    years_found = []
    ncols = sheet.max_column or 5
    for r in range(1, max_header_rows + 1):
        row_years = []
        for c in range(2, ncols + 1):
            v = str(_cell_val(sheet, merged_map, r, c) or '')
            m = _YEAR_RE.search(v)
            if m:
                yr = m.group(1)
                if yr not in row_years:
                    row_years.append(yr)
        if len(row_years) >= 2:
            return sorted(row_years, reverse=True)  # 최신 연도 먼저
    return []


# ──────────────────────────────────────────────────────────────
# 구조화된 행 데이터 변환 (규칙 기반 추출용)
# ──────────────────────────────────────────────────────────────

def parse_number(v) -> int | None:
    """셀 값을 정수로 변환. 괄호=(음수), None/'-'=None."""
    if v is None:
        return None
    s = str(v).replace(',', '').replace(' ', '').strip()
    if s in ('', '-', 'None', 'nan'):
        return None
    if s.startswith('(') and s.endswith(')'):
        try:
            return -int(float(s[1:-1]))
        except ValueError:
            return None
    try:
        return int(float(s))
    except ValueError:
        return None


def sheet_to_rows(sheet, years: list[str], max_rows: int = 200) -> list[dict]:
    """
    시트를 구조화된 행 목록으로 변환.
    반환: [{'account': str, 'raw': str, 'indent': int, 'fy<YYYY>': int|None, ...}]
    """
    merged = _merged_map(sheet)
    ncols = sheet.max_column or 5

    # 연도 → 열 인덱스 매핑 (헤더에서 탐지)
    year_col_map: dict[str, int] = {}
    for r in range(1, 14):
        for c in range(2, min(ncols + 1, 8)):
            v = str(_cell_val(sheet, merged, r, c) or '')
            m = _YEAR_RE.search(v)
            if m:
                yr = m.group(1)
                if yr in years and yr not in year_col_map:
                    year_col_map[yr] = c

    rows = []
    for r in range(1, max_rows + 1):
        raw = _cell_val(sheet, merged, r, 1)
        if raw is None:
            continue
        raw_str = str(raw)
        account = raw_str.strip()
        if not account:
            continue

        # 들여쓰기 레벨 (앞 공백 수)
        indent = len(raw_str) - len(raw_str.lstrip('  \t'))

        row_dict: dict = {'account': account, 'raw': raw_str, 'indent': indent}
        for yr, col in year_col_map.items():
            row_dict[f'fy{yr}'] = parse_number(_cell_val(sheet, merged, r, col))

        # 연도 컬럼이 탐지 안 됐을 경우 순서 기반 fallback
        if not year_col_map and years:
            for i, yr in enumerate(years):
                col = i + 2
                row_dict[f'fy{yr}'] = parse_number(_cell_val(sheet, merged, r, col))

        rows.append(row_dict)

    return rows


# ──────────────────────────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────────────────────────

def read_financial_statement(file_path: str) -> dict:
    """DART 재무제표 엑셀 파싱. 연결 기준 3개 시트 반환."""
    wb = load_workbook_safe(file_path)
    company_name = _extract_company_name(wb)

    income_sheet, income_name = _find_sheet_by_codes(wb, INCOME_CODES)
    if not income_sheet:
        income_sheet, income_name = _find_sheet_by_keyword(
            wb, ['손익', '포괄손익'], ['별도', '005'])

    cashflow_sheet, cashflow_name = _find_sheet_by_codes(wb, CASHFLOW_CODES)
    if not cashflow_sheet:
        cashflow_sheet, cashflow_name = _find_sheet_by_keyword(
            wb, ['현금흐름'], ['별도', '005'])

    balance_sheet_obj, balance_name = _find_sheet_by_codes(wb, BALANCE_CODES)
    if not balance_sheet_obj:
        balance_sheet_obj, balance_name = _find_sheet_by_keyword(
            wb, ['재무상태표', '대차대조표'], ['별도', '005'])

    # 연도 탐지 (손익계산서 기준)
    years: list[str] = []
    if income_sheet:
        years = _detect_years(income_sheet, _merged_map(income_sheet))
    if not years and cashflow_sheet:
        years = _detect_years(cashflow_sheet, _merged_map(cashflow_sheet))
    if not years:
        years = ['2025', '2024', '2023']

    return {
        'company_name': company_name,
        'sheet_names': list(wb.sheetnames),
        'years': years,
        # 구조화 행 (규칙 기반 추출용)
        'income_rows': sheet_to_rows(income_sheet, years) if income_sheet else [],
        'cashflow_rows': sheet_to_rows(cashflow_sheet, years) if cashflow_sheet else [],
        'balance_rows': sheet_to_rows(balance_sheet_obj, years) if balance_sheet_obj else [],
        # 시트명
        'income_sheet_name': income_name,
        'cashflow_sheet_name': cashflow_name,
        'balance_sheet_name': balance_name,
    }


def read_notes(file_path: str) -> dict:
    """DART 재무제표 주석 엑셀 파싱. 주당이익 + 성격별 비용 시트 반환."""
    wb = load_workbook_safe(file_path)
    company_name = _extract_company_name(wb)

    # 주당이익 주석 (D838000)
    eps_sheet, eps_name = _find_sheet_by_codes(wb, EPS_NOTE_CODES)
    if not eps_sheet:
        eps_sheet, eps_name = _find_sheet_by_keyword(
            wb, ['주당이익', '주당순이익', 'EPS', '주당손익'], ['별도', '005'])

    # 성격별 비용 주석 — D834300(전사 합계) 우선, 없으면 D834310(판관비 내역)
    da_sheet, da_name = _find_sheet_by_codes(wb, {'D834300', 'D834305'})
    if not da_sheet:
        da_sheet, da_name = _find_sheet_by_codes(wb, {'D834310', 'D834315'})
    if not da_sheet:
        da_sheet, da_name = _find_sheet_by_keyword(
            wb, ['성격별', '비용의 성격'], ['별도', '005'])

    # 주식기준보상 주석 (D851100) — 주식보상비용 fallback 출처
    sbp_sheet, sbp_name = _find_sheet_by_codes(wb, SBP_NOTE_CODES)
    if not sbp_sheet:
        sbp_sheet, sbp_name = _find_sheet_by_keyword(
            wb, ['주식기준보상', '주식보상'], ['별도', '005'])

    # 연도 탐지
    years: list[str] = []
    if eps_sheet:
        years = _detect_years(eps_sheet, _merged_map(eps_sheet))
    if not years and da_sheet:
        years = _detect_years(da_sheet, _merged_map(da_sheet))
    if not years:
        years = ['2025', '2024']

    return {
        'company_name': company_name,
        'sheet_names': list(wb.sheetnames),
        'years': years,
        'eps_rows': sheet_to_rows(eps_sheet, years) if eps_sheet else [],
        'da_rows': sheet_to_rows(da_sheet, years) if da_sheet else [],
        'sbp_rows': sheet_to_rows(sbp_sheet, years) if sbp_sheet else [],
        'eps_sheet_name': eps_name,
        'da_sheet_name': da_name,
        'sbp_sheet_name': sbp_name,
    }
