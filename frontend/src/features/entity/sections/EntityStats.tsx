import { useState } from 'react'
import { BrainCircuit, Check, SlidersHorizontal } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { KeyValueList, Section, StatBar } from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { type EntityContext, isThinking } from '../actions/context'
import { humanize } from '../actions/schema'
import { useLoreMutation } from '../api/mutations'
import { useCatalogue, useWorldState } from '../api/queries'
import { RULE, useRuleLookup } from '../api/rules'
import { COUNT_STATS, HIDDEN_STAT_KEYS, PERCENT_MAX } from '../constants'
import { EngineInsight } from './EngineInsight'

type EntityStatsProps = {
  ctx: EntityContext
  readOnlyReason: string | null
}

function statEntries(
  ctx: EntityContext,
  keys: string[]
): [string, number | null][] {
  const stats = ctx.entity.stats as unknown as Record<string, unknown>
  const known = keys.length
    ? keys
    : Object.keys(stats).filter((key) => !HIDDEN_STAT_KEYS.has(key))
  return known.map((key) => {
    const value = stats[key]
    return [key, typeof value === 'number' ? value : null]
  })
}

function StatEditor({
  ctx,
  stat,
  value,
  readOnlyReason,
}: {
  ctx: EntityContext
  stat: string
  value: number | null
  readOnlyReason: string | null
}) {
  const [draft, setDraft] = useState(value === null ? '' : String(value))
  const percent = !COUNT_STATS.has(stat)
  const mutation = useLoreMutation({
    run: (next: number) =>
      unwrap(
        api.PUT('/api/entities/{entity_id}/stat', {
          params: { path: { entity_id: ctx.entity.id } },
          body: { stat, value: next },
        })
      ),
    success: `${humanize(stat)} set`,
  })
  const parsed = draft.trim() === '' ? null : Number(draft)
  const reason =
    readOnlyReason ??
    (parsed === null || !Number.isFinite(parsed) ? 'Write a number.' : null) ??
    (parsed === value ? 'This is the present value.' : null) ??
    (mutation.isPending ? 'Working on it.' : null)
  return (
    <form
      className='flex min-w-0 items-end gap-2'
      onSubmit={(event) => {
        event.preventDefault()
        if (parsed !== null) mutation.mutate(parsed)
      }}
    >
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Label as='label' htmlFor={`stat-${stat}`} truncate>
          {percent ? `${humanize(stat)} (0–${PERCENT_MAX})` : humanize(stat)}
        </Label>
        <Input
          id={`stat-${stat}`}
          type='number'
          inputMode='numeric'
          min={percent ? 0 : undefined}
          max={percent ? PERCENT_MAX : undefined}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
      </div>
      <Button
        type='submit'
        variant='outline'
        size='icon'
        aria-label={`Set ${humanize(stat)}`}
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
      >
        <Check />
      </Button>
    </form>
  )
}

