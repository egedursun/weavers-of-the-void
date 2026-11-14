import { type ReactNode, useEffect } from 'react'
import {
  Check,
  CloudFog,
  Crown,
  HandHeart,
  Heart,
  type LucideIcon,
  Network,
  Orbit,
  Skull,
  Sparkles,
  Star,
  TrendingUp,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Progress, type ProgressTone } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Toggle } from '@/components/ui/toggle'
import {
  EntityLink,
  PagedList,
  Portrait,
  RarityBadge,
  Section,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { type SonPublic, useSonRelations, useSons } from './api'
import { useCompareSelection } from './compareStore'
import { COMPARE_MAX, COMPARE_MIN, STAT_SCALE } from './constants'
import { SON_PASSIONS, STATS } from './labels'
import { mediaUrl } from './media'
import { signed } from './relations'
import { reputationOf, starText, statValue } from './sonFacts'

const PERCENT = 100

type NumericRow = {
  label: string
  icon?: LucideIcon
  value: (view: SonPublic) => number
  max: (view: SonPublic) => number
  tone?: ProgressTone | ((view: SonPublic) => ProgressTone)
  bar?: boolean
  highlight?: boolean
}

function GroupRow({ label, span }: { label: string; span: number }) {
  return (
    <TableRow>
      <TableCell colSpan={span}>
        <Label variant='overline'>{label}</Label>
      </TableCell>
    </TableRow>
  )
}

function Row({
  label,
  icon: Icon,
  cells,
}: {
  label: string
  icon?: LucideIcon
  cells: ReactNode[]
}) {
  return (
    <TableRow>
      <TableHead scope='row' className='whitespace-normal'>
        <span className='flex min-w-0 items-center gap-2'>
          {Icon && (
            <Icon
              aria-hidden='true'
              className='size-icon-sm shrink-0 text-muted-foreground'
            />
          )}
          <Label>{label}</Label>
        </span>
      </TableHead>
      {cells.map((cell, index) => (
        <TableCell key={index} className='whitespace-normal'>
          {cell}
        </TableCell>
      ))}
    </TableRow>
  )
}

function NumberRow({ row, sons }: { row: NumericRow; sons: SonPublic[] }) {
  const values = sons.map(row.value)
  const best = Math.max(...values)
  return (
    <Row
      label={row.label}
      icon={row.icon}
      cells={sons.map((view, index) => {
        const value = values[index]
        const top = (row.highlight ?? true) && value === best && best > 0
        const tone = typeof row.tone === 'function' ? row.tone(view) : row.tone
        const max = row.max(view)
        return (
          <div className='flex min-w-0 flex-col gap-1'>
            <span className='flex min-w-0 items-center gap-1'>
              <Stat value={value} tone={top ? 'primary' : 'inherit'} />
              {top && (
                <Crown
                  aria-label='Highest'
                  className='size-icon-xs shrink-0 text-primary'
                />
              )}
            </span>
            {row.bar !== false && (
              <Progress
                size='sm'
                tone={tone}
                value={max > 0 ? (value / max) * PERCENT : 0}
                aria-label={`${row.label} of ${view.son.name}`}
              />
            )}
          </div>
        )
      })}
    />
  )
}

export function CompareSons() {
  const sons = useSons()
  const relations = useSonRelations()
  const { selected, toggle, prune, full } = useCompareSelection()
  const all = sons.data ?? []
  useEffect(() => {
    if (sons.data) prune(sons.data.map((view) => view.son.id))
  }, [sons.data, prune])
  if (all.length < COMPARE_MIN) return null
  const chosen = selected
    .map((id) => all.find((view) => view.son.id === id))
    .filter((view): view is SonPublic => view !== undefined)
  const relation = (first: number, second: number) =>
    relations.data?.find(
      (item) =>
        (item.son_a_id === first && item.son_b_id === second) ||
        (item.son_a_id === second && item.son_b_id === first)
    )?.value ?? 0
  const span = chosen.length + 1
  const numeric: NumericRow[] = [
    {
      label: 'Level',
      icon: TrendingUp,
      value: (view) => view.son.level,
      max: () => 0,
      bar: false,
    },
    {
      label: 'Life',
      icon: Heart,
      value: (view) => view.son.hp,
      max: (view) => view.max_hp,
      tone: 'destructive',
    },
    {
      label: 'Essence',
      icon: Sparkles,
      value: (view) => view.son.essence,
      max: (view) => view.max_essence,
    },
    {
      label: 'Existence',
      icon: Orbit,
      value: (view) => view.son.existence,
      max: () => STAT_SCALE,
      tone: 'epic',
    },
    {
      label: 'Faith',
      icon: HandHeart,
      value: (view) => view.son.faith,
      max: () => 0,
      bar: false,
    },
    {
      label: 'Fame',
      icon: Star,
      value: (view) => view.son.fame,
      max: () => STAT_SCALE,
    },
  ]
  return (
    <Section
      title='Compare cards'
      description={`Pick ${COMPARE_MIN} to ${plural(COMPARE_MAX, 'son', 'sons')}: power, passions, reputation and relationships side by side.`}
    >
      <PagedList
        items={all}
        initial={12}
        noun={['entry', 'entries']}
        as='div'
        className='flex min-w-0 flex-wrap gap-2'
        itemKey={(view) => view.son.id}
      >
        {(view) => {
          const on = selected.includes(view.son.id)
          return (
            <Toggle
              key={view.son.id}
              size='sm'
              variant='outline'
              pressed={on}
              disabled={!on && full}
              aria-label={`Compare ${view.son.name}`}
              onPressedChange={() => toggle(view.son.id)}
            >
              {on && <Check />}
              <span className='min-w-0 truncate'>{view.son.name}</span>
            </Toggle>
          )
        }}
      </PagedList>
      {full && (
        <Muted variant='caption'>{`At most ${plural(COMPARE_MAX, 'son', 'sons')}.`}</Muted>
      )}
      {chosen.length < COMPARE_MIN ? (
        <Muted>
          <Network aria-hidden='true' className='inline size-icon-sm' /> Pick at
          least two sons to compare.
        </Muted>
      ) : (
        <div className='min-w-0 overflow-x-auto'>
          <Table className='table-fixed'>
            <TableHeader>
              <TableRow>
                <TableHead className='w-36'>
                  <span className='sr-only'>Field</span>
                </TableHead>
                {chosen.map((view) => (
                  <TableHead key={view.son.id} className='whitespace-normal'>
                    <div className='flex min-w-0 flex-col gap-1 py-2'>
                      <Portrait
                        name={view.son.name}
                        src={mediaUrl(view.cover)}
                        size='md'
                        rarity={view.son.rarity}
                      />
                      <EntityLink
                        kind='son'
                        id={String(view.son.id)}
                        rarity={view.son.rarity}
                      >
                        {view.son.name}
                      </EntityLink>
                      <Muted variant='caption' truncate>
                        {view.son.title}
                      </Muted>
                      <div className='flex min-w-0 flex-wrap items-center gap-1'>
                        <RarityBadge
                          rarity={view.son.rarity}
                          size='sm'
                          showIcon={false}
                        />
                        <Label>{starText(view.son.stars)}</Label>
                      </div>
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {numeric.map((row) => (
                <NumberRow key={row.label} row={row} sons={chosen} />
              ))}
              <GroupRow label='Stats' span={span} />
              {STATS.map((stat) => (
                <NumberRow
                  key={stat.key}
                  row={{
                    label: stat.label,
                    icon: stat.icon,
                    value: (view) => statValue(view.son, stat.key),
                    max: () => STAT_SCALE,
                    tone: (view) => view.son.rarity,
                  }}
                  sons={chosen}
                />
              ))}
              <GroupRow label='Passions' span={span} />
              {SON_PASSIONS.map((passion) => (
                <NumberRow
                  key={passion.key}
                  row={{
                    label: passion.label,
                    icon: passion.icon,
                    value: (view) => view.son[passion.key],
                    max: () => STAT_SCALE,
                    tone: 'warning',
                    highlight: false,
                  }}
                  sons={chosen}
                />
              ))}
              <GroupRow label='How they see the Creator' span={span} />
              <Row
                label='Reputation'
                cells={chosen.map((view) => {
                  const label = reputationOf(view)
                  return label ? (
                    <Badge size='sm' variant='outline'>
                      {label}
                    </Badge>
                  ) : (
                    <Muted>{'—'}</Muted>
                  )
                })}
              />
              <NumberRow
                row={{
                  label: 'Love',
                  icon: Heart,
                  value: (view) => view.son.reputation_love ?? 0,
                  max: () => STAT_SCALE,
                  tone: 'success',
                }}
                sons={chosen}
              />
              <NumberRow
                row={{
                  label: 'Fear',
                  icon: Skull,
                  value: (view) => view.son.reputation_fear ?? 0,
                  max: () => STAT_SCALE,
                  tone: 'destructive',
                }}
                sons={chosen}
              />
              <NumberRow
                row={{
                  label: 'Forgottenness',
                  icon: CloudFog,
                  value: (view) => view.son.reputation_forgotten ?? 0,
                  max: () => STAT_SCALE,
                  tone: 'muted',
                }}
                sons={chosen}
              />
              <GroupRow label='Relationships' span={span} />
              <Row
                label='Closest'
                cells={chosen.map((view) =>
                  view.card.best_friend ? (
                    <span className='flex min-w-0 items-baseline gap-1'>
                      <EntityLink
                        kind='son'
                        id={String(view.card.best_friend.id)}
                      >
                        {view.card.best_friend.name}
                      </EntityLink>
                      <Stat
                        value={signed(view.card.best_friend.value)}
                        tone='success'
                      />
                    </span>
                  ) : (
                    <Muted>{'—'}</Muted>
                  )
                )}
              />
              <Row
                label='Rival'
                cells={chosen.map((view) =>
                  view.card.worst_rival ? (
                    <span className='flex min-w-0 items-baseline gap-1'>
                      <EntityLink
                        kind='son'
                        id={String(view.card.worst_rival.id)}
                      >
                        {view.card.worst_rival.name}
                      </EntityLink>
                      <Stat
                        value={signed(view.card.worst_rival.value)}
                        tone='destructive'
                      />
                    </span>
                  ) : (
                    <Muted>{'—'}</Muted>
                  )
                )}
              />
              <Row
                label='Towards the selected'
                cells={chosen.map((view) => (
                  <div className='flex min-w-0 flex-col gap-0.5'>
                    {chosen
                      .filter((other) => other.son.id !== view.son.id)
                      .map((other) => (
                        <span
                          key={other.son.id}
                          className='flex min-w-0 items-center justify-between gap-2'
                        >
                          <Text variant='caption' truncate>
                            {other.son.name}
                          </Text>
                          <Stat
                            value={signed(relation(view.son.id, other.son.id))}
                            tone={
                              relation(view.son.id, other.son.id) > 0
                                ? 'success'
                                : relation(view.son.id, other.son.id) < 0
                                  ? 'destructive'
                                  : 'muted'
                            }
                          />
                        </span>
                      ))}
                  </div>
                ))}
              />
              <Row
                label='Last word'
                cells={chosen.map((view) =>
                  view.card.last_words ? (
                    <Text variant='caption' italic truncate={3}>
                      {view.card.last_words}
                    </Text>
                  ) : (
                    <Muted>{'—'}</Muted>
                  )
                )}
              />
            </TableBody>
          </Table>
        </div>
      )}
    </Section>
  )
}
