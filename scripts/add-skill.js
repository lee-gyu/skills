import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { parseArgs } from 'node:util';

// skills/<name>/ 보일러플레이트를 만들고 .claude-plugin/marketplace.json의 plugin.skills에 등록합니다.
// 사용법: mise run add-skill <name> [--plugin <plugin-name>]
const repoRoot = new URL('../', import.meta.url);
const marketplaceFile = '.claude-plugin/marketplace.json';
const usage = '사용법: mise run add-skill <name> [--plugin <plugin-name>]';

const toTitle = (name) => name.split('-').map((word) => word[0].toUpperCase() + word.slice(1)).join(' ');

const skillTemplate = (name) => `---
name: ${name}
description: "TODO 스킬이 하는 일과 사용 시점을 작성한다. Use only when the user explicitly invokes or names the ${name} skill."
disable-model-invocation: true
---

# ${toTitle(name)}

TODO 스킬의 목적과 성공 기준을 작성한다.

## Workflow

1. TODO
`;

const openaiTemplate = (name) => `interface:
  display_name: "${toTitle(name)}"
  short_description: "TODO"
policy:
  allow_implicit_invocation: false
`;

try {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: { plugin: { type: 'string', short: 'p' } },
  });
  if (positionals.length !== 1) throw new Error(usage);

  const name = positionals[0].trim();
  if (name.length > 64 || !/^[a-z0-9]+(-[a-z0-9]+)*$/.test(name)) {
    const suggestion = name.toLowerCase().replace(/[\s_]+/g, '-');
    const hint = /^[a-z0-9]+(-[a-z0-9]+)*$/.test(suggestion) ? ` (예: ${suggestion})` : '';
    throw new Error(`스킬 이름은 64자 이하의 kebab-case(소문자, 숫자, 하이픈)여야 합니다${hint}: ${name}`);
  }

  const skillDir = new URL(`skills/${name}/`, repoRoot);
  if (existsSync(skillDir)) throw new Error(`skills/${name} 폴더가 이미 있습니다.`);

  const source = readFileSync(new URL(marketplaceFile, repoRoot), 'utf8');
  const marketplace = JSON.parse(source);
  const plugins = marketplace.plugins ?? [];
  const pluginNames = plugins.map((plugin) => plugin.name).join(', ');

  let plugin;
  if (values.plugin) {
    plugin = plugins.find((candidate) => candidate.name === values.plugin);
    if (!plugin) throw new Error(`plugin '${values.plugin}'이 없습니다. 선택 가능: ${pluginNames}`);
  } else if (plugins.length === 1) {
    plugin = plugins[0];
  } else {
    throw new Error(`plugin이 ${plugins.length}개입니다. --plugin으로 지정하세요: ${pluginNames}`);
  }
  // skills 경로는 plugin source 기준 상대 경로이므로, 저장소 루트를 source로 쓰는 plugin만 지원합니다.
  if (plugin.source !== './') {
    throw new Error(`plugin '${plugin.name}'의 source가 './'가 아닙니다: ${JSON.stringify(plugin.source)}`);
  }

  const entry = `./skills/${name}`;
  const owner = plugins.find((candidate) => candidate.skills?.includes(entry));
  if (owner) throw new Error(`${entry}가 이미 plugin '${owner.name}'에 등록되어 있습니다.`);
  plugin.skills = [...(plugin.skills ?? []), entry].sort();

  // update-version.js와 같은 방식으로 들여쓰기·줄바꿈을 보존합니다.
  const indent = source.match(/\n([\t ]+)"/)?.[1] ?? '  ';
  const newline = source.includes('\r\n') ? '\r\n' : '\n';
  const suffix = source.endsWith('\n') ? newline : '';
  const marketplaceContent = JSON.stringify(marketplace, null, indent).replace(/\n/g, newline) + suffix;

  mkdirSync(new URL('agents/', skillDir), { recursive: true });
  writeFileSync(new URL('SKILL.md', skillDir), skillTemplate(name));
  writeFileSync(new URL('agents/openai.yaml', skillDir), openaiTemplate(name));
  writeFileSync(new URL(marketplaceFile, repoRoot), marketplaceContent);

  console.log(`skills/${name}/SKILL.md 생성`);
  console.log(`skills/${name}/agents/openai.yaml 생성`);
  console.log(`${marketplaceFile}: plugin '${plugin.name}'에 ${entry} 등록`);
  console.log('TODO 항목(description, 본문, short_description)을 채우세요.');

  const registered = new Set(plugins.flatMap((candidate) => candidate.skills ?? []));
  const missing = readdirSync(new URL('skills/', repoRoot), { withFileTypes: true })
    .filter((dirent) => dirent.isDirectory() && existsSync(new URL(`skills/${dirent.name}/SKILL.md`, repoRoot)))
    .map((dirent) => `./skills/${dirent.name}`)
    .filter((path) => !registered.has(path));
  if (missing.length > 0) {
    console.warn(`경고: ${marketplaceFile}에 등록되지 않은 스킬: ${missing.join(', ')}`);
  }
} catch (error) {
  console.error(`오류: ${error.message}`);
  process.exitCode = 1;
}
