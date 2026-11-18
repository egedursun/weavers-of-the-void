import { useState } from 'react'
import {
  Ban,
  CalendarDays,
  Coins,
  HeartPulse,
  History,
  Plus,
  RotateCcw,
  Shapes,
  Sparkles,
  Trash2,
  TriangleAlert,
  Unlock,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { commodityKindValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { KpiTile, Paged, FieldTile } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { CustomKindChoice, HeldBadge, OptionalChoice } from '../CultureParts'
import {
  AdjustBlock,
  ChoicePicker,
  DictField,
  LoreAdjust,
  LoreCard,
  LoreFields,
  LoreHero,
  MeterList,
  MeterRow,
  NamedChip,
  RefChip,
  RowEditor,
  RowEditors,
  TermChips,
} from '../LoreFields'
import {
  ACTS,
  type TraditionEffect,
  TRADITION_EFFECTS,
  effectLabel,
  signed,
} from '../cultureLabels'
import { KindForge } from '../forge/KindForge'
import { CALENDAR_SLOTS } from '../forge/forgeModel'
import {
  CLASSES,
  KPI_GRID,
  LORE_GRID,
  PERCENT,
  RITE_STAGES,
  TRADITION_KINDS,
  TRADITION_TERMS,
  VALUES,
  busyOf,
  lookup,
  sentence,
} from '../model'
import { type Card, COST_ONLY, average } from './shared'

const COMMODITIES = Object.fromEntries(
  commodityKindValues.map((key) => [
    key,
    { label: sentence(key), icon: Ban, tone: 'danger' as const },
  ])
)
const ANYONE = ''

function targetsFor(effect: string) {
  if (effect === 'value') return VALUES
  if (effect === 'satisfaction')
    return {
      [ANYONE]: { label: 'Everyone', icon: Users, tone: 'success' as const },
      ...CLASSES,
    }
  return null
}

function EffectEditor({
  id,
  effects,
  blocked,
}: {
  id: number
  effects: readonly TraditionEffect[]
  blocked: string | null
}) {
  const [effect, setEffect] = useState('cohesion')
  const [target, setTarget] = useState('')
  const [magnitude, setMagnitude] = useState('2')
  const set = useGodAction<{
    effect: string
    target: string
    magnitude: number
  }>({
    run: (body) =>
      unwrap(
        api.POST('/api/actions/tradition:effect', {
          body: {
            tradition_id: id,
            effect: body.effect as TraditionEffect['effect'],
            target: body.target,
            magnitude: body.magnitude,
          },
        })
      ),
  })
  const reseed = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/tradition:reseed', {
          body: { tradition_id: id },
        })
      ),
  })
  const busy = busyOf(blocked, set.isPending, reseed.isPending)
  const targets = targetsFor(effect)
  const amount = Math.round(Number(magnitude))
  const problem =
    Number.isNaN(amount) || amount === 0 ? 'Give a strength' : null
  return (
    <div
      data-surface='TraditionEffects'
      className='flex min-w-0 flex-col gap-3'
    >
      {effects.length > 0 && (
        <RowEditors>
          {effects.map((row) => (
            <RowEditor
              key={`${row.effect}.${row.target}`}
              label={effectLabel(row)}
              icon={lookup(TRADITION_EFFECTS, row.effect).icon}
              value={row.magnitude}
              min={-PERCENT}
              max={PERCENT}
              blocked={busy}
              onSave={(value) =>
                set.mutate({
                  effect: row.effect,
                  target: row.target,
                  magnitude: value,
                })
              }
            >
              <Button
                size='icon'
                variant='ghost'
                aria-label={`Remove ${effectLabel(row)}`}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() =>
                  set.mutate({
                    effect: row.effect,
                    target: row.target,
                    magnitude: 0,
                  })
                }
              >
                <Trash2 />
              </Button>
            </RowEditor>
          ))}
        </RowEditors>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-4'>
        <ChoicePicker
          label='It brings'
          value={effect}
          table={TRADITION_EFFECTS}
          blocked={busy}
          onPick={(next) => {
            setEffect(next)
            setTarget(next === 'value' ? 'tradition' : '')
          }}
        />
        {targets && (
          <ChoicePicker
            label={effect === 'value' ? 'Which value' : 'To whom'}
            value={target}
            table={targets}
            blocked={busy}
            onPick={setTarget}
          />
        )}
        <FieldTile label='Strength'>
          <Input
            type='number'
            min={-PERCENT}
            max={PERCENT}
            value={magnitude}
            aria-label='Strength of the effect'
            onChange={(event) => setMagnitude(event.target.value)}
          />
        </FieldTile>
        <div className='flex min-w-0 items-end gap-2'>
          <Button
            size='sm'
            disabled={busy !== null || problem !== null}
            disabledReason={busy ?? problem ?? undefined}
            onClick={() => set.mutate({ effect, target, magnitude: amount })}
          >
            <Plus />
            Add
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => reseed.mutate(undefined)}
          >
            <RotateCcw />
            From its kind
          </Button>
        </div>
      </div>
    </div>
  )
}

