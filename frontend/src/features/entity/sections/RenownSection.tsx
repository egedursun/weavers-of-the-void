import { useState } from 'react'
import { Award, EyeOff, Plus, Trash2, VolumeX, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Paged,
  Section,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { named } from '../mind/labels'
import {
  AddBar,
  ControlPanel,
  FormBar,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'
import {
  type DeedRecord,
  type LocalReputation,
  type Renown,
  type ReputationAxis,
  useRenown,
} from '../renown/api'
import {
  AXES,
  CURRENCIES,
  DEED_ICON,
  LORE_ICON,
  PRICE_ICON,
  RENOWN_ICON,
  STANDING_ICON,
} from '../renown/labels'

const SPAN = 100
const WORKING = 'Working on it.'
const ANYONE = [
  'mortal',
  'house',
  'polity',
  'settlement',
  'people',
  'faction',
  'cult',
]
const PLACES = ['settlement', 'people', 'polity', 'region']
const MORTALS = ['mortal']
const ABOUT = ['place', 'region', 'prophecy']
const STANDINGS = ['prestige', 'piety', 'dread', 'tyranny'] as const
const HARMFUL = new Set([
  'cruelty',
  'trickery',
  'troublemaker',
  'dread',
  'tyranny',
])

type Props = { view: Renown; blocked: string | null; hold: boolean }

function table(
  items: { key: string; label: string }[]
): Record<string, string> {
  return Object.fromEntries(items.map((item) => [item.key, item.label]))
}

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
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

function Gauge({
  label,
  value,
  harmful,
}: {
  label: string
  value: number
  harmful: boolean
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Muted variant='caption'>{label}</Muted>
        <Text variant='caption' weight='semibold'>
          {value}
        </Text>
      </div>
      <Progress
        value={value}
        size='sm'
        tone={harmful ? 'destructive' : 'success'}
        aria-label={`${label} ${value}`}
      />
    </div>
  )
}

function ReputationRow({
  row,
  hold,
  blocked,
  viewer,
}: {
  row: LocalReputation
  hold: boolean
  blocked: string | null
  viewer: boolean
}) {
  const spec = named(AXES, row.axis)
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/renown:remove', {
          body: { reputation_id: row.id },
        })
      ),
  })
  const busy = why(blocked, remove.isPending)
  const other = viewer ? row.subject : row.community
  return (
    <ItemRow
      icon={spec.icon}
      tone={spec.tone}
      title={
        other ? (
          <EntityLink kind='entity' id={String(other.id)}>
            {other.name}
          </EntityLink>
        ) : (
          'Unknown'
        )
      }
      meta={`${row.label}${row.skill ? ` (${row.skill.replaceAll('_', ' ')})` : ''} · heard in epoch ${row.heard_epoch}`}
      badges={row.held ? <Badge variant='secondary'>Held</Badge> : undefined}
      actions={
        <RemoveButton
          label='Forget this reputation'
          busy={busy}
          onClick={() => remove.mutate()}
        />
      }
      editLabel='how strongly they are known for it'
      editor={
        <AdjustStats
          id={`reputation-${row.id}`}
          inline
          groups={[
            {
              title: 'How strongly they are known for it',
              fields: [
                {
                  key: 'value',
                  label: row.label,
                  value: row.value,
                  min: 0,
                  max: SPAN,
                },
              ],
            },
          ]}
          run={({ value }) =>
            unwrap(
              api.POST('/api/actions/renown:set', {
                body: {
                  subject_id: row.subject?.id ?? 0,
                  community_id: row.community?.id ?? 0,
                  axis: row.axis,
                  skill: row.skill,
                  value,
                  hold,
                },
              })
            )
          }
        />
      }
    >
      <Gauge
        label={row.label}
        value={row.value}
        harmful={HARMFUL.has(row.axis)}
      />
    </ItemRow>
  )
}

