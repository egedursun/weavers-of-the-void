import { PagedList } from '@/components/domain'
import { Text } from '@/components/typography'
import { Dot } from './ZoneDot'
import { type LandScene } from './api'
import { COVERS, COVER_FILL, GROUNDS, GROUND_FILL } from './labels'

type Swatch = { key: string; label: string; fill: string; count: number }

const SYMBOLS = [
  {
    key: 'settlement',
    label: 'Town',
    shape: (
      <>
        <circle
          cx='5'
          cy='5'
          r='4.2'
          className='fill-card stroke-foreground'
          strokeWidth='1'
        />
        <circle cx='5' cy='5' r='2' className='fill-brand-gold' />
      </>
    ),
  },
  {
    key: 'place',
    label: 'Place',
    shape: (
      <polygon
        points='5,0.8 9.2,5 5,9.2 0.8,5'
        className='fill-tincture-purple'
      />
    ),
  },
  {
    key: 'work',
    label: 'Work',
    shape: (
      <rect
        x='1.2'
        y='1.2'
        width='7.6'
        height='7.6'
        rx='1.2'
        className='fill-tincture-brown'
      />
    ),
  },
  {
    key: 'resource',
    label: 'Deposit',
    shape: <circle cx='5' cy='5' r='3.6' className='fill-tincture-celeste' />,
  },
  {
    key: 'river',
    label: 'River',
    shape: (
      <line
        x1='0.8'
        y1='7'
        x2='9.2'
        y2='3'
        className='stroke-land-river'
        strokeWidth='2.4'
        strokeLinecap='round'
      />
    ),
  },
  {
    key: 'coast',
    label: 'Coast',
    shape: (
      <line
        x1='0.8'
        y1='5'
        x2='9.2'
        y2='5'
        className='stroke-land-shore'
        strokeWidth='2.4'
        strokeLinecap='round'
      />
    ),
  },
] as const

function swatches(scene: LandScene): Swatch[] {
  const found = new Map<string, Swatch>()
  for (const tile of scene.tiles) {
    const open = tile.cover === 'open'
    const key = open ? `ground-${tile.ground}` : `cover-${tile.cover}`
    const swatch = found.get(key) ?? {
      key,
      label: open ? GROUNDS[tile.ground] : COVERS[tile.cover],
      fill: open ? GROUND_FILL[tile.ground] : COVER_FILL[tile.cover],
      count: 0,
    }
    found.set(key, { ...swatch, count: swatch.count + 1 })
  }
  return [...found.values()].sort((first, second) => second.count - first.count)
}

export function LandLegend({ scene }: { scene: LandScene }) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <PagedList
        items={swatches(scene)}
        initial={8}
        noun={['kind of ground', 'kinds of ground']}
        as='div'
        className='flex min-w-0 flex-wrap items-center gap-x-5 gap-y-1'
        listProps={{ role: 'list', 'aria-label': 'Ground of the land' }}
        itemKey={(swatch) => swatch.key}
      >
        {(swatch) => (
          <span role='listitem' className='flex items-center gap-1.5'>
            <Dot fill={swatch.fill} />
            <Text as='span' variant='caption'>
              {`${swatch.label} · ${swatch.count} of ${scene.tiles.length} tiles`}
            </Text>
          </span>
        )}
      </PagedList>
      <div
        role='list'
        aria-label='Symbols on the land'
        className='flex min-w-0 flex-wrap items-center gap-x-5 gap-y-1'
      >
        {SYMBOLS.map((symbol) => (
          <span
            key={symbol.key}
            role='listitem'
            className='flex items-center gap-1.5'
          >
            <svg
              aria-hidden='true'
              viewBox='0 0 10 10'
              className='size-icon-xs shrink-0'
            >
              {symbol.shape}
            </svg>
            <Text as='span' variant='caption' tone='muted'>
              {symbol.label}
            </Text>
          </span>
        ))}
      </div>
    </div>
  )
}
