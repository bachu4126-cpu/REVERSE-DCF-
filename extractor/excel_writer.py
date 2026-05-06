from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime

# ─── 색상 ────────────────────────────────────────────────────
C_SECTION  = "1F4E79"  # 섹션 헤더 (진파랑)
C_COLHEAD  = "BDD7EE"  # 열 헤더 (연파랑)
C_CALC     = "E2EFDA"  # 계산값 (연초록)
C_NA       = "FCE4D6"  # N/A (연주황)
C_FCFE_H   = "375623"  # FCFE 섹션 헤더 (진초록)
C_FCFE_R   = "C6EFCE"  # FCFE 결과 (연초록)
C_ALT      = "F2F2F2"  # 짝수 행 (연회색)
C_WHITE    = "FFFFFF"

BORDER = Border(
    left=Side(style='thin', color='BFBFBF'),
    right=Side(style='thin', color='BFBFBF'),
    top=Side(style='thin', color='BFBFBF'),
    bottom=Side(style='thin', color='BFBFBF'),
)
NUM_FMT = '#,##0'
PCT_FMT = '0.0%'

UNIT_DIVISORS = {'원': 1_000_000, '천원': 1_000, '백만원': 1}


def _fill(c): return PatternFill("solid", fgColor=c)
def _font(bold=False, color="000000", size=10):
    return Font(name="맑은 고딕", bold=bold, color=color, size=size)
def _align(h="center", wrap=False):
    return Alignment(horizontal=h, vertical="center", wrap_text=wrap)


# ─── 데이터 접근 ─────────────────────────────────────────────

def _acc(section: dict, key: str) -> dict | None:
    """섹션 dict에서 계정 dict 반환."""
    return (section or {}).get(key)


def _val(acc: dict | None, year: str, divisor: int = 1):
    """계정 dict에서 특정 연도 값을 백만원 단위로 반환."""
    if acc is None:
        return None
    v = acc.get(f'fy{year}')
    if v is None:
        return None
    try:
        return round(int(v) / divisor)
    except (TypeError, ValueError):
        return None


def _label(acc: dict | None) -> str:
    return (acc or {}).get('matched_label', '')


def _note(acc: dict | None) -> str:
    return (acc or {}).get('note', '')


# ─── 스타일 적용 헬퍼 ────────────────────────────────────────

def _style(cell, bg=C_WHITE, bold=False, color="000000", size=10,
           h="center", wrap=False, fmt=None, border=True):
    cell.fill = _fill(bg)
    cell.font = _font(bold=bold, color=color, size=size)
    cell.alignment = _align(h=h, wrap=wrap)
    if fmt:
        cell.number_format = fmt
    if border:
        cell.border = BORDER


def _set_col_widths(ws, years):
    ws.column_dimensions['A'].width = 32
    for i in range(len(years)):
        ws.column_dimensions[get_column_letter(i + 2)].width = 16
    ws.column_dimensions[get_column_letter(len(years) + 2)].width = 24  # 원본계정명
    ws.column_dimensions[get_column_letter(len(years) + 3)].width = 34  # 메모


# ─── 섹션/헤더 행 ────────────────────────────────────────────

def _section_row(ws, row, title, ncols, bg=C_SECTION):
    ws.merge_cells(f'A{row}:{get_column_letter(ncols)}{row}')
    c = ws[f'A{row}']
    c.value = f'  {title}'
    _style(c, bg=bg, bold=True, color='FFFFFF', size=10, h='left')
    ws.row_dimensions[row].height = 22


def _col_header_row(ws, row, years):
    headers = ['계정명'] + [f'FY{y}\n(백만원)' for y in years] + ['원본 계정명', '메모']
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=col, value=h)
        _style(c, bg=C_COLHEAD, bold=True, size=9, wrap=(col > 1 and col <= len(years) + 1))
    ws.row_dimensions[row].height = 28


def _total_cols(years): return len(years) + 3  # A + year cols + 원본계정명 + 메모


# ─── 데이터 행 ───────────────────────────────────────────────

def _data_row(ws, row, label, acc, years, divisor=1_000_000,
              bg=None, bold=False, fmt=NUM_FMT):
    is_alt = (row % 2 == 0)
    row_bg = bg or (C_ALT if is_alt else C_WHITE)

    # 계정명
    c = ws.cell(row=row, column=1, value=label)
    _style(c, bg=row_bg, bold=bold, size=9, h='left')

    # 연도별 값
    for i, yr in enumerate(years):
        v = _val(acc, yr, divisor)
        cell = ws.cell(row=row, column=i + 2)
        if v is None:
            cell.value = 'N/A'
            _style(cell, bg=C_NA, color='C00000', size=9)
        else:
            cell.value = v
            _style(cell, bg=row_bg, bold=bold, size=9, fmt=fmt)
        cell.alignment = _align(h='right')

    ncols = len(years)
    # 원본 계정명
    c2 = ws.cell(row=row, column=ncols + 2, value=_label(acc))
    _style(c2, bg=row_bg, size=8, color='595959')
    # 메모
    note_txt = _note(acc)
    c3 = ws.cell(row=row, column=ncols + 3, value=note_txt)
    _style(c3, bg=C_NA if note_txt else row_bg, size=8, color='595959', h='left', wrap=True)
    if note_txt:
        c3.fill = _fill(C_NA)

    ws.row_dimensions[row].height = 18
    return row


