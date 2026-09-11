import { readFileSync, writeFileSync } from 'node:fs';
import { createInterface } from 'node:readline';

const repoRoot = new URL('../', import.meta.url);
const targets = [
  ['package.json', ['version']],
  ['.claude-plugin/marketplace.json', ['metadata', 'version']],
  ['.codex-plugin/plugin.json', ['version']],
];

const numeric = '(0|[1-9][0-9]*)';
const identifier = '(0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)';
const semver = new RegExp(
  `^${numeric}\\.${numeric}\\.${numeric}` +
  `(-${identifier}(\\.${identifier})*)?` +
  '(\\+[0-9A-Za-z-]+(\\.[0-9A-Za-z-]+)*)?$',
);

try {
  const currentVersion = JSON.parse(
    readFileSync(new URL('package.json', repoRoot), 'utf8'),
  ).version;

  const version = await new Promise((resolve, reject) => {
    const readline = createInterface({ input: process.stdin, output: process.stdout });
    readline.once('close', () => reject(new Error('입력이 취소되었습니다.')));
    readline.once('SIGINT', () => readline.close());
    readline.question(`현재 버전: ${currentVersion}, 다음 버전은? `, (answer) => {
      resolve(answer.trim());
      readline.close();
    });
  });

  if (!semver.test(version)) {
    throw new Error('올바른 버전을 입력하세요. 예: 1.3.2, 2.0.0-beta.1');
  }

  // 모든 파일을 읽고 검증한 후에 쓰기를 시작합니다.
  const updates = targets.map(([file, path]) => {
    const source = readFileSync(new URL(file, repoRoot), 'utf8');
    const data = JSON.parse(source);
    const parent = path.slice(0, -1).reduce((value, key) => value?.[key], data);
    const key = path.at(-1);
    if (!parent || typeof parent[key] !== 'string') {
      throw new Error(`${file}: ${path.join('.')} 필드가 없습니다.`);
    }
    parent[key] = version;
    const indent = source.match(/\n([\t ]+)"/)?.[1] ?? '  ';
    const newline = source.includes('\r\n') ? '\r\n' : '\n';
    const suffix = source.endsWith('\n') ? newline : '';
    return [file, JSON.stringify(data, null, indent).replace(/\n/g, newline) + suffix];
  });

  for (const [file, content] of updates) {
    writeFileSync(new URL(file, repoRoot), content);
    console.log(`${file}: ${version}`);
  }
} catch (error) {
  console.error(`오류: ${error.message}`);
  process.exitCode = 1;
}
