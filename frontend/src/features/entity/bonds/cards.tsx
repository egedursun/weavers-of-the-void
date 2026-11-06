import { useState } from 'react'
import { Eye, EyeOff, Flame, Plus, Star, UserMinus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { EntityLink, Medallion, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodAction } from '@/features/pantheon/godAction'
import { EntityPicker } from '@/features/wars/military/controls'
import { VALUE_ICONS, named } from '../mind/labels'
import { MindCard, MindPicker } from '../mind/parts'
import {
  type AppealKind,
  type Bond,
  type Bonds,
  type Circle,
  type CircleKind,
  type ContestKind,
  type ContestStake,
  type PassionKind,
  type Rank,
  type ValueAxis,
} from './api'
import {
  BONDS_ICON,
  CIRCLE_ICON,
  CIRCLE_KINDS,
  CONTEST_ICON,
  CONTEST_KINDS,
  GROUP_KINDS,
  OUTCOMES,
  PASSION_ICON,
  PASSION_KINDS,
  PERSUASION_ICON,
  RELATION_TYPES,
  STANDING_ICON,
} from './labels'

const SPAN = 100
const WORKING = 'Working on it.'
const MORTALS = ['mortal']
const ANYTHING = [
  'mortal',
  'settlement',
  'people',
  'polity',
  'house',
  'faction',
  'cult',
  'region',
  'artifact',
  'place',
]

type Props = { view: Bonds; blocked: string | null; hold: boolean }

function table(
  items: { key: string; label: string }[]
): Record<string, string> {
  return Object.fromEntries(items.map((item) => [item.key, item.label]))
}

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function Meter({
  label,
  value,
  min = 0,
  tone,
}: {
  label: string
  value: number
  min?: number
  tone: 'success' | 'warning' | 'destructive' | 'default'
}) {
  const share = min < 0 ? (value + SPAN) / 2 : value
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Muted variant='caption'>{label}</Muted>
        <Text variant='caption' weight='semibold'>
          {value}
        </Text>
      </div>
      <Progress
        value={share}
        size='sm'
        tone={tone}
        aria-label={`${label} ${value}`}
      />
    </div>
  )
}

function BondRow({ bond, view, blocked, hold }: { bond: Bond } & Props) {
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/tie:remove', {
          body: { relation_id: bond.id },
        })
      ),
  })
  const secret = useGodAction({
    run: (known: boolean) =>
      unwrap(
        api.POST('/api/actions/tie:set', {
          body: {
            holder_id: view.node_id,
            subject_id: bond.subject.id,
            affair_known: known,
            mutual: false,
            hold,
          },
        })
      ),
  })
  const busy = why(blocked, remove.isPending, secret.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <EntityLink kind='entity' id={String(bond.subject.id)} showIcon>
          {bond.subject.name}
        </EntityLink>
        {bond.kinds.map((kind) => {
          const spec = named(RELATION_TYPES, kind)
          return (
            <Badge key={kind} variant='outline'>
              <spec.icon aria-hidden='true' />
              {spec.label}
            </Badge>
          )
        })}
        {bond.affair && (
          <Badge variant={bond.affair_known ? 'destructive' : 'secondary'}>
            {bond.affair_known ? 'Affair, found out' : 'Secret love'}
          </Badge>
        )}
        <div className='ml-auto flex shrink-0 items-center gap-1'>
          {bond.affair && (
            <Button
              size='icon-sm'
              variant='ghost'
              aria-label={
                bond.affair_known
                  ? 'Hide the affair again'
                  : 'Let the affair be found out'
              }
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => secret.mutate(!bond.affair_known)}
            >
              {bond.affair_known ? <EyeOff /> : <Eye />}
            </Button>
          )}
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={`Forget the bond with ${bond.subject.name}`}
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => remove.mutate()}
          >
            <X />
          </Button>
        </div>
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-3 @xl/mind:grid-cols-4'>
        <Meter
          label='Friendship'
          value={bond.friendship}
          min={-SPAN}
          tone={bond.friendship < 0 ? 'destructive' : 'success'}
        />
        <Meter label='Romance' value={bond.romance} tone='warning' />
        <Meter label='Familiarity' value={bond.familiarity} tone='default' />
        <Meter label='Rivalry' value={bond.rivalry} tone='destructive' />
      </div>
      <Muted variant='caption'>
        {bond.their_friendship === null
          ? `They have not yet formed a view in return. Known since epoch ${bond.since_epoch}.`
          : `In return: friendship ${bond.their_friendship}, romance ${bond.their_romance ?? 0}. Known since epoch ${bond.since_epoch}.`}
        {bond.held.length > 0 ? ` Held: ${bond.held.join(', ')}.` : ''}
      </Muted>
      <AdjustStats
        id={`bond-${bond.id}`}
        groups={[
          {
            title: 'How they feel',
            fields: [
              {
                key: 'friendship',
                label: 'Friendship',
                value: bond.friendship,
                min: -SPAN,
                max: SPAN,
              },
              {
                key: 'romance',
                label: 'Romance',
                value: bond.romance,
                min: 0,
                max: SPAN,
              },
              {
                key: 'familiarity',
                label: 'Familiarity',
                value: bond.familiarity,
                min: 0,
                max: SPAN,
              },
              {
                key: 'rivalry',
                label: 'Rivalry',
                value: bond.rivalry,
                min: 0,
                max: SPAN,
              },
            ],
          },
        ]}
        run={({ key, value }) =>
          unwrap(
            api.POST('/api/actions/tie:set', {
              body: {
                holder_id: view.node_id,
                subject_id: bond.subject.id,
                [key]: value,
                mutual: false,
                hold,
              },
            })
          )
        }
      />
    </div>
  )
}

