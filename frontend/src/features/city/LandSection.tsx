import { Link } from '@tanstack/react-router'
import { Gem, Maximize2, Mountain, Pickaxe, Trees, Wheat } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, KpiTile, LoadingBlock, Section } from '@/components/domain'
import { Text } from '@/components/typography'
import { LandPlan2D } from './LandPlan2D'
import { type LandScene, useLandScene } from './api'

function Summary({ scene }: { scene: LandScene }) {
  return (
    <div className='@container/land flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-2 @xl/land:grid-cols-4'>
        <KpiTile
          label='Forest'
          value={`${scene.forest_cover}%`}
          icon={Trees}
          tone='success'
        />
        <KpiTile
          label='Farmed'
          value={`${scene.farmed}%`}
          icon={Wheat}
          tone='gold'
        />
        <KpiTile
          label='Mined'
          value={`${scene.mined}%`}
          icon={Pickaxe}
          tone='warning'
        />
        <KpiTile
          label='Deposits'
          value={scene.resources.length}
          icon={Gem}
          tone='verdigris'
        />
      </div>
      <Link
        to='/cities'
        search={{ view: 'land', region: scene.region.id }}
        aria-label={`Walk the land of ${scene.region.name}`}
        className='group relative block min-w-0 overflow-hidden rounded-xl border bg-card p-3 transition-colors hover:border-primary'
      >
        <LandPlan2D scene={scene} selected={null} onPick={() => undefined} />
        <div className='pointer-events-none absolute right-3 bottom-3 flex items-center gap-1.5 rounded-full border bg-popover/90 px-3 py-1 text-popover-foreground shadow-sm backdrop-blur-sm'>
          <Maximize2 className='size-icon-xs' />
          <Text as='span' variant='caption' tone='inherit'>
            Walk the land
          </Text>
        </div>
      </Link>
      <Button asChild>
        <Link to='/cities' search={{ view: 'land', region: scene.region.id }}>
          <Maximize2 />
          Walk the land and shape it
        </Link>
      </Button>
    </div>
  )
}

export function LandSection({ regionId }: { regionId: number }) {
  const query = useLandScene(regionId)
  return (
    <Section
      id='section-land'
      title='The land'
      description='The land as the engine reckons it: its ground and cover tile by tile, its river and coast, its towns, places, works and deposits.'
      icon={Mountain}
      tone='verdigris'
    >
      <div data-surface='LandSection' className='flex min-w-0 flex-col gap-3'>
        {query.isPending ? (
          <LoadingBlock label='Drawing the land' />
        ) : query.isError ? (
          <EmptyState
            icon={Mountain}
            size='inline'
            title='The land could not be drawn'
            description={query.error.message}
          />
        ) : (
          <Summary scene={query.data} />
        )}
      </div>
    </Section>
  )
}
