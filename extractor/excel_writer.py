from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime

# ─── 색상 ────────────────────────────────────────────────────
C_SECTION  = "1F4E79"  # 섹션 헤더 (진파랑)
C_COLHEAD  = "BDD7EE"  # 열 헤더 (연파랑)
C_CALC     = "E2EFDA"  # 계산값 (연초록)
C_NA       = "FCE4D6"  # N/A (연주황)
C_FCFF_H   = "375623"  # FCFF 섹션 헤더 (진초록)
C_FCFF_R   = "C6EFCE"  # FCFF 결과 (연초록)
C_ALT      = "F2F2F2"  # 짝수 행 / 참조 행 (연회색)
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
    return (section or {}).get(key)


def _val(acc: dict | None, year: str, divisor: int = 1):
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
    ws.column_dimensions[get_column_letter(len(years) + 2)].width = 24
    ws.column_dimensions[get_column_letter(len(years) + 3)].width = 34


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


def _total_cols(years): return len(years) + 3


# ─── 데이터 행 ───────────────────────────────────────────────

def _data_row(ws, row, label, acc, years, divisor=1_000_000,
              bg=None, bold=False, fmt=NUM_FMT):
    is_alt = (row % 2 == 0)
    row_bg = bg or (C_ALT if is_alt else C_WHITE)

    c = ws.cell(row=row, column=1, value=label)
    _style(c, bg=row_bg, bold=bold, size=9, h='left')

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
    c2 = ws.cell(row=row, column=ncols + 2, value=_label(acc))
    _style(c2, bg=row_bg, size=8, color='595959')
    note_txt = _note(acc)
    c3 = ws.cell(row=row, column=ncols + 3, value=note_txt)
    _style(c3, bg=C_NA if note_txt else row_bg, size=8, color='595959', h='left', wrap=True)
    if note_txt:
        c3.fill = _fill(C_NA)

    ws.row_dimensions[row].height = 18
    return row


def _calc_row(ws, row, label, formula_fn, years, bg=C_CALC, fmt=NUM_FMT,
              text_color='375623'):
    """엑셀 수식이 들어가는 계산 행. text_color로 레이블·값 색상 지정."""
    c = ws.cell(row=row, column=1, value=label)
    _style(c, bg=bg, size=9, color=text_color, h='left')
    for i, yr in enumerate(years):
        col_l = get_column_letter(i + 2)
        formula = formula_fn(col_l)
        cell = ws.cell(row=row, column=i + 2, value=formula)
        _style(cell, bg=bg, size=9, color=text_color, fmt=fmt)
        cell.alignment = _align(h='right')
    ncols = len(years)
    for col in [ncols + 2, ncols + 3]:
        c2 = ws.cell(row=row, column=col,
                     value='섹션 1 참조' if text_color == '595959' else
                           ('계산값' if col == ncols + 2 else ''))
        _style(c2, bg=bg, size=8, color='595959')
    ws.row_dimensions[row].height = 18


def _fcff_result_row(ws, row, label, formula_fn, years):
    """FCFF 결과 행 (Section 2 미리보기 / Section 5 공용)."""
    c = ws.cell(row=row, column=1, value=label)
    _style(c, bg=C_FCFF_R, bold=True, size=10, h='left')
    for i, yr in enumerate(years):
        col_l = get_column_letter(i + 2)
        cell = ws.cell(row=row, column=i + 2, value=formula_fn(col_l))
        _style(cell, bg=C_FCFF_R, bold=True, size=10, fmt=NUM_FMT)
        cell.alignment = _align(h='right')
    for col in [len(years) + 2, len(years) + 3]:
        _style(ws.cell(row=row, column=col), bg=C_FCFF_R, size=8, color='595959')
    ws.row_dimensions[row].height = 22


# ─── 메인 ────────────────────────────────────────────────────

