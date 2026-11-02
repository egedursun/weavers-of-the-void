import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  COSMOS_QUALITIES,
  type CosmosQuality,
  type CosmosViewMode,
  QUALITY_LABEL,
  rendersInSoftware,
} from './useCosmosViewSettings'

const QUALITY_HINT = 'Pixel density, antialiasing, star count and glow'
const SOFTWARE_HINT = `${QUALITY_HINT}. This browser draws without a graphics card, so the sky starts at Low.`

type CosmosViewSettingsProps = {
  view: CosmosViewMode
  quality: CosmosQuality
  failure: string | null
  onView: (view: CosmosViewMode) => void
  onQuality: (quality: CosmosQuality) => void
}

export function CosmosViewSettings({
  view,
  quality,
  failure,
  onView,
  onQuality,
}: CosmosViewSettingsProps) {
  const threeD = (
    <ToggleGroupItem
      value='3d'
      disabled={failure !== null}
      aria-label='3D view'
    >
      3D
    </ToggleGroupItem>
  )
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2'>
      <ToggleGroup
        type='single'
        variant='outline'
        size='sm'
        value={view}
        onValueChange={(value) => value && onView(value as CosmosViewMode)}
        aria-label='Cosmos view'
      >
        {failure ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <span tabIndex={0} className='inline-flex'>
                {threeD}
              </span>
            </TooltipTrigger>
            <TooltipContent>{`${failure}; using the 2D view.`}</TooltipContent>
          </Tooltip>
        ) : (
          threeD
        )}
        <ToggleGroupItem value='2d' aria-label='2D view'>
          2D
        </ToggleGroupItem>
      </ToggleGroup>
      {view === '3d' && (
        <Select
          value={quality}
          onValueChange={(value) => onQuality(value as CosmosQuality)}
        >
          <SelectTrigger
            size='sm'
            aria-label='3D quality'
            title={rendersInSoftware() ? SOFTWARE_HINT : QUALITY_HINT}
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {COSMOS_QUALITIES.map((value) => (
              <SelectItem key={value} value={value}>
                {`${QUALITY_LABEL[value]} quality`}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  )
}
