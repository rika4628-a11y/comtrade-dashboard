"""
UN Comtrade 스테인리스 CR/HR 무역통계 대시보드 — 국가별 파트너 분석
먼저 fetch_data.py 를 실행해 데이터를 받은 뒤 이 앱을 실행하세요.

    streamlit run app.py
"""
import os
import pandas as pd
import streamlit as st

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "comtrade_raw.csv")

st.set_page_config(page_title="Comtrade 스테인리스 CR/HR", layout="wide")
st.title("UN Comtrade — 스테인리스 CR/HR 무역통계")
st.caption("리포터(대상국) 1개를 선택하면 해당 연도·거래형태 기준으로 파트너국별 수출입 내역을 보여줍니다.")

# World 집계행이 존재하는데 개별국 데이터도 함께 있으면 합산 시 수치가 중복 집계되므로,
# World(및 유사 집계 표기)는 로드 단계에서 아예 제외한다.
AGGREGATE_NAMES = {"World"}


def _is_aggregate(series):
    """대소문자/공백 차이까지 대비해 World(및 유사 집계 표기)를 안전하게 판별한다."""
    norm = {n.strip().casefold() for n in AGGREGATE_NAMES}
    return series.astype(str).str.strip().str.casefold().isin(norm)


# 입력하기 어려운 특수문자 국가명 및 UN 공식 집계 코드명을 실제 사용하는 이름으로 통일
NAME_FIXES = {"Türkiye": "Turkiye", "Other Asia, nes": "Taiwan"}

# ── 제품군(CR/HR) 및 세부 HS Code ──────────────────────────
PRODUCT_HS_CODES = {
    "STS CR (냉연)": [
        "721931", "721932", "721933", "721934", "721935", "721990", "722020", "722090",
    ],
    "STS HR (열연)": [
        "721911", "721912", "721913", "721914",
        "721921", "721922", "721923", "721924",
        "722011", "722012",
    ],
}

# 데이터에 cmdDesc가 없거나 못 찾을 경우를 대비한 대체 설명(참고용, 두께 구간은 근사치)
HS_CODE_FALLBACK_DESC = {
    "721931": "냉연 코일 · 두께 4.75mm 이상",
    "721932": "냉연 코일 · 두께 3~4.75mm",
    "721933": "냉연 코일 · 두께 1~3mm",
    "721934": "냉연 코일 · 두께 0.5~1mm",
    "721935": "냉연 코일 · 두께 0.5mm 미만",
    "721990": "냉연 코일 · 기타/미분류 두께",
    "722020": "냉연 코일 · 좁은 폭(600mm 미만)",
    "722090": "냉연 코일 · 좁은 폭(600mm 미만), 기타",
    "721911": "열연 코일 · 두께 10mm 초과",
    "721912": "열연 코일 · 두께 4.75~10mm",
    "721913": "열연 코일 · 두께 3~4.75mm",
    "721914": "열연 코일 · 두께 3mm 미만",
    "721921": "열연 판재(비코일) · 두께 10mm 초과",
    "721922": "열연 판재(비코일) · 두께 4.75~10mm",
    "721923": "열연 판재(비코일) · 두께 3~4.75mm",
    "721924": "열연 판재(비코일) · 두께 3mm 미만",
    "722011": "열연 · 좁은 폭(600mm 미만), 두께 4.75mm 이상",
    "722012": "열연 · 좁은 폭(600mm 미만), 두께 4.75mm 미만",
}