export function BondsCard({ view, blocked, hold }: Props) {
  const [subject, setSubject] = useState<number | null>(null)
  const begin = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/tie:set', {
          body: {
            holder_id: view.node_id,
            subject_id: subject ?? 0,
            familiarity: 20,
            friendship: 10,
            mutual: true,
            hold,
          },
        })
      ),
  })
  const busy = why(blocked, begin.isPending)
  return (
    <MindCard
      title='Bonds'
      icon={BONDS_ICON}
      hint='Mortals who share a place meet, talk, court, quarrel and teach; friendship, romance, familiarity and rivalry grow into bonds.'
      wide
    >
      {view.bonds.length === 0 ? (
        <Muted variant='caption'>
          No bonds yet. They grow as this mortal meets others, or you can begin
          one.
        </Muted>
      ) : (
        <Paged items={view.bonds} initial={4} noun={['bond', 'bonds']}>
          {(bond) => (
            <BondRow
              key={bond.id}
              bond={bond}
              view={view}
              blocked={blocked}
              hold={hold}
            />
          )}
        </Paged>
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='min-w-0 flex-1'>
          <EntityPicker
            label='Begin a bond with'
            types={MORTALS}
            value={subject}
            onChange={setSubject}
            blocked={busy}
            icon={BONDS_ICON}
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null || subject === null}
          disabledReason={
            busy ?? (subject === null ? 'Pick a mortal first.' : undefined)
          }
          onClick={() => begin.mutate()}
        >
          <Plus />
          Begin
        </Button>
      </div>
    </MindCard>
  )
}

