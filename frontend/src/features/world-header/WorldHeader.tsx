import { useState } from 'react'
import {
  CalendarClock,
  ChevronsUpDown,
  CloudFog,
  Feather,
  Flame,
  HandHelping,
  HeartCrack,
  type LucideIcon,
  Smile,
  SunMoon,
  Thermometer,
  Zap,
} from 'lucide-react'
import { useUniverseId } from '@/api/universeStore'
import { plural } from '@/lib/units'
import { useIsMobile } from '@/hooks/useIsMobile'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { type KpiTone, Portrait } from '@/components/domain'
import { useEntryStack } from '@/components/layout/entry/useEntryStack'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { RulingSkyList } from '@/features/cosmos/RulingSkyList'
import { useCosmos } from '@/features/cosmos/api'
import { CLIMATE_LABEL } from '@/features/cosmos/model/labels'
import { RevelationDialog } from '@/features/creator/RevelationDialog'
import { SummonButton } from '@/features/pantheon/SummonButton'
import { useWorldState } from '@/features/pantheon/api'
import { MOOD_LABEL } from '@/features/pantheon/labels'
import { mediaUrl } from '@/features/pantheon/media'
import { useUniverse } from '@/features/universes/api'
import { CreateHub } from './CreateHub'
import { DoomChip } from './DoomChip'
import { EssenceChip } from './EssenceChip'
import { HudChip, HudLink } from './HudChip'
import { useEpochStar } from './api'

const HEADER_GHOSTS = ['w-32', 'w-28', 'w-24', 'w-36', 'w-24', 'w-28']

function StarChips() {
  const star = useEpochStar()
  const current = star.data?.current ?? []
  const ruled = current.filter((entry) => entry.star !== null)
  if (ruled.length === 0) return null
  const only = ruled.length === 1 ? ruled[0].star : null
  return (
    <Popover>
      <PopoverTrigger asChild>
        <HudChip
          icon={SunMoon}
          tone='warning'
          label={only ? 'Ruling sky' : 'Ruling skies'}
          data-world-star
          aria-label='The bodies that rule the sky of each world this epoch'
        >
          {only ? only.name : `${plural(ruled.length, 'world', 'worlds')}`}
        </HudChip>
      </PopoverTrigger>
      <PopoverContent
        align='start'
        className='flex w-96 min-w-0 flex-col gap-3'
      >
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Label variant='overline'>Ruling skies of the epoch</Label>
          <Muted variant='caption'>
            Every epoch one celestial body rules the sky of each world: a star,
            a moon, a comet or stranger things.
          </Muted>
        </div>
        <RulingSkyList entries={current} />
      </PopoverContent>
    </Popover>
  )
}

type MoodKey = keyof typeof MOOD_LABEL

const MOOD_ICON: Record<MoodKey, LucideIcon> = {
  angry: Flame,
  distant: CloudFog,
  lonely: HeartCrack,
  content: Smile,
  uneasy: Zap,
  serene: Feather,
}

const MOOD_TONE: Record<MoodKey, KpiTone> = {
  angry: 'danger',
  distant: 'muted',
  lonely: 'info',
  content: 'gold',
  uneasy: 'warning',
  serene: 'success',
}

function climateNote(epochsLeft: number | null): string {
  return epochsLeft === null
    ? 'Lasts until it is changed'
    : `${plural(epochsLeft, 'epoch')} left`
}

function ClimateChips() {
  const cosmos = useCosmos()
  const active = (cosmos.data?.worlds ?? [])
    .map((item) => item.world)
    .filter(
      (world) =>
        world.climate_era &&
        world.discovery !== 'forgotten' &&
        world.climate_era !== 'temperate'
    )
  if (active.length === 0) return null
  if (active.length === 1 && active[0].climate_era)
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <HudChip icon={Thermometer} tone='info' data-world-climate>
            {CLIMATE_LABEL[active[0].climate_era]}
          </HudChip>
        </TooltipTrigger>
        <TooltipContent>
          {climateNote(active[0].climate_epochs_left)}
        </TooltipContent>
      </Tooltip>
    )
  return (
    <Popover>
      <PopoverTrigger asChild>
        <HudChip
          icon={Thermometer}
          tone='info'
          data-world-climate
          aria-label='Climates of the worlds'
        >
          {`${plural(active.length, 'climate', 'climates')}`}
        </HudChip>
      </PopoverTrigger>
      <PopoverContent align='start' className='flex w-80 flex-col gap-2'>
        {active.map((world) =>
          world.climate_era ? (
            <div
              key={world.id}
              className='flex min-w-0 items-center justify-between gap-3'
            >
              <Muted truncate>{world.name}</Muted>
              <Text as='span' truncate>
                {`${CLIMATE_LABEL[world.climate_era]} · ${climateNote(world.climate_epochs_left)}`}
              </Text>
            </div>
          ) : null
        )}
      </PopoverContent>
    </Popover>
  )
}