# 여러 국가를 하나로 묶어 조회할 수 있는 그룹 리포터
# (일부 항목은 UN Comtrade 표기가 다를 수 있어 후보 이름 목록으로 지정, 실제 데이터에 있는 표기를 자동 선택)
REPORTER_GROUPS_RAW = {
    "EU (유럽연합)": [
        "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia",
        "Denmark", "Estonia", "Finland", "France", "Germany", "Greece",
        "Hungary", "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg",
        "Malta", "Netherlands", "Poland", "Portugal", "Romania", "Slovakia",
        "Slovenia", "Spain", "Sweden",
    ],
    "North Africa (북아프리카)": ["Morocco", "Algeria", "Tunisia", "Libya", "Egypt"],
    "North America (북미)": [
        ["USA", "United States", "United States of America"], "Canada", "Mexico",
    ],
    "South America (남미)": [
        "Brazil", "Argentina", "Chile", "Colombia", "Peru", "Ecuador",
        ["Bolivia", "Bolivia (Plurinational State of)"],
        "Paraguay", "Uruguay",
        ["Venezuela", "Venezuela (Bolivarian Republic of)"],
        "Guyana", "Suriname",
    ],
    "CIS (독립국가연합)": [
        ["Russia", "Russian Federation"],
        "Belarus", "Kazakhstan", "Armenia", "Azerbaijan", "Kyrgyzstan",
        ["Moldova", "Rep. of Moldova", "Republic of Moldova"],
        "Tajikistan", "Uzbekistan", "Turkmenistan",
    ],
    "Middle East (중동)": [
        "Saudi Arabia", ["UAE", "United Arab Emirates"], "Qatar", "Kuwait",
        "Bahrain", "Oman", "Yemen", "Iraq",
        ["Iran", "Iran (Islamic Republic of)"],
        "Israel", "Jordan", "Lebanon",
        ["Syria", "Syrian Arab Republic"],
    ],
    "Southeast Asia (동남아시아)": [
        "Indonesia", "Malaysia", "Philippines", "Singapore", "Thailand",
        ["Vietnam", "Viet Nam"], "Myanmar", "Cambodia",
        ["Laos", "Lao People's Dem. Rep."],
        ["Brunei", "Brunei Darussalam"], "Timor-Leste",
    ],
}


def _resolve_group_names(raw_groups, available_names):
    """각 그룹의 국가명이 후보 목록(list)이면, 실제 데이터에 존재하는 표기를 골라 확정한다."""
    resolved = {}
    for group_name, members in raw_groups.items():
        picked = []
        for m in members:
            candidates = m if isinstance(m, list) else [m]
            match = next((c for c in candidates if c in available_names), candidates[0])
            picked.append(match)
        resolved[group_name] = picked
    return resolved


@st.cache_data
def load_data(path, mtime):
    d = pd.read_csv(path)
    partner_mask = _is_aggregate(d["partnerDesc"])
    reporter_mask = _is_aggregate(d["reporterDesc"])
    n_excluded_partner = int(partner_mask.sum())
    n_excluded_reporter = int(reporter_mask.sum())
    d = d[~partner_mask & ~reporter_mask]
    d["reporterDesc"] = d["reporterDesc"].replace(NAME_FIXES)
    d["partnerDesc"] = d["partnerDesc"].replace(NAME_FIXES)
    return d, n_excluded_partner, n_excluded_reporter


if not os.path.exists(DATA_PATH):
    st.warning("아직 데이터가 없습니다. 터미널에서 아래 명령을 먼저 실행하세요:")
    st.code("python fetch_data.py 2022 2023 2024 2025", language="bash")
    st.stop()

df, n_excluded_partner, n_excluded_reporter = load_data(DATA_PATH, os.path.getmtime(DATA_PATH))
st.caption(
    f"World 집계행 제외됨: 파트너 기준 {n_excluded_partner:,}건, 리포터 기준 {n_excluded_reporter:,}건 "
    "(국가별 실제 수치만 남긴 상태입니다)"
)

if "netWgt" not in df.columns:
    st.error(
        "이 데이터 파일에는 netWgt 컬럼이 없습니다. fetch_data.py를 최신 버전으로 교체한 뒤, "
        "data/comtrade_raw.csv 를 삭제하고 다시 받아주세요 (기존 파일은 qty 기준이라 호환되지 않습니다)."
    )
    st.stop()

df["period"] = df["period"].astype(str)
df["cmdCode"] = df["cmdCode"].astype(str)

# 실제 데이터에 있는 cmdDesc를 코드별로 매핑(있으면 보완용, 한글 설명을 우선 사용)
if "cmdDesc" in df.columns:
    _CMD_DESC_MAP = (
        df.dropna(subset=["cmdDesc"]).drop_duplicates("cmdCode").set_index("cmdCode")["cmdDesc"].to_dict()
    )
else:
    _CMD_DESC_MAP = {}


def _hs_label(code):
    desc = HS_CODE_FALLBACK_DESC.get(code) or _CMD_DESC_MAP.get(code, "")
    return f"{code} · {desc}" if desc else code


REPORTER_GROUPS = _resolve_group_names(REPORTER_GROUPS_RAW, set(df["reporterDesc"].unique()))

# HS Code/제품군 선택과 완전히 무관하도록, 데이터 로드 직후의 전체 값 목록을 고정해둔다.
ALL_REPORTERS = sorted(df["reporterDesc"].unique())
ALL_PERIODS = sorted(df["period"].unique(), reverse=True)
ALL_FLOWS = sorted(df["flowDesc"].unique())