def create_output_excel(data: dict, output_path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "재무데이터_추출"

    company     = data.get('company_name', '기업')
    years       = data.get('years', ['2025', '2024', '2023'])
    notes_years = data.get('notes_years', years[:2])
    sec         = data.get('sections', {})

    income = sec.get('income', {})
    cf     = sec.get('cashflow', {})
    da     = sec.get('da', {})
    eps    = sec.get('eps', {})
    bal    = sec.get('balance', {})

    divisor = 1_000_000  # 원 → 백만원

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
    c.value = (f'추출일: {datetime.now().strftime("%Y-%m-%d")}  |  추출 방식: 규칙 기반 키워드 매칭'
               f'  |  감가상각비 출처: 성격별 비용 주석(D834300)')
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

    oi_r  = income_rows.get('영업이익')
    rev_r = income_rows.get('매출액')
    if oi_r and rev_r:
        _calc_row(ws, row, '영업이익률',
                  lambda col: f'=IFERROR({col}{oi_r}/{col}{rev_r},"")',
                  years, fmt=PCT_FMT)
        row += 1

    row += 1  # 간격

    # ── 섹션 2: FCFF 구성요소 ────────────────────────────
    _section_row(ws, row, '섹션 2  |  FCFF 구성요소', ncols)
    row += 1
    _col_header_row(ws, row, years)
    row += 1

    fcff_rows = {}

    # ① 영업이익 (EBIT)
    _data_row(ws, row, '① 영업이익 (EBIT)', _acc(income, '영업이익'), years, divisor)
    fcff_rows['ebit'] = row
    row += 1

    # ② 세전이익 · 법인세비용 — Section 1 참조 (회색 스타일)
    pretax_sec1_r = income_rows['법인세차감전순이익']
    _calc_row(ws, row, '② 세전이익   (↑ 섹션 1 참조)',
              lambda col, _r=pretax_sec1_r: f'={col}{_r}',
              years, bg=C_ALT, fmt=NUM_FMT, text_color='595959')
    fcff_rows['세전이익'] = row
    row += 1

    tax_sec1_r = income_rows['법인세비용']
    _calc_row(ws, row, '② 법인세비용 (↑ 섹션 1 참조)',
              lambda col, _r=tax_sec1_r: f'={col}{_r}',
              years, bg=C_ALT, fmt=NUM_FMT, text_color='595959')
    fcff_rows['법인세비용'] = row
    row += 1

    # ③ 유효세율 — 0 ~ 100% 클램프
    pretax_r = fcff_rows['세전이익']
    tax_r    = fcff_rows['법인세비용']
    _calc_row(ws, row, '③ 유효세율 t (법인세비용 / 세전이익)',
              lambda col, _p=pretax_r, _t=tax_r:
                  f'=MAX(0,MIN(1,IFERROR({col}{_t}/{col}{_p},0)))',
              years, fmt=PCT_FMT)
    fcff_rows['세율'] = row
    row += 1

    # ④ NOPAT
    ebit_r = fcff_rows['ebit']
    t_r    = fcff_rows['세율']
    _calc_row(ws, row, '④ NOPAT = EBIT × (1-t)',
              lambda col, _e=ebit_r, _t=t_r:
                  f'=IF(ISNUMBER({col}{_e}),{col}{_e}*(1-IFERROR({col}{_t},0)),"")',
              years, fmt=NUM_FMT)
    fcff_rows['nopat'] = row
    row += 1

    # ⑤ D&A
    for key, label in [
        ('감가상각비',     '⑤ + 감가상각비'),
        ('무형자산상각비', '⑤ + 무형자산상각비'),
    ]:
        _data_row(ws, row, label, _acc(da, key), years, divisor)
        fcff_rows[key] = row
        row += 1

    # ⑥ CAPEX
    for key, label in [
        ('유형자산_취득', '⑥ - 유형자산의 취득 (CAPEX)'),
        ('무형자산_취득', '⑥ - 무형자산의 취득'),
    ]:
        _data_row(ws, row, label, _acc(cf, key), years, divisor)
        fcff_rows[key] = row
        row += 1

    # ⑦ ΔNWC
    _data_row(ws, row, '⑦ +/- 운전자본 변동 합계 (ΔNWC)', _acc(cf, '자산부채_변동'), years, divisor)
    fcff_rows['nwc'] = row
    row += 1

    # ── Section 2 하단: FCFF 미리보기 ────────────────────
    nopat_r = fcff_rows.get('nopat')
    dep_r   = fcff_rows.get('감가상각비')
    amor_r  = fcff_rows.get('무형자산상각비')
    ppe_r   = fcff_rows.get('유형자산_취득')
    ia_r    = fcff_rows.get('무형자산_취득')
    nwc_r   = fcff_rows.get('nwc')

    def fcff_formula(col):
        required = [r for r in [nopat_r, dep_r, amor_r] if r]
        guards = [f'NOT(ISNUMBER({col}{r}))' for r in required]
        parts = []
        if nopat_r: parts.append(f'IF(ISNUMBER({col}{nopat_r}),{col}{nopat_r},0)')
        if dep_r:   parts.append(f'IF(ISNUMBER({col}{dep_r}),{col}{dep_r},0)')
        if amor_r:  parts.append(f'IF(ISNUMBER({col}{amor_r}),{col}{amor_r},0)')
        if ppe_r:   parts.append(f'-IF(ISNUMBER({col}{ppe_r}),{col}{ppe_r},0)')
        if ia_r:    parts.append(f'-IF(ISNUMBER({col}{ia_r}),{col}{ia_r},0)')
        if nwc_r:   parts.append(f'IF(ISNUMBER({col}{nwc_r}),{col}{nwc_r},0)')
        calc = '+ '.join(parts) if parts else '0'
        if guards:
            return f'=IF(OR({",".join(guards)}),"",{calc})'
        return f'={calc}'

    row += 1  # 구분선 간격
    _fcff_result_row(ws, row, 'FCFF', fcff_formula, years)
    fcff_sec2_row = row
    row += 1

    row += 1  # 섹션 간 간격

    # ── 섹션 3: 주식 정보 ────────────────────────────────
    _section_row(ws, row, '섹션 3  |  주식 정보', ncols)
    row += 1
    _col_header_row(ws, row, years)
    row += 1

    share_row = row
    share_acc = _acc(eps, '희석_주식수')
    c = ws.cell(row=row, column=1, value='⑧ 희석평균유통보통주식수')
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

    d_r = bal_rows.get('부채총계')
    e_r = bal_rows.get('자기자본_지배')
    if d_r and e_r:
        _calc_row(ws, row, '부채비율',
                  lambda col: f'=IFERROR({col}{d_r}/{col}{e_r},"")',
                  years, fmt=PCT_FMT)
        row += 1

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

    cash_r = bal_rows.get('현금')
    net_debt_row = None
    if total_debt_row and cash_r:
        _calc_row(ws, row, '순부채 (총차입금 - 현금, 참고용)',
                  lambda col: f'=IFERROR({col}{total_debt_row}-{col}{cash_r},"")',
                  years)
        net_debt_row = row
        row += 1

    row += 1

    # ── 섹션 5: FCFF 계산 결과 ───────────────────────────
    _section_row(ws, row, '섹션 5  |  FCFF 계산 결과 (섹션 2 참조)', ncols, bg=C_FCFF_H)
    row += 1
    _col_header_row(ws, row, years)
    row += 1

    # Section 2 FCFF 행을 참조
    def fcff_ref_formula(col):
        return f'={col}{fcff_sec2_row}'

    _fcff_result_row(ws, row, 'FCFF', fcff_ref_formula, years)
    fcff_row = row
    row += 1

    # 주당 FCFF
    def per_share_formula(col):
        return f'=IFERROR({col}{fcff_row}*1000000/{col}{share_row},"")'

    _calc_row(ws, row, '주당 FCFF (원)', per_share_formula, years, bg=C_CALC)
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

    _add_dcf_sheet(wb, company, years, fcff_row, share_row, net_debt_row)
    wb.save(output_path)


# ─── DCF 시트 ─────────────────────────────────────────────────

def _add_dcf_sheet(wb: Workbook, company: str, years: list[str],
                   fcff_row: int | None, share_row: int | None,
                   net_debt_row: int | None):
    """Reverse DCF 입력·계산·민감도 시트 추가."""
    ws = wb.create_sheet('Reverse DCF')
    REF = '재무데이터_추출'   # 메인 시트명

    C_INPUT  = 'FFF2CC'   # 입력 셀 (노란색)
    C_RESULT = 'E2EFDA'   # 결과 행
    C_STAR   = 'C6EFCE'   # ★ 적정주가 행
    C_SENS_H = 'BDD7EE'   # 민감도 헤더
    C_SENS_C = 'DDEEFF'   # 민감도 현재 WACC 행
    C_WARN   = 'FCE4D6'   # 경고/주석

    def _w(col_letter, width):
        ws.column_dimensions[col_letter].width = width

    _w('A', 30); _w('B', 16); _w('C', 18)
    for ltr in ['D', 'E', 'F', 'G', 'H']:
        _w(ltr, 13)

    # ── 타이틀 ──────────────────────────────────────────────
    ws.merge_cells('A1:H1')
    c = ws['A1']
    c.value = f'Reverse DCF 분석기  |  {company}'
    _style(c, bg='1F3864', bold=True, color='FFFFFF', size=13, h='center')
    ws.row_dimensions[1].height = 28

    ws.merge_cells('A2:H2')
    c = ws['A2']
    c.value = '2단계 DCF (명시적 N년 + 영구가치)  |  입력 가정(노란 셀)을 직접 수정하세요'
    _style(c, bg=C_WHITE, size=9, color='595959', h='center')
    ws.row_dimensions[2].height = 14

    row = 3

    # ── 섹션: 입력 가정 ─────────────────────────────────────
    ws.merge_cells(f'A{row}:H{row}')
    c = ws[f'A{row}']
    c.value = '  ■ 입력 가정'
    _style(c, bg=C_SECTION, bold=True, color='FFFFFF', size=10, h='left')
    ws.row_dimensions[row].height = 22
    row += 1

    INPUT_ROW = {}  # label → row num

    def _input_row(label, default, unit='', note='', pct=False):
        nonlocal row
        c = ws.cell(row=row, column=1, value=label)
        _style(c, size=9, h='left')
        b = ws.cell(row=row, column=2, value=default)
        b.fill = _fill(C_INPUT)
        b.font = _font(bold=True, size=10)
        b.alignment = _align(h='right')
        b.border = BORDER
        if pct:
            b.number_format = '0.0%'
        ws.cell(row=row, column=3, value=unit).font = _font(size=8, color='595959')
        if note:
            nc = ws.cell(row=row, column=4, value=note)
            _style(nc, size=8, color='8E8B82', h='left', border=False)
            ws.merge_cells(f'D{row}:H{row}')
        ws.row_dimensions[row].height = 20
        r = row
        row += 1
        return r

    INPUT_ROW['wacc'] = _input_row('WACC (할인율)', 0.10, '%', '예: 10% → 0.10', pct=True)
    INPUT_ROW['g1']   = _input_row('고성장률 g₁ (예측기간 내)', 0.12, '%', '예: 12% → 0.12', pct=True)
    INPUT_ROW['g2']   = _input_row('영구성장률 g₂ (Terminal)', 0.03, '%', '예: 3% → 0.03 · WACC보다 작아야 함', pct=True)
    INPUT_ROW['n']    = _input_row('예측기간 N (년)', 5, '년', '정수 입력 (1~20)')
    INPUT_ROW['price']= _input_row('현재주가 (원)', None, '원', '증권앱에서 확인 후 입력')
    row += 1  # 간격

    WACC_R  = INPUT_ROW['wacc']
    G1_R    = INPUT_ROW['g1']
    G2_R    = INPUT_ROW['g2']
    N_R     = INPUT_ROW['n']
    PRICE_R = INPUT_ROW['price']

    WC = f'B{WACC_R}'   # WACC 셀 참조
    G1C = f'B{G1_R}'
    G2C = f'B{G2_R}'
    NC  = f'B{N_R}'
    PC  = f'B{PRICE_R}'

    # ── 섹션: 재무 기준값 ────────────────────────────────────
    ws.merge_cells(f'A{row}:H{row}')
    c = ws[f'A{row}']
    c.value = '  ■ 재무 기준값 (메인 시트 자동 참조)'
    _style(c, bg=C_SECTION, bold=True, color='FFFFFF', size=10, h='left')
    ws.row_dimensions[row].height = 22
    row += 1

    # 기준 연도 선택 (CHOOSE 인덱스)
    yr_note = '  '.join(f'{i+1}={y}' for i, y in enumerate(years))
    yr_input_row = row
    c = ws.cell(row=row, column=1, value='기준 연도 (숫자 입력)')
    _style(c, size=9, h='left')
    b = ws.cell(row=row, column=2, value=1)
    b.fill = _fill(C_INPUT)
    b.font = _font(bold=True, size=10)
    b.alignment = _align(h='right')
    b.border = BORDER
    nc = ws.cell(row=row, column=3, value=yr_note)
    _style(nc, size=8, color='595959', h='left', border=False)
    ws.merge_cells(f'C{row}:H{row}')
    ws.row_dimensions[row].height = 20
    row += 1

    YR_C = f'B{yr_input_row}'

    # FCFF₀
    def _choose_ref(target_row, fallback='0'):
        if target_row is None:
            return f'={fallback}'
        refs = ','.join(
            f"'{REF}'!{get_column_letter(i+2)}{target_row}"
            for i in range(len(years))
        )
        return f'=IFERROR(CHOOSE({YR_C},{refs}),{fallback})'

    FCFF0_R = row
    c = ws.cell(row=row, column=1, value='FCFF₀ (백만원)')
    _style(c, bg=C_RESULT, size=9, h='left')
    b = ws.cell(row=row, column=2, value=_choose_ref(fcff_row))
    _style(b, bg=C_RESULT, size=9, fmt=NUM_FMT)
    b.alignment = _align(h='right')
    ws.row_dimensions[row].height = 18
    row += 1

    ND_R = row
    c = ws.cell(row=row, column=1, value='순부채 (백만원)')
    _style(c, bg=C_RESULT, size=9, h='left')
    b = ws.cell(row=row, column=2, value=_choose_ref(net_debt_row))
    _style(b, bg=C_RESULT, size=9, fmt=NUM_FMT)
    b.alignment = _align(h='right')
    ws.row_dimensions[row].height = 18
    row += 1

    SH_R = row
    c = ws.cell(row=row, column=1, value='희석주식수 (주)')
    _style(c, bg=C_RESULT, size=9, h='left')
    b = ws.cell(row=row, column=2, value=_choose_ref(share_row))
    _style(b, bg=C_RESULT, size=9, fmt=NUM_FMT)
    b.alignment = _align(h='right')
    ws.row_dimensions[row].height = 18
    row += 1
    row += 1  # 간격

    FCFF0_C = f'B{FCFF0_R}'
    ND_C    = f'B{ND_R}'
    SH_C    = f'B{SH_R}'

    # ── 섹션: 2단계 DCF 계산 ────────────────────────────────
    ws.merge_cells(f'A{row}:H{row}')
    c = ws[f'A{row}']
    c.value = '  ■ 2단계 DCF 계산'
    _style(c, bg=C_SECTION, bold=True, color='FFFFFF', size=10, h='left')
    ws.row_dimensions[row].height = 22
    row += 1

    # 명시적 기간 테이블 헤더
    for col, (val, bg) in enumerate(
        [('연차', C_COLHEAD), ('FCFF_t (백만원)', C_COLHEAD), ('현재가치 PV (백만원)', C_COLHEAD)], 1
    ):
        c = ws.cell(row=row, column=col, value=val)
        _style(c, bg=bg, bold=True, size=9)
    ws.row_dimensions[row].height = 18
    row += 1

    TABLE_START = row
    for t in range(1, 11):
        is_alt = (t % 2 == 0)
        bg = C_ALT if is_alt else C_WHITE

        ws.cell(row=row, column=1, value=t)
        _style(ws.cell(row=row, column=1), bg=bg, size=9)

        fcff_t_f = f'=IF({t}<={NC},{FCFF0_C}*(1+{G1C})^{t},"")'
        c_ft = ws.cell(row=row, column=2, value=fcff_t_f)
        _style(c_ft, bg=bg, size=9, fmt=NUM_FMT)
        c_ft.alignment = _align(h='right')

        pv_f = f'=IF({t}<={NC},B{row}/(1+{WC})^{t},"")'
        c_pv = ws.cell(row=row, column=3, value=pv_f)
        _style(c_pv, bg=bg, size=9, fmt=NUM_FMT)
        c_pv.alignment = _align(h='right')

        ws.row_dimensions[row].height = 18
        row += 1

    TABLE_END = row - 1
    row += 1  # 간격

    # 집계 행들
    def _sum_row(label, formula, bg=C_CALC, bold=False, fmt=NUM_FMT):
        nonlocal row
        c = ws.cell(row=row, column=1, value=label)
        _style(c, bg=bg, bold=bold, size=9, h='left')
        b = ws.cell(row=row, column=2, value=formula)
        _style(b, bg=bg, bold=bold, size=9, fmt=fmt)
        b.alignment = _align(h='right')
        ws.row_dimensions[row].height = 18
        r = row; row += 1
        return r

    EXP_PV_R = _sum_row('명시적 기간 PV 합계', f'=SUM(C{TABLE_START}:C{TABLE_END})')
    TV_R = _sum_row(
        'Terminal Value (PV)',
        f'=IFERROR(IF({WC}>{G2C},{FCFF0_C}*(1+{G1C})^{NC}*(1+{G2C})/({WC}-{G2C})/(1+{WC})^{NC},"WACC≤g₂ 오류"),"")'
    )
    EV_R  = _sum_row('Enterprise Value (EV, 백만원)', f'=IFERROR(B{EXP_PV_R}+B{TV_R},"")', bold=True)
    _sum_row('(-) 순부채 (백만원)', f'=-{ND_C}')
    EQ_R  = _sum_row('= Equity Value (백만원)', f'=IFERROR(B{EV_R}+B{row-1},"")', bold=True)

    # ★ 적정주가
    star_row = row
    c = ws.cell(row=row, column=1, value='★ 적정 주가 (원)')
    _style(c, bg=C_STAR, bold=True, size=11, h='left')
    b = ws.cell(row=row, column=2, value=f'=IFERROR(B{EQ_R}*1000000/{SH_C},"")')
    _style(b, bg=C_STAR, bold=True, size=11, fmt='#,##0')
    b.alignment = _align(h='right')
    ws.row_dimensions[row].height = 24
    row += 1

    _sum_row('현재주가 (원)', f'={PC}', bg=C_WHITE, fmt='#,##0')
    _sum_row('괴리율 (적정/현재 - 1)', f'=IFERROR(B{star_row}/B{row-1}-1,"")', fmt=PCT_FMT)
    row += 1

    # 내재 성장률 주석
    ws.merge_cells(f'A{row}:H{row}')
    c = ws.cell(row=row, column=1,
                value='※ 내재 성장률(g*) 역산은 수치해석이 필요해 웹 분석기에서 확인하세요 → 웹 추출 결과 화면 하단 「Reverse DCF 분석기」')
    _style(c, bg=C_WARN, size=8, color='7F6000', h='left', border=False)
    ws.row_dimensions[row].height = 16
    row += 2

    # ── 민감도 분석: WACC × g₁ → 적정주가 ─────────────────
    ws.merge_cells(f'A{row}:H{row}')
    c = ws[f'A{row}']
    c.value = '  ■ 민감도 분석  |  WACC × 고성장률 g₁ → 적정 주가 (원)'
    _style(c, bg=C_SECTION, bold=True, color='FFFFFF', size=10, h='left')
    ws.row_dimensions[row].height = 22
    row += 1

    G1_OFFSETS   = [-0.02, -0.01, 0, 0.01, 0.02]
    WACC_OFFSETS = [-0.04, -0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03, 0.04]

    # 헤더 행
    c = ws.cell(row=row, column=1, value='WACC  ＼  g₁')
    _style(c, bg=C_SENS_H, bold=True, size=9)
    for j, dj in enumerate(G1_OFFSETS):
        lbl = f'g₁{"+" if dj > 0 else ""}{int(dj*100)}%' if dj != 0 else 'g₁ (입력값)'
        c = ws.cell(row=row, column=j + 2, value=lbl)
        _style(c, bg=C_SENS_H, bold=(dj == 0), size=9)
    ws.row_dimensions[row].height = 20
    row += 1

    for di in WACC_OFFSETS:
        is_center = (di == 0)
        bg = C_SENS_C if is_center else (C_ALT if WACC_OFFSETS.index(di) % 2 == 0 else C_WHITE)
        lbl = f'WACC{"+" if di > 0 else ""}{int(di*100)}%' if di != 0 else 'WACC (입력값)'

        c = ws.cell(row=row, column=1, value=lbl)
        _style(c, bg=bg, bold=is_center, size=9, h='left')

        for j, dj in enumerate(G1_OFFSETS):
            def _sign(d):
                if d == 0: return ''
                return f'+{d:.4f}' if d > 0 else f'{d:.4f}'

            wacc_expr = f'({WC}{_sign(di)})' if di != 0 else WC
            g1_expr   = f'({G1C}{_sign(dj)})' if dj != 0 else G1C

            f_str = (
                f'=IFERROR(IF({wacc_expr}>{G2C},'
                f'(SUMPRODUCT({FCFF0_C}*(1+{g1_expr})^ROW(INDIRECT("1:"&{NC}))'
                f'/(1+{wacc_expr})^ROW(INDIRECT("1:"&{NC})))'
                f'+{FCFF0_C}*(1+{g1_expr})^{NC}*(1+{G2C})/({wacc_expr}-{G2C})/(1+{wacc_expr})^{NC}'
                f'-{ND_C})*1000000/{SH_C},""),"")'
            )
            cell = ws.cell(row=row, column=j + 2, value=f_str)
            _style(cell, bg=bg, bold=is_center, size=9, fmt='#,##0')
            cell.alignment = _align(h='right')

        ws.row_dimensions[row].height = 18
        row += 1
