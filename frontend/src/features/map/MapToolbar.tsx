import { type ReactNode } from 'react'
import {
  Wifi,
  Scroll,
  Biohazard,
  BookOpen,
  Church,
  CloudFog,
  CloudRain,
  Coins,
  Crown,
  Flag,
  Flame,
  Footprints,
  Ghost,
  Landmark,
  Languages,
  Layers,
  Leaf,
  Map as MapIcon,
  MapPin,
  Maximize,
  Minus,
  Mountain,
  Plus,
  RefreshCw,
  Route,
  Shield,
  ShieldAlert,
  Sparkles,
  Sprout,
  Store,
  Sun,
  Swords,
  Tag,
  Thermometer,
  Users,
  Waypoints,
  Wheat,
  Zap,
  type LucideIcon,
  PawPrint,
  Building2,
  Droplets,
  Network,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { Toggle } from '@/components/ui/toggle'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Label } from '@/components/typography'
import { MapSearch } from './MapSearch'
import {
  type LayerMode,
  type Overlay,
  LAYER_LABEL,
  LAYER_MODES,
  LAYER_SURFACE,
  OVERLAYS,
  OVERLAY_LABEL,
  OVERLAY_SURFACE,
} from './mapModel'

const LAYER_ICON: Record<LayerMode, LucideIcon> = {
  terrain: Mountain,
  political: Flag,
  realms: Landmark,
  de_jure: Scroll,
  regions: MapIcon,
  creators: Crown,
  religions: Church,
  dominion: Sparkles,
  languages: Languages,
  ground: Mountain,
  soil: Sprout,
  climate: Thermometer,
  land_use: Wheat,
  rainfall: CloudRain,
  danger: ShieldAlert,
  scars: Swords,
  sacred: Sun,
  ley: Sparkles,
  population: Users,
  followers: Flame,
  soldiers: Shield,
  wildlife: Leaf,
  species_range: PawPrint,
  desirability: Building2,
  coverage: Droplets,
  niches: Network,
  solidarity: Shield,
  rings: Wheat,
  centrality: Store,
  nutrients: Sprout,
  networks: Wifi,
}

const OVERLAY_ICON: Record<Overlay, LucideIcon> = {
  roads: Route,
  trade: Coins,
  outbreaks: Biohazard,
  military: Flag,
  faith: Church,
  lore: Ghost,
  beasts: Footprints,
  ties: Waypoints,
  wars: Swords,
  events: Zap,
  labels: Tag,
  fog: CloudFog,
}

export type WorldOption = { id: number; name: string; typeLabel: string }

type MapToolbarProps = {
  mode: LayerMode
  onMode: (mode: LayerMode) => void
  overlays: Record<Overlay, boolean>
  onOverlay: (overlay: Overlay, on: boolean) => void
  worlds: readonly WorldOption[]
  worldId: number
  onWorld: (worldId: number) => void
  legendOpen: boolean
  onLegend: (open: boolean) => void
  noteMode: boolean
  onNoteMode: (on: boolean) => void
  past: boolean
  findable: readonly { id: number; name: string }[]
  onFind: (id: number) => void
  onZoom: (kind: 'in' | 'out' | 'fit') => void
  onRegenerate: () => void
  regenerating: boolean
  mobile: boolean
}