export function PassionsCard({ view, blocked, hold }: Props) {
  const [kind, setKind] = useState<string>('love')
  const [object, setObject] = useState<number | null>(null)
  const kindle = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/passion:set', {
          body: {
            holder_id: view.node_id,
            kind: kind as PassionKind,
            object_id: object ?? 0,
            strength: 80,
            source: 'divine',
            hold,
          },
        })
      ),
  })
  const invoke = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/passion:invoke', { body: { passion_id: id } })
      ),
  })
  const quench = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/passion:remove', { body: { passion_id: id } })
      ),
  })
  const busy = why(
    blocked,
    kindle.isPending,
    invoke.isPending,
    quench.isPending
  )
  return (
    <MindCard
      title='Passions'
      icon={PASSION_ICON}
      hint='Love, loyalty, hatred and devotion. A passion above 80 can be called on in a battle, duel, oath or crisis: it lifts or it breaks.'
    >
      {view.passions.length === 0 ? (
        <Muted variant='caption'>No passions burn yet.</Muted>
      ) : (
        <Paged items={view.passions} initial={4} noun={['passion', 'passions']}>
          {(item) => {
            const spec = named(PASSION_KINDS, item.kind)
            return (
              <div
                key={item.id}
                className='flex min-w-0 flex-col gap-2 rounded-md border p-2'
              >
                <div className='flex min-w-0 items-center gap-2'>
                  <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
                  <div className='flex min-w-0 flex-1 flex-col'>
                    <Text weight='semibold' truncate>
                      {item.label}
                      {item.object ? ` for ${item.object.name}` : ''}
                    </Text>
                    <Muted variant='caption'>{`${item.source_label}${item.held ? ' · held' : ''}${item.invoked_epoch !== null ? ` · last called on in epoch ${item.invoked_epoch}` : ''}`}</Muted>
                  </div>
                  <Button
                    size='icon-sm'
                    variant='ghost'
                    aria-label={`Call on the ${item.label.toLowerCase()}`}
                    disabled={busy !== null || !item.invocable}
                    disabledReason={
                      busy ??
                      (!item.invocable
                        ? 'Only a passion of 80 or more can be called on.'
                        : undefined)
                    }
                    onClick={() => invoke.mutate(item.id)}
                  >
                    <Flame />
                  </Button>
                  <Button
                    size='icon-sm'
                    variant='ghost'
                    aria-label={`Quench the ${item.label.toLowerCase()}`}
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => quench.mutate(item.id)}
                  >
                    <X />
                  </Button>
                </div>
                <Progress
                  value={item.strength}
                  size='sm'
                  tone={item.kind === 'hatred' ? 'destructive' : 'warning'}
                  aria-label={`${item.label} strength`}
                />
                <AdjustStats
                  id={`passion-${item.id}`}
                  groups={[
                    {
                      title: 'Strength',
                      fields: [
                        {
                          key: 'strength',
                          label: 'Strength',
                          value: item.strength,
                          min: 0,
                          max: SPAN,
                        },
                      ],
                    },
                  ]}
                  run={({ value }) =>
                    unwrap(
                      api.POST('/api/actions/passion:set', {
                        body: {
                          holder_id: view.node_id,
                          kind: item.kind,
                          object_id: item.object?.id ?? 0,
                          strength: value,
                          source: item.source,
                          hold,
                        },
                      })
                    )
                  }
                />
              </div>
            )
          }}
        </Paged>
      )}
      <div className='flex min-w-0 flex-col gap-2'>
        <MindPicker
          label='Kindle a passion of'
          value={kind}
          table={table(view.passion_kinds)}
          blocked={busy}
          onPick={setKind}
        />
        <EntityPicker
          label='For'
          types={ANYTHING}
          value={object}
          onChange={setObject}
          blocked={busy}
          icon={PASSION_ICON}
        />
        <Button
          size='sm'
          disabled={busy !== null || object === null}
          disabledReason={
            busy ??
            (object === null ? 'Pick what the passion is for.' : undefined)
          }
          onClick={() => kindle.mutate()}
        >
          <Flame />
          Kindle
        </Button>
      </div>
    </MindCard>
  )
}

