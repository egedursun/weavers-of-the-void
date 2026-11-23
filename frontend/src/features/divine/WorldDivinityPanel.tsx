import { useState } from 'react'
import {
  Eraser,
  Eye,
  Plus,
  Save,
  SlidersHorizontal,
  TriangleAlert,
} from 'lucide-react'
import { type ActionBody, type EditValues } from '@/api/actions'
import { domainHookValues, domainValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  LoadingBlock,
  Paged,
  Section,
  StatBar,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { busyOf } from '@/features/entity/lore/model'
import {
  Card,
  Group,
  NumberField,
  SwitchField,
} from '@/features/entity/wilds/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { useDivineAction, useWorldDivinity } from './api'
import { PickRow } from './parts'

export function WorldDivinityPanel({ worldId }: { worldId: number }) {
  const view = useWorldDivinity(worldId)
  const { reason } = useGodGate()
  const set = useDivineAction(
    'domain_hook:set',
    (vars: { domain: string; hook: string; pct: number }) => ({
      world_id: worldId,
      domain: vars.domain as ActionBody<'domain_hook:set'>['domain'],
      hook: vars.hook as ActionBody<'domain_hook:set'>['hook'],
      pct: vars.pct,
    })
  )
  const clear = useDivineAction(
    'domain_hook:clear',
    (vars: { domain: string; hook: string }) => ({
      world_id: worldId,
      domain: vars.domain as ActionBody<'domain_hook:clear'>['domain'],
      hook: vars.hook as ActionBody<'domain_hook:clear'>['hook'],
    })
  )
  const attend = useDivineAction(
    'attention:set',
    (vars: { values: EditValues; release: string[] }) => ({
      world_id: worldId,
      ...vars,
    })
  )
  const [domain, setDomain] = useState('')
  const [hook, setHook] = useState('')
  const [pct, setPct] = useState('100')
  const busy = busyOf(
    reason(),
    set.isPending,
    clear.isPending,
    attend.isPending
  )
  const problem =
    domain === '' ? 'Choose a domain' : hook === '' ? 'Choose a hook' : null
  return (
    <Section
      id='section-world-divinity'
      title='The gods in this world'
      description='How strongly each domain hook works here, and how closely the Creator watches. These belong to worlds; the gods carry their domains everywhere else.'
      icon={SlidersHorizontal}
      tone='gold'
    >
      {view.isPending && (
        <LoadingBlock label='Reading the gods’ workings here' />
      )}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='This could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='WorldDivinity'
          className='@container/wild grid min-w-0 grid-cols-1 gap-3 @xl/wild:grid-cols-2'
        >
          <Card
            title='Domain hooks in this world'
            icon={SlidersHorizontal}
            tone='gold'
            hint='100% is the usual strength; 0% silences a hook here'
          >
            {view.data.hooks.length === 0 ? (
              <EmptyState
                icon={SlidersHorizontal}
                title='Every hook works as usual here'
                description='Strengthen or weaken one domain hook in this world.'
              />
            ) : (
              <ul className='flex min-w-0 flex-col gap-2'>
                <Paged items={view.data.hooks} as='li'>
                  {(row) => (
                    <li
                      key={`${row.domain}-${row.hook}`}
                      className='flex min-w-0 items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'
                    >
                      <Badge size='sm' variant='outline'>
                        {wordOf(domainValues, row.domain)}
                      </Badge>
                      <Text as='span' weight='medium'>
                        {row.label}
                      </Text>
                      <Badge
                        size='sm'
                        variant='secondary'
                      >{`${row.pct}%`}</Badge>
                      <Button
                        size='sm'
                        variant='ghost'
                        disabled={busy !== null}
                        disabledReason={busy ?? undefined}
                        onClick={() =>
                          clear.mutate({ domain: row.domain, hook: row.hook })
                        }
                      >
                        <Eraser />
                        As usual
                      </Button>
                    </li>
                  )}
                </Paged>
              </ul>
            )}
            <Group title='Set a hook’s strength' icon={Plus}>
              <div className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-3'>
                <PickRow
                  label='Domain'
                  table={Object.fromEntries(
                    domainValues.map((value) => [
                      value,
                      wordOf(domainValues, value),
                    ])
                  )}
                  value={domain}
                  blocked={busy}
                  onPick={setDomain}
                />
                <PickRow
                  label='Hook'
                  table={Object.fromEntries(
                    domainHookValues.map((value) => [
                      value,
                      wordOf(domainHookValues, value),
                    ])
                  )}
                  value={hook}
                  blocked={busy}
                  onPick={setHook}
                />
                <NumberField
                  label='Strength (%)'
                  value={pct}
                  min={-100}
                  max={300}
                  disabled={busy !== null}
                  onChange={setPct}
                />
              </div>
              <Button
                disabled={busy !== null || problem !== null}
                disabledReason={busy ?? problem ?? undefined}
                onClick={() => set.mutate({ domain, hook, pct: Number(pct) })}
              >
                <Save />
                Set the strength
              </Button>
            </Group>
          </Card>
          <Card
            title='The Creator’s eye'
            icon={Eye}
            tone='verdigris'
            hint='A world far from the eye leaves its sons freer to defy the Creator'
          >
            {view.data.attention ? (
              <>
                <StatBar
                  label='Attention'
                  value={view.data.attention.attention}
                  max={100}
                  icon={Eye}
                  tone={view.data.attention.far ? 'muted' : 'default'}
                />
                {view.data.attention.far && (
                  <Badge variant='warning'>Far from the eye</Badge>
                )}
              </>
            ) : (
              <Muted variant='caption'>
                The Creator has not yet turned its eye here; it will after the
                next epoch.
              </Muted>
            )}
            <SwitchField
              label='Watched by the Creator'
              checked={view.data.attention?.watched ?? false}
              disabled={busy !== null}
              onChange={(watched) =>
                attend.mutate({ values: { watched }, release: [] })
              }
            />
          </Card>
        </div>
      )}
    </Section>
  )
}
