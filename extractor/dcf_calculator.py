"""
Reverse DCF 계산 엔진.
2단계 모델: 명시적 예측기간(N년, 단일 성장률 g1) + 영구가치(g2).
"""


def compute_fcff_data(sections: dict, years: list[str], divisor: int = 1_000_000) -> dict:
    """추출된 섹션 데이터에서 FCFF, 순부채, 주식수를 연도별로 계산."""
    income = sections.get('income', {})
    cf     = sections.get('cashflow', {})
    da     = sections.get('da', {})
    eps    = sections.get('eps', {})
    bal    = sections.get('balance', {})

    def v(section, key, yr):
        acc = section.get(key, {})
        val = acc.get(f'fy{yr}')
        return int(val) / divisor if val is not None else None

    fcff: dict = {}
    for yr in years:
        ebit   = v(income, '영업이익', yr)
        pretax = v(income, '법인세차감전순이익', yr)
        tax    = v(income, '법인세비용', yr)
        dep    = v(da, '감가상각비', yr)
        amor   = v(da, '무형자산상각비', yr)
        ppe    = v(cf, '유형자산_취득', yr)
        ia     = v(cf, '무형자산_취득', yr)
        nwc    = v(cf, '자산부채_변동', yr)

        if ebit is None or dep is None:
            fcff[yr] = None
            continue

        if pretax and pretax != 0 and tax is not None:
            t_rate = max(0.0, min(1.0, tax / pretax))
        else:
            t_rate = 0.0

        nopat = ebit * (1 - t_rate)
        val   = nopat + (dep or 0) + (amor or 0) - (ppe or 0) - (ia or 0) + (nwc or 0)
        fcff[yr] = round(val, 2)

    net_debt: dict = {}
    debt_keys = ['단기차입금', '유동성장기부채', '장기차입금', '사채_유동', '사채_비유동']
    for yr in years:
        total = sum(v(bal, k, yr) or 0 for k in debt_keys)
        cash  = v(bal, '현금', yr) or 0
        net_debt[yr] = round(total - cash, 2)

    shares: dict = {}
    share_acc = eps.get('희석_주식수', {})
    for yr in years:
        val = share_acc.get(f'fy{yr}')
        shares[yr] = int(val) if val is not None else None

    return {'fcff': fcff, 'net_debt': net_debt, 'shares': shares}


def calc_dcf(fcff0: float, wacc: float, g1: float, n: int, g2: float) -> float:
    """2단계 DCF → Enterprise Value (fcff0와 동일 단위)."""
    if wacc <= g2:
        raise ValueError('WACC must be > g2')
    pv = sum(fcff0 * (1 + g1) ** t / (1 + wacc) ** t for t in range(1, n + 1))
    fcff_n = fcff0 * (1 + g1) ** n
    tv = fcff_n * (1 + g2) / (wacc - g2) / (1 + wacc) ** n
    return pv + tv


def calc_implied_growth(ev_market: float, fcff0: float, wacc: float,
                        n: int, g2: float) -> float | None:
    """이진탐색으로 내재 성장률 역산. 해가 없으면 None 반환."""
    if fcff0 <= 0 or wacc <= g2:
        return None

    def f(g: float) -> float:
        try:
            return calc_dcf(fcff0, wacc, g, n, g2) - ev_market
        except Exception:
            return float('inf')

    lo, hi = -0.5, 5.0
    f_lo = f(lo)
    if f_lo * f(hi) > 0:
        return None

    for _ in range(200):
        mid = (lo + hi) / 2
        if abs(hi - lo) < 1e-7:
            return mid
        if f(mid) * f_lo > 0:
            lo = mid
            f_lo = f(mid)
        else:
            hi = mid
    return (lo + hi) / 2


def sensitivity_implied_g(fcff0: float, wacc_center: float, n: int, g2: float,
                           ev_market: float, steps: int = 4) -> list[dict]:
    """WACC ± steps×1% 구간에서 내재 성장률 계산."""
    results = []
    for i in range(-steps, steps + 1):
        wacc = round(wacc_center + i * 0.01, 4)
        if wacc <= g2 or wacc <= 0:
            results.append({'wacc': wacc, 'implied_g': None})
            continue
        g = calc_implied_growth(ev_market, fcff0, wacc, n, g2)
        results.append({
            'wacc': wacc,
            'implied_g': round(g, 6) if g is not None else None,
        })
    return results