function CircleRow({
  circle,
  view,
  blocked,
  hold,
}: { circle: Circle } & Props) {
  const [member, setMember] = useState<number | null>(null)
  const spec = named(CIRCLE_KINDS, circle.kind)
  const edit = useGodAction({
    run: (kind: CircleKind) =>
      unwrap(
        api.POST('/api/actions/circle:edit', {
          body: { circle_id: circle.circle.id, kind, hold },
        })
      ),
  })
  const join = useGodAction({
    run: (input: { id: number; remove: boolean }) =>
      unwrap(
        api.POST('/api/actions/circle:member', {
          body: {
            circle_id: circle.circle.id,
            mortal_id: input.id,
            remove: input.remove,
          },
        })
      ),
  })
  const disband = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/circle:disband', {
          body: { circle_id: circle.circle.id },
        })
      ),
  })
  const busy = why(blocked, edit.isPending, join.isPending, disband.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <EntityLink kind='entity' id={String(circle.circle.id)}>
            {circle.circle.name}
          </EntityLink>
          <Muted variant='caption'>
            {[
              circle.label,
              circle.axis
                ? `bound by ${named(VALUE_ICONS, circle.axis).label.toLowerCase()}`
                : null,
              circle.taste_key
                ? `drawn by ${circle.taste_key.replace(':', ' ').replaceAll('_', ' ')}`
                : null,
              circle.meeting_place
                ? `meets in ${circle.meeting_place.name}`
                : null,
              `since epoch ${circle.founded_epoch}`,
            ]
              .filter(Boolean)
              .join(' · ')}
          </Muted>
        </div>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => disband.mutate()}
        >
          <X />
          Break up
        </Button>
      </div>
      {circle.ideology && (
        <Muted variant='caption'>
          {'Spreads the creed '}
          <EntityLink kind='entity' id={String(circle.ideology.id)}>
            {circle.ideology.name}
          </EntityLink>
        </Muted>
      )}
      <div className='flex min-w-0 flex-wrap gap-2'>
        {circle.members.map((item) => (
          <Badge
            key={item.id}
            variant={circle.leader?.id === item.id ? 'default' : 'outline'}
          >
            {circle.leader?.id === item.id && <Star aria-hidden='true' />}
            {item.name}
            <Button
              size='icon-sm'
              variant='ghost'
              aria-label={`Send ${item.name} out of the circle`}
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => join.mutate({ id: item.id, remove: true })}
            >
              <UserMinus />
            </Button>
          </Badge>
        ))}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @xl/mind:grid-cols-2'>
        <MindPicker
          label='Kind of circle'
          value={circle.kind}
          table={table(view.circle_kinds)}
          blocked={busy}
          onPick={(value) => edit.mutate(value as CircleKind)}
        />
        <div className='flex min-w-0 items-end gap-2'>
          <div className='min-w-0 flex-1'>
            <EntityPicker
              label='Bring in'
              types={MORTALS}
              value={member}
              onChange={setMember}
              blocked={busy}
              icon={CIRCLE_ICON}
            />
          </div>
          <Button
            size='sm'
            disabled={busy !== null || member === null}
            disabledReason={
              busy ?? (member === null ? 'Pick a mortal first.' : undefined)
            }
            onClick={() =>
              member !== null && join.mutate({ id: member, remove: false })
            }
          >
            <Plus />
            Bring in
          </Button>
        </div>
      </div>
    </div>
  )
}

export function CirclesCard({
  view,
  blocked,
  hold,
  place,
}: Props & { place: boolean }) {
  const [kind, setKind] = useState<string>('study_circle')
  const found = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/circle:found', {
          body: {
            place_id: view.node_id,
            kind: kind as CircleKind,
            member_ids: [],
          },
        })
      ),
  })
  const busy = why(blocked, found.isPending)
  return (
    <MindCard
      title='Circles'
      icon={CIRCLE_ICON}
      hint='Mortals who share a strong taste or belief gather; circles bond their members, feed factions and spread a creed.'
      wide
    >
      {view.circles.length === 0 ? (
        <Muted variant='caption'>No circle gathers here yet.</Muted>
      ) : (
        <Paged items={view.circles} initial={3} noun={['circle', 'circles']}>
          {(circle) => (
            <CircleRow
              key={circle.circle.id}
              circle={circle}
              view={view}
              blocked={blocked}
              hold={hold}
            />
          )}
        </Paged>
      )}
      {place && (
        <div className='flex min-w-0 items-end gap-2'>
          <div className='min-w-0 flex-1'>
            <MindPicker
              label='Gather a circle here'
              value={kind}
              table={table(view.circle_kinds)}
              blocked={busy}
              onPick={setKind}
            />
          </div>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => found.mutate()}
          >
            <Plus />
            Gather
          </Button>
        </div>
      )}
    </MindCard>
  )
}

function RankRow({
  rank,
  hold,
  blocked,
}: {
  rank: Rank
  hold: boolean
  blocked: string | null
}) {
  const spec = named(GROUP_KINDS, rank.group_kind)
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/rank:remove', {
          body: { group_id: rank.group.id, member_id: rank.member.id },
        })
      ),
  })
  const busy = why(blocked, remove.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text
            weight='semibold'
            truncate
          >{`${rank.member.name}: rank ${rank.rank} of ${rank.size}`}</Text>
          <Muted variant='caption'>{`${rank.group_label} of ${rank.group.name} · since epoch ${rank.since_epoch}${rank.held.length ? ' · held' : ''}`}</Muted>
        </div>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Take ${rank.member.name}'s place away`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <X />
        </Button>
      </div>
      <Progress
        value={rank.dominance}
        size='sm'
        tone='warning'
        aria-label='Standing'
      />
      <AdjustStats
        id={`rank-${rank.group.id}-${rank.member.id}`}
        groups={[
          {
            title: 'Place in the order',
            fields: [
              {
                key: 'rank',
                label: 'Rank',
                value: rank.rank,
                min: 1,
                max: Math.max(rank.size, 1),
              },
              {
                key: 'dominance',
                label: 'Standing',
                value: rank.dominance,
                min: 0,
                max: SPAN,
              },
            ],
          },
        ]}
        run={({ key, value }) =>
          unwrap(
            api.POST('/api/actions/rank:set', {
              body: {
                group_id: rank.group.id,
                member_id: rank.member.id,
                group_kind: rank.group_kind,
                rank: key === 'rank' ? value : rank.rank,
                dominance: key === 'dominance' ? value : null,
                hold,
              },
            })
          )
        }
      />
    </div>
  )
}

