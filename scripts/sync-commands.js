import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';

// skills/<name>/SKILL.md 를 원본으로 Claude 커맨드(commands/<name>.md)를 생성합니다.
const repoRoot = new URL('../', import.meta.url);
const commands = [
  {
    name: 'markdown-rules',
    description: '한국어 Markdown 문서 작성·수정 규칙(구성, 포맷, 토큰 효율)을 적용한다',
    argumentHint: '[작성 또는 수정할 문서·요청]',
    replace: [['사용자가 이 스킬을 명시적으로 지정한 작업에서만', '이 커맨드로 호출한 작업에서만']],
  },
];

mkdirSync(new URL('commands/', repoRoot), { recursive: true });

for (const { name, description, argumentHint, replace } of commands) {
  const source = readFileSync(new URL(`skills/${name}/SKILL.md`, repoRoot), 'utf8').replace(/\r\n/g, '\n');
  const match = source.match(/^---\n[\s\S]*?\n---\n+([\s\S]*)$/);
  if (!match) throw new Error(`skills/${name}/SKILL.md: frontmatter가 없습니다.`);

  let body = match[1].trimEnd();
  for (const [from, to] of replace) {
    if (!body.includes(from)) throw new Error(`skills/${name}/SKILL.md: 치환 대상이 없습니다: ${from}`);
    body = body.replace(from, to);
  }

  const content = [
    '---',
    `description: ${description}`,
    `argument-hint: ${argumentHint}`,
    '---',
    '',
    body,
    '',
    '## 요청',
    '',
    '$ARGUMENTS',
    '',
    '위 요청이 비어 있으면 현재 대화의 문서 작업에 위 규칙을 적용한다.',
    '',
  ].join('\n');

  writeFileSync(new URL(`commands/${name}.md`, repoRoot), content);
  console.log(`commands/${name}.md 생성`);
}
