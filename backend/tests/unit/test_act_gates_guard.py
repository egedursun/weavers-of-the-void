import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[3] / "frontend"
GUARD = FRONTEND / "scripts" / "check_act_gates.mjs"

ESCAPES = """
import { useMutation } from '@tanstack/react-query'
export function Escapes() {
  const save = useGodAction({ run: () => api.POST('/api/actions/x:y', {}) })
  const [hold] = useState(true)
  return (
    <>
      <DialogTrigger asChild><Button>Open</Button></DialogTrigger>
      <Button onClick={() => save.mutate()}>Save</Button>
      <Switch checked={hold} />
    </>
  )
}
export function Forgets() {
  void api.DELETE('/api/presence')
  return null
}
export async function sendThing(id) {
  return api.POST('/api/actions/x:send', { body: { id } })
}
export function Sends() {
  const send = useLoreMutation({ run: (id) => sendThing(id) })
  return <Button act={send} onClick={() => send.mutate(1)}>Send</Button>
}
export function useRow() {
  const editing = useGodAction({ writes: [{ lever: 'x:edit' }], run: () => api.POST('/api/actions/x:edit', {}) })
  return { busy: editing.isPending ? 'Working' : null, onEdit: () => editing.mutate() }
}
export function Inline() {
  const save = useGodAction({ writes: [{ lever: 'x:save' }], run: () => api.POST('/api/actions/x:save', {}) })
  const [editing, setEditing] = useState(false)
  const [writing, setWriting] = useState(false)
  return (
    <>
      <Button onClick={() => setEditing((value) => !value)}>Edit</Button>
      {editing && <Button act={save} onClick={() => save.mutate()}>Save</Button>}
      <Button onClick={() => setWriting(true)}>Write</Button>
      {writing ? <Button act={save} onClick={() => save.mutate()}>Keep</Button> : null}
    </>
  )
}
function NoteEditor() {
  const keep = useGodAction({ writes: [{ lever: 'x:keep' }], run: () => api.POST('/api/actions/x:keep', {}) })
  return <Button act={keep} onClick={() => keep.mutate()}>Keep</Button>
}
export function OpensEditor() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button onClick={() => setOpen(!open)}>Edit note</Button>
      {open && <NoteEditor />}
    </>
  )
}
export function useWrapped(run) {
  return useMutation({ mutationFn: run })
}
export function Opens() {
  const strike = useGodAction({ writes: [{ lever: 'x:strike' }], run: () => api.POST('/api/actions/x:strike', {}) })
  const [confirming, setConfirming] = useState(false)
  const start = () => setConfirming(true)
  return (
    <>
      <Button onClick={() => setConfirming(true)}>Strike</Button>
      <Button onClick={start}>Strike again</Button>
      <ConfirmDialog act={strike} open={confirming} handleConfirm={() => strike.mutate()} />
    </>
  )
}
"""

GATED = """
import { useMutation } from '@/api/mutation'
export function Gated() {
  const save = useGodAction({ writes: [{ lever: 'x:y' }], run: () => api.POST('/api/actions/x:y', {}) })
  const [hold] = useState(true)
  return (
    <>
      <DialogTrigger asChild><Button act={save}>Open</Button></DialogTrigger>
      <Button act={save} onClick={() => save.mutate()}>Save</Button>
      <Switch permission='lock_canon' checked={hold} />
    </>
  )
}
export function useRowGated() {
  const editing = useGodAction({ writes: [{ lever: 'x:edit' }], run: () => api.POST('/api/actions/x:edit', {}) })
  return { busy: editing.blockedReason ?? (editing.isPending ? 'Working' : null), onEdit: () => editing.mutate() }
}
export function useWrappedGated(run) {
  return useMutation({ writes: [{ method: 'POST', path: '/api/map-notes' }], mutationFn: run })
}
export function OpensGated() {
  const strike = useGodAction({ writes: [{ lever: 'x:strike' }], run: () => api.POST('/api/actions/x:strike', {}) })
  const [confirming, setConfirming] = useState(false)
  return (
    <>
      <Button act={strike} onClick={() => setConfirming(true)}>Strike</Button>
      <Button onClick={() => setConfirming(false)}>Keep it</Button>
      <ConfirmDialog act={strike} open={confirming} handleConfirm={() => strike.mutate()} />
    </>
  )
}
"""


def guard(folder: Path, source: str) -> subprocess.CompletedProcess[str]:
    node = shutil.which("node")
    if node is None:
        pytest.fail("node is needed to run the frontend guards")
    folder.mkdir()
    (folder / "Screen.tsx").write_text(source)
    return subprocess.run([node, str(GUARD), str(folder)], cwd=FRONTEND, capture_output=True, text=True, check=False)


def test_every_way_a_write_escapes_the_team_gate_is_caught(tmp_path: Path) -> None:
    run = guard(tmp_path / "escapes", ESCAPES)
    assert run.returncode == 1
    for needle in (
        "import useMutation from '@/api/mutation'",
        "writes without naming it",
        "opens a place to act but its trigger has no act",
        "fires save without act",
        "a hold switch needs permission='lock_canon'",
        "fired and forgotten",
        "opens a <ConfirmDialog> that acts, but has no act",
        "whose writes the gate cannot see",
        "useLoreMutation writes without naming it",
        "busy reads editing.isPending but not its blockedReason",
        "opens an inline form that acts",
    ):
        assert needle in run.stdout
    assert run.stdout.count("opens an inline form that acts") == 3
    assert run.stdout.count("opens a <ConfirmDialog> that acts") == 2


def test_gated_writes_pass(tmp_path: Path) -> None:
    run = guard(tmp_path / "gated", GATED)
    assert run.returncode == 0, run.stdout
    assert "act gates: 0 problem(s)" in run.stdout