function ReputationsCard({
  view,
  blocked,
  hold,
  viewer,
}: Props & { viewer: boolean }) {
  const [other, setOther] = useState<number | null>(null)
  const [axis, setAxis] = useState<string>('heroism')
  const rows = viewer ? view.views : view.reputations
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/renown:set', {
          body: {
            subject_id: viewer ? (other ?? 0) : view.node_id,
            community_id: viewer ? view.node_id : (other ?? 0),
            axis: axis as ReputationAxis,
            value: 50,
            hold,
          },
        })
      ),
  })
  const busy = why(blocked, add.isPending)
  return (
    <MindCard
      title={viewer ? 'What this place thinks of others' : 'Known for'}
      icon={RENOWN_ICON}
      hint={
        viewer
          ? 'Each community keeps its own view of those it has seen or heard of, read through its ethics.'
          : 'Each community knows them for its own reasons: deeds seen or heard of in rumours, read through what it holds right.'
      }
      wide
    >
      {rows.length === 0 ? (
        <Muted variant='caption'>
          {viewer
            ? 'This place holds no view of anyone yet.'
            : 'No community knows them for anything yet.'}
        </Muted>
      ) : (
        <div className='grid min-w-0 grid-cols-1 gap-3 @xl/mind:grid-cols-2'>
          <Paged items={rows} initial={6} noun={['reputation', 'reputations']}>
            {(row) => (
              <ReputationRow
                key={row.id}
                row={row}
                hold={hold}
                blocked={blocked}
                viewer={viewer}
              />
            )}
          </Paged>
        </div>
      )}
      <AddBar
        title='Spread the word'
        action={
          <Button
            size='sm'
            disabled={busy !== null || other === null}
            disabledReason={
              busy ?? (other === null ? 'Pick who or where first.' : undefined)
            }
            onClick={() => add.mutate()}
          >
            <Plus />
            Spread
          </Button>
        }
      >
        <NodePicker
          label={viewer ? 'Of whom' : 'Where'}
          types={viewer ? ANYONE : PLACES}
          value={other}
          onChange={setOther}
          blocked={busy}
        />
        <MindPicker
          label='Known for'
          value={axis}
          table={table(view.axes)}
          blocked={busy}
          onPick={setAxis}
        />
      </AddBar>
    </MindCard>
  )
}

function StandingCard({ view, blocked, hold }: Props) {
  const standing = view.standing
  const begin = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/standing:set', {
          body: { subject_id: view.node_id, prestige: 0, hold: false },
        })
      ),
  })
  const silence = useGodAction({
    run: (until: number) =>
      unwrap(
        api.POST('/api/actions/standing:set', {
          body: { subject_id: view.node_id, silenced_until: until, hold },
        })
      ),
  })
  const wipe = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/standing:remove', {
          body: { subject_id: view.node_id },
        })
      ),
  })
  const busy = why(blocked, begin.isPending, silence.isPending, wipe.isPending)
  const silenced =
    standing !== null &&
    standing.silenced_until !== null &&
    standing.silenced_until >= standing.updated_epoch
  return (
    <MindCard
      title='Standing as a ruler'
      icon={STANDING_ICON}
      hint='Prestige buys acceptance of laws, piety the clergy’s loyalty, dread silences dissent; tyranny feeds faction pressure.'
      wide
    >
      {standing === null ? (
        <EmptyState
          icon={STANDING_ICON}
          size='compact'
          title='No standing yet'
          description='It grows each epoch while they rule. You can give it now.'
          action={
            <Button
              size='sm'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => begin.mutate()}
            >
              <Plus />
              Give standing
            </Button>
          }
        />
      ) : (
        <>
          <div className='grid min-w-0 grid-cols-2 gap-3 @xl/mind:grid-cols-4'>
            {STANDINGS.map((key) => {
              const spec = named(CURRENCIES, key)
              return (
                <div
                  key={key}
                  className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/10 p-3'
                >
                  <div className='flex min-w-0 items-center gap-2'>
                    <spec.icon
                      aria-hidden='true'
                      className='size-icon-sm text-muted-foreground'
                    />
                    <Label variant='overline'>{spec.label}</Label>
                  </div>
                  <Stat value={standing[key]} size='kpi' />
                  <Progress
                    value={standing[key]}
                    size='sm'
                    tone={HARMFUL.has(key) ? 'destructive' : 'success'}
                    aria-label={`${spec.label} ${standing[key]}`}
                  />
                </div>
              )
            })}
          </div>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            {standing.realm && (
              <Muted variant='caption'>
                {'Rules '}
                <EntityLink kind='entity' id={String(standing.realm.id)}>
                  {standing.realm.name}
                </EntityLink>
              </Muted>
            )}
            {silenced && (
              <Badge variant='secondary'>{`Dissent silenced until epoch ${standing.silenced_until}`}</Badge>
            )}
            <div className='ml-auto flex shrink-0 flex-wrap items-center gap-2'>
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null || silenced}
                disabledReason={
                  busy ??
                  (silenced ? 'Dissent is already silenced.' : undefined)
                }
                onClick={() => silence.mutate(standing.updated_epoch + 3)}
              >
                <VolumeX />
                Silence dissent
              </Button>
              <Button
                size='sm'
                variant='ghost'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => wipe.mutate()}
              >
                <Trash2 />
                Wipe clean
              </Button>
            </div>
          </div>
          <AdjustStats
            id={`standing-${view.node_id}`}
            groups={[
              {
                title: 'Standing (0 to 100)',
                fields: STANDINGS.map((key) => ({
                  key,
                  label: named(CURRENCIES, key).label,
                  value: standing[key],
                  min: 0,
                  max: SPAN,
                })),
              },
            ]}
            run={({ key, value }) =>
              unwrap(
                api.POST('/api/actions/standing:set', {
                  body: { subject_id: view.node_id, [key]: value, hold },
                })
              )
            }
          />
        </>
      )}
    </MindCard>
  )
}

