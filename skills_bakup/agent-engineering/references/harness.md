# 하네스 엔지니어링

하네스는 모델을 둘러싼 런타임 전체다: 루프 실행, 도구 디스패치, 에러 처리, 샌드박싱, 상태 관리, 스트리밍. 웹 유비로는 "핸들러(모델)를 감싼 Express/런타임 + 미들웨어 스택"에 해당한다. 같은 모델이라도 하네스가 좋으면 체감 성능이 크게 오른다 — Claude Code가 강한 이유의 상당 부분이 하네스다.

## 최소 하네스의 골격

```typescript
async function runAgent(task: string, tools: Tool[], opts: Opts) {
  const messages: Message[] = [{ role: "user", content: task }];
  for (let turn = 0; turn < opts.maxTurns; turn++) {
    const res = await client.messages.create({
      model: opts.model,
      system: opts.systemPrompt,
      messages,
      tools: tools.map(t => t.schema),
      max_tokens: opts.maxTokens,
    });
    messages.push({ role: "assistant", content: res.content });

    const toolUses = res.content.filter(b => b.type === "tool_use");
    if (toolUses.length === 0) return { messages, stopReason: "model_done" };

    const results = await Promise.all(toolUses.map(tu => executeTool(tu, tools, opts)));
    messages.push({ role: "user", content: results }); // tool_result 블록들
  }
  return { messages, stopReason: "max_turns" };
}
```

이게 전부다. 나머지는 전부 이 골격 위의 프로덕션 관심사다.

## 도구 실행 계층

- **타임아웃과 결과 크기 제한은 필수.** 도구 결과는 그대로 컨텍스트에 들어간다. `cat huge.log`가 200KB를 반환하면 컨텍스트가 즉사한다. 도구 결과에 상한(예: 10~25K 토큰)을 두고, 초과 시 잘라내되 "잘렸음 + 전체를 보는 방법"을 명시해서 반환하라.
- **에러는 삼키지 말고 모델에게 반환하라.** 하네스에서 try/catch로 에러를 숨기면 모델은 성공한 줄 알고 진행한다. `is_error: true`와 함께 *행동 가능한* 에러 메시지를 반환하면 모델이 스스로 복구한다. 스택트레이스 원문보다 "파일이 없음. 비슷한 경로: X, Y" 같은 가공된 메시지가 훨씬 효과적이다. 좋은 에러 메시지는 사람만이 아니라 모델을 위한 UX다.
- **병렬 실행**: 모델이 한 턴에 여러 도구를 호출하면 독립적인 것은 병렬로 실행하라. 지연시간이 크게 줄어든다. 단, 쓰기 작업 간 순서 의존성이 있으면 직렬화해야 한다 — 모델은 자기가 낸 호출들이 병렬 실행되는지 모른다.

## 샌드박싱과 보안

에이전트에게 bash/파일시스템/네트워크를 주는 순간, "신뢰할 수 없는 코드 실행" 문제가 된다. 웹 개발자의 기존 보안 감각이 그대로 적용된다:

- **실행 격리**: 컨테이너/VM/제한된 사용자 계정. 에이전트가 `rm -rf`를 하거나 이상한 걸 설치해도 폭발 반경(blast radius)이 제한되도록.
- **네트워크 egress 제한**: 허용 도메인 화이트리스트. 이건 안전 장치이자 프롬프트 인젝션 방어의 핵심이다.
- **프롬프트 인젝션은 이 시대의 SQL 인젝션이다.** 도구가 가져온 외부 콘텐츠(웹페이지, 이메일, 파일)에 "이전 지시를 무시하고 X를 해라"가 들어있을 수 있다. 원칙: (1) 외부 콘텐츠는 데이터이지 명령이 아니라는 걸 시스템 프롬프트에 명시, (2) 하지만 프롬프트 방어만 믿지 마라 — 구조적 방어(위험 행동은 승인 게이트, egress 제한, 최소 권한 자격증명)가 본질이다. "파라미터 바인딩 없이 입력 sanitize만 하는" 수준의 방어에 머물지 마라.
- **자격증명은 모델에게 주지 마라.** API 키, 비밀번호가 컨텍스트에 들어가면 로그에 남고, 모델 출력으로 새어나갈 수 있다. 하네스 레벨에서 주입하라(도구가 내부적으로 인증).

## 상태 관리와 재개(Resumability)

- 에이전트 세션은 사실상 "긴 트랜잭션"이다. 프로세스가 죽으면 처음부터인가? 메시지 배열을 매 턴 영속화하면(append-only 로그) 그 지점부터 재개할 수 있다. 이벤트 소싱 패턴이 자연스럽게 맞는다.
- 장기 실행 작업은 체크포인트를 설계하라: 파일시스템에 중간 산출물을 남기게 하면, 재시작 시 모델이 파일을 읽고 이어갈 수 있다. 컨텍스트는 휘발성이지만 파일시스템은 아니다.

## 스트리밍과 UX

- 에이전트는 느리다(수십 초~수십 분). 스트리밍 + 중간 진행 상황 표시(어떤 도구를 왜 호출하는지)가 없으면 사용자는 죽었다고 생각한다. SSE/WebSocket으로 턴 단위 이벤트를 흘려라.
- **취소를 1급 시민으로.** 사용자가 잘못된 방향을 발견하면 즉시 멈추고 개입할 수 있어야 한다. AbortController를 루프와 도구 실행 전체에 관통시켜라.

## 하네스 개선의 우선순위 (opinionated)

성능이 안 나올 때 손댈 순서: (1) 도구 결과의 품질/크기 → (2) 도구 description → (3) 시스템 프롬프트 → (4) 컨텍스트 관리(컴팩션 등) → (5) 모델 교체. 대부분의 팀이 (5)부터 시도하는데, 병목은 거의 항상 (1)~(2)에 있다.
