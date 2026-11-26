import {
  BookOpen,
  CloudOff,
  HandHeart,
  History,
  Languages,
  MapPin,
  MessagesSquare,
} from 'lucide-react'
import { nodeKindValues } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { HeroFrame, MiniStat, Picture, Portrait } from '@/components/domain'
import { type EntryKind } from '@/components/layout/entry/entryStack'
import { useEntryStack } from '@/components/layout/entry/useEntryStack'
import { Label, Muted, PageTitle } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { useLabels } from '@/features/pantheon/labels'
import { mediaUrl } from '@/features/pantheon/media'
import { DeadSeal } from './DeadSeal'
import { GROUP_LOOK, deathText, statusLabel } from './looks'
import { type SpeakerCard, type SpeakerGroup, type SpeakerView } from './types'

const ENTRY_OF_GROUP: Record<SpeakerGroup, EntryKind> = {
  sons: 'son',
  foreign_gods: 'foreign-god',
  mortals: 'entity',
  spirits: 'entity',
  beings: 'entity',
  beasts: 'entity',
}

const PORTRAIT_WIDTH = 640

export const STAGE_ID = 'presence-stage'

function StagePortrait({ card }: { card: SpeakerCard }) {
  return (
    <div
      data-domain='presence-portrait'
      data-dead={card.dead || undefined}
      className='relative flex shrink-0 flex-col items-center gap-2 self-center sm:self-start'
    >
      <Picture
        src={mediaUrl(card.cover, PORTRAIT_WIDTH)}
        alt={`Likeness of ${card.name}`}
        className={cn(
          'gilded-portrait aspect-square size-portrait-2xl rounded-lg object-cover',
          card.dead && 'grayscale'
        )}
        fallback={<Portrait name={card.name} size='xl' shape='square' />}
      />
      {card.dead && <DeadSeal death={deathText(card)} />}
    </div>
  )
}

function whereOf(card: SpeakerCard): string {
  return (
    [card.place_name, card.world_name].filter(Boolean).join(', ') ||
    'Nowhere known'
  )
}

function FaithStat({ card }: { card: SpeakerCard }) {
  if (card.faith !== null)
    return (
      <MiniStat
        icon={HandHeart}
        tone='gold'
        label='Faith it holds'
        value={formatInteger(card.faith)}
      />
    )
  return (
    <MiniStat
      icon={HandHeart}
      tone='gold'
      label='God it follows'
      value={card.patron_name || 'No patron god'}
    />
  )
}

export function PresenceStage({ view }: { view: SpeakerView }) {
  const card = view.card
  const stack = useEntryStack()
  const { entityType } = useLabels()
  const group = GROUP_LOOK[card.group]
  const GroupIcon = group.icon
  const kindLabel = card.entity_type
    ? entityType(card.entity_type)
    : wordOf(nodeKindValues, card.kind)
  const pastCount = view.past_sessions.length
  return (
    <HeroFrame>
      <header
        id={STAGE_ID}
        data-domain='presence-stage'
        className='flex min-w-0 flex-col gap-5 sm:flex-row sm:items-start'
      >
        <StagePortrait card={card} />
        <div className='flex min-w-0 flex-1 flex-col gap-3'>
          <div className='flex min-w-0 flex-col gap-1'>
            <Label
              variant='overline'
              className='flex min-w-0 items-center gap-1.5'
            >
              <GroupIcon aria-hidden='true' className='size-icon-xs' />
              {`${group.label} · ${kindLabel}`}
            </Label>
            <PageTitle truncate={2} className='text-gilded'>
              {card.dead ? `† ${card.name}` : card.name}
            </PageTitle>
            {card.epithet && <Muted>{card.epithet}</Muted>}
          </div>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Badge size='sm' variant={card.dead ? 'destructive' : 'success'}>
              {statusLabel(card)}
            </Badge>
            {card.dead && <DeadSeal size='sm' death={deathText(card)} />}
            {view.open_session && (
              <Badge size='sm' variant='default'>
                <MessagesSquare />
                In audience with you
              </Badge>
            )}
            <Badge size='sm' variant={card.can_act ? 'info' : 'outline'}>
              {card.can_act ? 'Can act on the record' : 'Reads the world only'}
            </Badge>
            {!view.model_enabled && (
              <Badge size='sm' variant='warning'>
                <CloudOff />
                No conversation model
              </Badge>
            )}
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            <MiniStat
              icon={MapPin}
              tone='info'
              label='Where it is'
              value={whereOf(card)}
            />
            <FaithStat card={card} />
            <MiniStat
              icon={Languages}
              tone='verdigris'
              label='Tongues it speaks'
              value={
                card.languages.length > 0
                  ? card.languages.join(', ')
                  : 'No tongue known'
              }
            />
            <MiniStat
              icon={History}
              tone='muted'
              label='Audiences kept'
              value={
                pastCount === 0 ? 'None yet' : plural(pastCount, 'audience')
              }
            />
          </div>
          {card.dead && card.death_line && (
            <Muted variant='caption'>{card.death_line}</Muted>
          )}
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              variant='outline'
              size='sm'
              onClick={() =>
                void stack.open({
                  kind: ENTRY_OF_GROUP[card.group],
                  id: String(card.node_id),
                })
              }
            >
              <BookOpen />
              Open its entry
            </Button>
          </div>
        </div>
      </header>
    </HeroFrame>
  )
}
