import { useState } from 'react'
import { Gavel, Save, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { ConfirmDialog } from '@/components/domain'
import { Muted } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { councilKeys } from './api'

const TOPIC_MAX = 400

export function CouncilRecordControls({
  councilId,
  topic,
  passed,
}: {
  councilId: number
  topic: string
  passed: boolean
}) {
  const [draft, setDraft] = useState(topic)
  const [carried, setCarried] = useState(passed)
  const [confirming, setConfirming] = useState(false)
  const { reason } = useGodGate()
  const invalidate = [councilKeys.list]
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/council_record:edit', {
          body: { council_id: councilId, topic: draft.trim(), passed: carried },
        })
      ),
    invalidate,
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/council_record:delete', {
          body: { council_id: councilId },
        })
      ),
    invalidate,
  })
  const busy =
    reason() ??
    (edit.isPending || strike.isPending ? 'Saving the record…' : null)
  const empty = draft.trim() === '' ? 'Write the topic first' : null
  const same =
    draft.trim() === topic && carried === passed
      ? 'Nothing has changed yet'
      : null
  return (
    <section
      aria-label='Rewrite the council record'
      className='flex min-w-0 flex-col gap-2'
    >
      <Label htmlFor={`council-topic-${councilId}`}>Topic of the council</Label>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Input
          id={`council-topic-${councilId}`}
          maxLength={TOPIC_MAX}
          className='min-w-0 flex-1'
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <div className='flex items-center gap-2'>
          <Switch
            id={`council-passed-${councilId}`}
            checked={carried}
            onCheckedChange={setCarried}
            aria-label='The motion passed'
          />
          <Label htmlFor={`council-passed-${councilId}`}>Passed</Label>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          disabled={busy !== null || empty !== null || same !== null}
          disabledReason={busy ?? empty ?? same ?? undefined}
          onClick={() => edit.mutate()}
        >
          <Save />
          Rewrite the record
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setConfirming(true)}
        >
          <Trash2 />
          Strike it from the record
        </Button>
      </div>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title='Strike this council from the record?'
        desc='The council, its speeches and its ballots leave the record of the gods. Rulings it passed stay in force.'
        confirmText='Strike it'
        destructive
        handleConfirm={() => {
          setConfirming(false)
          strike.mutate()
        }}
      />
    </section>
  )
}

export function CouncilRecordForge() {
  const [topic, setTopic] = useState('')
  const [carried, setCarried] = useState(false)
  const { reason } = useGodGate()
  const make = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/council_record:create', {
          body: { topic: topic.trim(), passed: carried },
        })
      ),
    invalidate: [councilKeys.list],
    onDone: () => setTopic(''),
  })
  const busy = reason() ?? (make.isPending ? 'Setting it down…' : null)
  const empty = topic.trim() === '' ? 'Write the topic first' : null
  return (
    <section
      aria-label='Set down a council'
      className='flex min-w-0 flex-col gap-2'
    >
      <Label htmlFor='council-new-topic'>Set down a council of the gods</Label>
      <Muted variant='caption'>
        Write a council into the record with its topic and whether its motion
        passed.
      </Muted>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Input
          id='council-new-topic'
          maxLength={TOPIC_MAX}
          className='min-w-0 flex-1'
          value={topic}
          onChange={(event) => setTopic(event.target.value)}
        />
        <div className='flex items-center gap-2'>
          <Switch
            id='council-new-passed'
            checked={carried}
            onCheckedChange={setCarried}
            aria-label='The motion passed'
          />
          <Label htmlFor='council-new-passed'>Passed</Label>
        </div>
        <Button
          size='sm'
          disabled={busy !== null || empty !== null}
          disabledReason={busy ?? empty ?? undefined}
          onClick={() => make.mutate()}
        >
          <Gavel />
          Set it down
        </Button>
      </div>
    </section>
  )
}
