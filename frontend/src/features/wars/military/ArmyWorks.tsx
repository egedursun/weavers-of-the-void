import { Bomb, Compass, HardHat, Route, Shovel, Wheat } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { agree, plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { EntityLink, MiniStat, StatBar } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { type ArmyCard, soldiersOf } from './api'
import { COMMAND_AREA, PERCENT, named } from './labels'
import { Plain, Tag } from './parts'

const PATROL = {
  label: 'Patrolling the routes',
  icon: Compass,
  tone: 'success' as const,
}
const ROAD = { label: 'On a road', icon: Route, tone: 'gold' as const }

export function ArmyWorks({ army }: { army: ArmyCard }) {
  const works = army.works
  const soldiers = soldiersOf(army)
  const fed =
    works.supply_low === works.supply_high
      ? formatInteger(works.supply_low)
      : `${formatInteger(works.supply_low)}–${formatInteger(works.supply_high)}`
  return (
    <div
      data-surface='ArmyWorks'
      className='flex min-w-0 flex-col gap-3 rounded-lg border bg-muted/20 p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Label variant='overline'>Land and works</Label>
        {works.eaten_out && (
          <Badge size='sm' variant='destructive'>
            <Wheat />
            Eating the land out
          </Badge>
        )}
        {works.road && <Tag item={ROAD} />}
        {works.patrolling && <Tag item={PATROL} />}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @lg/mil:grid-cols-2'>
        <MiniStat
          icon={Wheat}
          label='The land feeds'
          value={fed}
          tone={works.eaten_out ? 'danger' : 'success'}
          hint={
            works.eaten_out
              ? `${plural(soldiers, 'soldier', 'soldiers')} ${agree(soldiers, 'is', 'are')} more than it feeds; they starve away, plunder the land and sour its people`
              : 'Soldiers its region feeds a season, from the leanest season to the richest'
          }
        />
        <MiniStat
          icon={HardHat}
          label='Sappers'
          value={formatInteger(works.sappers)}
          tone={works.engineers ? 'gold' : 'muted'}
          hint={
            works.engineers
              ? 'Enough to bridge rivers, lay roads and blow bridges behind a retreat'
              : 'Too few to bridge rivers, lay roads or blow bridges'
          }
        />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @lg/mil:grid-cols-3'>
        <StatBar
          label='Earthworks left here'
          icon={Shovel}
          value={works.earthworks}
          max={PERCENT}
          tone='verdigris'
        />
        <StatBar
          label='Military road'
          icon={Route}
          value={works.military_road}
          max={PERCENT}
          tone='default'
        />
        {works.river ? (
          <StatBar
            label='Bridge down'
            icon={Bomb}
            value={works.bridge_down}
            max={PERCENT}
            tone='destructive'
          />
        ) : (
          <Muted variant='caption'>No river here to bridge or blow</Muted>
        )}
      </div>
      {army.region ? (
        <Muted variant='caption'>
          {'Earthworks, roads and bridges are scars on '}
          <EntityLink kind='entity' id={String(army.region.id)}>
            {army.region.name}
          </EntityLink>
          {'; set or hold them there.'}
        </Muted>
      ) : (
        <Muted variant='caption'>The army stands in no region.</Muted>
      )}
    </div>
  )
}

export function CommanderAreas({ army }: { army: ArmyCard }) {
  const best = army.best_area ? named(COMMAND_AREA, army.best_area) : null
  return (
    <div
      data-surface='CommanderAreas'
      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/20 p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Label variant='overline'>Leads best at</Label>
        {best ? (
          <Tag item={best} />
        ) : (
          <Plain icon={Compass}>No arm led well</Plain>
        )}
      </div>
      {army.commander ? (
        <div className='grid min-w-0 grid-cols-1 gap-2 @lg/mil:grid-cols-2 @3xl/mil:grid-cols-5'>
          {Object.entries(COMMAND_AREA).map(([key, area]) => (
            <StatBar
              key={key}
              label={area.label}
              icon={area.icon}
              value={army.command_areas[key as keyof typeof COMMAND_AREA] ?? 0}
              max={PERCENT}
              tone='info'
            />
          ))}
        </div>
      ) : (
        <Muted variant='caption'>
          Without a commander no arm fights better for its leader.
        </Muted>
      )}
      <Muted variant='caption'>
        Drawn from the commander's tactics, strategy, logistics, siegecraft and
        weapon skills and battle traits; change those to change these.
      </Muted>
    </div>
  )
}
