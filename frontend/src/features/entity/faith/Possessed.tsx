import { useState } from 'react'
import { Brain, Ghost, Lock, Save, ShieldOff, Unlock } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import {
  LoadingBlock,
  Medallion,
  RangeField,
  Section,
  StatBar,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { goodBand } from '../realm/labels'
import { AdjustPanel, RecordField, RefLink, Tag } from '../realm/parts'
import { usePossession } from './api'
import { STRESS_WORDS, busyOf, clampPercent, PERCENT } from './possessionParts'

export function PossessedSection({
  hostId,
  readOnlyReason,
}: {
  hostId: number
  readOnlyReason?: string | null
}) {
  const query = usePossession(hostId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const held = query.data ?? null
  const [spirit, setSpirit] = useState<number | null>(null)
  const [stress, setStress] = useState(held?.stress ?? 0)
  const possess = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:possess', {
          body: { spirit_id: spirit ?? 0, host_id: hostId },
        })
      ),
  })
  const edit = useGodAction<boolean>({
    run: (hold) =>
      unwrap(
        api.POST('/api/actions/soul:possession', {
          body: hold
            ? {
                host_id: hostId,
                values: { stress: clampPercent(stress) },
                release: [],
              }
            : { host_id: hostId, values: {}, release: held?.locked ?? [] },
        })
      ),
  })
  const exorcise = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:exorcise', { body: { host_id: hostId } })
      ),
  })
  const busy = busyOf(
    blocked,
    possess.isPending,
    edit.isPending,
    exorcise.isPending
  )
  return (
    <Section
      id='section-possessed'
      title='Possession'
      description='A spirit that lays its imprint over this body, or the means to set one upon it.'
      icon={Ghost}
      tone={held ? 'danger' : 'muted'}
    >
      {query.isPending ? (
        <LoadingBlock label='Reading the body' />
      ) : held ? (
        <div className='flex min-w-0 flex-col gap-3'>
          <div className='flex min-w-0 items-center gap-2'>
            <Medallion icon={Ghost} tone='danger' size='sm' />
            <div className='flex min-w-0 flex-1 flex-col'>
              <Label>Possessed by</Label>
              {held.spirit ? (
                <RefLink node={held.spirit} />
              ) : (
                <Muted>A spirit now lost</Muted>
              )}
            </div>
            <Muted
              as='span'
              variant='caption'
            >{`since ${held.since_epoch}`}</Muted>
            {held.locked.length > 0 && (
              <Tag spec={{ label: 'Held', icon: Lock, tone: 'info' }} />
            )}
          </div>
          <StatBar
            label={`Stress it lays on this body: ${goodBand(held.stress, STRESS_WORDS).label}`}
            value={held.stress}
            max={PERCENT}
            icon={Brain}
            tone='destructive'
          />
          <AdjustPanel
            trigger='Adjust the possession'
            title='The grip on this body'
            note='Set the stress the spirit lays on it, or drive the spirit out at once.'
          >
            <RangeField
              label='Stress on this body'
              icon={Brain}
              level={goodBand(stress, STRESS_WORDS).label}
              value={stress}
              min={0}
              max={PERCENT}
              lowLabel='Uneasy'
              highLabel='Breaking'
              onChange={setStress}
            />
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Button
                size='sm'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => edit.mutate(true)}
              >
                <Save />
                Set and hold
              </Button>
              {held.locked.length > 0 && (
                <Button
                  size='sm'
                  variant='outline'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => edit.mutate(false)}
                >
                  <Unlock />
                  Let it grow
                </Button>
              )}
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => exorcise.mutate(undefined)}
              >
                <ShieldOff />
                Drive it out
              </Button>
            </div>
          </AdjustPanel>
        </div>
      ) : (
        <AdjustPanel
          trigger='Set a spirit upon it'
          title='Possess this body'
          note='The spirit lays its imprint over this body’s values until it is driven out.'
        >
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <div className='min-w-48 flex-1'>
              <RecordField
                label='Spirit'
                types={['spirit']}
                value={spirit}
                onChange={setSpirit}
                blocked={busy}
              />
            </div>
            <Button
              size='sm'
              disabled={busy !== null || spirit === null}
              disabledReason={
                busy ?? (spirit === null ? 'Choose a spirit first' : undefined)
              }
              onClick={() => possess.mutate(undefined)}
            >
              <Ghost />
              Possess
            </Button>
          </div>
        </AdjustPanel>
      )}
    </Section>
  )
}