if st.button("🔄 데이터 다시 불러오기"):
    st.cache_data.clear()
    st.rerun()

# ── Reporter / Period / Flow — 한 줄에 모아서 선택 ──────────────
REPORTER_DIVIDER = "──────────"
reporter_options = list(REPORTER_GROUPS.keys()) + [REPORTER_DIVIDER] + ALL_REPORTERS

if "sel_reporter" not in st.session_state:
    st.session_state["sel_reporter"] = ALL_REPORTERS[0]
if st.session_state["sel_reporter"] not in reporter_options:
    st.session_state["sel_reporter"] = ALL_REPORTERS[0]

top_c1, top_c2, top_c3 = st.columns([2, 3, 2])
with top_c1:
    sel_reporter = st.selectbox(
        "Reporter (조회 대상국)", reporter_options, key="sel_reporter"
    )
with top_c2:
    sel_periods = st.pills(
        "Period (연도)", ALL_PERIODS, selection_mode="multi", default=ALL_PERIODS,
    )
    sel_periods = sel_periods or []
with top_c3:
    default_flow = "Import" if "Import" in ALL_FLOWS else ALL_FLOWS[0]
    sel_flow = st.pills(
        "Flow (거래형태)", ALL_FLOWS, selection_mode="single",
        default=default_flow, required=True,
    )

if sel_reporter == REPORTER_DIVIDER:
    # 구분선은 선택 불가 항목 — 자동으로 이전 상태를 무시하고 첫 번째 개별국으로 되돌린다.
    st.session_state["sel_reporter"] = ALL_REPORTERS[0]
    st.rerun()

# ── Product / 전체선택 / 전체해제 / HS Code — 한 줄 배치 ──
# HS Code는 4개씩 끊어서 여러 개의 pills 위젯으로 나눠 그린다.
# (하나의 pills 위젯에 전부 넣으면 화면 폭에 따라 줄바꿈이 안 되고 옆으로 삐져나가기 때문)
prod_col1, prod_col2, prod_col3, prod_col4 = st.columns([1.3, 0.7, 0.7, 4.3])
with prod_col1:
    sel_product = st.selectbox("Product (제품군)", list(PRODUCT_HS_CODES.keys()), key="sel_product")

all_codes_for_product = PRODUCT_HS_CODES[sel_product]

PER_ROW = 4  # 한 줄에 배치할 HS Code 개수 (화면 폭과 무관하게 항상 이 개수로 줄바꿈)
_hs_chunks = [
    all_codes_for_product[i:i + PER_ROW]
    for i in range(0, len(all_codes_for_product), PER_ROW)
]


def _chunk_key(idx):
    return f"hs_{sel_product}_{idx}"


# 최초 진입 시 기본값: 전체 선택
for _i, _chunk in enumerate(_hs_chunks):
    if _chunk_key(_i) not in st.session_state:
        st.session_state[_chunk_key(_i)] = list(_chunk)

with prod_col2:
    st.write("")
    if st.button("전체선택", key=f"hs_all_{sel_product}", use_container_width=True):
        for _i, _chunk in enumerate(_hs_chunks):
            st.session_state[_chunk_key(_i)] = list(_chunk)
        st.rerun()
with prod_col3:
    st.write("")
    if st.button("전체해제", key=f"hs_none_{sel_product}", use_container_width=True):
        for _i in range(len(_hs_chunks)):
            st.session_state[_chunk_key(_i)] = []
        st.rerun()

with prod_col4:
    sel_hscodes = []
    for _i, _chunk in enumerate(_hs_chunks):
        _picked = st.pills(
            "HS Code",
            _chunk,
            selection_mode="multi",
            format_func=_hs_label,
            key=_chunk_key(_i),
            label_visibility="collapsed",
        )
        sel_hscodes.extend(_picked or [])

# 원래 코드 순서대로 정렬
sel_hscodes = [c for c in all_codes_for_product if c in set(sel_hscodes)]

st.caption("선택된 HS Code: " + (", ".join(sel_hscodes) if sel_hscodes else "없음") + "  (수량 단위: 톤, netWgt 기준)")

if not sel_hscodes:
    st.info("HS Code를 1개 이상 선택해주세요.")
    st.stop()

df = df[df["cmdCode"].isin(sel_hscodes)]

if df.empty:
    st.info(f"선택한 HS Code({', '.join(sel_hscodes)})에 해당하는 데이터가 없습니다.")
    st.stop()

st.divider()

if not sel_periods:
    st.info("연도를 1개 이상 선택해주세요.")
    st.stop()

