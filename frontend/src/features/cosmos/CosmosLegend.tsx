import { Text } from '@/components/typography'
import { MethodGlyph, VoyageGlyph } from './Glyphs'
import { type TravelMethod } from './api'
import { type CosmosIndex, isUnderway } from './model/cosmosModel'
import { TRAVEL_METHODS, TRAVEL_METHOD_LABEL } from './model/labels'

export function CosmosLegend({ index }: { index: CosmosIndex }) {
  const present = new Set<TravelMethod>(
    index.data.routes.map((route) => route.method)
  )
  const methods = TRAVEL_METHODS.filter((method) => present.has(method))
  const voyages = index.data.journeys.some(isUnderway)
  if (methods.length === 0)
    return (
      <Text variant='caption' tone='inherit' className='opacity-80'>
        No known route between worlds yet.
      </Text>
    )
  return (
    <div
      className='flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2'
      aria-label='Route legend'
    >
      <Text as='span' variant='caption' weight='medium' tone='inherit'>
        Routes
      </Text>
      {methods.map((method) => (
        <span key={method} className='inline-flex min-w-0 items-center gap-1.5'>
          <MethodGlyph method={method} />
          <Text
            as='span'
            variant='caption'
            tone='inherit'
            truncate
            className='opacity-80'
          >
            {TRAVEL_METHOD_LABEL[method]}
          </Text>
        </span>
      ))}
      {voyages && (
        <span className='inline-flex min-w-0 items-center gap-1.5'>
          <VoyageGlyph />
          <Text
            as='span'
            variant='caption'
            tone='inherit'
            className='opacity-80'
          >
            Voyage under way
          </Text>
        </span>
      )}
    </div>
  )
}