export function WorldHeader() {
  const state = useWorldState()
  const universe = useUniverse(useUniverseId())
  const { open } = useEntryStack()
  const mobile = useIsMobile()
  const [expanded, setExpanded] = useState<boolean | null>(null)
  const shown = expanded ?? !mobile
  if (state.isPending)
    return (
      <div
        data-layout='world-header'
        className='flex min-w-0 items-center gap-3 border-b px-3 py-2 md:px-4'
      >
        <Skeleton className='size-control-lg shrink-0 rounded-full' />
        <div className='flex min-w-0 flex-1 flex-wrap items-center gap-2'>
          {HEADER_GHOSTS.map((width, index) => (
            <Skeleton key={index} className={`h-control-sm ${width}`} />
          ))}
        </div>
        <Skeleton className='h-control-sm w-24 shrink-0' />
      </div>
    )
  const data = state.data
  const world = data?.world
  if (!data || !world) return null
  const title = universe.data?.name ?? world.name
  const mood = data.mood
  const prayers = data.prayers_pending
  return (
    <div
      data-layout='world-header'
      className='@container/header flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2 border-b bg-linear-to-r from-primary/6 via-background to-background px-3 py-2 md:px-4'
    >
      <div className='flex min-w-0 flex-1 basis-56 items-center gap-2.5 @5xl/header:max-w-sm @5xl/header:flex-none'>
        <Portrait name={title} src={mediaUrl(data.world_cover)} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text
            as='span'
            weight='semibold'
            truncate
            title={title}
            className='font-display'
          >
            {title}
          </Text>
          <Muted as='span' variant='caption' truncate title={world.seed_idea}>
            {world.seed_idea}
          </Muted>
        </div>
        {mobile && (
          <Button
            variant='ghost'
            size='icon'
            aria-expanded={shown}
            aria-label={shown ? 'Hide world status' : 'Show world status'}
            onClick={() => setExpanded(!shown)}
          >
            <ChevronsUpDown />
          </Button>
        )}
      </div>
      {shown && (
        <div
          data-layout='world-hud'
          className='flex min-w-0 flex-1 basis-3xl flex-wrap items-center gap-1.5'
        >
          <HudLink
            to='/epoch'
            icon={CalendarClock}
            tone='gold'
            label='Epoch'
            aria-label={`Epoch ${world.epoch}, year ${world.epoch_start_year}`}
          >
            <Stat value={world.epoch} />
            <Muted as='span' variant='caption'>
              {`Year ${world.epoch_start_year}`}
            </Muted>
            {data.epoch_running && (
              <Badge size='sm' variant='default'>
                Running
              </Badge>
            )}
          </HudLink>
          <EssenceChip state={data} />
          <DoomChip state={data} />
          <StarChips />
          <ClimateChips />
          {mood && (
            <Tooltip>
              <TooltipTrigger asChild>
                <HudChip
                  icon={MOOD_ICON[mood.label]}
                  tone={MOOD_TONE[mood.label]}
                  label='Creator'
                  onClick={() => open({ kind: 'creator' })}
                  aria-label={`Creator mood ${MOOD_LABEL[mood.label]}, open the creator`}
                >
                  {MOOD_LABEL[mood.label]}
                </HudChip>
              </TooltipTrigger>
              <TooltipContent>
                {`Anger ${mood.anger} · Contentment ${mood.contentment} · Interest ${mood.interest} · Loneliness ${mood.loneliness}`}
              </TooltipContent>
            </Tooltip>
          )}
          <HudLink
            to='/prayers'
            icon={HandHelping}
            tone={prayers > 0 ? 'gold' : 'muted'}
            label='Prayers'
            aria-label={`${plural(prayers, 'prayer', 'prayers')} awaiting an answer`}
            data-prayers-badge
          >
            {prayers > 0 ? (
              <Badge size='sm' variant='solid'>
                {prayers}
              </Badge>
            ) : (
              <Stat value={prayers} />
            )}
          </HudLink>
        </div>
      )}
      {shown && (
        <div className='ms-auto flex shrink-0 flex-wrap items-center justify-end gap-2'>
          <RevelationDialog triggerLabel='Reveal' triggerSize='sm' />
          <CreateHub />
          <SummonButton size='sm' />
        </div>
      )}
    </div>
  )
}
