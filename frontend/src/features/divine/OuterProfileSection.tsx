import { useState } from 'react'
import {
  Coins,
  Plus,
  Save,
  Skull,
  Trash2,
  TriangleAlert,
  Zap,
} from 'lucide-react'
import { outerHungerValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  LoadingBlock,
  Medallion,
  Paged,
  Section,
  StatBar,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { busyOf } from '@/features/entity/lore/model'
import {
  AdjustPanel,
  Card,
  Group,
  Held,
  NumberField,
} from '@/features/entity/wilds/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { useDivineAction, useOuterProfile } from './api'
import { GAINS, HUNGERS, PRICES, heldLabel } from './labels'
import { NodeName, PickRow } from './parts'

export function OuterProfileSection({ beingId }: { beingId: number }) {
  const view = useOuterProfile(beingId)
  const [hunger, setHunger] = useState('')
  const [reach, setReach] = useState('')
  const [region, setRegion] = useState<number | null>(null)
  const [strength, setStrength] = useState('30')
  const [breachDraft, setBreachDraft] = useState<Record<number, string>>({})
  const { reason } = useGodGate()
  const edit = useDivineAction<{
    values: Record<string, unknown>
    release: string[]
  }>('outer_profile:edit', (vars) => ({ being_id: beingId, ...vars }))
  const open = useDivineAction<void>('breach:open', () => ({
    being_id: beingId,
    region_id: region,
    strength: Number(strength),
  }))
  const change = useDivineAction<{
    breach: number
    values: Record<string, unknown>
  }>('breach:edit', (vars) => ({
    breach_id: vars.breach,
    values: vars.values,
    release: [],
  }))
  const close = useDivineAction<number>('breach:close', (breach) => ({
    breach_id: breach,
  }))
  const busy = busyOf(
    reason(),
    edit.isPending,
    open.isPending,
    change.isPending,
    close.isPending
  )
  const values: Record<string, unknown> = {}
  if (hunger !== '') values.hunger = hunger
  if (reach !== '') values.reach = Number(reach)
  const nothing =
    Object.keys(values).length === 0 ? 'Change its hunger or reach first' : null
  const hungers = Object.fromEntries(
    outerHungerValues.map((value) => [value, HUNGERS[value].label])
  )
  return (
    <Section
      id='section-outer-profile'
      title='Hunger and breaches'
      description='What the outer being feeds on, how far it reaches, where it touches the cosmos and the bargains made with it. Only outer beings have these.'
      icon={Skull}
      tone='danger'
    >
      {view.isPending && <LoadingBlock label='Reading the outer being' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='It could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='OuterProfile'
          className='@container/wild grid min-w-0 grid-cols-1 gap-3 @xl/wild:grid-cols-2'
        >
          <Card
            title={`Feeds on ${view.data.hunger_label.toLowerCase()}`}
            icon={HUNGERS[view.data.hunger].icon}
            tone='danger'
            hint={`Warding against it costs ${view.data.oppose_cost} essence`}
          >
            <div className='flex min-w-0 flex-wrap gap-2'>
              <Badge variant='destructive'>{`Reaches ${view.data.reach} lands`}</Badge>
              <Badge variant='secondary'>{`Fed ${view.data.fed} times`}</Badge>
            </div>
            <Held
              keys={view.data.locked}
              label={heldLabel}
              busy={busy}
              onRelease={() =>
                edit.mutate({ values: {}, release: view.data?.locked ?? [] })
              }
            />
            <AdjustPanel
              title='Reshape its hunger'
              note='What you set is held until you let the world decide again.'
            >
              <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
                <PickRow
                  label='Hunger'
                  table={hungers}
                  value={hunger}
                  blocked={busy}
                  onPick={setHunger}
                />
                <NumberField
                  label='Reach (lands)'
                  value={reach}
                  min={0}
                  disabled={busy !== null}
                  onChange={setReach}
                />
              </div>
              <Button
                disabled={busy !== null || nothing !== null}
                disabledReason={busy ?? nothing ?? undefined}
                onClick={() => {
                  edit.mutate({ values, release: [] })
                  setHunger('')
                  setReach('')
                }}
              >
                <Save />
                Hold it this way
              </Button>
            </AdjustPanel>
          </Card>
          <Card
            title='Breach points'
            icon={Zap}
            tone='warning'
            hint='Where it touches the cosmos: sanity drains and the world leaks there'
          >
            {view.data.breaches.length === 0 ? (
              <EmptyState
                icon={Zap}
                title='No breach'
                description='It opens breaches as far as it reaches; you can open or seal them.'
              />
            ) : (
              <ul className='flex min-w-0 flex-col gap-2'>
                <Paged items={view.data.breaches} as='li'>
                  {(row) => (
                    <li
                      key={row.id}
                      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'
                    >
                      <div className='flex min-w-0 items-center gap-2'>
                        <Medallion icon={Zap} tone='warning' size='sm' />
                        <div className='flex min-w-0 flex-1 flex-col'>
                          {row.region ? (
                            <NodeName item={row.region} />
                          ) : (
                            <Text weight='medium'>Its whole world</Text>
                          )}
                          <Muted variant='caption'>{`Open since epoch ${row.opened_epoch}`}</Muted>
                        </div>
                        <Button
                          size='sm'
                          variant='ghost'
                          disabled={busy !== null}
                          disabledReason={busy ?? undefined}
                          onClick={() => close.mutate(row.id)}
                        >
                          <Trash2 />
                          Seal
                        </Button>
                      </div>
                      <StatBar
                        label='Strength'
                        value={row.strength}
                        max={100}
                        tone='warning'
                      />
                      <div className='flex min-w-0 items-end gap-2'>
                        <NumberField
                          label='Hold strength at'
                          value={breachDraft[row.id] ?? ''}
                          min={1}
                          max={100}
                          disabled={busy !== null}
                          onChange={(text) =>
                            setBreachDraft((old) => ({
                              ...old,
                              [row.id]: text,
                            }))
                          }
                        />
                        <Button
                          size='sm'
                          disabled={
                            busy !== null || (breachDraft[row.id] ?? '') === ''
                          }
                          disabledReason={
                            busy ??
                            ((breachDraft[row.id] ?? '') === ''
                              ? 'Set a value first'
                              : undefined)
                          }
                          onClick={() =>
                            change.mutate({
                              breach: row.id,
                              values: { strength: Number(breachDraft[row.id]) },
                            })
                          }
                        >
                          <Save />
                          Hold
                        </Button>
                      </div>
                    </li>
                  )}
                </Paged>
              </ul>
            )}
            <Group title='Open a breach' icon={Plus}>
              <EntityPicker
                types={['region']}
                value={region}
                onChange={setRegion}
                placeholder='The land it opens in'
              />
              <NumberField
                label='Strength'
                value={strength}
                min={1}
                max={100}
                disabled={busy !== null}
                onChange={setStrength}
              />
              <Button
                variant='destructive'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => open.mutate()}
              >
                <Zap />
                Open the breach
              </Button>
            </Group>
          </Card>
          <Card title='Bargains made with it' icon={Coins} tone='muted' wide>
            {view.data.bargains.length === 0 ? (
              <EmptyState
                icon={Coins}
                title='No bargain yet'
                description='Sons who bargain with it choose what they take and what they pay.'
              />
            ) : (
              <ul className='flex min-w-0 flex-col gap-2'>
                <Paged items={view.data.bargains} as='li'>
                  {(row) => (
                    <li
                      key={`${row.son.id}-${row.epoch}`}
                      className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-2'
                    >
                      <NodeName item={row.son} />
                      <Badge
                        size='sm'
                        variant='success'
                      >{`Took ${GAINS[row.gain].toLowerCase()}`}</Badge>
                      <Badge
                        size='sm'
                        variant='destructive'
                      >{`Paid ${PRICES[row.price].toLowerCase()}${row.price_domain ? ` (${row.price_domain})` : ''}`}</Badge>
                      {row.price_world && <NodeName item={row.price_world} />}
                      <Muted variant='caption'>{`Epoch ${row.epoch}${row.terms ? ` — ${row.terms}` : ''}`}</Muted>
                    </li>
                  )}
                </Paged>
              </ul>
            )}
          </Card>
        </div>
      )}
    </Section>
  )
}
