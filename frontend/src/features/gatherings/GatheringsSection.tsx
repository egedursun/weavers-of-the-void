import { useState } from 'react'
import {
  CalendarCheck,
  Coins,
  MapPin,
  PartyPopper,
  Play,
  Star,
  Trash2,
  UserPlus,
  X,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import {
  Chip,
  Facts,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import {
  type GatheringView,
  type GuestView,
  useGatheringAction,
  useNodeGatherings,
} from './api'
import { why } from './history'
import {
  ATTENDANCE_REASONS,
  GATHERING_KINDS,
  GATHERING_OUTCOMES,
  GATHERING_STATUSES,
  GUEST_ROLES,
  MILESTONES,
  table,
} from './labels'
import { Ref, ThingPicker } from './parts'

const ATTENDED = { true: 'Came', false: 'Stayed away' }
const PLACE_TYPES = ['place', 'settlement', 'structure', 'region']

type Edit = { values: EditValues; release: string[] }

function GuestRow({
  gathering,
  guest,
  blocked,
}: {
  gathering: GatheringView
  guest: GuestView
  blocked: string | null
}) {
  const nodeId = guest.node?.id ?? 0
  const set = useGatheringAction(
    'gathering_guest:set',
    (vars: {
      role?: GuestView['role']
      reason?: GuestView['reason']
      attended?: boolean | null
      hold: boolean
    }) => ({
      gathering_id: gathering.id,
      node_id: nodeId,
      role: vars.role ?? guest.role,
      reason: vars.reason ?? guest.reason,
      attended: vars.attended === undefined ? guest.attended : vars.attended,
      hold: vars.hold,
    }),
    'The guest list is set'
  )
  const remove = useGatheringAction(
    'gathering_guest:remove',
    (_: void) => ({ gathering_id: gathering.id, node_id: nodeId }),
    'The guest is struck from the list'
  )
  const busy = why(blocked, set.isPending, remove.isPending)
  const role = GUEST_ROLES[guest.role]
  const reason = ATTENDANCE_REASONS[guest.reason]
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-2.5'>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <role.icon
          aria-hidden='true'
          className='size-icon-xs shrink-0 text-muted-foreground'
        />
        <Ref node={guest.node} empty='someone forgotten' />
        <Chip>{role.label}</Chip>
        <Chip icon={reason.icon}>{reason.label}</Chip>
        {guest.invited && <Chip variant='info'>Invited</Chip>}
        {guest.attended !== null && (
          <Chip variant={guest.attended ? 'success' : 'secondary'}>
            {guest.attended ? 'Came' : 'Stayed away'}
          </Chip>
        )}
        {guest.harmed && <Chip variant='destructive'>Harmed</Chip>}
        {guest.locked && <Badge variant='outline'>Held</Badge>}
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Strike ${guest.node?.name ?? 'this guest'} from the list`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <X />
        </Button>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
        <MindPicker
          label='Role'
          value={guest.role}
          table={table(GUEST_ROLES)}
          blocked={busy}
          onPick={(value) =>
            set.mutate({ role: value as GuestView['role'], hold: true })
          }
        />
        <MindPicker
          label='Why they come'
          value={guest.reason}
          table={table(ATTENDANCE_REASONS)}
          blocked={busy}
          onPick={(value) =>
            set.mutate({ reason: value as GuestView['reason'], hold: true })
          }
        />
        <MindPicker
          label='Came'
          value={guest.attended === null ? '' : String(guest.attended)}
          table={ATTENDED}
          blocked={busy}
          onPick={(value) =>
            set.mutate({ attended: value === 'true', hold: true })
          }
        />
      </div>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Muted variant='caption'>
          A held guest is never struck or changed by the engine.
        </Muted>
        <Switch
          aria-label={`Hold ${guest.node?.name ?? 'this guest'} on the list`}
          checked={guest.locked}
          disabled={busy !== null}
          onCheckedChange={(hold) => set.mutate({ hold })}
        />
      </div>
    </div>
  )
}

function AddGuest({
  gathering,
  blocked,
}: {
  gathering: GatheringView
  blocked: string | null
}) {
  const [node, setNode] = useState<number | null>(null)
  const [role, setRole] = useState<GuestView['role']>('guest')
  const add = useGatheringAction(
    'gathering_guest:set',
    (_: void) => ({
      gathering_id: gathering.id,
      node_id: node ?? 0,
      role,
      reason: 'summoned' as const,
      hold: true,
    }),
    'A guest is summoned'
  )
  const busy = why(blocked, add.isPending)
  const listed = gathering.guests.some((guest) => guest.node?.id === node)
  const missing =
    node === null
      ? 'Choose a guest first'
      : listed
        ? 'This one is already on the list'
        : null
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-3'>
      <ThingPicker
        label='Summon a guest'
        value={node}
        onChange={setNode}
        blocked={busy}
      />
      <MindPicker
        label='As'
        value={role}
        table={table(GUEST_ROLES)}
        blocked={busy}
        onPick={(value) => setRole(value as GuestView['role'])}
      />
      <Button
        size='sm'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() => {
          add.mutate()
          setNode(null)
        }}
      >
        <UserPlus />
        Summon
      </Button>
    </div>
  )
}

function MovePlace({
  edit,
  blocked,
}: {
  edit: (vars: Edit) => void
  blocked: string | null
}) {
  const [place, setPlace] = useState<number | null>(null)
  const missing = place === null ? 'Choose a place first' : null
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
      <ThingPicker
        label='Hold it at'
        value={place}
        onChange={setPlace}
        blocked={blocked}
        types={PLACE_TYPES}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={blocked !== null || missing !== null}
        disabledReason={blocked ?? missing ?? undefined}
        onClick={() => {
          edit({ values: { place_entity_id: place }, release: [] })
          setPlace(null)
        }}
      >
        <MapPin />
        Move it
      </Button>
    </div>
  )
}

function GatheringCard({
  gathering,
  blocked,
}: {
  gathering: GatheringView
  blocked: string | null
}) {
  const edit = useGatheringAction(
    'gathering:edit',
    (vars: Edit) => ({ gathering_id: gathering.id, ...vars }),
    'The gathering is reshaped'
  )
  const hold = useGatheringAction(
    'gathering:hold',
    (_: void) => ({ gathering_id: gathering.id }),
    'The gathering is held'
  )
  const remove = useGatheringAction(
    'gathering:delete',
    (_: void) => ({ gathering_id: gathering.id }),
    'The gathering is gone from the record'
  )
  const busy = why(blocked, edit.isPending, hold.isPending, remove.isPending)
  const kind = GATHERING_KINDS[gathering.kind]
  const status = GATHERING_STATUSES[gathering.status]
  const outcome = gathering.outcome
    ? GATHERING_OUTCOMES[gathering.outcome]
    : null
  const planned = gathering.status === 'planned'
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={
        <span className='flex min-w-0 flex-wrap items-center gap-1.5'>
          {kind.label}
          {gathering.milestone &&
            ` for ${MILESTONES[gathering.milestone].label.toLowerCase()}`}
        </span>
      }
      caption={`${status.label}${outcome ? ` · ${outcome.label}` : ''} · epoch ${gathering.epoch}${gathering.year !== null ? `, year ${gathering.year}` : ''}${gathering.season_name ? `, ${gathering.season_name}` : ''}${gathering.by_player ? ' · by your hand' : ''}`}
      aside={
        <div className='flex shrink-0 flex-wrap items-center gap-1'>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || !planned}
            disabledReason={
              busy ??
              (planned ? undefined : 'Only a planned gathering can be held')
            }
            onClick={() => hold.mutate()}
          >
            <Play />
            Hold now
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => remove.mutate()}
          >
            <Trash2 />
            Remove
          </Button>
        </div>
      }
    >
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Chip icon={status.icon}>{status.label}</Chip>
        {outcome && <Chip icon={outcome.icon}>{outcome.label}</Chip>}
        {gathering.collection_id !== null && (
          <Chip icon={CalendarCheck}>
            {`Told in ${gathering.collection_name ?? 'a history'}`}
          </Chip>
        )}
      </div>
      <Facts
        items={[
          ['Host', <Ref key='host' node={gathering.host} />],
          [
            'Place',
            <Ref key='place' node={gathering.place} empty='nowhere fixed' />,
          ],
          [
            'Honoured',
            <Ref key='honoured' node={gathering.honoured} empty='no one' />,
          ],
          [
            'Tradition',
            <Ref key='tradition' node={gathering.tradition} empty='none' />,
          ],
          [
            'Year',
            gathering.year === null ? 'Not fixed' : String(gathering.year),
          ],
          [
            'Season',
            gathering.season_name ??
              (gathering.season === null
                ? 'Not fixed'
                : `Season ${gathering.season + 1}`),
          ],
          ['Cost', `${gathering.cost} coin`],
          ['Food served', `${plural(gathering.food, 'unit', 'units')}`],
          ['Prestige', String(gathering.prestige)],
        ]}
      />
      {gathering.note && <Muted variant='caption'>{gathering.note}</Muted>}
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>{`Guests (${gathering.guests.length})`}</Label>
        {gathering.guests.length === 0 ? (
          <Muted variant='caption'>No one is on the list yet.</Muted>
        ) : (
          <PagedList
            items={gathering.guests}
            initial={6}
            noun={['guest', 'guests']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(guest) => guest.node?.id ?? 0}
          >
            {(guest) => (
              <GuestRow gathering={gathering} guest={guest} blocked={busy} />
            )}
          </PagedList>
        )}
        <AddGuest gathering={gathering} blocked={busy} />
      </div>
      <MovePlace edit={edit.mutate} blocked={busy} />
      <RecordEditor
        title='Reshape this gathering'
        note='Values you set are held against the engine until you release them.'
        fields={[
          {
            key: 'kind',
            label: 'Kind',
            kind: 'pick',
            table: table(GATHERING_KINDS),
          },
          {
            key: 'status',
            label: 'Status',
            kind: 'pick',
            table: table(GATHERING_STATUSES),
          },
          {
            key: 'outcome',
            label: 'Outcome',
            kind: 'pick',
            table: table(GATHERING_OUTCOMES),
          },
          {
            key: 'milestone',
            label: 'Milestone',
            kind: 'pick',
            table: table(MILESTONES),
          },
          { key: 'epoch', label: 'Epoch', kind: 'number', min: 0 },
          { key: 'year', label: 'Year', kind: 'number', min: 0 },
          {
            key: 'season',
            label: 'Season',
            kind: 'pick',
            table: Object.fromEntries(
              gathering.seasons.map((option) => [
                String(option.position),
                option.name,
              ])
            ),
          },
          { key: 'cost', label: 'Cost in coin', kind: 'number', min: 0 },
          { key: 'food', label: 'Food served', kind: 'number', min: 0 },
          {
            key: 'prestige',
            label: 'Prestige',
            kind: 'number',
            min: 0,
            max: 100,
          },
          { key: 'note', label: 'Note', kind: 'text', long: true },
        ]}
        locked={gathering.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function ConveneForm({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const [kind, setKind] = useState<GatheringView['kind'] | ''>('')
  const [place, setPlace] = useState<number | null>(null)
  const [honoured, setHonoured] = useState<number | null>(null)
  const [milestone, setMilestone] = useState<GatheringView['milestone'] | ''>(
    ''
  )
  const [guest, setGuest] = useState<number | null>(null)
  const [guests, setGuests] = useState<number[]>([])
  const [now, setNow] = useState(true)
  const convene = useGatheringAction(
    'gathering:convene',
    (_: void) => ({
      host_id: nodeId,
      kind: kind === '' ? 'feast' : kind,
      place_id: place,
      honoured_id: honoured,
      milestone: milestone === '' ? null : milestone,
      guests,
      hold_now: now,
    }),
    now ? 'The gathering is held' : 'The gathering is planned'
  )
  const busy = why(blocked, convene.isPending)
  const missing =
    kind === ''
      ? 'Choose a kind of gathering first'
      : kind === 'milestone' && milestone === ''
        ? 'Choose the milestone it marks'
        : null
  return (
    <ForgeCard
      icon={PartyPopper}
      tone='gold'
      title='Convene a gathering'
      note='Call a feast, a wedding, a council or any other gathering with this one as host; guests you summon are bound to come.'
      columns={3}
      meta={<Chip icon={UserPlus}>{`${guests.length} summoned`}</Chip>}
      action={
        <div className='flex min-w-0 flex-wrap items-center justify-end gap-3'>
          <div className='flex items-center gap-2'>
            <Switch
              id={`convene-now-${nodeId}`}
              checked={now}
              disabled={busy !== null}
              onCheckedChange={setNow}
            />
            <Label as='label' htmlFor={`convene-now-${nodeId}`}>
              Hold it at once
            </Label>
          </div>
          <Button
            size='sm'
            disabled={busy !== null || missing !== null}
            disabledReason={busy ?? missing ?? undefined}
            onClick={() => {
              convene.mutate()
              setGuests([])
            }}
          >
            <PartyPopper />
            Convene
          </Button>
        </div>
      }
    >
      <MindPicker
        label='Kind of gathering'
        value={kind}
        table={table(GATHERING_KINDS)}
        blocked={busy}
        onPick={(value) => setKind(value as GatheringView['kind'])}
      />
      <ThingPicker
        label='Place'
        value={place}
        onChange={setPlace}
        blocked={busy}
        types={PLACE_TYPES}
      />
      <ThingPicker
        label='In honour of'
        value={honoured}
        onChange={setHonoured}
        blocked={busy}
      />
      <MindPicker
        label='Milestone'
        value={milestone ?? ''}
        table={table(MILESTONES)}
        blocked={
          busy ??
          (kind === 'milestone' ? null : 'Only a milestone gathering marks one')
        }
        onPick={(value) => setMilestone(value as GatheringView['milestone'])}
      />
      <ThingPicker
        label='Guest'
        value={guest}
        onChange={setGuest}
        blocked={busy}
      />
      <div className='flex min-w-0 flex-col justify-end gap-1'>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || guest === null || guests.includes(guest)}
          disabledReason={
            busy ??
            (guest === null
              ? 'Choose a guest first'
              : guests.includes(guest)
                ? 'Already summoned'
                : undefined)
          }
          onClick={() => {
            if (guest !== null) setGuests([...guests, guest])
            setGuest(null)
          }}
        >
          <UserPlus />
          Add to the list
        </Button>
        {guests.length > 0 && (
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => setGuests([])}
          >
            <X />
            Clear the list
          </Button>
        )}
      </div>
    </ForgeCard>
  )
}

export function GatheringsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeGatherings(nodeId)
  const data = query.data
  const hosted = data?.hosted ?? []
  const attended = data?.attended ?? []
  const prestige = hosted.reduce((sum, row) => sum + row.prestige, 0)
  const spent = hosted.reduce((sum, row) => sum + row.cost, 0)
  return (
    <Section
      id='section-gatherings'
      title='Gatherings'
      description='Feasts, weddings, funerals, councils, tournaments and every other gathering hosted or attended, with their guests.'
      icon={PartyPopper}
      tone='gold'
    >
      <div
        data-surface='GatheringsSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the guest lists' />
        ) : query.isError ? (
          <EmptyState
            icon={PartyPopper}
            size='inline'
            title='The gatherings could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
              <KpiTile
                label='Hosted'
                value={hosted.length}
                icon={PartyPopper}
                tone='gold'
              />
              <KpiTile
                label='Attended'
                value={attended.length}
                icon={UserPlus}
                tone='info'
              />
              <KpiTile
                label='Prestige won'
                value={prestige}
                icon={Star}
                tone='success'
              />
              <KpiTile
                label='Coin spent'
                value={spent}
                icon={Coins}
                tone='warning'
              />
            </div>
            <Label variant='overline'>Hosted</Label>
            {hosted.length === 0 ? (
              <EmptyState
                icon={PartyPopper}
                size='inline'
                title='No gathering hosted yet'
                description='Convene one below, or let the epochs bring them.'
              />
            ) : (
              <PagedList
                items={hosted}
                initial={4}
                noun={['gathering', 'gatherings']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(row) => row.id}
              >
                {(row) => (
                  <GatheringCard gathering={row} blocked={readOnlyReason} />
                )}
              </PagedList>
            )}
            <Label variant='overline'>Attended</Label>
            {attended.length === 0 ? (
              <Muted variant='caption'>Not yet a guest anywhere.</Muted>
            ) : (
              <PagedList
                items={attended}
                initial={4}
                noun={['gathering', 'gatherings']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(row) => row.id}
              >
                {(row) => (
                  <GatheringCard gathering={row} blocked={readOnlyReason} />
                )}
              </PagedList>
            )}
          </>
        )}
        <ConveneForm nodeId={nodeId} blocked={readOnlyReason} />
      </div>
    </Section>
  )
}
