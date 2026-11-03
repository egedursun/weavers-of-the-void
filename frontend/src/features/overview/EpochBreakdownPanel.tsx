import { useState } from 'react'
import {
  GitCompareArrows,
  type LucideIcon,
  Skull,
  Sparkle,
  Sparkles,
  Users,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { type Rarity } from '@/constants/rarity'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ChangeChip,
  EmptyState,
  EntityLink,
  type KpiTone,
  Medallion,
  Portrait,
  Section,
} from '@/components/domain'
import { Label, Muted, SectionTitle, Stat, Text } from '@/components/typography'
import { mediaUrl } from '@/features/pantheon/media'
import { type LedgerItem, type WorldState, useEpochBreakdown } from './api'
import {
  HARMFUL_STATS,
  type NumericStat,
  SON_STAT_ICON,
  SON_STAT_LABEL,
  STAT_FIELDS,
  STAT_ICON,
  STAT_LABEL,
  STAT_TONE,
  humanize,
} from './statFields'

const ITEMS_SHOWN = 10
const PERCENT = 100

function signed(value: number): string {
  if (value > 0) return `+${formatInteger(value)}`
  if (value < 0) return `−${formatInteger(Math.abs(value))}`
  return '±0'
}

function toneOf(value: number, harmful: boolean) {
  if (value === 0) return 'muted' as const
  return value > 0 === harmful ? ('destructive' as const) : ('success' as const)
}

type MeasureProps = {
  field: NumericStat
  after: number | null
  before: number | null
  delta: number | null
}

function Measure({ field, after, before, delta }: MeasureProps) {
  return (
    <div
      data-measure={field}
      className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'
    >
      <Medallion icon={STAT_ICON[field]} tone={STAT_TONE[field]} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col'>
        <Label truncate>{STAT_LABEL[field]}</Label>
        <div className='flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1'>
          {after === null ? (
            <Muted variant='caption'>Not counted in this epoch yet</Muted>
          ) : (
            <Stat value={after} />
          )}
          {delta !== null && (
            <ChangeChip value={delta} harmful={HARMFUL_STATS.has(field)} />
          )}
        </div>
        {before !== null && (
          <Muted
            variant='caption'
            truncate
          >{`from ${formatInteger(before)}`}</Muted>
        )}
      </div>
    </div>
  )
}

type ItemListProps = {
  title: string
  icon: LucideIcon
  tone: KpiTone
  items: LedgerItem[]
  harmful: boolean
}

