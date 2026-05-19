import re
from pathlib import Path

root = Path('.')
files = list(root.glob('tests/**/*.py'))

for path in files:
    text = path.read_text(encoding='utf-8')
    fixed = re.sub(
        r'^(async\s+def|def)\s+([A-Za-z_]\w*\([^)]*\)(?:\s*->\s*[^\r\n]*)?)(?!:)\s*\r?\n(?=\s{4,})',
        r'\1 \2:\n',
        text,
        flags=re.M,
    )
    fixed = re.sub(
        r'(@pytest\.fixture\s*\n\s*def\s+[A-Za-z_]\w*\([^\)]*\)\s*->\s*)None(\s*:)',
        r'\1Any\2',
        fixed,
        flags=re.M,
    )
    fixed = re.sub(
        r'async def run_gate\(\)\s*:',
        r'async def run_gate() -> tuple[Any, Any]:',
        fixed,
        flags=re.M,
    )
    fixed = re.sub(
        r'->\s*Any::',
        r'-> Any:',
        fixed,
        flags=re.M,
    )
    if fixed != text:
        print(f'patched {path}')
        path.write_text(fixed, encoding='utf-8')
