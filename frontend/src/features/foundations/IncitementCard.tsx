import { useState } from 'react'
import { Flame, Lock, Save, Sparkles, UserX } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { EntityLink, Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { militaryKeys } from '@/features/wars/military/api'
import { Adjust } from '@/features/wars/military/parts'
import { HoldToggle, NO_SON, SonSelect } from './parts'

type War = components['schemas']['WarSummary']

export function IncitementCard({
  war,
  blocked,
}: {
  war: War
  blocked: string | null
}) {
  const instigator = war.instigator ?? null
  const [son, setSon] = useState(instigator ? String(instigator.id) : NO_SON)
  const [hold, setHold] = useState(true)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/war:incite', {
          body: {
            war_id: war.id,
            son_id: son === NO_SON ? null : Number(son),
            hold,
          },
        })
      ),
    invalidate: [militaryKeys.room(war.id)],
  })
  const busy = blocked ?? (save.isPending ? 'Working…' : null)
  const ended = war.status === 'ended'
  return (
    <div
      data-surface='WarIncitement'
      className='flex min-w-0 flex-col gap-3 rounded-xl border bg-card p-4'
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion
          icon={instigator ? Flame : Sparkles}
          tone={instigator ? 'danger' : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold' truncate>
            {instigator ? (
              <>
                Set off by{' '}
                <EntityLink kind='son' id={String(instigator.id)}>
                  {instigator.name}
                </EntityLink>
              </>
            ) : (
              'No god is blamed for this war'
            )}
          </Text>
          <Muted variant='caption'>
            {instigator
              ? ended
                ? 'The instigator reaped fame, and the losers kept a grievance against them.'
                : 'When the war ends the instigator gains fame for every battle; the losers remember who set it upon them.'
              : 'A god who stirs a war up gains fame from its battles and the hatred of its losers.'}
          </Muted>
        </div>
        {war.incitement_held && (
          <Badge size='sm' variant='outline'>
            <Lock aria-hidden='true' />
            Held
          </Badge>
        )}
      </div>
      <Adjust
        label='Who set it off'
        title='Lay the war at a god’s feet'
        note='Name the god who incited this war, or clear the blame. Held, the war keeps it and its next fronts inherit it.'
      >
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
          <SonSelect
            label='Instigator'
            value={son}
            onChange={setSon}
            allowNone
            disabled={busy !== null}
          />
          <label className='flex min-w-0 items-center gap-2 self-end rounded-lg border bg-background p-2.5'>
            <Switch
              checked={hold}
              onCheckedChange={setHold}
              aria-label='Hold the blame'
            />
            <Text as='span'>Hold the blame</Text>
          </label>
        </div>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => save.mutate(undefined)}
          >
            {son === NO_SON ? <UserX /> : <Save />}
            {son === NO_SON ? 'Clear the blame' : 'Lay the blame'}
          </Button>
        </div>
        {war.event && (
          <HoldToggle
            kind='incited_by_son_id'
            nodeId={war.event.id}
            held={war.incitement_held ?? false}
            blocked={blocked}
            what='who incited the war'
            invalidate={[militaryKeys.room(war.id)]}
          />
        )}
      </Adjust>
    </div>
  )
}
