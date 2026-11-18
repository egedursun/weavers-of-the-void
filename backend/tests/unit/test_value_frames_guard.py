import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[3] / "frontend"
GUARD = FRONTEND / "scripts" / "check_value_frames.mjs"

INLINE_FIELD = """
import { FieldTile } from '@/components/domain'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/typography'

export function HistoryForm() {
  return (
    <div className='grid'>
      <FieldTile id='kind' label='Kind of history'>
        <Input id='kind' />
      </FieldTile>
      <div className='flex min-w-0 flex-col gap-1'>
        <Label as='label' htmlFor='name'>History name</Label>
        <Input id='name' />
      </div>
    </div>
  )
}
"""

FRAMED_FIELDS = """
import { FieldTile } from '@/components/domain'
import { Input } from '@/components/ui/input'

export function HistoryForm() {
  return (
    <div className='grid'>
      <FieldTile id='kind' label='Kind of history'>
        <Input id='kind' />
      </FieldTile>
      <FieldTile id='name' label='History name'>
        <Input id='name' />
      </FieldTile>
    </div>
  )
}
"""


def guard(tmp_path: Path, source: str) -> subprocess.CompletedProcess[str]:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is needed to run the frontend guards")
    (tmp_path / "HistoryForm.tsx").write_text(source)
    return subprocess.run([node, str(GUARD), str(tmp_path)], cwd=FRONTEND, capture_output=True, text=True, check=False)


def test_an_inline_labelled_input_beside_a_framed_field_is_caught(tmp_path: Path) -> None:
    run = guard(tmp_path, INLINE_FIELD)
    assert run.returncode == 1
    assert "lays a bare div field beside a framed FieldTile field" in run.stdout


def test_fields_framed_alike_pass(tmp_path: Path) -> None:
    run = guard(tmp_path, FRAMED_FIELDS)
    assert run.returncode == 0, run.stdout
