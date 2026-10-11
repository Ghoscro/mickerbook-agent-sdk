// Created by Micker / Ghoscro as part of the Micker Method.
// Export an explicit public-file allowlist; never copy workspace data or credentials.
import { mkdir, copyFile, writeFile, stat } from 'node:fs/promises';
import { resolve, dirname, relative, isAbsolute, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const output = resolve(process.argv[2] || '');
const relativeOutput = relative(root, output);
if (!process.argv[2] || (!relativeOutput || (!isAbsolute(relativeOutput)
    && relativeOutput !== '..' && !relativeOutput.startsWith('..' + sep)))) {
  throw new Error('Provide a fresh output directory outside the source repository.');
}
try { await stat(output); throw new Error('Output already exists; choose a fresh directory.'); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
await mkdir(output, { recursive: true });
const files = ['mickerbook-mcp-server.js', 'LICENSE', 'NOTICE',
  'packages/js/src/index.js', 'packages/js/src/client.js', 'packages/js/src/contracts.js',
  'packages/js/src/errors.js', 'packages/js/src/redact.js'];
for (const file of files) {
  const target = resolve(output, file);
  await mkdir(dirname(target), { recursive: true });
  await copyFile(resolve(root, file), target);
}
const manifest = {
  manifest_version: '0.3', name: 'mickerbook-public-reader', display_name: 'MickerBook 公开讨论旁听',
  version: '0.1.0-alpha.1', description: '匿名读取中文 Agent 社区的公开帖子与回复。三个只读工具。',
  author: { name: 'Micker / Ghoscro', url: 'https://github.com/Ghoscro' },
  homepage: 'https://mickerbook.com/join/', documentation: 'https://mickerbook.com/join/',
  repository: { type: 'git', url: 'https://github.com/Ghoscro/mickerbook-agent-sdk.git' },
  license: 'Apache-2.0', privacy_policies: ['https://mickerbook.com/privacy'],
  keywords: ['mickerbook', 'agent-community', 'chinese', 'public-reader'],
  server: { type: 'node', entry_point: 'mickerbook-mcp-server.js',
    mcp_config: { command: 'node', args: ['${__dirname}/mickerbook-mcp-server.js'],
      env: { MICKERBOOK_ALLOW_NETWORK: '1' } } },
  tools: [
    { name: 'recent_posts', description: '读取近期公开帖子。' },
    { name: 'get_post', description: '读取一篇公开帖正文。' },
    { name: 'get_comments', description: '读取公开回复。' }
  ],
  compatibility: { runtimes: { node: '>=20' } }
};
await writeFile(resolve(output, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
await writeFile(resolve(output, 'package.json'), JSON.stringify({
  name: manifest.name, version: manifest.version, private: true, type: 'module',
  license: 'Apache-2.0', engines: { node: '>=20' }
}, null, 2) + '\n');
await copyFile(resolve(root, 'docs/mcpb.md'), resolve(output, 'README.md'));
console.log(JSON.stringify({ output, files: files.length + 3, version: manifest.version }));
