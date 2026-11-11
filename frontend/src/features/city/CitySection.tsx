import { Link } from '@tanstack/react-router'
import { Building2, Home, Maximize2, Tent, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, KpiTile, LoadingBlock, Section } from '@/components/domain'
import { Text } from '@/components/typography'
import { BuildForge } from './CityControls'
import { CityLegend } from './CityLegend'
import { CityPlan2D } from './CityPlan2D'
import { type CityScene, useCityScene } from './api'
import { CITY_ICON } from './labels'

function Summary({
  scene,
  blocked,
}: {
  scene: CityScene
  blocked: string | null
}) {
  const homes = scene.districts.reduce((sum, item) => sum + item.dwellings, 0)
  const empty = scene.districts.length === 0 && scene.buildings.length === 0
  return (
    <div className='@container/city flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-2 @xl/city:grid-cols-4'>
        <KpiTile
          label='People'
          value={scene.population}
          icon={Users}
          tone='info'
        />
        <KpiTile label='Homes' value={homes} icon={Home} tone='success' />
        <KpiTile
          label='Homeless'
          value={scene.homeless}
          icon={Tent}
          tone='danger'
          harmful
        />
        <KpiTile
          label='Buildings'
          value={scene.buildings.length}
          icon={Building2}
          tone='gold'
        />
      </div>
      <Link
        to='/cities'
        search={{ view: 'city', town: scene.town.id }}
        aria-label={`Walk the city of ${scene.town.name}`}
        className='group relative block min-w-0 overflow-hidden rounded-xl border bg-card transition-colors hover:border-primary'
      >
        {empty ? (
          <div className='p-4'>
            <EmptyState
              icon={CITY_ICON}
              size='inline'
              title='Nothing is built here yet'
              description='The town raises its first districts in the next epoch, or raise one now below.'
            />
          </div>
        ) : (
          <div className='p-3'>
            <CityPlan2D
              scene={scene}
              selected={null}
              onPick={() => undefined}
            />
          </div>
        )}
        <div className='pointer-events-none absolute right-3 bottom-3 flex items-center gap-1.5 rounded-full border bg-popover/90 px-3 py-1 text-popover-foreground shadow-sm backdrop-blur-sm'>
          <Maximize2 className='size-icon-xs' />
          <Text as='span' variant='caption' tone='inherit'>
            Walk the city
          </Text>
        </div>
      </Link>
      <CityLegend scene={scene} hexes={false} />
      <Button asChild>
        <Link to='/cities' search={{ view: 'city', town: scene.town.id }}>
          <Maximize2 />
          Walk the city and rule its districts
        </Link>
      </Button>
      <BuildForge scene={scene} blocked={blocked} />
    </div>
  )
}

export function CitySection({
  settlementId,
  readOnlyReason = null,
}: {
  settlementId: number
  readOnlyReason?: string | null
}) {
  const query = useCityScene(settlementId)
  return (
    <Section
      id='section-city'
      title='The city'
      description='The town as the engine reckons it: its zones and districts on their hexes, every building at its stage, its homes and homeless, its walls and water.'
      icon={CITY_ICON}
      tone='gold'
    >
      <div data-surface='CitySection' className='flex min-w-0 flex-col gap-3'>
        {query.isPending ? (
          <LoadingBlock label='Drawing the city' />
        ) : query.isError ? (
          <EmptyState
            icon={CITY_ICON}
            size='inline'
            title='The city could not be drawn'
            description={query.error.message}
          />
        ) : (
          <Summary scene={query.data} blocked={readOnlyReason} />
        )}
      </div>
    </Section>
  )
}
