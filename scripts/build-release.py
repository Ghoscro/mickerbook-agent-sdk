"""Build official-download artifacts after npm pack and python -m build.

Run from any directory. Output is public-only; upload versioned files first,
verify them, then atomically publish mickerbook-updates.json as the last step.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=root/'dist/release')
args = parser.parse_args()
sdk = json.loads((root/'package.json').read_text())['version']
skill_text = (root/'skill/SKILL.md').read_text(encoding='utf-8')
skill = re.search(r'^  version: "([0-9.]+)"$', skill_text, re.M).group(1)
assert re.fullmatch(r'\d+\.\d+\.\d+', sdk)
assert json.loads((root/'packages/js/package.json').read_text())['version'] == sdk
assert f'version = "{sdk}"' in (root/'packages/python/pyproject.toml').read_text()
out = args.output
out.mkdir(parents=True, exist_ok=False)
names = [f'mickerbook_sdk-{sdk}-py3-none-any.whl', f'mickerbook_sdk-{sdk}.tar.gz', f'mickerbook-sdk-js-{sdk}.tgz']
for name in names:
    shutil.copyfile(root/'dist'/name, out/name)
for source, name in [('skill/SKILL.md','SKILL.md'), ('packages/python/src/mickerbook_sdk/update.py','update.py'), ('packages/js/bin/micker.cjs','micker.cjs')]:
    shutil.copyfile(root/source,out/name)
archive = f'mickerbook-skill-{skill}.zip'
with zipfile.ZipFile(out/archive,'w',zipfile.ZIP_DEFLATED) as bundle:
    for name in ['SKILL.md','update.py','micker.cjs']:
        bundle.write(out/name,name)
def artifact(name):
    return {'url':f'https://mickerbook.com/sdk/v{sdk}/{name}', 'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()}
manifest = {'schemaVersion':1, 'sdkVersion':sdk, 'skillVersion':skill,
    'releaseNotes':'https://mickerbook.com/updates',
    'releaseUrl':f'https://github.com/Ghoscro/mickerbook-agent-sdk/releases/tag/v{sdk}',
    'skillFiles':{name:artifact(name) for name in ['SKILL.md','update.py','micker.cjs']},
    'packages':{'python':artifact(names[0]),'javascript':artifact(names[2]),'skill':artifact(archive)}}
(out/'mickerbook-updates.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.iterdir())))
print(out)
