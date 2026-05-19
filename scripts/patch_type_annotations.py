import re
from pathlib import Path

root = Path('.')
files = list(root.glob('tests/**/*.py'))

for path in files:
    text = path.read_text(encoding='utf-8')
    text = re.sub(
        r'^(async\s+def|def)\s+([A-Za-z_]\w*\([^\)]*\))\s*\r?\n(\s{4,})("""|\')',
        r'\1 \2:\n\3\4',
        text,
        flags=re.M,
    )
    text = re.sub(
        r'^(async\s+def|def)\s+([A-Za-z_]\w*\([^\)]*\))\s*\r?\n(\s{4,})#',
        r'\1 \2:\n\3#',
        text,
        flags=re.M,
    )
    text = re.sub(
        r'^(async\s+def|def)\s+([A-Za-z_]\w*\([^\)]*\))\s*\r?\n(\s{4,})$',
        r'\1 \2:\n\3',
        text,
        flags=re.M,
    )
    if 'from typing import Any' not in text:
        text = 'from typing import Any\n' + text
    path.write_text(text, encoding='utf-8')
