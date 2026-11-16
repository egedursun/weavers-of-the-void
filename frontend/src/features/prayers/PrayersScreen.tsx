import { useMemo, useState } from 'react'
import { navItem } from '@/config/navigation'
import {
  CircleCheck,
  Crown,
  Globe,
  HandHeart,
  HandHelping,
  HeartHandshake,
  Hourglass,
  KeyRound,
  type LucideIcon,
  Quote,
  Sparkles,
  Star,
  Sun,
  Swords,
  User,
  Users,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  PagedList,
  PageHeader,
  Portrait,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { PRAYER_TONES } from '@/features/dominion/labels'
import { NamedRecord } from '@/features/entity/NamedRecord'
import {
  type SonPublic,
  useNames,
  useSons,
  useWorldState,
} from '@/features/pantheon/api'
import { mediaUrl } from '@/features/pantheon/media'
import { PrayerAnswerForm } from './PrayerAnswerForm'
import {
  type PrayerRequest,
  type PrayerView,
  WISH_LABEL,
  usePrayers,
} from './api'

const ITEM = navItem('prayers')
const ALL_WORLDS = 'all'

type Filter = 'all' | 'awaiting' | 'sons' | 'mortals'

const FILTERS: { key: Filter; label: string; icon: LucideIcon }[] = [
  { key: 'all', label: 'All', icon: HandHeart },
  { key: 'awaiting', label: 'Awaiting answer', icon: Hourglass },
  { key: 'sons', label: 'Sons', icon: Crown },
  { key: 'mortals', label: 'Mortals', icon: Users },
]

const WISH_ICON: Record<PrayerRequest, LucideIcon> = {
  essence: Sparkles,
  blessing: Sun,
  permission: KeyRound,
  vengeance: Swords,
  forgiveness: HeartHandshake,
  wish: Star,
  none: HandHeart,
}

function matchesFilter(prayer: PrayerView, filter: Filter): boolean {
  if (filter === 'awaiting') return !prayer.message.answered
  if (filter === 'sons') return prayer.sender?.kind === 'son'
  if (filter === 'mortals') return prayer.sender?.kind === 'entity'
  return true
}

function PrayerCard({
  prayer,
  worldName,
  son,
}: {
  prayer: PrayerView
  worldName: string | null
  son: SonPublic | undefined
}) {
  const message = prayer.message
  const sender = prayer.sender
  const mortal = sender?.kind === 'entity'
  const wish = message.request ? WISH_LABEL[message.request] : null
  const tone = message.tone ? PRAYER_TONES[message.tone] : null
  const WishIcon = message.request ? WISH_ICON[message.request] : HandHeart
  return (
    <Card
      data-prayer={message.id}
      className={cn(message.answered ? 'opacity-80' : 'border-warning/40')}
    >
      <CardHeader>
        <div className='flex min-w-0 items-start gap-3'>
          <Portrait
            name={sender?.name ?? '?'}
            src={mediaUrl(prayer.sender_cover ?? son?.cover)}
            size='md'
            rarity={son?.son.rarity}
          />
          <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              {sender ? (
                <EntityLink
                  kind={mortal ? 'entity' : 'son'}
                  id={String(sender.id)}
                  rarity={son?.son.rarity}
                >
                  {sender.name}
                </EntityLink>
              ) : (
                <Text as='span'>Someone unknown</Text>
              )}
              <Badge size='sm' variant={mortal ? 'info' : 'default'}>
                {mortal ? <User /> : <Crown />}
                {mortal ? 'Mortal prayer' : 'Son'}
              </Badge>
            </div>
            <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
              <Badge
                size='sm'
                variant='outline'
              >{`Epoch ${message.epoch}`}</Badge>
              <Muted as='span' variant='caption'>
                {'To '}
                <NamedRecord id={message.recipient_node_id} fallback='you' />
              </Muted>
              {worldName && (
                <Badge size='sm' variant='outline'>
                  <Globe />
                  {worldName}
                </Badge>
              )}
              {wish && (
                <Badge size='sm' variant='outline'>
                  <WishIcon />
                  {`Wishes: ${message.wish ?? wish}`}
                </Badge>
              )}
              {tone && (
                <Badge size='sm' variant='outline'>
                  <tone.icon />
                  {tone.label}
                </Badge>
              )}
            </div>
          </div>
          {message.answered ? (
            <Badge size='sm' variant='success'>
              <CircleCheck />
              {[
                message.answered_epoch !== null
                  ? `Answered in epoch ${message.answered_epoch}`
                  : 'Answered',
                message.answer_essence
                  ? `${message.answer_essence} essence`
                  : null,
              ]
                .filter(Boolean)
                .join(' · ')}
            </Badge>
          ) : (
            <Badge size='sm' variant='warning'>
              <Hourglass />
              Awaiting
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className='flex flex-col gap-4'>
        <div className='flex min-w-0 items-start gap-2 rounded-md rounded-tl-sm border surface-well border-gild/20 bg-muted/60 p-3'>
          <Quote
            aria-hidden='true'
            className='size-icon-sm shrink-0 text-primary'
          />
          <Text as='blockquote' variant='prose' italic>
            {message.text}
          </Text>
        </div>
        {!message.answered && (
          <PrayerAnswerForm messageId={message.id} mortal={mortal} />
        )}
      </CardContent>
    </Card>
  )
}

export function PrayersScreen() {
  const prayers = usePrayers()
  const state = useWorldState()
  const sons = useSons()
  const names = useNames()
  const [filter, setFilter] = useState<Filter>('all')
  const [worldId, setWorldId] = useState(ALL_WORLDS)
  const worlds = state.data?.worlds ?? []
  const worldOf = useMemo(() => {
    const map = new Map<string, number | null>()
    for (const view of sons.data ?? [])
      map.set(`son:${view.son.id}`, view.son.current_world_id)
    for (const entry of names.data ?? [])
      if (entry.kind === 'entity')
        map.set(`entity:${entry.id}`, entry.world_id ?? null)
    return map
  }, [sons.data, names.data])
  const worldName = (prayer: PrayerView) => {
    if (worlds.length < 2 || !prayer.sender) return null
    const id = worldOf.get(`${prayer.sender.kind}:${prayer.sender.id}`)
    return worlds.find((world) => world.id === id)?.name ?? null
  }
  const inWorld = (prayer: PrayerView) =>
    worldId === ALL_WORLDS ||
    (prayer.sender !== null &&
      worldOf.get(`${prayer.sender.kind}:${prayer.sender.id}`) ===
        Number(worldId))
  const list = (prayers.data ?? []).filter(inWorld)
  const shown = list.filter((prayer) => matchesFilter(prayer, filter))
  const awaiting = list.filter((prayer) => !prayer.message.answered).length
  const selectedWorld = worlds.find((world) => String(world.id) === worldId)
  const answered = list.length - awaiting
  const fromSons = list.filter((prayer) => prayer.sender?.kind === 'son').length
  const gifted = list.reduce(
    (sum, prayer) => sum + (prayer.message.answer_essence ?? 0),
    0
  )
  const sonOf = (prayer: PrayerView) =>
    prayer.sender?.kind === 'son'
      ? sons.data?.find((view) => view.son.id === prayer.sender?.id)
      : undefined
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <PageHeader
        title={ITEM.title}
        description='Your sons and the mortals pray to you. Sons hear your answer on their next turn; to mortals it descends as a dream, blesses them and binds them to a cult of you. Gifting essence raises loyalty and faith.'
        icon={ITEM.icon}
        meta={
          <>
            {awaiting > 0 && (
              <Badge variant='warning'>{`${plural(awaiting, 'prayer', 'prayers')} await an answer`}</Badge>
            )}
            {selectedWorld && (
              <Badge variant='outline'>{`Showing ${selectedWorld.name}`}</Badge>
            )}
          </>
        }
      />
      {list.length > 0 && (
        <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4'>
          <KpiTile
            label='Awaiting'
            icon={HandHelping}
            tone={awaiting > 0 ? 'warning' : 'success'}
            value={awaiting}
            hint={
              awaiting > 0
                ? 'Unanswered prayers erode love and faith'
                : 'Every prayer has an answer'
            }
          />
          <KpiTile
            label='Answered'
            icon={CircleCheck}
            tone='success'
            value={answered}
            meter={{
              value: answered,
              max: list.length,
              label: 'Answered share',
            }}
          />
          <KpiTile
            label='Senders'
            icon={Users}
            tone='info'
            value={`${fromSons} / ${list.length - fromSons}`}
            hint='Sons / mortals'
          />
          <KpiTile
            label='Essence given'
            icon={Sparkles}
            tone='verdigris'
            value={gifted}
          />
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <ToggleGroup
          type='single'
          variant='outline'
          className='flex-wrap'
          value={filter}
          onValueChange={(value) => value && setFilter(value as Filter)}
        >
          {FILTERS.map((item) => (
            <ToggleGroupItem key={item.key} value={item.key}>
              <item.icon aria-hidden='true' />
              {`${item.label} · ${list.filter((prayer) => matchesFilter(prayer, item.key)).length}`}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        {worlds.length > 1 && (
          <Select value={worldId} onValueChange={setWorldId}>
            <SelectTrigger aria-label='World' className='w-56'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_WORLDS}>Whole cosmos</SelectItem>
              {worlds.map((world) => (
                <SelectItem key={world.id} value={String(world.id)}>
                  {world.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
      {prayers.isPending ? (
        <div className='flex flex-col gap-3'>
          <Skeleton className='h-textarea w-full' />
          <Skeleton className='h-textarea w-full' />
        </div>
      ) : prayers.isError ? (
        <Alert variant='destructive'>
          <HandHeart />
          <AlertTitle>Prayers could not be read</AlertTitle>
          <AlertDescription>{prayers.error.message}</AlertDescription>
        </Alert>
      ) : shown.length === 0 ? (
        <EmptyState
          icon={HandHeart}
          title={
            list.length === 0
              ? 'No prayers yet'
              : 'No prayer matches this filter'
          }
          description={
            list.length === 0
              ? 'They appear here when your sons or mortals wish for something.'
              : 'Pick another filter or world.'
          }
        />
      ) : (
        <PagedList
          items={shown}
          initial={10}
          noun={['prayer', 'prayers']}
          as='div'
          className='flex min-w-0 flex-col gap-4'
          itemKey={(prayer) => prayer.message.id}
        >
          {(prayer) => (
            <PrayerCard
              prayer={prayer}
              worldName={worldName(prayer)}
              son={sonOf(prayer)}
            />
          )}
        </PagedList>
      )}
    </div>
  )
}