export function TraditionPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'tradition'>
  blocked: string | null
}) {
  const keep = useGodAction<{ community: number; value: number }>({
    run: ({ community, value }) =>
      unwrap(
        api.POST('/api/actions/tradition:participation', {
          body: {
            tradition_id: id,
            community_id: community,
            participation: value,
          },
        })
      ),
  })
  const release = useGodAction<{ community: number }>({
    run: ({ community }) =>
      unwrap(
        api.POST('/api/actions/tradition:release_participation', {
          body: { tradition_id: id, community_id: community },
        })
      ),
  })
  const busy = busyOf(blocked, keep.isPending, release.isPending)
  const kind = lookup(TRADITION_KINDS, card.kind)
  const skipped = card.keepers.reduce((sum, row) => sum + row.skipped, 0)
  const kept = card.keepers
    .map((row) => row.last_celebrated_epoch)
    .filter((epoch): epoch is number => epoch !== null)
  return (
    <div data-surface='TraditionCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero spec={kind} kicker='A custom kept'>
        {card.stage && (
          <NamedChip spec={lookup(RITE_STAGES, card.stage)}>
            {`Marks ${lookup(RITE_STAGES, card.stage).label.toLowerCase()}`}
          </NamedChip>
        )}
        {card.calendar_slot && (
          <NamedChip spec={lookup(CALENDAR_SLOTS, card.calendar_slot)}>
            {lookup(CALENDAR_SLOTS, card.calendar_slot).label}
          </NamedChip>
        )}
        {card.in_season === true && (
          <NamedChip spec={{ label: '', icon: CalendarDays, tone: 'success' }}>
            Kept in its season
          </NamedChip>
        )}
        {card.in_season === false && (
          <NamedChip spec={{ label: '', icon: CalendarDays, tone: 'warning' }}>
            Drifted off its season
          </NamedChip>
        )}
        {card.calendar_entity_id != null && (
          <NamedChip
            spec={{ label: '', icon: CalendarDays, tone: 'verdigris' }}
          >
            Date fixed by a calendar
          </NamedChip>
        )}
        {card.taboo_target && (
          <NamedChip spec={TRADITION_KINDS.taboo}>
            {`Will not touch ${card.taboo_target.replaceAll('_', ' ')}`}
          </NamedChip>
        )}
        {card.taboo_act && (
          <NamedChip spec={lookup(ACTS, card.taboo_act)}>
            {`Forbids ${lookup(ACTS, card.taboo_act).label.toLowerCase()}`}
          </NamedChip>
        )}
        {card.custom_kind_id && (
          <NamedChip spec={{ label: '', icon: Shapes, tone: 'gold' }}>
            A kind of your own
          </NamedChip>
        )}
        <RefChip icon={History} label='Remembers' item={card.origin} />
        {card.origin_incident && (
          <NamedChip spec={{ label: '', icon: History, tone: 'muted' }}>
            {`Born of an incident in epoch ${card.origin_incident.epoch}`}
          </NamedChip>
        )}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Kept by'
          value={card.keepers.length}
          icon={Users}
          tone='info'
          hint='Communities that keep it'
        />
        <KpiTile
          label='Devotion'
          value={`${average(card.keepers.map((row) => row.participation))}%`}
          icon={HeartPulse}
          tone='success'
          hint='How many of its keepers take part, on average'
          meter={{
            value: average(card.keepers.map((row) => row.participation)),
            max: PERCENT,
            label: 'Devotion',
          }}
        />
        <KpiTile
          label='Skipped'
          value={skipped}
          icon={TriangleAlert}
          tone={skipped > 0 ? 'warning' : 'muted'}
          hint='Times it was skipped in hunger; each costs cohesion'
        />
        <KpiTile
          label='Last kept'
          value={kept.length > 0 ? `Epoch ${Math.max(...kept)}` : 'Never'}
          icon={CalendarDays}
          tone='verdigris'
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='What it costs' icon={Coins} tone='warning'>
          <TermChips
            entries={card.cost}
            table={TRADITION_TERMS}
            empty='It costs nothing to keep.'
          />
        </LoreCard>
        <LoreCard title='What it brings' icon={Sparkles} tone='success'>
          {card.effects.length === 0 ? (
            <Muted>It brings nothing but habit.</Muted>
          ) : (
            <div className='flex min-w-0 flex-wrap gap-2'>
              <Paged items={card.effects}>
                {(row) => (
                  <NamedChip
                    key={`${row.effect}.${row.target}`}
                    spec={lookup(TRADITION_EFFECTS, row.effect)}
                  >
                    {`${effectLabel(row)} ${signed(row.magnitude)}`}
                  </NamedChip>
                )}
              </Paged>
            </div>
          )}
        </LoreCard>
        <LoreCard
          title='Kept by'
          icon={Users}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.keepers.length}</Badge>}
        >
          {card.keepers.length === 0 ? (
            <Muted>No one keeps it any more.</Muted>
          ) : (
            <MeterList surface='TraditionKeepers'>
              <Paged items={card.keepers}>
                {(row) => (
                  <MeterRow
                    key={row.community?.id}
                    item={row.community}
                    label={
                      row.last_celebrated_epoch !== null
                        ? `Takes part · last kept in epoch ${row.last_celebrated_epoch}`
                        : 'Takes part'
                    }
                    value={row.participation}
                    icon={kind.icon}
                    tone={kind.tone}
                  >
                    <HeldBadge held={row.held} />
                    {row.skipped > 0 && (
                      <Badge size='sm' variant='warning'>
                        {`Skipped ${row.skipped}×`}
                      </Badge>
                    )}
                  </MeterRow>
                )}
              </Paged>
            </MeterList>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='tradition'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The custom' icon={kind.icon}>
          <LoreFields
            entityId={id}
            surface='TraditionForm'
            fields={[
              { key: 'kind', kind: 'enum', table: TRADITION_KINDS },
              { key: 'stage', kind: 'enum', table: RITE_STAGES },
              {
                key: 'season_position',
                kind: 'number',
                min: 0,
                nullable: true,
              },
              {
                key: 'calendar_entity_id',
                kind: 'number',
                min: 1,
                nullable: true,
              },
            ]}
            current={card}
            blocked={blocked}
          />
          <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
            <OptionalChoice
              entityId={id}
              field='calendar_slot'
              label='When it is kept'
              value={card.calendar_slot}
              table={CALENDAR_SLOTS}
              noneLabel='Whenever it falls'
              blocked={blocked}
            />
            <CustomKindChoice
              entityId={id}
              field='custom_kind_id'
              catalog='tradition_kind'
              value={card.custom_kind_id}
              blocked={blocked}
            />
          </div>
        </AdjustBlock>
        <AdjustBlock title='What it forbids' icon={Ban}>
          <Text as='p'>
            A taboo can forbid a good from the market and a deed from the
            people. Its keepers refrain; those who break it are held in infamy.
          </Text>
          <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
            <OptionalChoice
              entityId={id}
              field='taboo_target'
              label='A good never touched'
              value={card.taboo_target}
              table={COMMODITIES}
              noneLabel='No good'
              blocked={blocked}
            />
            <OptionalChoice
              entityId={id}
              field='taboo_act'
              label='A deed never done'
              value={card.taboo_act}
              table={ACTS}
              noneLabel='No deed'
              blocked={blocked}
            />
          </div>
        </AdjustBlock>
        <div className={LORE_GRID}>
          <AdjustBlock title='What it costs' icon={Coins}>
            <DictField
              entityId={id}
              spec={{ key: 'cost', label: 'The cost', value: card.cost }}
              blocked={blocked}
              table={COST_ONLY}
            />
          </AdjustBlock>
          <AdjustBlock title='What it brings' icon={Sparkles}>
            <EffectEditor id={id} effects={card.effects} blocked={blocked} />
          </AdjustBlock>
        </div>
        {card.keepers.length > 0 && (
          <AdjustBlock title='How many take part' icon={Users}>
            <RowEditors>
              <Paged items={card.keepers}>
                {(row) => (
                  <RowEditor
                    key={row.community?.id}
                    label={row.community?.name ?? 'Unknown'}
                    icon={Users}
                    value={row.participation}
                    max={PERCENT}
                    blocked={busy}
                    onSave={(value) =>
                      keep.mutate({ community: row.community?.id ?? 0, value })
                    }
                  >
                    {row.held && (
                      <Button
                        size='icon'
                        variant='ghost'
                        aria-label={`Let ${row.community?.name ?? 'them'} decide again`}
                        disabled={busy !== null}
                        disabledReason={busy ?? undefined}
                        onClick={() =>
                          release.mutate({ community: row.community?.id ?? 0 })
                        }
                      >
                        <Unlock />
                      </Button>
                    )}
                  </RowEditor>
                )}
              </Paged>
            </RowEditors>
          </AdjustBlock>
        )}
        <AdjustBlock title='Kinds of custom of your own' icon={Shapes}>
          <KindForge catalog='tradition_kind' />
        </AdjustBlock>
      </LoreAdjust>
    </div>
  )
}
