# 행사 참가 신청 앱

이름·이메일·참가 회차를 입력받아 Supabase PostgreSQL에 저장합니다. 코드는 GitHub에 백업하고 화면 및 Python API는 Vercel에서 실행합니다. 외부 서비스는 GitHub·Supabase·Vercel만 사용합니다.

## 기능

- PC·모바일 신청 화면, 필수 입력과 이메일 검증
- 저장 성공 시 입력 초기화, 실패 시 입력 유지
- 같은 이메일의 새 신청 허용. 동일한 요청 ID의 재시도는 중복 저장하지 않음
- 익명 조회·수정·삭제 및 저장 RPC 접근 차단. 서버용 키는 브라우저에 전달하지 않음
- Supabase에서 원자적으로 IP별 10분 구간당 최대 10건 제한. 원본 IP 대신 서버 키로 만든 HMAC 저장
- 로그인·관리자 화면·수정·삭제 기능 없음. 확인은 Supabase Table Editor에서 가능

## 환경변수

`.env.example`을 참고해 아래 두 값을 Vercel의 Production·Preview 환경에 등록하세요.

| 변수 | 설명 |
|---|---|
| `SUPABASE_URL` | Supabase 프로젝트 HTTPS 주소 |
| `SUPABASE_SECRET_KEY` | 서버 전용 secret key 또는 기존 service_role 키 |

키는 GitHub에 커밋하거나 HTML에 넣지 마세요. Vercel 환경변수 변경 후 재배포해야 적용됩니다.

## 데이터베이스

`supabase/migrations/202609300001_workshop_registrations.sql`을 새 프로젝트에 적용합니다. 이미 적용된 프로젝트에서는 반복 실행하지 마세요.

- `workshop_registrations`: 요청 UUID, 이름, 이메일, 회차, 서버 생성 신청 시각
- `workshop_rate_limits`: HMAC 지문, 10분 구간, 제출 수
- 두 테이블은 RLS가 활성화되고 공개 역할 접근이 차단됩니다. 공개 정책이 없는 것은 서버 전용 구조의 의도된 설정입니다.
- `submit_workshop_registration` 함수는 `service_role`만 호출할 수 있으며 SECURITY INVOKER를 사용합니다.
- 기존 `registrations.db`는 자동 업로드하지 않으며 새 버전은 SQLite를 사용하지 않습니다.

## GitHub·Vercel 배포

1. 앱 폴더의 소스를 GitHub 저장소에 올립니다. `.env*`, 실제 DB, `.vercel/`은 제외합니다.
2. Vercel에서 해당 저장소를 Import합니다. 저장소가 앱 자체라면 Root Directory는 기본값이고, 하위 폴더에 앱이 있다면 그 폴더를 지정합니다.
3. Framework Preset은 Other, Output Directory는 `public`입니다. `vercel.json`이 함수와 배포 지역을 지정합니다.
4. 환경변수를 등록하고 배포합니다. `/api/registrations`는 `api/registrations.py`의 handler로 실행됩니다.
5. 배포 주소에서 가상 정보로 신청하고 Supabase Table Editor에서 저장을 확인합니다.

## 로컬 개발

이 폴더에 `.env.local`을 만들고 위 환경변수를 저장한 후 실행합니다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 --port 8001
```

http://127.0.0.1:8001 에서 열고 Ctrl+C로 종료합니다. 일반 Python 환경에서는 `python app.py --port 8001`로 실행할 수 있습니다. Python 3.12 이상 권장. 기본 라이브러리만 사용합니다.

## 검증

```powershell
python -m unittest discover -v
```

자동 테스트는 실제 Supabase 데이터에 쓰지 않습니다. 실제 배포 검증은 별도의 가상 신청으로 확인합니다. 기본 Python 명령이 없다면 `start.ps1`의 Codex 내장 Python 경로를 사용하세요.
