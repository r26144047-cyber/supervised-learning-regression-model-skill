"""使用內附人工資料測試三種指令及全部七個模型。"""
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
script = root / 'scripts' / 'run_regression.py'
data = root / 'tests' / 'demo.csv'
for action in ('inspect', 'diagnose'):
    subprocess.run([sys.executable, str(script), action, '--data', str(data),
                    '--target', 'y', '--features', 'x', 'z', 'group'], check=True,
                   stdout=subprocess.DEVNULL)
with tempfile.TemporaryDirectory() as td:
    for model in ('linear', 'polynomial', 'ridge', 'lasso', 'logistic', 'ridge_logistic', 'lasso_logistic'):
        target = 'binary' if 'logistic' in model else 'y'
        subprocess.run([sys.executable, str(script), 'fit', '--data', str(data),
                        '--target', target, '--features', 'x', 'z', 'group',
                        '--model', model, '--output', str(Path(td) / model)],
                       check=True, stdout=subprocess.DEVNULL)
print('全部測試通過')
