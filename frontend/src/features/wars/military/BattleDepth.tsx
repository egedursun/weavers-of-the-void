import {
  Bandage,
  Crosshair,
  Flag,
  HeartCrack,
  Link as Chain,
  Skull,
  Swords,
  UserMinus,
  UserX,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import {
  EntityLink,
  MiniStat,
  Paged,
  PagedList,
  StatBar,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import {
  FATE_OF,
  MAGIC_PART,
  MORALE_PART,
  nameOf,
  useBattleDepth,
} from './depth'
import { FORMATION, MORALE_STATE, PERCENT, TARGET_CLASS } from './labels'
import { Plain, TableTag, Tag } from './parts'

const CASUALTY_PARTS = [
  { key: 'killed', label: 'Killed', icon: Skull, tone: 'danger' },
  { key: 'walking', label: 'Walking wounded', icon: Bandage, tone: 'warning' },
  {
    key: 'stretcher',
    label: 'Stretcher cases',
    icon: HeartCrack,
    tone: 'danger',
  },
  { key: 'captured', label: 'Captured', icon: Chain, tone: 'warning' },
  { key: 'missing', label: 'Stragglers', icon: UserMinus, tone: 'muted' },
  { key: 'deserted', label: 'Deserted', icon: UserX, tone: 'muted' },
] as const

const TACTIC_SIDES = new Set(['attacker', 'defender'])
const SIDE_FACTORS: Record<string, (value: number) => string> = {
  luck: (value) => `fortune ×${value.toFixed(2)}`,
  span: (value) => `${plural(value, 'stack', 'stacks')} on the front`,
  concealment: (value) => `concealment ${formatInteger(value)}`,
  square_reserve: (value) =>
    `${formatInteger(value)} in reserve loosed their volleys (square law)`,
  linear_cap: (value) =>
    `${Math.round(value * PERCENT)}% of melee strength found no enemy front to strike (linear law)`,
}
const FACTOR_LABELS: Record<string, (value: number) => string> =
  Object.fromEntries(
    Object.entries(SIDE_FACTORS).flatMap(([key, label]) => [
      [`attacker_${key}`, label],
      [`defender_${key}`, label],
    ])
  )

function Signed({ value }: { value: number }) {
  return (
    <Text
      as='span'
      variant='caption'
      className={value < 0 ? 'text-destructive' : 'text-success'}
    >
      {value > 0 ? `+${value}` : value}
    </Text>
  )
}

export function BattleDepthPanel({
  battleId,
  sides,
}: {
  battleId: number
  sides: Record<string, string>
}) {
  const query = useBattleDepth(battleId)
  const depth = query.data
  if (!depth) return null
  const magic = Object.entries(depth.magic).filter(([, value]) => value > 0)
  const factors = Object.entries(depth.tactic_factors).filter(([key]) =>
    TACTIC_SIDES.has(key)
  )
  const flanks = Object.entries(depth.tactic_factors).filter(
    ([key, value]) => key.endsWith('_flank') && value > 0
  )
  const readings = Object.entries(depth.tactic_factors).filter(
    ([key, value]) => key in FACTOR_LABELS && value !== 0
  )
  return (
    <div data-surface='BattleDepth' className='flex min-w-0 flex-col gap-3'>
      {factors.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Label>Tactic counters</Label>
          {factors.map(([side, value]) => (
            <Badge
              key={side}
              size='sm'
              variant={
                value >= 1.05
                  ? 'success'
                  : value <= 0.95
                    ? 'destructive'
                    : 'secondary'
              }
            >
              {side === 'attacker' ? 'Attackers' : 'Defenders'} ×
              {value.toFixed(2)}
            </Badge>
          ))}
          {flanks.map(([key]) => (
            <Badge key={key} size='sm' variant='warning'>
              <Flag aria-hidden='true' />
              {key.startsWith('attacker') ? 'Attackers' : 'Defenders'} turned
              the flank
            </Badge>
          ))}
        </div>
      )}
      {readings.length > 0 && (
        <div
          data-chart='chart-battle-laws'
          className='flex min-w-0 flex-wrap items-center gap-1.5'
        >
          <Label>Laws of the fight</Label>
          {readings.map(([key, value]) => (
            <Badge key={key} size='sm' variant='outline'>
              {key.startsWith('attacker') ? 'Attackers' : 'Defenders'}:{' '}
              {FACTOR_LABELS[key](value)}
            </Badge>
          ))}
        </div>
      )}
      {magic.length > 0 && (
        <PagedList
          items={magic}
          initial={12}
          noun={['entry', 'entries']}
          as='div'
          className='flex min-w-0 flex-wrap gap-1.5'
          itemKey={([key]) => key}
        >
          {([key, value]) => (
            <Tag
              key={key}
              item={{
                ...nameOf(MAGIC_PART, key),
                label: `${nameOf(MAGIC_PART, key).label}: ${value}`,
              }}
            />
          )}
        </PagedList>
      )}
      {Object.keys(depth.morale).length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-2 @lg/mil:grid-cols-2'>
          {Object.entries(depth.morale).map(([side, parts]) => (
            <div
              key={side}
              className='flex min-w-0 flex-col gap-1.5 rounded-md border surface-framed border-gild/70 bg-card p-2.5'
            >
              <Label variant='overline'>
                {sides[side] ?? 'A side'}: morale
              </Label>
              <div className='flex min-w-0 flex-wrap gap-1.5'>
                {Object.entries(parts)
                  .filter(([, value]) => value !== 0)
                  .map(([key, value]) => {
                    const item = nameOf(MORALE_PART, key)
                    const Icon = item.icon
                    return (
                      <Badge key={key} size='sm' variant='secondary'>
                        <Icon aria-hidden='true' />
                        {item.label}
                        {key === 'willpower' ? (
                          <Text as='span' variant='caption'>
                            {value}
                          </Text>
                        ) : (
                          <Signed value={value} />
                        )}
                      </Badge>
                    )
                  })}
              </div>
            </div>
          ))}
        </div>
      )}
      {depth.stacks.length > 0 && (
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label>Losses by stack</Label>
          <div className='grid min-w-0 grid-cols-1 gap-1.5 @lg/mil:grid-cols-2'>
            <Paged items={depth.stacks}>
              {(stack, index) => (
                <div
                  key={`${stack.kind}.${index}`}
                  className='flex min-w-0 flex-col gap-1 rounded-md border surface-sheen border-gild/60 bg-card p-2'
                >
                  <div className='flex min-w-0 items-center gap-1.5'>
                    <Swords
                      aria-hidden='true'
                      className='size-icon-xs shrink-0 text-muted-foreground'
                    />
                    <Text as='span' truncate>
                      {stack.label}
                    </Text>
                    <Muted as='span' variant='caption' truncate>
                      {stack.side?.name}
                    </Muted>
                    {stack.routed && (
                      <Badge size='sm' variant='destructive'>
                        Routed
                      </Badge>
                    )}
                    {stack.reserve && (
                      <Badge size='sm' variant='secondary'>
                        Held in reserve
                      </Badge>
                    )}
                  </div>
                  <div className='flex min-w-0 flex-wrap gap-1'>
                    {stack.formation && (
                      <TableTag table={FORMATION} value={stack.formation} />
                    )}
                    {stack.morale_state && (
                      <TableTag
                        table={MORALE_STATE}
                        value={stack.morale_state}
                      />
                    )}
                    {stack.target_class && (
                      <TableTag
                        table={TARGET_CLASS}
                        value={stack.target_class}
                      />
                    )}
                    {stack.ammunition_spent > 0 && (
                      <Plain icon={Crosshair}>
                        {`${plural(stack.ammunition_spent, 'volley', 'volleys')} loosed`}
                      </Plain>
                    )}
                  </div>
                  <StatBar
                    label={`Lost of ${formatInteger(stack.start)}`}
                    value={stack.lost}
                    max={Math.max(1, stack.start)}
                    tone='destructive'
                  />
                  <StatBar
                    label='Organisation left'
                    value={stack.organisation}
                    max={PERCENT}
                    tone='info'
                  />
                  {stack.lost > 0 && (
                    <div className='grid min-w-0 grid-cols-2 gap-1 @md/mil:grid-cols-3'>
                      {CASUALTY_PARTS.filter((part) => stack[part.key] > 0).map(
                        (part) => (
                          <MiniStat
                            key={part.key}
                            icon={part.icon}
                            label={part.label}
                            value={formatInteger(stack[part.key])}
                            tone={part.tone}
                          />
                        )
                      )}
                    </div>
                  )}
                </div>
              )}
            </Paged>
          </div>
        </div>
      )}
      {depth.casualties.length > 0 && (
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label>Named casualties</Label>
          <ul className='flex min-w-0 flex-col gap-1'>
            <Paged items={depth.casualties} as='li'>
              {(casualty, index) => {
                const fate = nameOf(FATE_OF, casualty.fate)
                return (
                  <li
                    key={`${casualty.mortal?.id}.${index}`}
                    className='flex min-w-0 flex-wrap items-center gap-1.5'
                  >
                    <Tag item={fate} />
                    {casualty.mortal && (
                      <EntityLink kind='entity' id={String(casualty.mortal.id)}>
                        {casualty.mortal.name}
                      </EntityLink>
                    )}
                    {casualty.harm > 0 && (
                      <MiniStat
                        icon={Skull}
                        label='Harm'
                        value={casualty.harm}
                        tone='danger'
                      />
                    )}
                    {casualty.note && (
                      <Muted as='span' variant='caption' truncate>
                        {casualty.note}
                      </Muted>
                    )}
                  </li>
                )
              }}
            </Paged>
          </ul>
        </div>
      )}
    </div>
  )
}
