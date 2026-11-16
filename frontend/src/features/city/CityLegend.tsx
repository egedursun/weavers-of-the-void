import { plural } from '@/lib/units'
import { PagedList } from '@/components/domain'
import { Text } from '@/components/typography'
import { ZoneDot } from './ZoneDot'
import { type CityScene } from './api'
import { ZONES } from './labels'

export function CityLegend({
  scene,
  hexes = true,
}: {
  scene: CityScene
  hexes?: boolean
}) {
  return (
    <PagedList
      items={scene.zones.filter(
        (row) => row.districts > 0 || row.buildings > 0
      )}
      initial={7}
      noun={['zone', 'zones']}
      as='div'
      className='flex min-w-0 flex-wrap items-center gap-x-5 gap-y-1 rounded-md border surface-sheen border-gild/60 bg-card px-3 py-2'
      listProps={{ role: 'list', 'aria-label': 'Zones of the city' }}
      itemKey={(row) => row.zone}
    >
      {(row) => (
        <span role='listitem' className='flex items-center gap-1.5'>
          <ZoneDot spec={ZONES[row.zone]} />
          <Text as='span' variant='caption'>
            {`${ZONES[row.zone].label} · ${plural(row.districts, 'district', 'districts')}${hexes ? ` · ${plural(row.cells, 'hex', 'hexes')}` : ''} · ${plural(row.buildings, 'building', 'buildings')}`}
          </Text>
        </span>
      )}
    </PagedList>
  )
}
