import { useState } from 'react'
import { Eraser, Lock, Tag } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label, Muted } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { recordKeys } from './api'

const NAME_MAX = 200

export function IncidentNameForge({
  incidentId,
  name,
}: {
  incidentId: number
  name: string | null
}) {
  const [draft, setDraft] = useState(name ?? '')
  const { reason } = useGodGate()
  const invalidate = [recordKeys.all]
  const give = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident_name:set', {
          body: { incident_id: incidentId, name: draft.trim(), hold: true },
        })
      ),
    invalidate,
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident_name:delete', {
          body: { incident_id: incidentId },
        })
      ),
    invalidate,
  })
  const busy =
    reason() ?? (give.isPending || strike.isPending ? 'Saving the name…' : null)
  const empty = draft.trim() === '' ? 'Write a name first' : null
  return (
    <section
      aria-label='Name of the happening'
      className='flex min-w-0 flex-col gap-2'
    >
      <Label>Name of the happening</Label>
      <Muted variant='caption'>
        {name
          ? `It is called ${name}. A name you give is held against the world.`
          : 'It has no name yet. Weighty happenings are named in the tongue of those it befell, or you may name it.'}
      </Muted>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Input
          aria-label='Name to give the happening'
          maxLength={NAME_MAX}
          className='min-w-0 flex-1'
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <Button
          size='sm'
          disabled={busy !== null || empty !== null}
          disabledReason={busy ?? empty ?? undefined}
          onClick={() => give.mutate()}
        >
          {name ? <Lock /> : <Tag />}
          {name ? 'Rename and hold' : 'Name it'}
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || name === null}
          disabledReason={
            busy ?? (name === null ? 'It has no name to take away' : undefined)
          }
          onClick={() => strike.mutate()}
        >
          <Eraser />
          Take the name away
        </Button>
      </div>
    </section>
  )
}