function DeedRow({ deed, view, blocked, hold }: { deed: DeedRecord } & Props) {
  const [claimant, setClaimant] = useState<number | null>(null)
  const [kind, setKind] = useState<string>('shared')
  const spec = named(AXES, deed.axis)
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/deed:remove', { body: { deed_id: deed.id } })
      ),
  })
  const token = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/deed:edit', {
          body: { deed_id: deed.id, token: !deed.token, hold },
        })
      ),
  })
  const expose = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/deed_claim:expose', { body: { claim_id: id } })
      ),
  })
  const drop = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/deed_claim:remove', { body: { claim_id: id } })
      ),
  })
  const claim = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/deed_claim:set', {
          body: {
            deed_id: deed.id,
            claimant_id: claimant ?? 0,
            kind: kind as 'true' | 'shared' | 'false',
            status: 'standing',
            hold,
          },
        })
      ),
  })
  const busy = why(
    blocked,
    strike.isPending,
    token.isPending,
    expose.isPending,
    drop.isPending,
    claim.isPending
  )
  return (
    <ItemRow
      icon={spec.icon}
      tone={spec.tone}
      title={`A deed of ${deed.label.toLowerCase()}${deed.act ? ` (${deed.act.replaceAll('_', ' ')})` : ''}`}
      meta={`${deed.doer?.name ?? 'Someone'}${deed.place ? ` in ${deed.place.name}` : ''} · size ${deed.magnitude} · seen by ${deed.witnesses} · epoch ${deed.epoch}`}
      badges={
        deed.token ? <Badge variant='secondary'>Token kept</Badge> : undefined
      }
      actions={
        <>
          <Button
            size='icon-sm'
            variant={deed.token ? 'secondary' : 'ghost'}
            aria-label={
              deed.token ? 'Take the token away' : 'Give the doer a token'
            }
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => token.mutate()}
          >
            <Award />
          </Button>
          <RemoveButton
            label='Strike the deed from memory'
            busy={busy}
            onClick={() => strike.mutate()}
          />
        </>
      }
      editLabel='claims and size'
      editor={
        <>
          <FormBar
            action={
              <Button
                size='sm'
                disabled={busy !== null || claimant === null}
                disabledReason={
                  busy ??
                  (claimant === null ? 'Pick a claimant first.' : undefined)
                }
                onClick={() => claim.mutate()}
              >
                <Plus />
                Add claim
              </Button>
            }
          >
            <NodePicker
              label='Claimed by'
              types={MORTALS}
              value={claimant}
              onChange={setClaimant}
              blocked={busy}
            />
            <MindPicker
              label='Claim'
              value={kind}
              table={table(view.claim_kinds)}
              blocked={busy}
              onPick={setKind}
            />
          </FormBar>
          <AdjustStats
            id={`deed-${deed.id}`}
            inline
            groups={[
              {
                title: 'Size of the deed',
                fields: [
                  {
                    key: 'magnitude',
                    label: 'Size',
                    value: deed.magnitude,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ value }) =>
              unwrap(
                api.POST('/api/actions/deed:edit', {
                  body: { deed_id: deed.id, magnitude: value, hold },
                })
              )
            }
          />
        </>
      }
    >
      <div className='flex min-w-0 flex-col divide-y rounded-md border bg-background'>
        {deed.claims.map((item) => (
          <div
            key={item.id}
            className='flex min-w-0 items-center gap-2 px-3 py-2'
          >
            <Badge
              variant={
                item.kind === 'false'
                  ? 'destructive'
                  : item.kind === 'true'
                    ? 'default'
                    : 'outline'
              }
            >
              {item.kind_label}
            </Badge>
            <Text variant='caption' truncate className='flex-1'>
              {item.claimant?.name ?? 'Someone'}
            </Text>
            <Muted variant='caption'>{`${item.status_label} · credited ${item.credited}`}</Muted>
            {item.kind === 'false' && item.status === 'standing' && (
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label='Expose the false claim'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => expose.mutate(item.id)}
              >
                <EyeOff />
              </Button>
            )}
            <RemoveButton
              label='Withdraw the claim'
              busy={busy}
              onClick={() => drop.mutate(item.id)}
            />
          </div>
        ))}
      </div>
    </ItemRow>
  )
}

