import {
  ChevronDown,
  CircleCheck,
  CircleX,
  Crown,
  Gavel,
  type LucideIcon,
  Minus,
  ScrollText,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  EntityLink,
  Medallion,
  Paged,
  PagedList,
  Portrait,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { MOTIONS, type Named } from '@/features/divine/labels'
import { type SonPublic, useSons } from '@/features/pantheon/api'
import { mediaUrl } from '@/features/pantheon/media'
import { CouncilRecordControls } from './CouncilRecordControls'
import { type CouncilRecord as Council, type CouncilVote } from './api'

const VOTE_LABEL: Record<CouncilVote, string> = {
  yes: 'Yes',
  no: 'No',
  abstain: 'Abstain',
}

const VOTE_ICON: Record<CouncilVote, LucideIcon> = {
  yes: ThumbsUp,
  no: ThumbsDown,
  abstain: Minus,
}

const VOTE_BADGE: Record<CouncilVote, 'success' | 'destructive' | 'outline'> = {
  yes: 'success',
  no: 'destructive',
  abstain: 'outline',
}

const VOTE_RING: Record<CouncilVote, string> = {
  yes: 'ring-success',
  no: 'ring-destructive',
  abstain: 'ring-border',
}

const VOTE_ORDER: readonly CouncilVote[] = ['yes', 'abstain', 'no']

const PERCENT = 100

function VoteBadge({ vote }: { vote: CouncilVote }) {
  const Icon = VOTE_ICON[vote]
  return (
    <Badge size='sm' variant={VOTE_BADGE[vote]}>
      <Icon />
      {VOTE_LABEL[vote]}
    </Badge>
  )
}

function DecisionBadge({ decision }: { decision: Named }) {
  const Icon = decision.icon
  return (
    <Badge variant='outline' className='self-start'>
      <Icon />
      {decision.label}
    </Badge>
  )
}

function BallotDots({
  ballots,
  sonOf,
}: {
  ballots: Council['minutes']['ballots']
  sonOf: (sonId: number) => SonPublic | undefined
}) {
  return (
    <PagedList
      items={ballots}
      initial={12}
      noun={['entry', 'entries']}
      as='ul'
      className='flex min-w-0 flex-wrap items-center gap-1.5'
      listProps={{ 'aria-label': 'How each son voted' }}
      itemKey={(ballot) => ballot.son_id}
    >
      {(ballot) => {
        const view = sonOf(ballot.son_id)
        return (
          <Tooltip key={ballot.son_id}>
            <TooltipTrigger asChild>
              <li
                tabIndex={0}
                aria-label={`${ballot.name}: ${VOTE_LABEL[ballot.vote]}`}
                className={cn(
                  'rounded-full ring-2 ring-offset-2 ring-offset-card',
                  VOTE_RING[ballot.vote]
                )}
              >
                <Portrait
                  name={ballot.name}
                  src={mediaUrl(view?.cover)}
                  size='xs'
                />
              </li>
            </TooltipTrigger>
            <TooltipContent>{`${ballot.name} · ${VOTE_LABEL[ballot.vote]}`}</TooltipContent>
          </Tooltip>
        )
      }}
    </PagedList>
  )
}

export function CouncilRecord({
  council,
  defaultOpen = false,
}: {
  council: Council
  defaultOpen?: boolean
}) {
  const sons = useSons()
  const minutes = council.minutes
  const count = (vote: CouncilVote) =>
    minutes.ballots.filter((ballot) => ballot.vote === vote).length
  const total = Math.max(1, minutes.ballots.length)
  const sonOf = (sonId: number) =>
    sons.data?.find((view) => view.son.id === sonId)
  const voteOf = (sonId: number) =>
    minutes.ballots.find((ballot) => ballot.son_id === sonId)?.vote
  const byFate = minutes.convened_by === 'fate'
  const decision =
    minutes.decision === 'none' ? null : MOTIONS[minutes.decision]
  return (
    <Collapsible
      defaultOpen={defaultOpen}
      data-council={council.id}
      className={cn(
        'flex min-w-0 flex-col gap-4 rounded-md border surface-framed border-gild/70 bg-card p-4',
        council.passed ? 'border-success/30' : 'border-destructive/30'
      )}
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={Gavel} tone={council.passed ? 'success' : 'danger'} />
        <div className='flex min-w-0 flex-1 flex-col gap-2'>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Badge
              size='sm'
              variant='outline'
            >{`Epoch ${council.epoch}`}</Badge>
            <Badge size='sm' variant={byFate ? 'info' : 'default'}>
              {byFate ? <Sparkles /> : <Crown />}
              {byFate ? 'Called by Fate' : 'Called by you'}
            </Badge>
            <Badge
              size='sm'
              variant={council.passed ? 'success' : 'destructive'}
            >
              {council.passed ? <CircleCheck /> : <CircleX />}
              {council.passed ? 'Accepted' : 'Rejected'}
            </Badge>
          </div>
          <Text weight='semibold' truncate={2}>
            {council.topic}
          </Text>
          <div className='flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2'>
            <BallotDots ballots={minutes.ballots} sonOf={sonOf} />
            <Label>{`${count('yes')} yes · ${count('abstain')} abstain · ${count('no')} no`}</Label>
          </div>
        </div>
        <CollapsibleTrigger asChild>
          <Button variant='ghost' size='sm'>
            <ChevronDown />
            {`${plural(minutes.speeches.length, 'speech', 'speeches')}`}
          </Button>
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent className='flex min-w-0 flex-col gap-5'>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>The debate</Label>
          <ul className='flex min-w-0 flex-col gap-3'>
            <Paged items={minutes.speeches} as='li'>
              {(speech, index) => {
                const view = sonOf(speech.son_id)
                const vote = voteOf(speech.son_id)
                return (
                  <li
                    key={`${speech.son_id}-${index}`}
                    className='flex min-w-0 items-start gap-3'
                  >
                    <Portrait
                      name={speech.name}
                      src={mediaUrl(view?.cover)}
                      size='md'
                      rarity={view?.son.rarity}
                    />
                    <div className='flex min-w-0 flex-1 flex-col gap-1.5 rounded-md rounded-tl-sm border surface-well border-gild/20 bg-muted/60 p-3'>
                      <div className='flex min-w-0 flex-wrap items-center gap-2'>
                        <EntityLink
                          kind='son'
                          id={String(speech.son_id)}
                          rarity={view?.son.rarity}
                        >
                          {speech.name}
                        </EntityLink>
                        {vote && <VoteBadge vote={vote} />}
                      </div>
                      <Text italic>{speech.words}</Text>
                    </div>
                  </li>
                )
              }}
            </Paged>
          </ul>
        </div>
        <div className='flex min-w-0 items-start gap-3 rounded-md border surface-framed border-primary/30 bg-primary/5 p-3'>
          <Medallion icon={ScrollText} size='sm' />
          <div className='flex min-w-0 flex-1 flex-col gap-1'>
            <Label variant='overline'>The motion</Label>
            <Text>{minutes.motion}</Text>
          </div>
        </div>
        <div className='flex min-w-0 flex-col gap-3'>
          <Label variant='overline'>The vote</Label>
          <div className='grid min-w-0 grid-cols-3 gap-3'>
            {VOTE_ORDER.map((vote) => {
              const Icon = VOTE_ICON[vote]
              return (
                <div
                  key={vote}
                  className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'
                >
                  <div className='flex min-w-0 items-center gap-2'>
                    <Icon
                      aria-hidden='true'
                      className={cn(
                        'size-icon-sm shrink-0',
                        vote === 'yes'
                          ? 'text-success'
                          : vote === 'no'
                            ? 'text-destructive'
                            : 'text-muted-foreground'
                      )}
                    />
                    <Label className='flex-1'>{VOTE_LABEL[vote]}</Label>
                    <Stat value={count(vote)} />
                  </div>
                  <Progress
                    size='sm'
                    tone={
                      vote === 'yes'
                        ? 'success'
                        : vote === 'no'
                          ? 'destructive'
                          : 'muted'
                    }
                    value={(count(vote) / total) * PERCENT}
                    aria-label={`${VOTE_LABEL[vote]} votes`}
                  />
                </div>
              )
            })}
          </div>
          <ul className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
            <Paged items={minutes.ballots} as='li'>
              {(ballot) => {
                const view = sonOf(ballot.son_id)
                return (
                  <li
                    key={ballot.son_id}
                    className='flex min-w-0 items-start gap-3 rounded-md border surface-sheen border-gild/60 bg-card p-2'
                  >
                    <Portrait
                      name={ballot.name}
                      src={mediaUrl(view?.cover)}
                      size='sm'
                      rarity={view?.son.rarity}
                    />
                    <div className='flex min-w-0 flex-1 flex-col gap-1'>
                      <div className='flex min-w-0 items-center gap-2'>
                        <span className='min-w-0 flex-1 truncate'>
                          <EntityLink kind='son' id={String(ballot.son_id)}>
                            {ballot.name}
                          </EntityLink>
                        </span>
                        <VoteBadge vote={ballot.vote} />
                      </div>
                      {ballot.reason && (
                        <Muted variant='caption'>{ballot.reason}</Muted>
                      )}
                    </div>
                  </li>
                )
              }}
            </Paged>
          </ul>
        </div>
        <div
          className={cn(
            'flex min-w-0 items-start gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3',
            council.passed
              ? 'border-success/40 bg-success/5'
              : 'border-destructive/40 bg-destructive/5'
          )}
        >
          <Medallion
            icon={council.passed ? CircleCheck : CircleX}
            tone={council.passed ? 'success' : 'danger'}
            size='sm'
          />
          <div className='flex min-w-0 flex-1 flex-col gap-2'>
            <Text weight='semibold'>
              {council.passed ? 'Motion accepted' : 'Motion rejected'}
            </Text>
            {decision && <DecisionBadge decision={decision} />}
            {minutes.notes.length > 0 && (
              <ul className='flex min-w-0 list-disc flex-col gap-1 pl-5'>
                <Paged items={minutes.notes} as='li'>
                  {(note, index) => (
                    <Text as='li' key={index}>
                      {note}
                    </Text>
                  )}
                </Paged>
              </ul>
            )}
          </div>
        </div>
        {minutes.summary && (
          <div className='flex min-w-0 items-start gap-3 rounded-md p-3 sealed-well'>
            <Medallion icon={ScrollText} tone='muted' size='sm' />
            <div className='flex min-w-0 flex-1 flex-col gap-1'>
              <Label variant='overline'>Minutes · from a seer's dream</Label>
              <Muted italic>{minutes.summary}</Muted>
            </div>
          </div>
        )}
        <CouncilRecordControls
          councilId={council.id}
          topic={council.topic}
          passed={council.passed}
        />
      </CollapsibleContent>
    </Collapsible>
  )
}
