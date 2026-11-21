import { plural } from '@/lib/units'
import {
  CAMPAIGN_STAGE,
  MIGRATION_CAUSE,
  MIGRATION_RECEPTION,
} from '@/features/interworld/labels'
import { type CosmosData } from './api'
import { curvedPath, type Layout2D } from './model/layout2d'
import { cssVar } from './model/looks'

const CAMPAIGN_CURVE = 0.18
const MIGRATION_CURVE = -0.18
const ORBIT_RING = 22

export function Crossings2D({
  data,
  layout,
}: {
  data: CosmosData
  layout: Layout2D
}) {
  return (
    <g aria-label='Crossings between worlds'>
      {data.campaigns.map((campaign) => {
        const from = layout.worlds.get(campaign.from_world_id)
        const to = layout.worlds.get(campaign.target_world_id)
        if (!from || !to) return null
        return (
          <path
            key={`campaign-${campaign.id}`}
            d={curvedPath(from, to, CAMPAIGN_CURVE)}
            fill='none'
            stroke={cssVar('--cosmos-hostile')}
            strokeWidth={3}
            strokeDasharray='8 4'
            strokeLinecap='round'
          >
            <title>{`A campaign of ${campaign.attacker_name || 'an unnamed host'} between worlds · ${CAMPAIGN_STAGE[campaign.stage]} · ${plural(campaign.forces, 'soldier')}`}</title>
          </path>
        )
      })}
      {data.migrations.map((movement) => {
        const from = layout.worlds.get(movement.from_world_id)
        const to = layout.worlds.get(movement.to_world_id)
        if (!from || !to) return null
        return (
          <path
            key={`migration-${movement.id}`}
            d={curvedPath(from, to, MIGRATION_CURVE)}
            fill='none'
            stroke={cssVar('--cosmos-bone')}
            strokeWidth={2}
            strokeDasharray='2 5'
            strokeLinecap='round'
          >
            <title>{`A people moving between worlds · ${MIGRATION_CAUSE[movement.cause]} · ${MIGRATION_RECEPTION[movement.reception]} · ${movement.moved.toLocaleString()} gone`}</title>
          </path>
        )
      })}
      {data.orbits.map((orbit) => {
        const point = layout.worlds.get(orbit.world_id)
        if (!point) return null
        return (
          <circle
            key={`orbit-${orbit.world_id}`}
            cx={point.x}
            cy={point.y}
            r={ORBIT_RING}
            fill='none'
            stroke={cssVar('--cosmos-copper')}
            strokeWidth={2}
          >
            <title>{`The space around this world is held at strength ${orbit.strength}`}</title>
          </circle>
        )
      })}
    </g>
  )
}