function DeedsCard({ view, blocked, hold }: Props) {
  const [axis, setAxis] = useState<string>('heroism')
  const [place, setPlace] = useState<number | null>(null)
  const record = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/deed:record', {
          body: {
            doer_id: view.node_id,
            axis: axis as ReputationAxis,
            magnitude: 30,
            place_id: place,
            token: false,
          },
        })
      ),
  })
  const busy = why(blocked, record.isPending)
  return (
    <MindCard
      title='Deeds and claims'
      icon={DEED_ICON}
      hint='Glory goes to whoever is believed: comrades share it, the vain claim it falsely, and witnesses, tokens and contests expose them.'
      wide
    >
      {view.deeds.length === 0 ? (
        <Muted variant='caption'>No deeds set down yet.</Muted>
      ) : (
        <Paged items={view.deeds} initial={3} noun={['deed', 'deeds']}>
          {(deed) => (
            <DeedRow
              key={deed.id}
              deed={deed}
              view={view}
              blocked={blocked}
              hold={hold}
            />
          )}
        </Paged>
      )}
      <AddBar
        title='Set down a deed'
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => record.mutate()}
          >
            <DEED_ICON />
            Set it down
          </Button>
        }
      >
        <MindPicker
          label='A deed of'
          value={axis}
          table={table(view.axes)}
          blocked={busy}
          onPick={setAxis}
        />
        <NodePicker
          label='Seen in'
          types={PLACES}
          value={place}
          onChange={setPlace}
          blocked={busy}
        />
      </AddBar>
    </MindCard>
  )
}

