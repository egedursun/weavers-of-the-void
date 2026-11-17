import { useState } from 'react'
import { Eye, EyeOff, Flame, Plus, Star, UserMinus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { EntityLink, Paged, PagedList } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { NodeName } from '@/features/divine/parts'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodAction } from '@/features/pantheon/godAction'
import { VALUE_ICONS, named } from '../mind/labels'
import {
  AddBar,
  FormBar,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'
import {
  type AppealKind,
  type Bond,
  type Bonds,
  type Circle,
  type CircleKind,
  type ContestKind,
  type ContestStake,
  type PassionKind,
  type PassionSource,
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

function RemoveButton({
  label,
  busy,
  onClick,
}: {
  label: string
  busy: string | null
  onClick: () => void
}) {
  return (
    <Button
      size='icon-sm'
      variant='ghost'
      aria-label={label}
      disabled={busy !== null}
      disabledReason={busy ?? undefined}
      onClick={onClick}
    >
      <X />
    </Button>
  )
}

function BondRow({ bond, view, blocked, hold }: { bond: Bond } & Props) {
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/tie:remove', { body: { relation_id: bond.id } })
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
  const lead = named(RELATION_TYPES, bond.kinds[0] ?? 'acquaintance')
  return (
    <ItemRow
      icon={lead.icon}
      tone={lead.tone}
      title={
        <EntityLink kind='entity' id={String(bond.subject.id)}>
          {bond.subject.name}
        </EntityLink>
      }
      meta={
        bond.their_friendship === null
          ? `Known since epoch ${bond.since_epoch}; no view in return yet`
          : `Known since epoch ${bond.since_epoch} · in return: friendship ${bond.their_friendship}, romance ${bond.their_romance ?? 0}`
      }
      badges={
        <>
          {bond.kinds.map((kind) => (
            <Badge key={kind} variant='outline'>
              {named(RELATION_TYPES, kind).label}
            </Badge>
          ))}
          {bond.affair && (
            <Badge variant={bond.affair_known ? 'destructive' : 'secondary'}>
              {bond.affair_known ? 'Affair found out' : 'Secret love'}
            </Badge>
          )}
          {bond.held.length > 0 && <Badge variant='secondary'>Held</Badge>}
        </>
      }
      actions={
        <>
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
          <RemoveButton
            label={`Forget the bond with ${bond.subject.name}`}
            busy={busy}
            onClick={() => remove.mutate()}
          />
        </>
      }
      editLabel={`how they feel about ${bond.subject.name}`}
      editor={
        <AdjustStats
          id={`bond-${bond.id}`}
          inline
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
      }
    >
      <div className='grid min-w-0 grid-cols-2 gap-x-4 gap-y-2 @xl/mind:grid-cols-4'>
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
    </ItemRow>
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
      hint='Mortals who share a place meet, talk, court, quarrel and teach; what they feel grows into bonds.'
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
      <AddBar
        title='Begin a bond'
        action={
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
        }
      >
        <NodePicker
          label='With'
          types={MORTALS}
          value={subject}
          onChange={setSubject}
          blocked={busy}
        />
      </AddBar>
    </MindCard>
  )
}

export function PassionsCard({ view, blocked, hold }: Props) {
  const [kind, setKind] = useState<string>('love')
  const [source, setSource] = useState<string>('divine')
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
            source: source as PassionSource,
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
      hint='Love, loyalty, hatred and devotion. At 80 or more a passion can be called on: it lifts or it breaks.'
    >
      {view.passions.length === 0 ? (
        <Muted variant='caption'>No passions burn yet.</Muted>
      ) : (
        <Paged items={view.passions} initial={4} noun={['passion', 'passions']}>
          {(item) => {
            const spec = named(PASSION_KINDS, item.kind)
            return (
              <ItemRow
                key={item.id}
                icon={spec.icon}
                tone={spec.tone}
                title={
                  item.object
                    ? `${item.label} for ${item.object.name}`
                    : item.label
                }
                meta={`${item.source_label}${item.invoked_epoch !== null ? ` · called on in epoch ${item.invoked_epoch}` : ''}`}
                badges={
                  item.held ? (
                    <Badge variant='secondary'>Held</Badge>
                  ) : undefined
                }
                actions={
                  <>
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
                    <RemoveButton
                      label={`Quench the ${item.label.toLowerCase()}`}
                      busy={busy}
                      onClick={() => quench.mutate(item.id)}
                    />
                  </>
                }
                editLabel='the strength'
                editor={
                  <AdjustStats
                    id={`passion-${item.id}`}
                    inline
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
                }
              >
                <Meter
                  label='Strength'
                  value={item.strength}
                  tone={item.kind === 'hatred' ? 'destructive' : 'warning'}
                />
              </ItemRow>
            )
          }}
        </Paged>
      )}
      <AddBar
        title='Kindle a passion'
        action={
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
        }
      >
        <MindPicker
          label='Passion'
          value={kind}
          table={table(view.passion_kinds)}
          blocked={busy}
          onPick={setKind}
        />
        <MindPicker
          label='Kindled by'
          value={source}
          table={table(view.passion_sources)}
          blocked={busy}
          onPick={setSource}
        />
        <NodePicker
          label='For'
          types={ANYTHING}
          value={object}
          onChange={setObject}
          blocked={busy}
        />
      </AddBar>
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
  const facts = [
    circle.axis
      ? `bound by ${named(VALUE_ICONS, circle.axis).label.toLowerCase()}`
      : null,
    circle.taste_key
      ? `drawn by ${circle.taste_key.replace(':', ' ').replaceAll('_', ' ')}`
      : null,
    circle.meeting_place ? `meets in ${circle.meeting_place.name}` : null,
    `since epoch ${circle.founded_epoch}`,
  ].filter(Boolean)
  return (
    <ItemRow
      icon={spec.icon}
      tone={spec.tone}
      title={
        <EntityLink kind='entity' id={String(circle.circle.id)}>
          {circle.circle.name}
        </EntityLink>
      }
      meta={facts.join(' · ')}
      badges={
        <Badge variant='outline'>{`${circle.label} · ${circle.members.length}`}</Badge>
      }
      actions={
        <RemoveButton
          label={`Break up ${circle.circle.name}`}
          busy={busy}
          onClick={() => disband.mutate()}
        />
      }
      editLabel='the circle'
      editor={
        <>
          <FormBar
            action={
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
            }
          >
            <MindPicker
              label='Kind of circle'
              value={circle.kind}
              table={table(view.circle_kinds)}
              blocked={busy}
              onPick={(value) => edit.mutate(value as CircleKind)}
            />
            <NodePicker
              label='Bring in a mortal'
              types={MORTALS}
              value={member}
              onChange={setMember}
              blocked={busy}
            />
          </FormBar>
        </>
      }
    >
      <div className='flex min-w-0 flex-col gap-2'>
        {circle.ideology && (
          <Muted variant='caption'>
            {'Spreads the creed '}
            <EntityLink kind='entity' id={String(circle.ideology.id)}>
              {circle.ideology.name}
            </EntityLink>
          </Muted>
        )}
        <PagedList
          items={circle.members}
          initial={12}
          noun={['entry', 'entries']}
          as='div'
          className='flex min-w-0 flex-wrap gap-2'
          itemKey={(item) => item.id}
        >
          {(item) => (
            <div
              key={item.id}
              className='flex min-w-0 items-center gap-1 rounded-full border surface-sheen border-gild/60 bg-card py-0.5 pr-0.5 pl-3'
            >
              {circle.leader?.id === item.id && (
                <Star
                  aria-hidden='true'
                  className='size-icon-xs text-primary'
                />
              )}
              <EntityLink kind='entity' id={String(item.id)}>
                {item.name}
              </EntityLink>
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
            </div>
          )}
        </PagedList>
      </div>
    </ItemRow>
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
        <Muted variant='caption'>
          {place
            ? 'No circle gathers here yet.'
            : 'Not a member of any circle.'}
        </Muted>
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
        <AddBar
          title='Gather a circle here'
          action={
            <Button
              size='sm'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => found.mutate()}
            >
              <Plus />
              Gather
            </Button>
          }
        >
          <MindPicker
            label='Kind of circle'
            value={kind}
            table={table(view.circle_kinds)}
            blocked={busy}
            onPick={setKind}
          />
        </AddBar>
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
    <ItemRow
      icon={spec.icon}
      tone={spec.tone}
      title={`${rank.member.name}: rank ${rank.rank} of ${rank.size}`}
      meta={`${rank.group_label} of ${rank.group.name} · since epoch ${rank.since_epoch}`}
      badges={
        rank.held.length > 0 ? (
          <Badge variant='secondary'>Held</Badge>
        ) : undefined
      }
      actions={
        <RemoveButton
          label={`Take ${rank.member.name}'s place away`}
          busy={busy}
          onClick={() => remove.mutate()}
        />
      }
      editLabel='the place in the order'
      editor={
        <AdjustStats
          id={`rank-${rank.group.id}-${rank.member.id}`}
          inline
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
      }
    >
      <Meter label='Standing' value={rank.dominance} tone='warning' />
    </ItemRow>
  )
}

export function StandingCard({ view, blocked, hold }: Props) {
  const rows = view.ranks.length > 0 ? view.ranks : view.order
  return (
    <MindCard
      title='Pecking order'
      icon={STANDING_ICON}
      hint='Groups rank their members by strength, office, renown and assertiveness; those below may challenge.'
    >
      {rows.length === 0 ? (
        <Muted variant='caption'>
          No pecking order yet. Households, courts, circles, warbands and crews
          of three or more form one.
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
  const stage = useGodAction({
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
  const busy = why(blocked, stage.isPending, fame.isPending, strike.isPending)
  return (
    <MindCard
      title='Contests of wit'
      icon={CONTEST_ICON}
      hint='Riddles, contests of insults, debates, games, trials, songs and tales for honour, a union, a wager, a place, a freedom or a god’s favour.'
      wide
    >
      {view.contests.length === 0 ? (
        <Muted variant='caption'>No contests yet.</Muted>
      ) : (
        <Paged items={view.contests} initial={4} noun={['contest', 'contests']}>
          {(item) => {
            const spec = named(CONTEST_KINDS, item.kind)
            return (
              <ItemRow
                key={item.id}
                icon={spec.icon}
                tone={spec.tone}
                title={`${item.label} for ${item.stake_label.toLowerCase()}`}
                meta={`${item.challenger?.name ?? 'Someone'} against ${item.defender?.name ?? 'someone'}${item.judge ? `, judged by ${item.judge.name}` : ''}${item.place ? ` at ${item.place.name}` : ''}${item.wager > 0 ? ` · wager ${item.wager}` : ''} · epoch ${item.epoch}`}
                badges={
                  <>
                    <Badge
                      variant={item.outcome === 'drawn' ? 'outline' : 'default'}
                    >
                      {OUTCOMES[item.outcome] ?? item.outcome}
                    </Badge>
                    {item.famous && <Badge variant='secondary'>Famous</Badge>}
                  </>
                }
                actions={
                  <>
                    <Button
                      size='icon-sm'
                      variant={item.famous ? 'secondary' : 'ghost'}
                      aria-label={
                        item.famous
                          ? 'Let the bards forget the contest'
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
                    <RemoveButton
                      label='Strike the contest from memory'
                      busy={busy}
                      onClick={() => strike.mutate(item.id)}
                    />
                  </>
                }
              >
                <div className='flex min-w-0 flex-col gap-2'>
                  <PagedList
                    items={item.rounds}
                    initial={12}
                    noun={['entry', 'entries']}
                    as='div'
                    className='flex min-w-0 flex-wrap items-center gap-2'
                    itemKey={(_, index) => `${item.id}-${index}`}
                  >
                    {(round, index) => {
                      const first = Math.round(round[0] ?? 0)
                      const second = Math.round(round[1] ?? 0)
                      return (
                        <Badge
                          key={`${item.id}-${index}`}
                          variant={
                            first > second
                              ? 'default'
                              : first < second
                                ? 'destructive'
                                : 'outline'
                          }
                        >
                          {`Round ${index + 1}: ${first}–${second}`}
                        </Badge>
                      )
                    }}
                  </PagedList>
                  <div className='flex min-w-0 flex-wrap items-center gap-2'>
                    {item.stake_node && (
                      <Muted as='span' variant='caption'>
                        {'The stake: '}
                        <NodeName item={item.stake_node} />
                      </Muted>
                    )}
                    {item.work && (
                      <EntityLink
                        kind='entity'
                        id={String(item.work.id)}
                        showIcon
                      >
                        {item.work.name}
                      </EntityLink>
                    )}
                  </div>
                </div>
                {item.note && <Muted variant='caption'>{item.note}</Muted>}
              </ItemRow>
            )
          }}
        </Paged>
      )}
      {mortal && (
        <AddBar
          title='Stage a contest'
          action={
            <Button
              size='sm'
              disabled={busy !== null || rival === null}
              disabledReason={
                busy ?? (rival === null ? 'Pick an opponent first.' : undefined)
              }
              onClick={() => stage.mutate()}
            >
              <CONTEST_ICON />
              Stage
            </Button>
          }
        >
          <NodePicker
            label='Against'
            types={MORTALS}
            value={rival}
            onChange={setRival}
            blocked={busy}
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
        </AddBar>
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
      hint='Appeals to belief, self-interest, authority, evidence or fear; oratory and fit against stubbornness and passions.'
      wide
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
            <ItemRow
              key={item.id}
              icon={PERSUASION_ICON}
              tone={item.success ? 'success' : 'muted'}
              title={`${item.speaker?.name ?? 'Someone'} to ${item.target?.name ?? 'someone'}`}
              meta={`${item.appeal_label} · ${item.aim_label.toLowerCase()}${item.axis ? ` (${named(VALUE_ICONS, item.axis).label.toLowerCase()})` : ''} · epoch ${item.epoch}`}
              badges={
                <Badge
                  variant={item.success ? 'default' : 'outline'}
                >{`${item.success ? 'Swayed' : 'Unmoved'} · ${item.score}`}</Badge>
              }
              actions={
                <RemoveButton
                  label='Forget the argument'
                  busy={busy}
                  onClick={() => forget.mutate(item.id)}
                />
              }
            />
          )}
        </Paged>
      )}
      <AddBar
        title='Argue'
        action={
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
        }
      >
        <NodePicker
          label='With'
          types={MORTALS}
          value={target}
          onChange={setTarget}
          blocked={busy}
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
      </AddBar>
    </MindCard>
  )
}
