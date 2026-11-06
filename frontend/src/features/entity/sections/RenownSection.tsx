import { useState } from 'react'
import {
  Award,
  EyeOff,
  Plus,
  ShieldCheck,
  Trash2,
  VolumeX,
  X,
} from 'lucide-react'
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
  Medallion,
  Paged,
  Section,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { EntityPicker } from '@/features/wars/military/controls'
import { named } from '../mind/labels'
import { ControlPanel, MindCard, MindPicker } from '../mind/parts'
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

type Props = { view: Renown; blocked: string | null; hold: boolean }

function table(
  items: { key: string; label: string }[]
): Record<string, string> {
  return Object.fromEntries(items.map((item) => [item.key, item.label]))
}

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
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
    <div className='flex min-w-0 flex-col gap-2 rounded-md border p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text
            weight='semibold'
            truncate
          >{`${row.label}${row.skill ? ` (${row.skill.replaceAll('_', ' ')})` : ''}`}</Text>
          {other && (
            <Muted variant='caption'>
              {viewer ? 'Of ' : 'In '}
              <EntityLink kind='entity' id={String(other.id)}>
                {other.name}
              </EntityLink>
              {` · heard in epoch ${row.heard_epoch}${row.held ? ' · held' : ''}`}
            </Muted>
          )}
        </div>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Forget this reputation'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <X />
        </Button>
      </div>
      <Progress
        value={row.value}
        size='sm'
        tone={
          spec.tone === 'danger' || spec.tone === 'warning'
            ? 'destructive'
            : 'success'
        }
        aria-label={`${row.label} ${row.value}`}
      />
      <AdjustStats
        id={`reputation-${row.id}`}
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
    </div>
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
          : 'Each community knows this one for its own reasons: deeds seen, deeds heard of in rumours, read through what it holds right.'
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
        <Paged items={rows} initial={4} noun={['reputation', 'reputations']}>
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
      )}
      <div className='grid min-w-0 grid-cols-1 gap-2 @xl/mind:grid-cols-3'>
        <EntityPicker
          label={viewer ? 'Of whom' : 'Where'}
          types={viewer ? ANYONE : PLACES}
          value={other}
          onChange={setOther}
          blocked={busy}
          icon={RENOWN_ICON}
        />
        <MindPicker
          label='For'
          value={axis}
          table={table(view.axes)}
          blocked={busy}
          onPick={setAxis}
        />
        <Button
          size='sm'
          disabled={busy !== null || other === null}
          disabledReason={
            busy ?? (other === null ? 'Pick who or where first.' : undefined)
          }
          onClick={() => add.mutate()}
        >
          <Plus />
          Spread the word
        </Button>
      </div>
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
  return (
    <MindCard
      title='Standing as a ruler'
      icon={STANDING_ICON}
      hint='Prestige buys acceptance of laws, piety the clergy’s loyalty, dread silences dissent; tyranny feeds faction pressure.'
      wide
    >
      {standing === null ? (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Muted variant='caption'>
            No standing yet. It grows each epoch while they rule.
          </Muted>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => begin.mutate()}
          >
            <Plus />
            Give them standing
          </Button>
        </div>
      ) : (
        <>
          <div className='grid min-w-0 grid-cols-2 gap-3 @xl/mind:grid-cols-4'>
            {(['prestige', 'piety', 'dread', 'tyranny'] as const).map((key) => {
              const spec = named(CURRENCIES, key)
              return (
                <div key={key} className='flex min-w-0 flex-col gap-1'>
                  <div className='flex min-w-0 items-center gap-2'>
                    <spec.icon
                      aria-hidden='true'
                      className='size-icon-sm text-muted-foreground'
                    />
                    <Muted variant='caption'>{spec.label}</Muted>
                    <Text
                      variant='caption'
                      weight='semibold'
                      className='ml-auto'
                    >
                      {standing[key]}
                    </Text>
                  </div>
                  <Progress
                    value={standing[key]}
                    size='sm'
                    tone={
                      key === 'dread' || key === 'tyranny'
                        ? 'destructive'
                        : 'success'
                    }
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
            {standing.silenced_until !== null &&
              standing.silenced_until >= standing.updated_epoch && (
                <Badge variant='secondary'>{`Dissent silenced until epoch ${standing.silenced_until}`}</Badge>
              )}
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
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
          <AdjustStats
            id={`standing-${view.node_id}`}
            groups={[
              {
                title: 'Standing (0 to 100)',
                fields: (
                  ['prestige', 'piety', 'dread', 'tyranny'] as const
                ).map((key) => ({
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
    <div className='flex min-w-0 flex-col gap-2 rounded-md border p-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <Text weight='semibold'>{`A deed of ${deed.label.toLowerCase()}${deed.act ? ` (${deed.act.replaceAll('_', ' ')})` : ''}`}</Text>
        {deed.token && <Badge variant='secondary'>Token kept</Badge>}
        <div className='ml-auto flex shrink-0 items-center gap-1'>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={deed.token ? 'Lose the token' : 'Give the doer a token'}
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => token.mutate()}
          >
            <Award />
          </Button>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Strike the deed from memory'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <X />
          </Button>
        </div>
      </div>
      <Muted variant='caption'>
        {`${deed.doer?.name ?? 'Someone'}${deed.place ? ` in ${deed.place.name}` : ''} · size ${deed.magnitude} · seen by ${deed.witnesses} · epoch ${deed.epoch}`}
      </Muted>
      <div className='flex min-w-0 flex-col gap-1'>
        {deed.claims.map((item) => (
          <div key={item.id} className='flex min-w-0 items-center gap-2'>
            <Badge variant={item.kind === 'false' ? 'destructive' : 'outline'}>
              {item.kind_label}
            </Badge>
            <Text
              variant='caption'
              truncate
              className='flex-1'
            >{`${item.claimant?.name ?? 'Someone'} · ${item.status_label} · credited ${item.credited}`}</Text>
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
            <Button
              size='icon-sm'
              variant='ghost'
              aria-label='Withdraw the claim'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => drop.mutate(item.id)}
            >
              <X />
            </Button>
          </div>
        ))}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @xl/mind:grid-cols-3'>
        <EntityPicker
          label='Claimed by'
          types={MORTALS}
          value={claimant}
          onChange={setClaimant}
          blocked={busy}
          icon={ShieldCheck}
        />
        <MindPicker
          label='Claim'
          value={kind}
          table={table(view.claim_kinds)}
          blocked={busy}
          onPick={setKind}
        />
        <Button
          size='sm'
          disabled={busy !== null || claimant === null}
          disabledReason={
            busy ?? (claimant === null ? 'Pick a claimant first.' : undefined)
          }
          onClick={() => claim.mutate()}
        >
          <Plus />
          Add claim
        </Button>
      </div>
      <AdjustStats
        id={`deed-${deed.id}`}
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
    </div>
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
      hint='Glory goes to whoever is believed: comrades share it, the vain may claim it falsely, witnesses, tokens and contests expose them.'
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
      <div className='grid min-w-0 grid-cols-1 gap-2 @xl/mind:grid-cols-3'>
        <MindPicker
          label='A deed of'
          value={axis}
          table={table(view.axes)}
          blocked={busy}
          onPick={setAxis}
        />
        <EntityPicker
          label='Seen in'
          types={PLACES}
          value={place}
          onChange={setPlace}
          blocked={busy}
          icon={DEED_ICON}
        />
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => record.mutate()}
        >
          <DEED_ICON />
          Set it down
        </Button>
      </div>
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
    >
      {view.trades.length === 0 ? (
        <Muted variant='caption'>No lore has changed hands yet.</Muted>
      ) : (
        <Paged items={view.trades} initial={4} noun={['trade', 'trades']}>
          {(item) => (
            <div
              key={item.id}
              className='flex min-w-0 items-center gap-2 rounded-md border p-2'
            >
              <PRICE_ICON
                aria-hidden='true'
                className='size-icon-sm text-muted-foreground'
              />
              <div className='flex min-w-0 flex-1 flex-col'>
                <Text
                  weight='semibold'
                  truncate
                >{`${item.kind_label}: ${item.subject?.name ?? item.key.replaceAll('_', ' ')}`}</Text>
                <Muted variant='caption'>{`${item.seller?.name ?? 'Someone'} to ${item.buyer?.name ?? 'someone'} · worth ${item.value} · paid in ${item.price_label.toLowerCase()} · epoch ${item.epoch}`}</Muted>
              </div>
              <Button
                size='icon-sm'
                variant='ghost'
                aria-label='Strike the trade from the record'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => strike.mutate(item.id)}
              >
                <X />
              </Button>
            </div>
          )}
        </Paged>
      )}
      <div className='flex min-w-0 flex-col gap-2'>
        <EntityPicker
          label='Give lore to'
          types={ANYONE}
          value={buyer}
          onChange={setBuyer}
          blocked={busy}
          icon={LORE_ICON}
        />
        <MindPicker
          label='Kind of lore'
          value={kind}
          table={table(view.lore_kinds)}
          blocked={busy}
          onPick={setKind}
        />
        <Input
          aria-label='Which piece of lore'
          placeholder='Technique key, or site, region or prophecy'
          value={key}
          onChange={(event) => setKey(event.target.value)}
          disabled={busy !== null}
        />
        <EntityPicker
          label='About (site, land or prophecy)'
          types={['place', 'region', 'prophecy']}
          value={subject}
          onChange={setSubject}
          blocked={busy}
          icon={LORE_ICON}
        />
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => sell.mutate()}
        >
          <LORE_ICON />
          Pass it on
        </Button>
      </div>
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
      description='What each community thinks of this one and what this one thinks of others, a ruler’s prestige, piety, dread and tyranny, deeds and who claims them, and lore traded.'
      icon={RENOWN_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-1 gap-3 @md/mind:grid-cols-2 @3xl/mind:grid-cols-4'>
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
            value={`${places} places`}
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
        <div className='grid min-w-0 grid-cols-1 gap-3 @xl/mind:grid-cols-2'>
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
          note='Values you set here are held against the world while the switch is on. Every change goes into the ledger and can be undone.'
          hold={hold}
          onHold={setHold}
        >
          <Muted variant='caption'>
            Reputations fade where nothing renews them; held ones stay.
          </Muted>
        </ControlPanel>
      </div>
    </Section>
  )
}