is_group = sel_reporter in REPORTER_GROUPS
reporter_countries = REPORTER_GROUPS[sel_reporter] if is_group else [sel_reporter]

detail = df[
    (df["reporterDesc"].isin(reporter_countries))
    & (df["period"].isin(sel_periods))
    & (df["flowDesc"] == sel_flow)
]

if detail.empty:
    st.info("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()

if is_group:
    # ── 그룹 모드: 그룹 전체 총량 + 회원국별 수입량만 보여준다 (파트너국 상세는 표시하지 않음) ──
    st.info(f"'{sel_reporter}'는 아래 {len(reporter_countries)}개국 데이터의 합산입니다. 국가를 클릭하면 그 나라만 따로 조회합니다.")

    by_member = detail.pivot_table(
        index="reporterDesc", columns="period", values="netWgt", aggfunc="sum", fill_value=0
    )
    year_cols = list(by_member.columns)
    by_member = (by_member / 1000).round(0)  # kg -> 톤
    by_member["Total"] = by_member[year_cols].sum(axis=1)
    by_member = by_member.sort_values("Total", ascending=False)
    by_member.insert(0, "순위", range(1, len(by_member) + 1))
    by_member.index.name = "국가"

    def _set_reporter(country):
        st.session_state["sel_reporter"] = country

    btn_cols = st.columns(4)
    for i, country in enumerate(reporter_countries):
        amt = by_member["Total"].get(country, 0)
        label = f"{country} ({amt:,.0f} 톤)" if amt > 0 else f"{country} (데이터 없음)"
        btn_cols[i % 4].button(
            label, key=f"drill_{country}", disabled=(amt == 0),
            on_click=_set_reporter, args=(country,),
        )
    st.divider()

    period_label = ", ".join(sel_periods)
    m1, m2 = st.columns(2)
    m1.metric(f"{sel_reporter} ({period_label}) {sel_flow} 총 수량", f"{by_member['Total'].sum():,.0f} 톤")
    m2.metric("데이터 있는 회원국 수", f"{(by_member['Total'] > 0).sum():,}개국")

    st.subheader(f"{sel_reporter} 회원국별 수입량 상세 (연도별, 톤)")
    num_cols = year_cols + ["Total"]
    table_df = by_member.reset_index()

    col_config = {
        "순위": st.column_config.NumberColumn("순위", width="small"),
        "국가": st.column_config.TextColumn("국가", width=110),
    }
    for c in num_cols:
        col_config[c] = st.column_config.NumberColumn(str(c), format="%,d 톤", width="medium")

    st.dataframe(
        table_df,
        column_config=col_config,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        f"{sel_reporter} 회원국별 데이터 CSV 다운로드",
        by_member.to_csv().encode("utf-8-sig"),
        f"comtrade_{sel_product}_{sel_reporter}_{'-'.join(sel_periods)}_{sel_flow}.csv",
        "text/csv",
    )

else:
    # ── 개별국 모드: 파트너국별 상세 ──
    by_partner = detail.pivot_table(
        index="partnerDesc", columns="period", values="netWgt", aggfunc="sum", fill_value=0
    )
    year_cols = list(by_partner.columns)
    by_partner = (by_partner / 1000).round(0)  # kg -> 톤
    by_partner["Total"] = by_partner[year_cols].sum(axis=1)
    by_partner = by_partner.sort_values("Total", ascending=False)
    by_partner.insert(0, "순위", range(1, len(by_partner) + 1))
    by_partner.index.name = "Partner"

    period_label = ", ".join(sel_periods)
    m1, m2 = st.columns(2)
    m1.metric(f"{sel_reporter} ({period_label}) {sel_flow} 총 수량", f"{by_partner['Total'].sum():,.0f} 톤")
    m2.metric("파트너국 수", f"{len(by_partner):,}개국")

    st.subheader("파트너국별 상세 (연도별, 톤)")
    num_cols = year_cols + ["Total"]
    table_df = by_partner.reset_index()

    col_config = {
        "순위": st.column_config.NumberColumn("순위", width="small"),
        "Partner": st.column_config.TextColumn("Partner", width=110),
    }
    for c in num_cols:
        col_config[c] = st.column_config.NumberColumn(str(c), format="%,d 톤", width="medium")

    st.dataframe(
        table_df,
        column_config=col_config,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "파트너국별 데이터 CSV 다운로드",
        by_partner.to_csv().encode("utf-8-sig"),
        f"comtrade_{sel_product}_{sel_reporter}_{'-'.join(sel_periods)}_{sel_flow}.csv",
        "text/csv",
    )
