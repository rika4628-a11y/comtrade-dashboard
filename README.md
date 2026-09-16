# UN Comtrade 대시보드 — 웹 배포 + 분기별 자동 갱신 설정 가이드

이 폴더 그대로 GitHub에 올리고 Streamlit Community Cloud에 연결하면,
**Python 설치 없이 누구나 링크만 클릭하면** 브라우저로 바로 조회할 수 있는 웹 대시보드가 생깁니다.
데이터는 1월/4월/7월/10월(분기)마다 자동으로 갱신됩니다.

---

## 1단계. GitHub 계정 만들기 (이미 있으면 건너뛰기)

1. https://github.com 접속 → 우측 상단 **Sign up**
2. 이메일/비밀번호/아이디 입력하고 가입 완료 (무료)

## 2단계. 저장소(Repository) 만들기

1. 로그인 후 우측 상단 **+** → **New repository**
2. Repository name: 예) `comtrade-dashboard`
3. **Public** 선택
4. **Create repository** 클릭

## 3단계. 파일 업로드

1. 저장소 페이지에서 **Add file → Upload files** 클릭
2. 이 폴더 안의 파일/폴더를 **전부 그대로** 끌어다 놓기
   - `app.py`
   - `fetch_data.py`
   - `requirements.txt`
   - `.github/workflows/update-data.yml` (폴더째로 올리면 구조가 유지됩니다)
3. 하단 **Commit changes** 클릭

> ⚠️ `fetch_data.py`에는 API 키가 들어있지 않습니다. 4단계에서 안전하게 별도 등록합니다.

## 4단계. API 키를 "비밀 값(Secret)"으로 등록

Public 저장소라도 이렇게 등록한 키는 절대 다른 사람에게 보이지 않습니다.

1. 저장소 페이지에서 **Settings** 탭 클릭
2. 왼쪽 메뉴 **Secrets and variables → Actions**
3. **New repository secret** 클릭
4. Name: `COMTRADE_API_KEY`
5. Secret: 본인의 UN Comtrade 구독키 붙여넣기
6. **Add secret** 클릭

## 5단계. 데이터 최초 1회 수동 생성

자동 스케줄은 1/4/7/10월에만 돌기 때문에, 지금 처음 한 번은 수동으로 실행해서 데이터를 만들어야 합니다.

1. 저장소 상단 **Actions** 탭 클릭
2. 처음이면 "I understand my workflows, go ahead and enable them" 클릭
3. 왼쪽에서 **Comtrade 분기별 자동 갱신** 클릭
4. 오른쪽 **Run workflow** 버튼 → 다시 **Run workflow** 클릭
5. 1~2분 후 초록색 체크가 뜨면 완료. 저장소에 `data/comtrade_raw.csv`가 생성되어 있을 것입니다.

## 6단계. Streamlit Community Cloud로 웹 배포

1. https://share.streamlit.io 접속 → **Sign in with GitHub**으로 로그인 (같은 GitHub 계정 사용)
2. **Create app** (또는 **New app**) 클릭
3. Repository: 방금 만든 저장소 선택
4. Branch: `main`
5. Main file path: `app.py`
6. **Deploy** 클릭

몇 분 기다리면 `https://xxxxx.streamlit.app` 형태의 공개 링크가 생성됩니다.
**이 링크만 사업실에 공유하면 끝입니다.** 받는 사람은 Python이나 아무것도 설치할 필요가 없습니다.

---

## 이후 유지 관리

- **데이터 갱신 확인**: GitHub 저장소의 **Actions** 탭에서 실행 이력과 성공/실패 여부를 확인할 수 있습니다.
- **지금 바로 갱신하고 싶을 때**: Actions 탭 → 워크플로 선택 → **Run workflow**로 수동 실행 가능합니다.
- **앱 코드 수정 시**: GitHub 저장소의 파일을 수정(웹에서 직접 편집 가능)하면, Streamlit Cloud가 자동으로 반영합니다.
- **API 키가 노출된 것 같으면**: comtradeplus.un.org에서 키를 재발급하고, GitHub 저장소 Secret 값도 같이 업데이트하세요.
