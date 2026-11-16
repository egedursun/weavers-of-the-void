import { PawPrint, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Medallion, PagedList } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { type RangeMap } from '@/features/entity/wilds/api'
import { RANGE_BANDS, rangeBand } from './speciesRange'

const SWATCH: Record<string, string> = {
  trace: 'opacity-30',
  scattered: 'opacity-45',
  common: 'opacity-60',
  abundant: 'opacity-80',
  teeming: 'opacity-100',
}

export function SpeciesRangePanel({
  worldId,
  speciesId,
  range,
  onSpecies,
}: {
  worldId: number
  speciesId: number | null
  range: RangeMap | null
  onSpecies: (id: number | null) => void
}) {
  const lands = range?.cells.length ?? 0
  const rising =
    range?.cells.filter((cell) => cell.trend === 'rising').length ?? 0
  const falling =
    range?.cells.filter((cell) => cell.trend === 'falling').length ?? 0
  return (
    <div
      data-surface='map-layer-species-range'
      className='flex min-w-0 flex-wrap items-center gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <Medallion icon={PawPrint} tone='success' size='sm' />
      <div className='flex min-w-0 flex-1 basis-60 flex-col gap-1'>
        <Label>Show the range of one kind</Label>
        <EntityPicker
          types={['species']}
          value={speciesId}
          worldId={worldId}
          onChange={onSpecies}
          placeholder='Choose a kind…'
        />
      </div>
      {speciesId !== null && range && (
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Text weight='semibold'>
            {lands === 0
              ? 'It ranges nowhere in this world'
              : `${lands} ${lands === 1 ? 'land' : 'lands'}, at most ${range.peak} strong`}
          </Text>
          <div className='flex min-w-0 flex-wrap gap-1'>
            <Badge size='sm' variant='success'>{`${rising} rising`}</Badge>
            <Badge
              size='sm'
              variant='destructive'
            >{`${falling} falling`}</Badge>
          </div>
          <div
            className='flex min-w-0 flex-wrap items-center gap-1'
            aria-label='Shading'
          >
            {RANGE_BANDS.map((band) => (
              <span
                key={band.key}
                className='flex items-center gap-1'
                title={band.label}
              >
                <span
                  aria-hidden='true'
                  className={cn(
                    'inline-block size-icon-xs rounded-sm bg-success',
                    SWATCH[band.key]
                  )}
                />
                <Muted as='span' variant='caption'>
                  {band.label}
                </Muted>
              </span>
            ))}
          </div>
        </div>
      )}
      {speciesId !== null && (
        <Button size='sm' variant='ghost' onClick={() => onSpecies(null)}>
          <X />
          Clear
        </Button>
      )}
      {speciesId !== null && range && range.cells.length > 0 && (
        <PagedList
          items={range.cells}
          initial={12}
          noun={['entry', 'entries']}
          as='ul'
          className='flex w-full min-w-0 flex-wrap gap-1.5'
          itemKey={(cell) => cell.region.id}
        >
          {(cell) => (
            <li key={cell.region.id}>
              <Badge size='sm' variant='secondary'>
                {`${cell.region.name}: ${cell.abundance} (${rangeBand(cell.abundance, range.peak) ?? 'none'})`}
              </Badge>
            </li>
          )}
        </PagedList>
      )}
    </div>
  )
}