def _calc_row(ws, row, label, formula_fn, years, bg=C_CALC, fmt=NUM_FMT):
    """엑셀 수식이 들어가는 계산 행."""
    c = ws.cell(row=row, column=1, value=label)
    _style(c, bg=bg, size=9, color='375623', h='left')
    for i, yr in enumerate(years):
        col_l = get_column_letter(i + 2)
        formula = formula_fn(col_l)
        cell = ws.cell(row=row, column=i + 2, value=formula)
        _style(cell, bg=bg, size=9, color='375623', fmt=fmt)
        cell.alignment = _align(h='right')
    ncols = len(years)
    for col in [ncols + 2, ncols + 3]:
        c2 = ws.cell(row=row, column=col, value='계산값' if col == ncols + 2 else '')
        _style(c2, bg=bg, size=8, color='595959')
    ws.row_dimensions[row].height = 18


# ─── 메인 ────────────────────────────────────────────────────

def create_output_excel(data: dict, output_path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "재무데이터_추출"

    company = data.get('company_name', '기업')
    years   = data.get('years', ['2025', '2024', '2023'])
    notes_years = data.get('notes_years', years[:2])
    sec     = data.get('sections', {})

    income  = sec.get('income', {})
    cf      = sec.get('cashflow', {})
    da      = sec.get('da', {})
    eps     = sec.get('eps', {})
    bal     = sec.get('balance', {})

    # 원 단위 (DART 기본) → 백만원 변환
    divisor = 1_000_000

    ncols = _total_cols(years)
    _set_col_widths(ws, years)
    ws.freeze_panes = 'B4'

    # ── 타이틀 ─────────────────────────────────────────────
    row = 1
    ws.merge_cells(f'A1:{get_column_letter(ncols)}1')
    c = ws['A1']
    c.value = f'{company}  재무 데이터 추출  (연결 기준 · 단위: 백만원)'
    _style(c, bg='1F3864', bold=True, color='FFFFFF', size=13, h='center')
    ws.row_dimensions[1].height = 28

    ws.merge_cells(f'A2:{get_column_letter(ncols)}2')
    c = ws['A2']
    c.value = f'추출일: {datetime.now().strftime("%Y-%m-%d")}  |  추출 방식: 규칙 기반 키워드 매칭  |  감가상각비 출처: 성격별 비용 주석(D834300)'
    _style(c, bg=C_WHITE, size=9, color='595959', h='right')
    ws.row_dimensions[2].height = 14

    row = 3

    # ── 섹션 1: 손익계산서 ───────────────────────────────
    _section_row(ws, row, '섹션 1  |  손익계산서 (컨텍스트 지표)', ncols)
    row += 1
    _col_header_row(ws, row, years)
    row += 1

    income_rows = {}
    for key, label in [
        ('매출액',            '매출액'),
        ('매출원가',          '매출원가'),
        ('판매비와관리비',    '판매비와관리비'),
        ('영업이익',          '영업이익'),
        ('법인세차감전순이익','법인세차감전순이익'),
        ('법인세비용',        '법인세비용'),
        ('당기순이익_지배',   '당기순이익 (지배지분)'),
    ]:
        _data_row(ws, row, label, _acc(income, key), years, divisor)
        income_rows[key] = row
        row += 1

    # 영업이익률 (계산)
    oi_r  = income_rows.get('영업이익')
    rev_r = income_rows.get('매출액')
    if oi_r and rev_r:
        _calc_row(ws, row, '영업이익률',
                  lambda col: f'=IFERROR({col}{oi_r}/{col}{rev_r},"")',
                  years, fmt=PCT_FMT)
        row += 1

    row += 1  # 간격

    # ── 섹션 2: FCFE 구성요소 ────────────────────────────
    _section_row(ws, row, '섹션 2  |  FCFE 구성요소', ncols)
    row += 1
    _col_header_row(ws, row, years)
    row += 1

    fcfe_rows = {}

    # ① 희석 당기순이익 (주석 연도 기준)
    _data_row(ws, row, '① 희석효과 포함 당기순이익', _acc(eps, '희석_순이익'), years, divisor)
    fcfe_rows['ni'] = row
    row += 1

    # ② 비현금성 비용
    for key, label in [
        ('감가상각비',     '② + 감가상각비'),
        ('무형자산상각비', '② + 무형자산상각비'),
    ]:
        _data_row(ws, row, label, _acc(da, key), years, divisor)
        fcfe_rows[key] = row
        row += 1

    sbc = _acc(cf, '주식보상비용')
    _data_row(ws, row, '② + 주식보상비용', sbc, years, divisor)
    fcfe_rows['sbc'] = row
    row += 1

    # ③ CAPEX (절댓값으로 저장됨)
    for key, label in [
        ('유형자산_취득', '③ - 유형자산의 취득 (CAPEX)'),
        ('무형자산_취득', '③ - 무형자산의 취득'),
    ]:
        _data_row(ws, row, label, _acc(cf, key), years, divisor)
        fcfe_rows[key] = row
        row += 1

    # ④ 운전자본 변동
    _data_row(ws, row, '④ +/- 운전자본 변동 합계 (ΔNWC)', _acc(cf, '자산부채_변동'), years, divisor)
    fcfe_rows['nwc'] = row
    row += 1

    # ⑤ 재무활동
    for key, label in [
        ('차입금_유입', '⑤ + 차입금의 유입'),
        ('차입금_상환', '⑤ - 차입금의 상환'),
    ]:
        _data_row(ws, row, label, _acc(cf, key), years, divisor)
        fcfe_rows[key] = row
        row += 1

    row += 1

    # ── 섹션 3: 주식 정보 ────────────────────────────────
    _section_row(ws, row, '섹션 3  |  주식 정보', ncols)
    row += 1
    _col_header_row(ws, row, years)
    row += 1

    share_row = row
    share_acc = _acc(eps, '희석_주식수')
    # 주식수: 단위 변환 없이 그대로 (주 단위)
    c = ws.cell(row=row, column=1, value='⑥ 희석평균유통보통주식수')
    _style(c, size=9, h='left')
    for i, yr in enumerate(years):
        v = share_acc.get(f'fy{yr}') if share_acc else None
        cell = ws.cell(row=row, column=i + 2)
        if v is None:
            cell.value = 'N/A'
            _style(cell, bg=C_NA, color='C00000', size=9)
        else:
            try:
                cell.value = int(float(v))
                _style(cell, size=9, fmt=NUM_FMT)
            except (TypeError, ValueError):
                cell.value = v
                _style(cell, size=9)
        cell.alignment = _align(h='right')
    ncols_yr = len(years)
    ws.cell(row=row, column=ncols_yr + 2).value = _label(share_acc)
    _style(ws.cell(row=row, column=ncols_yr + 2), size=8, color='595959')
    ws.cell(row=row, column=ncols_yr + 3).value = '단위: 주(shares)  ' + _note(share_acc)
    _style(ws.cell(row=row, column=ncols_yr + 3), size=8, color='595959', h='left')
    ws.row_dimensions[row].height = 18
    row += 1
    row += 1

    # ── 섹션 4: 재무 건전성 ──────────────────────────────
    _section_row(ws, row, '섹션 4  |  재무 건전성 (재무상태표 기준)', ncols)
    row += 1
    _col_header_row(ws, row, years)
    row += 1

    bal_rows = {}
    for key, label in [
        ('부채총계',        '부채총계'),
        ('자기자본_지배',   '자기자본 (지배지분)'),
        ('현금',            '현금및현금성자산'),
        ('단기차입금',      '단기차입금'),
        ('유동성장기부채',  '유동성 장기부채'),
        ('장기차입금',      '장기차입금'),
        ('사채_유동',       '사채 (유동)'),
        ('사채_비유동',     '사채 (비유동)'),
    ]:
        _data_row(ws, row, label, _acc(bal, key), years, divisor)
        bal_rows[key] = row
        row += 1

    # 부채비율 (계산)
    d_r = bal_rows.get('부채총계')
    e_r = bal_rows.get('자기자본_지배')
    if d_r and e_r:
        _calc_row(ws, row, '부채비율',
                  lambda col: f'=IFERROR({col}{d_r}/{col}{e_r},"")',
                  years, fmt=PCT_FMT)
        row += 1

    # 총차입금 (계산)
    debt_keys = ['단기차입금', '유동성장기부채', '장기차입금', '사채_유동', '사채_비유동']
    d_rows = [bal_rows[k] for k in debt_keys if k in bal_rows]
    total_debt_row = None
    if d_rows:
        def total_debt_formula(col):
            refs = '+'.join(f'IF(ISNUMBER({col}{r}),{col}{r},0)' for r in d_rows)
            return f'={refs}'
        _calc_row(ws, row, '총차입금 (합계)', total_debt_formula, years)
        total_debt_row = row
        row += 1

    # 순부채 (계산)
    cash_r = bal_rows.get('현금')
    if total_debt_row and cash_r:
        _calc_row(ws, row, '순부채 (총차입금 - 현금, 참고용)',
                  lambda col: f'=IFERROR({col}{total_debt_row}-{col}{cash_r},"")',
                  years)
        row += 1

    row += 1

    # ── 섹션 5: FCFE 계산 결과 ───────────────────────────
    _section_row(ws, row, '섹션 5  |  FCFE 계산 결과', ncols, bg=C_FCFE_H)
    row += 1
    _col_header_row(ws, row, years)
    row += 1

    # FCFE = 순이익 + D&A + SBC - CAPEX(abs) + ΔNWC + 차입유입 - 차입상환(abs)
    ni_r   = fcfe_rows.get('ni')
    dep_r  = fcfe_rows.get('감가상각비')
    amor_r = fcfe_rows.get('무형자산상각비')
    sbc_r  = fcfe_rows.get('sbc')
    ppe_r  = fcfe_rows.get('유형자산_취득')
    ia_r   = fcfe_rows.get('무형자산_취득')
    nwc_r  = fcfe_rows.get('nwc')
    borr_r = fcfe_rows.get('차입금_유입')
    rep_r  = fcfe_rows.get('차입금_상환')

    def fcfe_formula(col):
        # 순이익·감가상각비·무형상각비가 N/A이면 FCFE 미산출 (과소평가 방지)
        required = [r for r in [ni_r, dep_r, amor_r] if r]
        guards = [f'NOT(ISNUMBER({col}{r}))' for r in required]

        parts = []
        if ni_r:   parts.append(f'IF(ISNUMBER({col}{ni_r}),{col}{ni_r},0)')
        if dep_r:  parts.append(f'IF(ISNUMBER({col}{dep_r}),{col}{dep_r},0)')
        if amor_r: parts.append(f'IF(ISNUMBER({col}{amor_r}),{col}{amor_r},0)')
        if sbc_r:  parts.append(f'IF(ISNUMBER({col}{sbc_r}),{col}{sbc_r},0)')
        if ppe_r:  parts.append(f'-IF(ISNUMBER({col}{ppe_r}),{col}{ppe_r},0)')
        if ia_r:   parts.append(f'-IF(ISNUMBER({col}{ia_r}),{col}{ia_r},0)')
        if nwc_r:  parts.append(f'IF(ISNUMBER({col}{nwc_r}),{col}{nwc_r},0)')
        if borr_r: parts.append(f'IF(ISNUMBER({col}{borr_r}),{col}{borr_r},0)')
        if rep_r:  parts.append(f'-IF(ISNUMBER({col}{rep_r}),{col}{rep_r},0)')
        calc = '+ '.join(parts) if parts else '0'
        if guards:
            return f'=IF(OR({",".join(guards)}),"",{calc})'
        return f'={calc}'

    # FCFE 행
    c = ws.cell(row=row, column=1, value='FCFE')
    _style(c, bg=C_FCFE_R, bold=True, size=10, h='left')
    for i, yr in enumerate(years):
        col_l = get_column_letter(i + 2)
        cell = ws.cell(row=row, column=i + 2, value=fcfe_formula(col_l))
        _style(cell, bg=C_FCFE_R, bold=True, size=10, fmt=NUM_FMT)
        cell.alignment = _align(h='right')
    for col in [len(years) + 2, len(years) + 3]:
        ws.cell(row=row, column=col).fill = _fill(C_FCFE_R)
        _style(ws.cell(row=row, column=col), bg=C_FCFE_R,
               size=8, color='595959')
    ws.row_dimensions[row].height = 22
    fcfe_row = row
    row += 1

    # 주당 FCFE
    def per_share_formula(col):
        return f'=IFERROR({col}{fcfe_row}*1000000/{col}{share_row},"")'

    _calc_row(ws, row, '주당 FCFE (원)',
              per_share_formula, years, bg=C_CALC)
    row += 1

    # ── 오류/경고 ─────────────────────────────────────────
    errors = data.get('errors', [])
    if errors:
        row += 1
        ws.merge_cells(f'A{row}:{get_column_letter(ncols)}{row}')
        c = ws.cell(row=row, column=1,
                    value='⚠ 추출 중 발생한 오류/경고: ' + '  |  '.join(errors))
        _style(c, bg='FFF2CC', color='7F6000', size=8, h='left', wrap=True)
        ws.row_dimensions[row].height = 30

    wb.save(output_path)
