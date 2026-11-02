import { useId, useState } from 'react'
import {
  Box,
  Crosshair,
  Globe2,
  Group,
  Link2,
  RotateCcw,
  Settings2,
  Square,
  Waypoints,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Toggle } from '@/components/ui/toggle'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Label, Muted } from '@/components/typography'
import { MapSearch } from '@/features/map/MapSearch'
import { type LinkGroup, type LinkGroupInfo } from './api'
import { type GraphMode, RADII } from './graphModel'

const ALL_WORLDS = 'all'
const WHOLE = 'whole'

type GraphToolbarProps = {
  mode: GraphMode
  onMode: (mode: GraphMode) => void
  findable: readonly { id: number; name: string }[]
  onFind: (id: number) => void
  group: LinkGroup
  groups: readonly LinkGroupInfo[]
  onGroup: (group: LinkGroup) => void
  radius: number
  onRadius: (radius: number) => void
  shownRadius: number
  reduced: boolean
  cap: number
  ruleCap: number
  capOverridden: boolean
  total: number
  onCap: (cap: number | null) => void
  worlds: readonly { id: number; name: string }[]
  worldId: number | null
  onWorld: (id: number | null) => void
  cluster: boolean
  onCluster: (on: boolean) => void
  focusName: string | null
  automaticFocus: boolean
  whole: boolean
  onWhole: (whole: boolean) => void
}

export function GraphToolbar(props: GraphToolbarProps) {
  const multiWorld = props.worlds.length > 1
  const limitId = useId()
  const [draft, setDraft] = useState(String(props.cap))
  const [shownCap, setShownCap] = useState(props.cap)
  if (shownCap !== props.cap) {
    setShownCap(props.cap)
    setDraft(String(props.cap))
  }
  const commit = () => {
    const value = Math.round(Number(draft))
    if (!Number.isFinite(value) || value < 1) {
      setDraft(String(props.cap))
      return
    }
    props.onCap(value === props.ruleCap ? null : value)
  }
  return (
    <div
      data-graph-toolbar
      className='flex min-w-0 flex-wrap items-center gap-2'
    >
      <ToggleGroup
        type='single'
        size='sm'
        variant='outline'
        value={props.mode}
        aria-label='View'
        onValueChange={(value) => value && props.onMode(value as GraphMode)}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <ToggleGroupItem value='2d'>
              <Square />
              2D
            </ToggleGroupItem>
          </TooltipTrigger>
          <TooltipContent>Flat, top-down view</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <ToggleGroupItem value='3d'>
              <Box />
              3D
            </ToggleGroupItem>
          </TooltipTrigger>
          <TooltipContent>
            Three-dimensional, rotatable and navigable
          </TooltipContent>
        </Tooltip>
      </ToggleGroup>
      <MapSearch
        items={props.findable}
        onFind={props.onFind}
        placeholder='Search a node and focus…'
        missing='No such node in the network.'
        label='Search a node and focus'
      />
      <Select
        value={props.group}
        onValueChange={(value) => props.onGroup(value as LinkGroup)}
      >
        <SelectTrigger size='sm' aria-label='Links shown' className='max-w-64'>
          <Link2 />
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {props.groups.map((group) => (
            <SelectItem key={group.key} value={group.key}>
              {group.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {multiWorld && (
        <Select
          value={props.worldId === null ? ALL_WORLDS : String(props.worldId)}
          onValueChange={(value) =>
            props.onWorld(value === ALL_WORLDS ? null : Number(value))
          }
        >
          <SelectTrigger size='sm' aria-label='World' className='max-w-60'>
            <Globe2 />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_WORLDS}>Whole cosmos</SelectItem>
            {props.worlds.map((world) => (
              <SelectItem key={world.id} value={String(world.id)}>
                <span className='min-w-0 truncate'>{world.name}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
      {multiWorld && (
        <Toggle
          size='sm'
          variant='outline'
          pressed={props.cluster}
          onPressedChange={props.onCluster}
        >
          <Group />
          Cluster by world
        </Toggle>
      )}
      <div className='flex min-w-0 items-center gap-1.5'>
        <Label as='span' variant='overline'>
          Depth
        </Label>
        <ToggleGroup
          type='single'
          size='sm'
          variant='outline'
          value={props.whole ? WHOLE : String(props.radius)}
          aria-label='How many steps around the focus'
          onValueChange={(value) => {
            if (!value) return
            if (value === WHOLE) {
              props.onWhole(true)
              return
            }
            props.onRadius(Number(value))
            if (props.whole) props.onWhole(false)
          }}
        >
          {RADII.map((radius) => (
            <Tooltip key={radius}>
              <TooltipTrigger asChild>
                <ToggleGroupItem
                  value={String(radius)}
                  aria-label={`${radius} ${radius === 1 ? 'step' : 'steps'} around the focus`}
                >
                  {radius}
                </ToggleGroupItem>
              </TooltipTrigger>
              <TooltipContent>{`Records up to ${radius} ${radius === 1 ? 'bond' : 'bonds'} away from the focus`}</TooltipContent>
            </Tooltip>
          ))}
          <Tooltip>
            <TooltipTrigger asChild>
              <ToggleGroupItem value={WHOLE} aria-label='The whole network'>
                <Waypoints />
                All
              </ToggleGroupItem>
            </TooltipTrigger>
            <TooltipContent>
              Every record and bond, with no limit
            </TooltipContent>
          </Tooltip>
        </ToggleGroup>
      </div>
      {!props.whole && (
        <div className='flex min-w-0 items-center gap-1.5'>
          <Label as='label' variant='overline' htmlFor={limitId}>
            Up to
          </Label>
          <Input
            id={limitId}
            type='number'
            inputMode='numeric'
            min={1}
            max={props.total}
            step={1}
            value={draft}
            aria-label='Most records shown around the focus'
            className='w-24'
            onChange={(event) => setDraft(event.target.value)}
            onBlur={commit}
            onKeyDown={(event) => {
              if (event.key === 'Enter') commit()
            }}
          />
          <Muted as='span' variant='caption'>
            records
          </Muted>
          {props.capOverridden && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size='icon-sm'
                  variant='ghost'
                  aria-label={`Back to the world rule (${props.ruleCap.toLocaleString('en-US')})`}
                  onClick={() => props.onCap(null)}
                >
                  <RotateCcw />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{`Back to the world rule: ${props.ruleCap.toLocaleString('en-US')} records (World rules › Interface › Graph)`}</TooltipContent>
            </Tooltip>
          )}
        </div>
      )}
      {props.reduced && !props.whole && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant='warning'>
              <Settings2 aria-hidden='true' />
              {`${props.radius} steps would pass ${props.cap.toLocaleString('en-US')}; showing ${props.shownRadius}`}
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            Raise “Up to” or choose All to see further.
          </TooltipContent>
        </Tooltip>
      )}
      {props.focusName !== null && !props.whole && (
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant='outline' className='max-w-60'>
              <Crosshair aria-hidden='true' />
              <span className='min-w-0 truncate'>
                {props.automaticFocus
                  ? `${props.focusName} · focus`
                  : props.focusName}
              </span>
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            {props.automaticFocus
              ? 'Automatically chosen focus: the most connected record. Search a node to focus elsewhere.'
              : 'Your chosen focus'}
          </TooltipContent>
        </Tooltip>
      )}
    </div>
  )
}
