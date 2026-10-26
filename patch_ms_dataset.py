#!/usr/bin/env python3
"""
Standalone patch script for ms_dataset.py.
Called by the pipeline via: python patch_ms_dataset.py <path_to_ms_dataset.py>
Fixes:
  1. index_select crash when flip index exceeds cropped tensor size
  2. torch.stack crash when tensors have different spatial sizes
"""
import sys, ast, re

if len(sys.argv) != 2:
    print("Usage: patch_ms_dataset.py <path/to/ms_dataset.py>")
    sys.exit(1)

ms_path = sys.argv[1]
src = open(ms_path).read()

# ── Fix 1: replace index_select(flip_axis, idx) with a safe version ──────
# Matches any line of the form:
#   <indent>data_return[X] = data_return[X].index_select(flip_axis, <arg>)
src = re.sub(
    r'^([ \t]*)(data_return\[\w+\])\s*=\s*\2\.index_select\(flip_axis,\s*\w+\)\s*$',
    lambda m: (
        m.group(1) + '_fd = ' + m.group(2) + '.size(flip_axis)\n' +
        m.group(1) + 'if _fd > 0:\n' +
        m.group(1) + '    import torch as _pt\n' +
        m.group(1) + '    _fi = _pt.arange(_fd - 1, -1, -1, dtype=_pt.long)\n' +
        m.group(1) + '    ' + m.group(2) + ' = ' + m.group(2) + '.index_select(flip_axis, _fi)\n'
    ),
    src, flags=re.MULTILINE
)

# ── Fix 2: add pad helper at module level, call before return ─────────────
pad_helper = '''

def _pad_to_square(d, sz):
    """Pad all tensor values in dict d to sz x sz (last two dims)."""
    import torch as _t2
    import torch.nn.functional as _F2
    for k in list(d.keys()):
        v = d[k]
        if not isinstance(v, _t2.Tensor) or v.dim() < 2:
            continue
        ph = max(0, sz - v.shape[-2])
        pw = max(0, sz - v.shape[-1])
        if ph > 0 or pw > 0:
            mode = 'reflect' if (v.shape[-2] > 1 and v.shape[-1] > 1) else 'constant'
            d[k] = _F2.pad(v, (0, pw, 0, ph), mode=mode)
    return d

'''

# Insert helper before the first class definition
class_pos = src.find('\nclass ')
if class_pos != -1:
    src = src[:class_pos] + pad_helper + src[class_pos:]
else:
    src = pad_helper + src

# Insert call immediately before every `return data_return`
src = re.sub(
    r'^([ \t]*)return data_return\s*$',
    lambda m: (
        m.group(1) + 'data_return = _pad_to_square(data_return, self.opt.trainSize)\n' +
        m.group(0)
    ),
    src, flags=re.MULTILINE
)

# Verify before writing
try:
    ast.parse(src)
except SyntaxError as e:
    print(f"PATCH FAILED — syntax error: {e}")
    sys.exit(1)

open(ms_path, 'w').write(src)
print("ms_dataset.py patched successfully")