function LayerControls({
  mode,
  onMode,
  overlays,
  onOverlay,
}: Pick<MapToolbarProps, 'mode' | 'onMode' | 'overlays' | 'onOverlay'>) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>Map layer</Label>
      <ToggleGroup
        type='single'
        size='sm'
        variant='outline'
        value={mode}
        aria-label='Map layer'
        className='flex-wrap justify-start'
        onValueChange={(value) => value && onMode(value as LayerMode)}
      >
        {LAYER_MODES.map((option) => {
          const Icon = LAYER_ICON[option]
          return (
            <ToggleGroupItem
              key={option}
              value={option}
              data-surface={LAYER_SURFACE[option]}
            >
              <Icon aria-hidden='true' />
              {LAYER_LABEL[option]}
            </ToggleGroupItem>
          )
        })}
      </ToggleGroup>
      <Label variant='overline'>Overlays</Label>
      <div
        role='group'
        aria-label='Map overlays'
        className='flex min-w-0 flex-wrap items-center gap-2'
      >
        {OVERLAYS.map((overlay) => {
          const Icon = OVERLAY_ICON[overlay]
          return (
            <Toggle
              key={overlay}
              size='sm'
              variant='outline'
              data-surface={OVERLAY_SURFACE[overlay]}
              pressed={overlays[overlay]}
              onPressedChange={(pressed) => onOverlay(overlay, pressed)}
            >
              <Icon aria-hidden='true' />
              {OVERLAY_LABEL[overlay]}
            </Toggle>
          )
        })}
      </div>
    </div>
  )
}

function IconButton({
  label,
  onClick,
  children,
}: {
  label: string
  onClick: () => void
  children: ReactNode
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          size='icon-sm'
          variant='outline'
          aria-label={label}
          onClick={onClick}
        >
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}

export function MapToolbar(props: MapToolbarProps) {
  const {
    worlds,
    worldId,
    onWorld,
    legendOpen,
    onLegend,
    noteMode,
    onNoteMode,
    past,
    mobile,
  } = props
  return (
    <div data-map-toolbar className='flex min-w-0 flex-col gap-2'>
      {!mobile && <LayerControls {...props} />}
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {worlds.length > 1 && (
          <Select
            value={String(worldId)}
            onValueChange={(value) => onWorld(Number(value))}
          >
            <SelectTrigger
              size='sm'
              aria-label='World shown on the map'
              className='max-w-60'
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {worlds.map((world) => (
                <SelectItem key={world.id} value={String(world.id)}>
                  <span className='min-w-0 truncate'>{world.name}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        {mobile && (
          <Sheet>
            <SheetTrigger asChild>
              <Button size='sm' variant='outline'>
                <Layers />
                Layers
              </Button>
            </SheetTrigger>
            <SheetContent side='bottom'>
              <SheetHeader>
                <SheetTitle>Layers</SheetTitle>
                <SheetDescription>
                  Choose what the map colours and which marks it draws.
                </SheetDescription>
              </SheetHeader>
              <div className='flex flex-col gap-3 px-4 pb-6'>
                <Label variant='overline'>Colour by</Label>
                <LayerControls {...props} />
              </div>
            </SheetContent>
          </Sheet>
        )}
        <Toggle
          size='sm'
          variant='outline'
          pressed={legendOpen}
          onPressedChange={onLegend}
        >
          <BookOpen aria-hidden='true' />
          Legend
        </Toggle>
        <Tooltip>
          <TooltipTrigger asChild>
            <span className='inline-flex'>
              <Toggle
                size='sm'
                variant='outline'
                pressed={noteMode}
                disabled={past}
                onPressedChange={onNoteMode}
              >
                <MapPin aria-hidden='true' />
                Note pin
              </Toggle>
            </span>
          </TooltipTrigger>
          <TooltipContent>
            {past
              ? 'Cannot pin notes while looking at the past'
              : 'Click the map, leave a note'}
          </TooltipContent>
        </Tooltip>
        <MapSearch items={props.findable} onFind={props.onFind} />
        <div className='flex items-center gap-1'>
          <IconButton label='Zoom in' onClick={() => props.onZoom('in')}>
            <Plus />
          </IconButton>
          <IconButton label='Zoom out' onClick={() => props.onZoom('out')}>
            <Minus />
          </IconButton>
          <IconButton
            label='Fit the known lands'
            onClick={() => props.onZoom('fit')}
          >
            <Maximize />
          </IconButton>
        </div>
        <Button
          size='sm'
          variant='outline'
          onClick={props.onRegenerate}
          disabled={props.regenerating || past}
          disabledReason={
            past
              ? 'Return to today to redraw the map'
              : 'The map is being redrawn'
          }
        >
          <RefreshCw />
          Redraw map
        </Button>
      </div>
    </div>
  )
}