export function EntityStats({ ctx, readOnlyReason }: EntityStatsProps) {
  const catalogue = useCatalogue()
  const state = useWorldState()
  const rule = useRuleLookup()
  const typeInfo = catalogue.data?.entity_types.find(
    (item) => item.key === ctx.type
  )
  const entries = statEntries(ctx, typeInfo?.stats ?? [])
  const insight = ctx.detail.insight
  const life = insight.life
  const capacity = insight.capacity
  const exploration = insight.exploration
  const sanity = ctx.entity.sanity
  const clouding = rule(RULE.sanityClouding)
  const madness = rule(RULE.sanityMadness)
  const epoch = state.data?.world?.epoch ?? ctx.entity.birth_epoch
  const editable = [...entries.map(([key, value]) => ({ key, value }))]
  if (isThinking(ctx.type) && !entries.some(([key]) => key === 'sanity'))
    editable.push({ key: 'sanity', value: sanity })
  const thinking = isThinking(ctx.type)
  const engine =
    insight.knowledge ?? insight.resource ?? insight.faith ?? insight.reward
  if (entries.length === 0 && !life && !capacity && !thinking && !engine)
    return null
  return (
    <Section id='section-stats' title='Stats'>
      {thinking && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Badge variant='outline'>
            {ctx.entity.last_acted_epoch > 0
              ? `Last turn: epoch ${formatInteger(ctx.entity.last_acted_epoch)}`
              : 'Has not acted yet'}
          </Badge>
          {ctx.flags.has('agent_selected') && (
            <Badge variant='success'>{`Acts this epoch (${formatInteger(epoch)})`}</Badge>
          )}
          {ctx.entity.civ_tier !== null && (
            <Badge variant='outline'>{`Civilization tier ${formatInteger(ctx.entity.civ_tier)}`}</Badge>
          )}
        </div>
      )}
      {entries.length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2'>
          {entries.map(([key, value]) =>
            value === null ? (
              <div
                key={key}
                className='flex min-w-0 items-center justify-between gap-2'
              >
                <Label truncate>{humanize(key)}</Label>
                <Muted variant='caption'>Unknown</Muted>
              </div>
            ) : COUNT_STATS.has(key) || value > PERCENT_MAX ? (
              <div
                key={key}
                className='flex min-w-0 items-center justify-between gap-2'
              >
                <Label truncate>{humanize(key)}</Label>
                <Stat value={value} />
              </div>
            ) : (
              <StatBar
                key={key}
                label={humanize(key)}
                value={value}
                max={PERCENT_MAX}
              />
            )
          )}
        </div>
      )}
      {sanity !== null && (
        <div className='flex min-w-0 flex-col gap-1.5'>
          <div className='flex min-w-0 items-center gap-2'>
            <BrainCircuit
              aria-hidden='true'
              className='size-icon-sm text-muted-foreground'
            />
            <Label truncate className='flex-1'>
              Sanity
            </Label>
            <Stat value={sanity} unit={`/ ${PERCENT_MAX}`} />
          </div>
          <Progress
            value={sanity}
            size='sm'
            tone={
              madness !== undefined && sanity <= madness
                ? 'destructive'
                : clouding !== undefined && sanity <= clouding
                  ? 'warning'
                  : 'default'
            }
            aria-label='Sanity'
          />
          {clouding !== undefined && sanity <= clouding && (
            <Text variant='caption' tone='destructive'>
              The mind is cracking: open to outer cults and madness.
            </Text>
          )}
        </div>
      )}
      <EngineInsight ctx={ctx} />
      {life && (
        <KeyValueList
          items={[
            {
              label: 'Life',
              value: life.immortal
                ? `${plural(life.age ?? 0, 'year', 'years')} old · deathless`
                : life.death_year !== null
                  ? `Died at ${formatInteger(life.age ?? 0)} (world year ${formatInteger(life.death_year)})`
                  : `${plural(life.age ?? 0, 'year', 'years')} old · ${plural(Math.max(0, life.lifespan - (life.age ?? 0)), 'year', 'years')} left`,
            },
            {
              label: 'Lifespan',
              value: `${formatInteger(life.lifespan_base)} base + ${formatInteger(life.medicine_bonus)} medicine + ${formatInteger(life.notable_bonus)} renown = ${formatInteger(life.lifespan)}`,
            },
            ...(life.death_year === null && !life.immortal
              ? [
                  {
                    label: 'Death',
                    value: `A son pays ${formatInteger(life.son_kill_cost)} essence for a ${formatInteger(life.kill_chance_pct)}% chance; you pay ${formatInteger(life.creator_kill_cost)}.`,
                  },
                ]
              : []),
          ]}
        />
      )}
      {capacity && (
        <div className='flex min-w-0 flex-col gap-1.5'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Label className='flex-1'>
              {capacity.region
                ? `Carrying capacity of ${capacity.region.name}`
                : 'Carrying capacity'}
            </Label>
            <Stat
              value={capacity.region_population}
              unit={`/ ${formatInteger(capacity.capacity)}`}
            />
          </div>
          <Progress
            value={Math.min(PERCENT_MAX, capacity.occupancy_pct)}
            size='sm'
            tone={
              capacity.occupancy_pct >= PERCENT_MAX ? 'destructive' : 'default'
            }
            aria-label='Carrying capacity'
          />
          <Muted variant='caption'>
            {capacity.occupancy_pct >= PERCENT_MAX
              ? `Full ${formatInteger(capacity.occupancy_pct)}%: growth stops, famine and migration pressure rise.`
              : `Full ${formatInteger(capacity.occupancy_pct)}%`}
          </Muted>
        </div>
      )}
      {exploration && (
        <Muted variant='caption'>
          {`Spontaneous exploration pressure ${formatInteger(exploration.pressure)} · the land holds ${plural(exploration.regions, 'region', 'regions')}, ${plural(exploration.places, 'place', 'places')} and ${plural(exploration.communities, 'community', 'communities')}${exploration.narrow ? '; it feels narrow' : ''}.`}
        </Muted>
      )}
      {editable.length > 0 && (
        <Collapsible className='flex min-w-0 flex-col gap-3'>
          <CollapsibleTrigger asChild>
            <Button variant='outline' className='self-start'>
              <SlidersHorizontal />
              Adjust stats
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
            {editable.map((item) => (
              <StatEditor
                key={`${item.key}-${item.value ?? ''}`}
                ctx={ctx}
                stat={item.key}
                value={item.value}
                readOnlyReason={readOnlyReason}
              />
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}
    </Section>
  )
}