export function StandingCard({ view, blocked, hold }: Props) {
  const rows = view.ranks.length > 0 ? view.ranks : view.order
  return (
    <MindCard
      title='Pecking order'
      icon={STANDING_ICON}
      hint='Households, courts, circles, warbands and crews rank their members by strength, office, renown and assertiveness; those below may challenge.'
    >
      {rows.length === 0 ? (
        <Muted variant='caption'>
          No pecking order yet. Groups of three or more form one.
        </Muted>
      ) : (
        <Paged items={rows} initial={4} noun={['place', 'places']}>
          {(rank) => (
            <RankRow
              key={`${rank.group.id}-${rank.member.id}`}
              rank={rank}
              hold={hold}
              blocked={blocked}
            />
          )}
        </Paged>
      )}
    </MindCard>
  )
}

export function ContestsCard({
  view,
  blocked,
  mortal,
}: Props & { mortal: boolean }) {
  const [rival, setRival] = useState<number | null>(null)
  const [kind, setKind] = useState<string>('riddle_game')
  const [stake, setStake] = useState<string>('honour')
  const hold = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/contest:hold', {
          body: {
            challenger_id: view.node_id,
            defender_id: rival ?? 0,
            kind: kind as ContestKind,
            stake: stake as ContestStake,
            wager: 0,
          },
        })
      ),
  })
  const fame = useGodAction({
    run: (input: { id: number; famous: boolean }) =>
      unwrap(
        api.POST('/api/actions/contest:edit', {
          body: { contest_id: input.id, famous: input.famous },
        })
      ),
  })
  const strike = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/contest:remove', { body: { contest_id: id } })
      ),
  })
  const busy = why(blocked, hold.isPending, fame.isPending, strike.isPending)
  return (
    <MindCard
      title='Contests of wit'
      icon={CONTEST_ICON}
      hint='Riddles, flytings, debates, games, trials, songs and tales for honour, a hand, a wager, a place, a freedom or a god’s favour.'
      wide
    >
      {view.contests.length === 0 ? (
        <Muted variant='caption'>No contests yet.</Muted>
      ) : (
        <Paged items={view.contests} initial={4} noun={['contest', 'contests']}>
          {(item) => {
            const spec = named(CONTEST_KINDS, item.kind)
            return (
              <div
                key={item.id}
                className='flex min-w-0 flex-col gap-2 rounded-md border p-2'
              >
                <div className='flex min-w-0 flex-wrap items-center gap-2'>
                  <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
                  <Text weight='semibold'>{`${item.label} for ${item.stake_label.toLowerCase()}`}</Text>
                  <Badge
                    variant={item.outcome === 'drawn' ? 'outline' : 'default'}
                  >
                    {OUTCOMES[item.outcome] ?? item.outcome}
                  </Badge>
                  {item.famous && <Badge variant='secondary'>Famous</Badge>}
                  <div className='ml-auto flex shrink-0 items-center gap-1'>
                    <Button
                      size='icon-sm'
                      variant='ghost'
                      aria-label={
                        item.famous
                          ? 'Let the contest be forgotten by the bards'
                          : 'Make the contest famous'
                      }
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() =>
                        fame.mutate({ id: item.id, famous: !item.famous })
                      }
                    >
                      <Star />
                    </Button>
                    <Button
                      size='icon-sm'
                      variant='ghost'
                      aria-label='Strike the contest from memory'
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() => strike.mutate(item.id)}
                    >
                      <X />
                    </Button>
                  </div>
                </div>
                <Muted variant='caption'>
                  {`${item.challenger?.name ?? 'Someone'} against ${item.defender?.name ?? 'someone'}`}
                  {item.judge ? `, judged by ${item.judge.name}` : ''}
                  {` · epoch ${item.epoch} · rounds ${item.rounds.map((round) => `${Math.round(round[0] ?? 0)}–${Math.round(round[1] ?? 0)}`).join(', ')}`}
                </Muted>
                {item.work && (
                  <EntityLink kind='entity' id={String(item.work.id)} showIcon>
                    {item.work.name}
                  </EntityLink>
                )}
              </div>
            )
          }}
        </Paged>
      )}
      {mortal && (
        <div className='grid min-w-0 grid-cols-1 gap-2 @xl/mind:grid-cols-3'>
          <EntityPicker
            label='Challenge'
            types={MORTALS}
            value={rival}
            onChange={setRival}
            blocked={busy}
            icon={CONTEST_ICON}
          />
          <MindPicker
            label='Contest'
            value={kind}
            table={table(view.contest_kinds)}
            blocked={busy}
            onPick={setKind}
          />
          <MindPicker
            label='Stake'
            value={stake}
            table={table(view.stakes)}
            blocked={busy}
            onPick={setStake}
          />
          <Button
            size='sm'
            disabled={busy !== null || rival === null}
            disabledReason={
              busy ?? (rival === null ? 'Pick an opponent first.' : undefined)
            }
            onClick={() => hold.mutate()}
          >
            <CONTEST_ICON />
            Stage the contest
          </Button>
        </div>
      )}
    </MindCard>
  )
}

