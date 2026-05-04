# digital-asset-redteam-lab
## 1. Project Overview
Local intentionally vulnerable Flask security lab.
## 2. Why This Lab Exists
Red Team 포트폴리오 재현용.
## 3. Threat Scenario
Stored XSS -> API Key abuse.
## 4. Initial Access Vector: Stored XSS
/support/view/<id>에서 safe 렌더링.
## 5. Why This Lab Does Not Steal Cookies
쿠키 탈취 미구현, same-origin 요청만 사용.
## 6. Session Riding via Authenticated Browser Context
로그인된 브라우저 컨텍스트로 /api/key 호출.
## 7. Discovery Phase
/openapi.json, static/app.js 노출.
## 8. XSS to API Key Generation
XSS payload가 /api/key 호출 후 /lab/events 기록.
## 9. API Key-Only Withdrawal
X-API-KEY만으로 /api/withdraw 가능.
## 10. Persistent Access Scenario
세션 만료와 무관하게 키 지속 사용 가능(의도된 취약점).
## 11. Attack Chain
Stored XSS → Authenticated Browser Context → API Key Generation → API Key-Only Withdrawal → Persistent Access → Automation Scenario  
저장형 XSS → 인증된 브라우저 컨텍스트 악용 → API Key 발급 → API Key 단독 출금 → 지속 접근 → 자동화 공격 시나리오
## 12. Business Impact
계정 탈취 후 자동화 출금 확대 가능.
## 13. Reproduction with curl
Windows/macOS-Linux 명령 포함(요구사항 반영).
## 14. Burp Suite Capture Points
1) POST /login ... 11) auth_method 확인.
## 15. Defensive Recommendations
출력 인코딩, sanitize, CSP, API key expiry/scope, 2FA, rate limit 등 15개 권고.
## 16. Disclaimer: Local Lab Only
실자산/실거래소/외부연동 없음.
## 17. Acceptance Tests
요구된 16-step 수동 테스트 수행.

핵심 설명: 본 프로젝트는 가상의 디지털 자산 서비스 환경에서 세션 기반 인증, API Key 발급, API Key 기반 출금 기능을 구성하고, 정상 사용자 트래픽 분석 및 프론트엔드 JS/API 문서 노출을 통해 API 엔드포인트를 식별한 뒤, Stored XSS를 통해 피해자의 인증된 브라우저 컨텍스트에서 API Key 발급을 유도하고, API Key 단독 인증 구조가 계정 탈취 이후 지속 접근 및 자동화 공격으로 확장될 수 있음을 검증한 Red Team 포트폴리오 랩입니다.

본 시나리오는 XSS로 HttpOnly 세션 쿠키를 직접 탈취하는 방식이 아니다. 피해자의 로그인된 브라우저 컨텍스트에서 same-origin 요청을 수행하여 /api/key를 호출하고, 발급된 API Key가 만료·scope·IP 제한 없이 동작하는 구조를 악용한다. 이후 공격자는 세션 쿠키 없이 X-API-KEY 헤더만으로 /api/withdraw를 호출할 수 있으며, 이는 계정 탈취 이후 지속 접근 및 자동화 공격으로 확장될 수 있다.

### Local XSS payload (only /lab/events)
```html
<script>
fetch('/api/key', { method: 'POST', credentials: 'same-origin' })
.then(r => r.json())
.then(data => fetch('/lab/events', {
  method: 'POST', headers: {'Content-Type': 'application/json'}, credentials: 'same-origin',
  body: JSON.stringify({ event_type: 'xss_api_key_generation', detail: JSON.stringify(data) })
}));
</script>
```
