import { Link } from '@tanstack/react-router'
import {
  BookOpenText,
  CalendarClock,
  Crown,
  Globe,
  HandHelping,
  Hourglass,
  Skull,
  Sparkles,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { EntityLink, KpiTile, Portrait, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { EpochStarChip } from '@/features/cosmos/EpochStarChip'
import { useRuleLookup } from '@/features/pantheon/gate'
import { mediaUrl } from '@/features/pantheon/media'
import { type WorldState, useEpochStatistics } from './api'

const MOOD_LABEL: Record<string, string> = {
  angry: 'Angry',
  distant: 'Distant and silent',
  lonely: 'Lonely',
  content: 'Pleased',
  uneasy: 'Restless',
  serene: 'Calm',
}

const LORE_LANGUAGE_LABEL: Record<string, string> = {
  english: 'English',
  turkish: 'Turkish',
}

const COVER_WIDTH = 320

type WorldSummaryProps = {
  state: WorldState
}

export function WorldSummary({ state }: WorldSummaryProps) {
  const rule = useRuleLookup()
  const doomLimit = rule('balance.apocalypse_threshold')
  const stats = useEpochStatistics(true)
  const world = state.world
  if (!world) return null
  const records = Object.values(state.counts).reduce(
    (sum, value) => sum + value,
    0
  )
  const activeSons = state.sons.filter(
    (item) => item.son.status === 'active'
  ).length
  const mood = state.mood
  const series = stats.data ?? []
  const closed = series.filter((item) => !item.live)
  const previous = closed.length > 0 ? closed[closed.length - 1].data : null
  const doomChange = previous ? world.doom_clock - previous.doom : undefined
  return (
    <Section
      title={world.name}
      surface='card'
      actions={
        <>
          <EpochStarChip />
          <Badge variant='outline'>
            {`Lore in ${LORE_LANGUAGE_LABEL[world.lore_language] ?? world.lore_language}`}
          </Badge>
          {world.fate_debt_epoch !== null && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge variant='warning' tabIndex={0}>
                  {`Fate in debt since epoch ${world.fate_debt_epoch}`}
                </Badge>
              </TooltipTrigger>
              <TooltipContent className='max-w-xs'>
                Fate could not weigh that epoch; everything created since is
                weighed together at the end of the next epoch.
              </TooltipContent>
            </Tooltip>
          )}
          {mood && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge
                  variant={mood.label === 'angry' ? 'destructive' : 'secondary'}
                  tabIndex={0}
                >
                  {MOOD_LABEL[mood.label] ?? mood.label}
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                {`Anger ${mood.anger} · Contentment ${mood.contentment} · Interest ${mood.interest} · Loneliness ${mood.loneliness}`}
              </TooltipContent>
            </Tooltip>
          )}
        </>
      }
    >
      <div className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center'>
        <Portrait
          name={world.name}
          src={mediaUrl(state.world_cover, COVER_WIDTH)}
          size='xl'
          shape='square'
        />
        <div className='flex min-w-0 flex-1 flex-col gap-3'>
          <Text variant='prose' italic>
            {world.seed_idea}
          </Text>
          {state.creator && (
            <div className='flex min-w-0 items-center gap-2.5'>
              <Portrait
                name={state.creator.name}
                src={mediaUrl(state.creator_cover)}
                size='sm'
              />
              <div className='flex min-w-0 flex-col'>
                <Muted as='span' variant='caption'>
                  Watched over by
                </Muted>
                <EntityLink kind='creator' showIcon>
                  {state.creator.name}
                </EntityLink>
              </div>
            </div>
          )}
        </div>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4'>
        <KpiTile
          label='Epoch'
          value={world.epoch}
          icon={Hourglass}
          tone='gold'
          hint={
            state.last_epoch?.name
              ? `After ${state.last_epoch.name}`
              : 'The first age'
          }
        />
        <KpiTile
          label='Year'
          value={world.epoch_start_year}
          icon={CalendarClock}
          tone='verdigris'
          hint='Since the first light'
        />
        <KpiTile
          label='Divine essence'
          value={state.creator?.essence ?? 0}
          icon={Sparkles}
          tone='gold'
          hint='Refills every epoch'
        />
        <KpiTile
          label='Doom clock'
          value={world.doom_clock}
          icon={Skull}
          tone={world.doom_clock > 0 ? 'danger' : 'muted'}
          change={doomChange}
          harmful
          meter={
            doomLimit
              ? {
                  value: world.doom_clock,
                  max: doomLimit,
                  label: `Doom clock ${world.doom_clock} of ${doomLimit}`,
                }
              : undefined
          }
          hint={doomLimit ? `The end comes at ${doomLimit}` : undefined}
        />
        <KpiTile
          label='Sons'
          value={activeSons}
          icon={Crown}
          tone='info'
          hint={
            state.pending_son_ids.length > 0
              ? `${state.pending_son_ids.length} still to act`
              : 'Everyone has acted'
          }
        />
        <KpiTile
          label='Records'
          value={records}
          icon={BookOpenText}
          tone='verdigris'
          hint='Living lore of every kind'
        />
        <KpiTile
          label='Worlds'
          value={state.worlds.length}
          icon={Globe}
          tone='info'
          hint={`${state.foreign_god_count} foreign gods watch`}
        />
        <KpiTile
          label='Prayers awaiting'
          value={state.prayers_pending}
          icon={HandHelping}
          tone={state.prayers_pending > 0 ? 'warning' : 'muted'}
          hint={
            state.prayers_pending > 0
              ? 'Your faithful are waiting'
              : 'All answered'
          }
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2'>
        <Text as='span' weight='medium'>
          <Link
            to='/notifications'
            className='text-primary underline-offset-4 hover:underline'
          >
            {`${state.notifications_unread} unread notifications`}
          </Link>
        </Text>
        <Muted as='span'>{`${plural(state.promptless_count, 'record', 'records')} without an image prompt`}</Muted>
      </div>
    </Section>
  )
}