function ItemList({ title, icon, tone, items, harmful }: ItemListProps) {
  const top = [...items]
    .sort((left, right) => Math.abs(right.delta) - Math.abs(left.delta))
    .slice(0, ITEMS_SHOWN)
  if (top.length === 0) return null
  const net = items.reduce((sum, item) => sum + item.delta, 0)
  const largest = Math.max(...top.map((item) => Math.abs(item.delta)), 1)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-lg border bg-background p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={icon} tone={tone} size='sm' />
        <Label variant='overline' truncate className='flex-1'>
          {title}
        </Label>
        <ChangeChip value={net} harmful={harmful} />
      </div>
      <ul className='flex min-w-0 flex-col gap-2'>
        {top.map((item) => (
          <li key={item.item} className='flex min-w-0 flex-col gap-1'>
            <div className='flex min-w-0 items-baseline justify-between gap-3'>
              <Text as='span' truncate className='min-w-0 flex-1'>
                {humanize(item.item)}
              </Text>
              <Stat
                value={signed(item.delta)}
                tone={toneOf(item.delta, harmful)}
                className='shrink-0'
              />
            </div>
            <Progress
              size='sm'
              tone={
                toneOf(item.delta, harmful) === 'destructive'
                  ? 'destructive'
                  : 'success'
              }
              value={(Math.abs(item.delta) / largest) * PERCENT}
              aria-label={`${humanize(item.item)} ${signed(item.delta)}`}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}

type SonCardProps = {
  name: string
  rarity: Rarity | null
  cover: string | null
  sonId: number
  changes: Record<string, number>
}

function SonCard({ name, rarity, cover, sonId, changes }: SonCardProps) {
  return (
    <li className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
      <Portrait
        name={name}
        src={mediaUrl(cover)}
        size='sm'
        rarity={rarity ?? undefined}
      />
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <EntityLink kind='son' id={String(sonId)} rarity={rarity ?? undefined}>
          {name}
        </EntityLink>
        <div className='flex min-w-0 flex-wrap items-center gap-1'>
          {Object.entries(changes).map(([key, value]) => (
            <ChangeChip
              key={key}
              value={value}
              icon={SON_STAT_ICON[key] ?? Sparkle}
              label={SON_STAT_LABEL[key] ?? humanize(key)}
            />
          ))}
        </div>
      </div>
    </li>
  )
}

type EpochBreakdownPanelProps = {
  state: WorldState
}

export function EpochBreakdownPanel({ state }: EpochBreakdownPanelProps) {
  const latest = state.last_epoch?.epoch ?? null
  const [chosen, setChosen] = useState<number | null>(null)
  const epoch = chosen ?? latest
  const breakdown = useEpochBreakdown(epoch)
  const views = new Map(state.sons.map((item) => [item.son.id, item]))
  const epochs = latest
    ? Array.from({ length: latest }, (_, index) => latest - index)
    : []
  const current = breakdown.data?.current ?? null
  const previous = breakdown.data?.previous ?? null
  const deltas = breakdown.data?.deltas ?? {}
  const changeOf = (field: NumericStat): number | null => {
    const after = current?.[field] ?? null
    const before = previous ? (previous[field] ?? null) : 0
    if (deltas[field] !== undefined) return deltas[field]
    return after === null || before === null ? null : after - before
  }

  return (
    <Section
      title='Epoch breakdown'
      description='What one epoch changed, compared with the epoch before it.'
      surface='card'
      actions={
        epochs.length > 0 && epoch !== null ? (
          <Select
            value={String(epoch)}
            onValueChange={(value) => setChosen(Number(value))}
          >
            <SelectTrigger size='sm' aria-label='Epoch' className='w-40'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {epochs.map((item) => (
                <SelectItem key={item} value={String(item)}>
                  {`Epoch ${item}`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : null
      }
    >
      {epoch === null && (
        <EmptyState
          size='compact'
          icon={GitCompareArrows}
          title='No epoch has closed yet'
          description='Complete the first epoch to see what it changed.'
        />
      )}
      {epoch !== null && breakdown.isPending && (
        <Skeleton className='h-48 w-full' />
      )}
      {epoch !== null && breakdown.isError && (
        <Text tone='destructive'>{breakdown.error.message}</Text>
      )}
      {current && (
        <div className='flex min-w-0 flex-col gap-6'>
          <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4'>
            {STAT_FIELDS.map((field) => (
              <Measure
                key={field}
                field={field}
                after={current[field] ?? null}
                before={previous?.[field] ?? null}
                delta={changeOf(field)}
              />
            ))}
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-3 empty:hidden lg:grid-cols-3'>
            <ItemList
              title='Doom clock'
              icon={Skull}
              tone='danger'
              items={current.doom_items}
              harmful
            />
            <ItemList
              title='Divine essence'
              icon={Sparkles}
              tone='gold'
              items={current.essence_items}
              harmful={false}
            />
            <ItemList
              title='Population'
              icon={Users}
              tone='verdigris'
              items={current.population_items}
              harmful={false}
            />
          </div>
          {(breakdown.data?.sons ?? []).length > 0 && (
            <div className='flex min-w-0 flex-col gap-3'>
              <SectionTitle level={4}>Sons</SectionTitle>
              <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3'>
                {(breakdown.data?.sons ?? []).map((item) => {
                  const view = views.get(item.son_id)
                  return (
                    <SonCard
                      key={item.son_id}
                      sonId={item.son_id}
                      name={view?.son.name ?? `Son #${item.son_id}`}
                      rarity={view?.son.rarity ?? null}
                      cover={view?.cover ?? null}
                      changes={item.changes}
                    />
                  )
                })}
              </ul>
            </div>
          )}
        </div>
      )}
    </Section>
  )
}
