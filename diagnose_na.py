"""N/A 항목 전수 진단 스크립트"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

from extractor.excel_reader import read_financial_statement, read_notes
from extractor.rule_extractor import extract_all_data

COMPANIES = [
    {
        'name': '파마리서치',
        'fs':    r"C:\Users\User\OneDrive\문서\project\DCF 테스트\[(주)파마리서치]사업보고서_재무제표(2026.03.19)_ko (1).xlsx",
        'notes': r"C:\Users\User\OneDrive\문서\project\DCF 테스트\[(주)파마리서치]사업보고서_재무제표주석(2026.03.19)_ko.xlsx",
    },
    {
        'name': 'SK하이닉스',
        'fs':    r"C:\Users\User\OneDrive\문서\project\DCF 테스트\[SK하이닉스]사업보고서_재무제표(2026.03.17)_ko.xlsx",
        'notes': r"C:\Users\User\OneDrive\문서\project\DCF 테스트\[SK하이닉스]사업보고서_재무제표주석(2026.03.17)_ko.xlsx",
    },
    {
        'name': '한미반도체',
        'fs':    r"C:\Users\User\OneDrive\문서\project\DCF 테스트\[한미반도체(주)]사업보고서_재무제표(2026.03.12)_ko.xlsx",
        'notes': r"C:\Users\User\OneDrive\문서\project\DCF 테스트\[한미반도체(주)]사업보고서_재무제표주석(2026.03.12)_ko.xlsx",
    },
    {
        'name': 'LG전자',
        'fs':    r"C:\Users\User\OneDrive\문서\project\DCF 테스트\[LG전자]사업보고서_재무제표(2026.03.13)_ko.xlsx",
        'notes': r"C:\Users\User\OneDrive\문서\project\DCF 테스트\[LG전자]사업보고서_재무제표주석(2026.03.13)_ko.xlsx",
    },
]

SECTION_KEYS = {
    'income':   ['매출액','매출원가','판매비와관리비','영업이익','법인세차감전순이익','법인세비용','당기순이익_지배'],
    'cashflow': ['주식보상비용','자산부채_변동','유형자산_취득','무형자산_취득','차입금_유입','차입금_상환'],
    'da':       ['감가상각비','무형자산상각비'],
    'eps':      ['희석_순이익','희석_주식수'],
    'balance':  ['부채총계','자기자본_지배','현금','단기차입금','유동성장기부채','장기차입금','사채_유동','사채_비유동'],
}

for co in COMPANIES:
    print(f'\n{"="*60}')
    print(f'  {co["name"]}')
    print(f'{"="*60}')
    fs_data    = read_financial_statement(co['fs'])
    notes_data = read_notes(co['notes'])
    result     = extract_all_data(fs_data, notes_data)
    years      = result['years']
    sec        = result['sections']

    na_items = []
    for section_key, keys in SECTION_KEYS.items():
        section = sec.get(section_key, {})
        for k in keys:
            acc = section.get(k)
            if acc is None:
                na_items.append((section_key, k, 'None'))
                continue
            label = acc.get('matched_label', '')
            note  = acc.get('note', '')
            vals  = {yr: acc.get(f'fy{yr}') for yr in years}
            has_na_year = any(v is None for v in vals.values())
            is_all_na   = all(v is None for v in vals.values())

            if label in ('N/A',) or is_all_na:
                na_items.append((section_key, k, f'N/A | note={note}'))
            elif has_na_year:
                na_yrs = [yr for yr in years if vals[yr] is None]
                na_items.append((section_key, k, f'일부 N/A ({na_yrs}) | label={label}'))

    if na_items:
        print(f'  [N/A 항목]')
        for sec_k, acc_k, reason in na_items:
            print(f'    [{sec_k}] {acc_k:25s} → {reason}')
    else:
        print('  모든 항목 추출 성공')

    if result['errors']:
        print(f'  [경고]')
        for e in result['errors']:
            print(f'    - {e}')

    # 각 시트 실제 계정명 출력 (매칭 안된 항목 진단용)
    print(f'\n  [시트 실제 계정명 일부]')
    for sheet_key, label in [('income_rows','손익'), ('cashflow_rows','현금흐름'), ('balance_rows','재무상태표')]:
        rows = fs_data.get(sheet_key, [])
        print(f'    --- {label} ({len(rows)}행) ---')
        for row in rows[:60]:
            print(f'      {row["account"][:70]}')

    for sheet_key, label in [('da_rows','D&A주석'), ('eps_rows','EPS주석')]:
        rows = notes_data.get(sheet_key, [])
        print(f'    --- {label} ({len(rows)}행) ---')
        for row in rows[:40]:
            print(f'      {row["account"][:70]}')