export function PersuasionsCard({ view, blocked }: Props) {
  const [target, setTarget] = useState<number | null>(null)
  const [appeal, setAppeal] = useState<string>('belief')
  const [axis, setAxis] = useState<string>('knowledge')
  const axes = Object.fromEntries(
    Object.entries(VALUE_ICONS).map(([key, spec]) => [key, spec.label])
  )
  const argue = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/persuasion:attempt', {
          body: {
            speaker_id: view.node_id,
            target_id: target ?? 0,
            appeal: appeal as AppealKind,
            aim: 'belief',
            axis: axis as ValueAxis,
            toward: SPAN,
          },
        })
      ),
  })
  const forget = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/persuasion:remove', {
          body: { persuasion_id: id },
        })
      ),
  })
  const busy = why(blocked, argue.isPending, forget.isPending)
  return (
    <MindCard
      title='Arguments'
      icon={PERSUASION_ICON}
      hint='Arguments appeal to belief, self-interest, authority, evidence or fear. Oratory and fit against stubbornness and passions decide them.'
    >
      {view.persuasions.length === 0 ? (
        <Muted variant='caption'>No arguments yet.</Muted>
      ) : (
        <Paged
          items={view.persuasions}
          initial={4}
          noun={['argument', 'arguments']}
        >
          {(item) => (
            <div
              key={item.id}
              className='flex min-w-0 items-center gap-2 rounded-md border p-2'
            >
              <div className='flex min-w-0 flex-1 flex-col'>
                <Text
                  weight='semibold'
                  truncate
                >{`${item.speaker?.name ?? 'Someone'} to ${item.target?.name ?? 'someone'}`}</Text>
                <Muted variant='caption'>{`${item.appeal_label} · ${item.aim_label.toLowerCase()}${item.axis ? ` (${named(VALUE_ICONS, item.axis).label.toLowerCase()})` : ''} · epoch ${item.epoch}`}</Muted>
              </div>
              <Badge
                variant={item.success ? 'default' : 'outline'}
              >{`${item.success ? 'Swayed' : 'Unmoved'} ${item.score}`}</Badge>
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label='Forget the argument'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => forget.mutate(item.id)}
              >
                <X />
              </Button>
            </div>
          )}
        </Paged>
      )}
      <div className='flex min-w-0 flex-col gap-2'>
        <EntityPicker
          label='Argue with'
          types={MORTALS}
          value={target}
          onChange={setTarget}
          blocked={busy}
          icon={PERSUASION_ICON}
        />
        <MindPicker
          label='Appeal'
          value={appeal}
          table={table(view.appeals)}
          blocked={busy}
          onPick={setAppeal}
        />
        <MindPicker
          label='Belief'
          value={axis}
          table={axes}
          blocked={busy}
          onPick={setAxis}
        />
        <Button
          size='sm'
          disabled={busy !== null || target === null}
          disabledReason={
            busy ?? (target === null ? 'Pick who to argue with.' : undefined)
          }
          onClick={() => argue.mutate()}
        >
          <PERSUASION_ICON />
          Argue
        </Button>
      </div>
    </MindCard>
  )
}
