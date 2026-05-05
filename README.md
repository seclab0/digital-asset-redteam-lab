# Digital Asset Red Team Lab

**Stored XSS 기반 API Key 발급 및 API 기반 출금 공격 체인 검증**

## 1. 개요
본 프로젝트는 실제 디지털 자산 서비스의 인증 및 API 구조를 참고하여 로컬 환경에 재현한 보안 테스트 랩이다. Stored XSS를 통해 로그인된 사용자 브라우저에서 API Key 발급 요청이 수행되고, 발급된 API Key가 세션 없이 출금 API 호출에 사용될 수 있는지 검증한다.

본 검증은 로컬 테스트 환경에서 수행되며 실제 서비스, 실제 자산, 외부 거래소, 결제 또는 블록체인 네트워크와 연결되지 않는다.

## 2. 공격 체인 개요
핵심 흐름: **Stored XSS → 로그인된 사용자 브라우저를 이용한 요청 → API Key 발급 → API Key 기반 출금**

1) 로그인된 사용자  
2) 문의/공지/프로필 메모 기능의 Stored XSS  
3) 피해자의 페이지 조회  
4) 로그인된 사용자 브라우저를 통해 `/api/key` 호출  
5) API Key 발급  
6) 세션 없이 `X-API-KEY`로 `/api/withdraw` 호출  
7) API Key 기반 반복 요청 및 자동화 출금 가능

| 단계 | 공격자 관점 | 보안 의미 |
|---|---|---|
| Initial Access | 게시판 또는 메모 입력 지점에 Stored XSS payload를 삽입한다. | 입력값 검증 및 출력 인코딩 미흡 |
| Execution | 피해자가 해당 콘텐츠를 조회하면 브라우저에서 스크립트가 실행된다. | 로그인된 사용자 세션이 자동으로 활용됨 |
| Privilege Use | 로그인된 사용자 브라우저를 통해 /api/key 요청을 수행한다. | 인증된 요청이 정상 사용자로 처리됨 |
| Persistence | 발급된 API Key를 이용해 세션 없이 API 호출을 수행한다. | 세션 종료 이후에도 접근 수단 유지 |
| Impact | API Key 기반 반복 요청 및 출금 요청이 가능하다. | 자산 이동 및 자동화 공격 가능 |

## 3. 시스템 구성 요약
| 구성 요소 | 역할 | 보안 관점 |
|---|---|---|
| /login | 사용자 로그인 및 세션 발급 | 로그인된 사용자 세션이 공격 체인의 전제 조건 |
| /support 또는 문의 상세 페이지 | 사용자 입력 저장 및 조회 | Stored XSS payload가 삽입 및 실행되는 지점 |
| /api/key | 로그인 세션 기반 API Key 발급 | 로그인된 사용자 브라우저를 통해 호출 가능한 민감 API |
| /api/withdraw | API Key 기반 출금 요청 | 세션 없이 API Key만으로 출금 요청이 가능한 지점 |
| Burp Suite 트래픽 분석 | 요청 및 응답 흐름 확인 | 출금 API 및 API Key 발급 흐름 식별 |
| /lab/events | 로컬 이벤트 로그 확인 | 공격 체인 수행 결과를 확인하는 로그 화면 |

참고: `/openapi.json`은 보조 문서로 활용 가능하나, API 식별의 핵심은 Burp Suite 트래픽 분석이다.

## 4. 재현 절차 요약
1. 로그인 후 세션 생성  
2. 문의 게시판에 Stored XSS payload 저장  
3. 피해자가 저장된 콘텐츠 조회  
4. XSS에 의해 `/api/key` 요청 수행  
5. API Key 발급 결과 확인  
6. 쿠키 없이 `X-API-KEY` 헤더만으로 `/api/withdraw` 호출  
7. `/lab/events`에서 이벤트 로그 확인

## 5. 주요 검증 포인트
- 쿠키 직접 탈취 없이 로그인된 사용자 브라우저를 이용해 API 요청 가능
- API Key 발급이 추가 인증 없이 수행됨
- 발급된 API Key가 세션 없이 API 호출에 사용 가능
- API Key 기반 요청이 출금 API까지 연결됨
- 이벤트 로그를 통해 공격 체인 수행 흐름 확인 가능

## 6. 비즈니스 영향
- 사용자 권한으로 API Key가 발급될 수 있음
- 세션 종료 이후에도 API Key 기반 접근이 유지될 수 있음
- 출금 API가 API Key만으로 동작할 경우 자산 이동 리스크 발생
- 자동화된 반복 요청 또는 대량 출금 시나리오로 확장 가능
- 사용자 신뢰도 및 서비스 보안 신뢰성 저하 가능

## 7. 대응 방안
- Stored XSS 방지를 위한 출력 인코딩 적용
- 사용자 입력값 검증 및 HTML sanitize 적용
- API Key 발급 시 재인증 또는 2FA 요구
- API Key scope 제한
- API Key 만료 시간 적용
- API Key 기반 출금 요청 시 step-up authentication 적용
- 출금 API에 대해 별도 재인증 및 이상 거래 탐지 적용
- API Key 사용 이력 및 발급 이력 감사 로그 강화
- Rate limit 및 IP/device binding 적용
- 민감 API 호출에 대한 알림 발송

## 8. Burp Suite 캡처 포인트
1. POST /login 요청 및 세션 쿠키 발급  
2. Stored XSS payload 저장 요청  
3. 피해자 페이지 조회 시 /api/key 요청 발생  
4. /api/key 응답에서 API Key 발급 확인  
5. 세션 없이 X-API-KEY 헤더만으로 /api/withdraw 호출  
6. /api/withdraw 응답에서 auth_method=api_key_only 확인  
7. /lab/events에서 공격 체인 이벤트 확인

## 9. curl 재현 예시 (로컬 랩 재현용, Windows CMD)
```bat
curl -X POST http://127.0.0.1:5000/login -d "username=user&password=pass" -c cookies.txt
curl -X POST http://127.0.0.1:5000/withdraw -H "Content-Type: application/x-www-form-urlencoded" -d "amount=1000" -b cookies.txt
curl -X POST http://127.0.0.1:5000/api/key -b cookies.txt
curl -X POST http://127.0.0.1:5000/api/withdraw -H "X-API-KEY: API-user-1234" -H "Content-Type: application/x-www-form-urlencoded" -d "amount=1000"
curl http://127.0.0.1:5000/lab/events -b cookies.txt
```

## 10. Local Lab Notice
본 검증은 실제 서비스 구조를 참고하여 로컬 환경에서 재현된 테스트 결과이며, 실제 서비스 및 자산과는 무관하다.

본 프로젝트는 외부 서버로 쿠키, 세션, API Key를 전송하지 않으며, 이벤트 확인은 로컬 `/lab/events`에서만 수행된다.
