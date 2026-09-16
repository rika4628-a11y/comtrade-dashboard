"""
UN Comtrade raw data downloader
--------------------------------
Stainless steel CR + HR 통합 수집
- STS CR (냉연): HS 721931 / 721932 / 721933 / 721934 / 721935 / 721990 / 722020 / 722090
- STS HR (열연): HS 721911 / 721912 / 721913 / 721914 / 721921 / 721922 / 721923 / 721924 / 722011 / 722012
Reporter = ALL countries, Partner = ALL countries, Flow = Import + Export

인자 없이 실행하면 "올해 포함 최근 3개년"을 자동으로 받습니다 (스케줄링용).
특정 연도만 받고 싶으면 예전처럼 인자로 지정: python fetch_data.py 2023 2024

World(전세계 집계) 행은 개별국 데이터와 합산 시 수치가 중복 계산되므로,
raw data 저장 단계에서 아예 제외합니다 (기존에 저장된 파일에 남아있던 World 행도
이번 실행부터 자동으로 함께 정리됩니다).
"""
import os
import sys
import time
import datetime
import requests
import pandas as pd

API_KEY = os.environ.get("COMTRADE_API_KEY", "")

BASE_URL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
HS_CODES_CR = "721931,721932,721933,721934,721935,721990,722020,722090"  # STS CR (냉연)
HS_CODES_HR = "721911,721912,721913,721914,721921,721922,721923,721924,722011,722012"  # STS HR (열연)
HS_CODES = ",".join([HS_CODES_CR, HS_CODES_HR])  # 한번에 다 받아서 app.py에서 cmdCode로 CR/HR을 구분
OUT_DIR = os.path.join(os.path.dirname(__file__), "data")
OUT_PATH = os.path.join(OUT_DIR, "comtrade_raw.csv")
KEEP_COLS = ["period", "reporterDesc", "flowDesc", "partnerDesc", "cmdCode", "cmdDesc", "netWgt"]
RECENT_YEARS_COUNT = 3  # 인자 없이 실행 시 "올해 포함 최근 N개년" 자동 수집
AGGREGATE_NAMES = {"World"}  # 이 이름에 해당하는 행은 partner/reporter 어느 쪽이든 제외


def fetch_one(period, flow_code):
    params = {
        "period": str(period),
        "cmdCode": HS_CODES,
        "flowCode": flow_code,
        "motCode": "0",
        "partner2Code": "0",
        "customsCode": "C00",
        "includeDesc": "true",
    }
    headers = {"Ocp-Apim-Subscription-Key": API_KEY}
    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=90, verify=False)
    resp.raise_for_status()
    js = resp.json()
    if isinstance(js, dict) and js.get("error"):
        raise RuntimeError(js["error"])
    return pd.DataFrame(js.get("data", []))


def drop_world(df):
    """partnerDesc 또는 reporterDesc가 World(대소문자/공백 무관)인 행을 제거한다."""
    if df.empty:
        return df
    norm = {n.strip().casefold() for n in AGGREGATE_NAMES}
    partner_mask = df["partnerDesc"].astype(str).str.strip().str.casefold().isin(norm)
    reporter_mask = df["reporterDesc"].astype(str).str.strip().str.casefold().isin(norm)
    removed = int((partner_mask | reporter_mask).sum())
    if removed:
        print(f"  (World 집계행 {removed:,}건 제외)")
    return df[~partner_mask & ~reporter_mask]


def normalize_keys(df):
    """중복 판정에 쓰이는 컬럼들의 타입을 강제로 통일한다.
    (CSV에서 다시 읽은 값과 API에서 새로 받은 값의 타입이 다르면
    drop_duplicates가 같은 데이터를 다른 값으로 착각해 중복이 쌓이는 문제를 방지)"""
    if df.empty:
        return df
    for col in ["period", "reporterDesc", "flowDesc", "partnerDesc", "cmdCode"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df


def main(years):
    if not API_KEY:
        print("!! COMTRADE_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    frames = []
    for year in years:
        for flow in ("M", "X"):
            print(f"[{year} / {flow}] 요청 중...")
            try:
                df = fetch_one(year, flow)
                print(f"  -> {len(df)}건 수신")
                if len(df):
                    frames.append(df)
            except requests.HTTPError as e:
                print(f"  !! HTTP 오류: {e}")
            except Exception as e:
                print(f"  !! 오류: {e}")
            time.sleep(1)

    if not frames:
        print("받아온 데이터가 없습니다.")
        return

    new_data = pd.concat(frames, ignore_index=True)
    cols = [c for c in KEEP_COLS if c in new_data.columns]
    new_data = new_data[cols]
    new_data = drop_world(new_data)
    new_data = normalize_keys(new_data)

    if os.path.exists(OUT_PATH):
        # dtype=str 로 강제 로드하여, pandas가 숫자/문자를 제멋대로 다르게
        # 추론해서 중복 제거가 실패하는 일을 원천 차단한다.
        existing = pd.read_csv(OUT_PATH, dtype=str)
        existing["netWgt"] = pd.to_numeric(existing["netWgt"], errors="coerce")
        existing = drop_world(existing)
        existing = normalize_keys(existing)
        combined = pd.concat([existing, new_data], ignore_index=True)
        before = len(combined)
        combined = combined.drop_duplicates(
            subset=["period", "reporterDesc", "flowDesc", "partnerDesc", "cmdCode"],
            keep="last",
        )
        removed_dupe = before - len(combined)
        if removed_dupe:
            print(f"(과거 실행에서 쌓였던 중복 행 {removed_dupe:,}건 정리됨)")
    else:
        combined = new_data

    combined.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n완료: {OUT_PATH} 에 총 {len(combined):,}건 저장됨 (World 집계행 없음)")


if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    print(f"===== 실행 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")

    if len(sys.argv) > 1:
        years = [int(y) for y in sys.argv[1:]]
    else:
        current_year = datetime.datetime.now().year
        years = list(range(current_year - RECENT_YEARS_COUNT + 1, current_year + 1))
        print(f"(인자 없이 실행됨 -> 최근 {RECENT_YEARS_COUNT}개년 자동 수집: {years})")

    main(years)
    print(f"===== 종료 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")