function LoreCard({ view, blocked }: Props) {
  const [buyer, setBuyer] = useState<number | null>(null)
  const [kind, setKind] = useState<string>('technique')
  const [key, setKey] = useState('')
  const [subject, setSubject] = useState<number | null>(null)
  const sell = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/lore_trade:make', {
          body: {
            seller_id: view.node_id,
            buyer_id: buyer ?? 0,
            kind: kind as 'technique' | 'site' | 'map' | 'prophecy',
            key: key.trim(),
            subject_id: subject,
          },
        })
      ),
  })
  const strike = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/lore_trade:remove', { body: { trade_id: id } })
      ),
  })
  const busy = why(blocked, sell.isPending, strike.isPending)
  const missing =
    buyer === null
      ? 'Pick who receives it.'
      : key.trim() === ''
        ? 'Name the piece of lore.'
        : null
  return (
    <MindCard
      title='Lore as currency'
      icon={LORE_ICON}
      hint='Techniques, hidden sites, maps and prophecies are worth more the fewer hold them; each telling makes them cheaper.'
      wide
    >
      {view.trades.length === 0 ? (
        <Muted variant='caption'>No lore has changed hands yet.</Muted>
      ) : (
        <Paged items={view.trades} initial={4} noun={['trade', 'trades']}>
          {(item) => (
            <ItemRow
              key={item.id}
              icon={PRICE_ICON}
              tone='gold'
              title={`${item.kind_label}: ${item.subject?.name ?? item.key.replaceAll('_', ' ')}`}
              meta={`${item.seller?.name ?? 'Someone'} to ${item.buyer?.name ?? 'someone'} · epoch ${item.epoch}`}
              badges={
                <Badge variant='outline'>{`Worth ${item.value} · ${item.price_label.toLowerCase()}`}</Badge>
              }
              actions={
                <RemoveButton
                  label='Strike the trade from the record'
                  busy={busy}
                  onClick={() => strike.mutate(item.id)}
                />
              }
            />
          )}
        </Paged>
      )}
      <AddBar
        title='Pass on a piece of lore'
        action={
          <Button
            size='sm'
            disabled={busy !== null || missing !== null}
            disabledReason={busy ?? missing ?? undefined}
            onClick={() => sell.mutate()}
          >
            <LORE_ICON />
            Pass it on
          </Button>
        }
      >
        <NodePicker
          label='To'
          types={ANYONE}
          value={buyer}
          onChange={setBuyer}
          blocked={busy}
        />
        <MindPicker
          label='Kind of lore'
          value={kind}
          table={table(view.lore_kinds)}
          blocked={busy}
          onPick={setKind}
        />
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor={`lore-key-${view.node_id}`}>
            Which piece
          </Label>
          <Input
            id={`lore-key-${view.node_id}`}
            placeholder='Technique key, or site, region or prophecy'
            value={key}
            onChange={(event) => setKey(event.target.value)}
            disabled={busy !== null}
          />
        </div>
        <NodePicker
          label='About'
          types={ABOUT}
          value={subject}
          onChange={setSubject}
          blocked={busy}
        />
      </AddBar>
    </MindCard>
  )
}

export function RenownSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useRenown(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section
        id='section-renown'
        title='Reputation and standing'
        icon={RENOWN_ICON}
      >
        <EmptyState
          icon={RENOWN_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  const blocked = reason()
  const places = new Set(view.reputations.map((row) => row.community?.id)).size
  return (
    <Section
      id='section-renown'
      title='Reputation and standing'
      description='What each community thinks of this one and what this one thinks of others; a ruler’s standing; deeds and who claims them; lore traded.'
      icon={RENOWN_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-2 gap-3 @3xl/mind:grid-cols-4'>
          <KpiTile
            label='Glory'
            value={view.glory}
            icon={RENOWN_ICON}
            tone='gold'
            meter={{ value: view.glory, max: SPAN, label: 'Glory' }}
          />
          <KpiTile
            label='Infamy'
            value={view.infamy}
            icon={RENOWN_ICON}
            tone='danger'
            meter={{ value: view.infamy, max: SPAN, label: 'Infamy' }}
          />
          <KpiTile
            label='Known in'
            value={`${places} ${places === 1 ? 'place' : 'places'}`}
            icon={RENOWN_ICON}
            tone='verdigris'
          />
          <KpiTile
            label='Deeds'
            value={view.deeds.length}
            icon={DEED_ICON}
            tone='warning'
          />
        </div>
        <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
          <ReputationsCard
            view={view}
            blocked={blocked}
            hold={hold}
            viewer={false}
          />
          {(view.views.length > 0 || view.reputations.length === 0) && (
            <ReputationsCard view={view} blocked={blocked} hold={hold} viewer />
          )}
          {(view.ruler || view.standing !== null) && (
            <StandingCard view={view} blocked={blocked} hold={hold} />
          )}
          <DeedsCard view={view} blocked={blocked} hold={hold} />
          <LoreCard view={view} blocked={blocked} hold={hold} />
        </div>
        <ControlPanel
          title='Hold what you set'
          note='Values you set here are held against the world while the switch is on. Reputations fade where nothing renews them; held ones stay. Every change goes into the ledger and can be undone.'
          hold={hold}
          onHold={setHold}
        >
          {null}
        </ControlPanel>
      </div>
    </Section>
  )
}
