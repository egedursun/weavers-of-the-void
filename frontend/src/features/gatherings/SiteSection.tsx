import { useState } from 'react'
import {
  Castle,
  DoorOpen,
  FastForward,
  Flag,
  Footprints,
  Plus,
  Shovel,
  Trash2,
  X,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { techniqueValues, skillKindValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import {
  Chip,
  Facts,
  ForgeCard,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import {
  type ContentView,
  type DigView,
  type FeatureView,
  type HolderView,
  type RoomView,
  type SiteView,
  type StageView,
  useGatheringAction,
  useSite,
} from './api'
import { why } from './history'
import {
  BATTLEFIELD_FEATURES,
  CHALLENGES,
  CONTENT_KINDS,
  DIG_FINDS,
  DIG_RISKS,
  DIG_STAGES,
  DIG_STATUSES,
  ROOM_KINDS,
  table,
  words,
} from './labels'
import { Ref, ThingPicker } from './parts'

const SPAN = 100
const DELVERS = ['mortal', 'beast']
const HOLDERS = undefined
const SKILLS = Object.fromEntries(
  skillKindValues.map((value) => [value, words(value)])
)
const TECHNIQUES = Object.fromEntries(
  techniqueValues.map((value) => [value, words(value)])
)

type Edit = { values: EditValues; release: string[] }

function ContentChip({
  content,
  blocked,
}: {
  content: ContentView
  blocked: string | null
}) {
  const remove = useGatheringAction(
    'room_content:remove',
    (_: void) => ({ content_id: content.id }),
    'It is taken from the room'
  )
  const busy = why(blocked, remove.isPending)
  const look = CONTENT_KINDS[content.kind]
  return (
    <Badge variant='outline'>
      <look.icon />
      {content.entity ? <Ref node={content.entity} /> : look.label}
      {` · ${content.strength}`}
      {content.locked && ' · held'}
      <Button
        size='icon-sm'
        variant='ghost'
        aria-label={`Take the ${look.label.toLowerCase()} from the room`}
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => remove.mutate()}
      >
        <X />
      </Button>
    </Badge>
  )
}

function AddContent({
  room,
  blocked,
}: {
  room: RoomView
  blocked: string | null
}) {
  const [kind, setKind] = useState<ContentView['kind'] | ''>('')
  const [thing, setThing] = useState<number | null>(null)
  const [strength, setStrength] = useState('40')
  const add = useGatheringAction(
    'room_content:add',
    (_: void) => ({
      room_id: room.id,
      kind: kind === '' ? 'trap' : kind,
      entity_id: thing,
      strength: Math.max(0, Math.min(SPAN, Number(strength) || 0)),
    }),
    'It waits in the room'
  )
  const busy = why(blocked, add.isPending)
  const missing =
    kind === ''
      ? 'Choose what waits in the room'
      : kind !== 'trap' && thing === null
        ? 'Choose the thing itself; only a trap stands alone'
        : null
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-4'>
      <MindPicker
        label='Place in the room'
        value={kind}
        table={table(CONTENT_KINDS)}
        blocked={busy}
        onPick={(value) => setKind(value as ContentView['kind'])}
      />
      <ThingPicker
        label='The thing'
        value={thing}
        onChange={setThing}
        blocked={busy ?? (kind === 'trap' ? 'A trap needs no thing' : null)}
        types={
          kind === 'item'
            ? ['item']
            : kind === 'spirit'
              ? ['spirit']
              : ['beast', 'species']
        }
      />
      <MindPicker
        label='Strength'
        value={strength}
        table={Object.fromEntries(
          [10, 20, 40, 60, 80, 100].map((value) => [
            String(value),
            String(value),
          ])
        )}
        blocked={busy}
        onPick={setStrength}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() => add.mutate()}
      >
        <Plus />
        Place it
      </Button>
    </div>
  )
}

function RoomCard({
  room,
  blocked,
}: {
  room: RoomView
  blocked: string | null
}) {
  const edit = useGatheringAction(
    'site_room:edit',
    (vars: Edit) => ({ room_id: room.id, ...vars }),
    'The room is reshaped'
  )
  const remove = useGatheringAction(
    'site_room:delete',
    (_: void) => ({ room_id: room.id }),
    'The room is sealed away'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const look = ROOM_KINDS[room.kind]
  const challenge = CHALLENGES[room.challenge]
  return (
    <RecordRow
      icon={look.icon}
      tone={room.cleared_epoch === null ? look.tone : 'success'}
      title={`${room.position + 1}. ${look.label}`}
      caption={`${challenge.label} · difficulty ${room.difficulty}${room.cleared_epoch !== null ? ` · cleared in epoch ${room.cleared_epoch}` : ' · not yet cleared'}`}
      aside={
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
      }
    >
      <Meter
        label='Difficulty'
        value={room.difficulty}
        tone='warning'
        icon={challenge.icon}
      />
      {room.cleared_by && (
        <Muted variant='caption'>
          Cleared by <Ref node={room.cleared_by} />
        </Muted>
      )}
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {room.contents.length === 0 ? (
          <Muted variant='caption'>The room stands empty.</Muted>
        ) : (
          room.contents.map((content) => (
            <ContentChip key={content.id} content={content} blocked={busy} />
          ))
        )}
      </div>
      <AddContent room={room} blocked={busy} />
      <RecordEditor
        title='Reshape this room'
        note='Values you set are held against the engine until you release them.'
        fields={[
          {
            key: 'kind',
            label: 'Kind',
            kind: 'pick',
            table: table(ROOM_KINDS),
          },
          {
            key: 'challenge',
            label: 'Challenge',
            kind: 'pick',
            table: table(CHALLENGES),
          },
          {
            key: 'difficulty',
            label: 'Difficulty',
            kind: 'number',
            min: 0,
            max: SPAN,
          },
          { key: 'position', label: 'Position', kind: 'number', min: 0 },
          {
            key: 'cleared_epoch',
            label: 'Cleared in epoch',
            kind: 'number',
            min: 0,
          },
        ]}
        locked={room.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function OpenRoom({
  siteId,
  count,
  blocked,
}: {
  siteId: number
  count: number
  blocked: string | null
}) {
  const [kind, setKind] = useState<RoomView['kind'] | ''>('')
  const [challenge, setChallenge] = useState<RoomView['challenge']>('none')
  const [difficulty, setDifficulty] = useState('30')
  const create = useGatheringAction(
    'site_room:create',
    (_: void) => ({
      site_id: siteId,
      kind: kind === '' ? 'chamber' : kind,
      challenge,
      difficulty: Number(difficulty),
      position: null,
    }),
    'A room opens in the site'
  )
  const busy = why(blocked, create.isPending)
  return (
    <ForgeCard
      icon={DoorOpen}
      tone='info'
      title='Open a room'
      note='Add a room at the end of the way through this site, with its challenge and how hard it is.'
      columns={3}
      meta={<Chip icon={DoorOpen}>{`${count} rooms`}</Chip>}
      action={
        <Button
          size='sm'
          disabled={busy !== null || kind === ''}
          disabledReason={
            busy ?? (kind === '' ? 'Choose a kind of room first' : undefined)
          }
          onClick={() => create.mutate()}
        >
          <DoorOpen />
          Open it
        </Button>
      }
    >
      <MindPicker
        label='Kind of room'
        value={kind}
        table={table(ROOM_KINDS)}
        blocked={busy}
        onPick={(value) => setKind(value as RoomView['kind'])}
      />
      <MindPicker
        label='Challenge'
        value={challenge}
        table={table(CHALLENGES)}
        blocked={busy}
        onPick={(value) => setChallenge(value as RoomView['challenge'])}
      />
      <MindPicker
        label='Difficulty'
        value={difficulty}
        table={Object.fromEntries(
          [10, 20, 30, 50, 70, 90].map((value) => [
            String(value),
            String(value),
          ])
        )}
        blocked={busy}
        onPick={setDifficulty}
      />
    </ForgeCard>
  )
}

function Delve({
  siteId,
  blocked,
  ready,
}: {
  siteId: number
  blocked: string | null
  ready: boolean
}) {
  const [delver, setDelver] = useState<number | null>(null)
  const delve = useGatheringAction(
    'site:delve',
    (_: void) => ({ delver_id: delver ?? 0, site_id: siteId }),
    'The delver walks the site'
  )
  const busy = why(blocked, delve.isPending)
  const missing = !ready
    ? 'This site has no room to walk yet'
    : delver === null
      ? 'Choose who walks the site'
      : null
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
      <ThingPicker
        label='Send a delver'
        value={delver}
        onChange={setDelver}
        blocked={busy}
        types={DELVERS}
      />
      <Button
        size='sm'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() => delve.mutate()}
      >
        <Footprints />
        Walk it now
      </Button>
    </div>
  )
}

function HolderRow({
  holder,
  blocked,
}: {
  holder: HolderView
  blocked: string | null
}) {
  const remove = useGatheringAction(
    'site_holder:delete',
    (_: void) => ({ holder_row_id: holder.id }),
    'The holding is struck from the record'
  )
  const busy = why(blocked, remove.isPending)
  return (
    <div className='flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-lg border bg-background p-2.5'>
      <span className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Flag
          aria-hidden='true'
          className='size-icon-xs shrink-0 text-muted-foreground'
        />
        <Ref node={holder.holder} />
        <Muted as='span' variant='caption'>
          {`from epoch ${holder.from_epoch}${holder.to_epoch !== null ? ` to ${holder.to_epoch}` : ', holding it still'}${holder.how ? ` · ${holder.how}` : ''}`}
        </Muted>
      </span>
      <Button
        size='icon-sm'
        variant='ghost'
        aria-label='Strike this holding'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => remove.mutate()}
      >
        <X />
      </Button>
    </div>
  )
}

function Holders({
  site,
  blocked,
}: {
  site: SiteView
  blocked: string | null
}) {
  const [holder, setHolder] = useState<number | null>(null)
  const set = useGatheringAction(
    'site_holder:set',
    (_: void) => ({ site_id: site.site_id, holder_id: holder ?? 0 }),
    'The site passes into new hands'
  )
  const busy = why(blocked, set.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{`Who has held it (${site.holders.length})`}</Label>
      {site.holders.length === 0 ? (
        <Muted variant='caption'>No one has held it.</Muted>
      ) : (
        <PagedList
          items={site.holders}
          initial={5}
          noun={['holder', 'holders']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.id}
        >
          {(row) => <HolderRow holder={row} blocked={busy} />}
        </PagedList>
      )}
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <ThingPicker
          label='Give it to'
          value={holder}
          onChange={setHolder}
          blocked={busy}
          types={HOLDERS}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || holder === null}
          disabledReason={
            busy ??
            (holder === null ? 'Choose the new holder first' : undefined)
          }
          onClick={() => set.mutate()}
        >
          <Castle />
          Hand it over
        </Button>
      </div>
    </div>
  )
}

function StageRow({
  stage,
  blocked,
}: {
  stage: StageView
  blocked: string | null
}) {
  const edit = useGatheringAction(
    'excavation_stage:edit',
    (vars: Edit) => ({ stage_id: stage.id, ...vars }),
    'The stage is reshaped'
  )
  const busy = why(blocked, edit.isPending)
  const look = DIG_STAGES[stage.stage]
  const risk = DIG_RISKS[stage.risk]
  const find = DIG_FINDS[stage.find]
  return (
    <RecordRow
      icon={look.icon}
      tone={stage.resolved_epoch === null ? look.tone : 'success'}
      title={look.label}
      caption={`${words(stage.skill)}${stage.technique ? ` with ${words(stage.technique)}` : ''} · difficulty ${stage.difficulty}${stage.resolved_epoch !== null ? ` · passed in epoch ${stage.resolved_epoch}` : ''}`}
    >
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Chip icon={risk.icon}>{risk.label}</Chip>
        <Chip icon={find.icon}>{find.label}</Chip>
        {stage.find_item && (
          <Badge variant='secondary'>
            <Ref node={stage.find_item} />
          </Badge>
        )}
      </div>
      <RecordEditor
        title='Reshape this stage'
        note='Values you set are held until you release them.'
        fields={[
          {
            key: 'skill',
            label: 'Skill it tests',
            kind: 'pick',
            table: SKILLS,
          },
          {
            key: 'technique',
            label: 'Technique it needs',
            kind: 'pick',
            table: TECHNIQUES,
          },
          {
            key: 'difficulty',
            label: 'Difficulty',
            kind: 'number',
            min: 0,
            max: SPAN,
          },
          { key: 'risk', label: 'Risk', kind: 'pick', table: table(DIG_RISKS) },
          { key: 'find', label: 'Find', kind: 'pick', table: table(DIG_FINDS) },
        ]}
        locked={stage.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function DigCard({ dig, blocked }: { dig: DigView; blocked: string | null }) {
  const edit = useGatheringAction(
    'excavation:edit',
    (vars: Edit) => ({ dig_id: dig.id, ...vars }),
    'The dig is reshaped'
  )
  const advance = useGatheringAction(
    'excavation:advance',
    (_: void) => ({ dig_id: dig.id }),
    'The dig goes deeper'
  )
  const remove = useGatheringAction(
    'excavation:delete',
    (_: void) => ({ dig_id: dig.id }),
    'The dig is gone from the record'
  )
  const busy = why(blocked, edit.isPending, advance.isPending, remove.isPending)
  const status = DIG_STATUSES[dig.status]
  const stage = DIG_STAGES[dig.stage]
  const going = dig.status === 'open' || dig.status === 'stalled'
  return (
    <RecordRow
      icon={Shovel}
      tone={status.tone}
      title={`Dig of epoch ${dig.started_epoch}`}
      caption={`${status.label} · at the ${stage.label.toLowerCase()}${dig.ended_epoch !== null ? ` · ended in epoch ${dig.ended_epoch}` : ''}${dig.idle_epochs > 0 ? ` · idle ${dig.idle_epochs} epochs` : ''}`}
      aside={
        <div className='flex shrink-0 flex-wrap items-center gap-1'>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || !going}
            disabledReason={busy ?? (going ? undefined : 'This dig is over')}
            onClick={() => advance.mutate()}
          >
            <FastForward />
            Dig deeper
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
      <Meter
        label={`Progress through the ${stage.label.toLowerCase()}`}
        value={dig.progress}
        tone='verdigris'
        icon={stage.icon}
      />
      <Facts
        items={[
          ['Leader', <Ref key='leader' node={dig.leader} />],
          ['Sponsor', <Ref key='sponsor' node={dig.sponsor} empty='none' />],
          ['History', dig.collection_name ?? 'Not yet told'],
          ['Idle', `${dig.idle_epochs} epochs`],
        ]}
      />
      {dig.note && <Muted variant='caption'>{dig.note}</Muted>}
      <Label variant='overline'>{`Stages (${dig.stages.length})`}</Label>
      <div className='flex min-w-0 flex-col gap-2'>
        {dig.stages.map((row) => (
          <StageRow key={row.id} stage={row} blocked={busy} />
        ))}
      </div>
      <RecordEditor
        title='Reshape this dig'
        note='Values you set are held against the engine until you release them.'
        fields={[
          {
            key: 'stage',
            label: 'Stage',
            kind: 'pick',
            table: table(DIG_STAGES),
          },
          {
            key: 'status',
            label: 'Status',
            kind: 'pick',
            table: table(DIG_STATUSES),
          },
          {
            key: 'progress',
            label: 'Progress',
            kind: 'number',
            min: 0,
            max: SPAN,
          },
        ]}
        locked={dig.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
      <DigPeople dig={dig} edit={edit.mutate} blocked={busy} />
    </RecordRow>
  )
}

function DigPeople({
  dig,
  edit,
  blocked,
}: {
  dig: DigView
  edit: (vars: Edit) => void
  blocked: string | null
}) {
  const [leader, setLeader] = useState<number | null>(null)
  const [sponsor, setSponsor] = useState<number | null>(null)
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
      <ThingPicker
        label='New leader'
        value={leader}
        onChange={setLeader}
        blocked={blocked}
        types={['mortal']}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={
          blocked !== null || leader === null || leader === dig.leader?.id
        }
        disabledReason={
          blocked ??
          (leader === null
            ? 'Choose the new leader first'
            : leader === dig.leader?.id
              ? 'Already leading it'
              : undefined)
        }
        onClick={() => {
          edit({ values: { leader_entity_id: leader }, release: [] })
          setLeader(null)
        }}
      >
        Put them in charge
      </Button>
      <ThingPicker
        label='New sponsor'
        value={sponsor}
        onChange={setSponsor}
        blocked={blocked}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={blocked !== null || sponsor === null}
        disabledReason={
          blocked ??
          (sponsor === null ? 'Choose the new sponsor first' : undefined)
        }
        onClick={() => {
          edit({ values: { sponsor_node_id: sponsor }, release: [] })
          setSponsor(null)
        }}
      >
        Make them the sponsor
      </Button>
    </div>
  )
}

function BeginDig({
  site,
  blocked,
}: {
  site: SiteView
  blocked: string | null
}) {
  const [leader, setLeader] = useState<number | null>(null)
  const [sponsor, setSponsor] = useState<number | null>(null)
  const begin = useGatheringAction(
    'excavation:begin',
    (_: void) => ({
      site_id: site.site_id,
      leader_id: leader ?? 0,
      sponsor_id: sponsor,
    }),
    'The dig begins'
  )
  const busy = why(blocked, begin.isPending)
  const open = site.digs.some(
    (dig) => dig.status === 'open' || dig.status === 'stalled'
  )
  const missing = !site.diggable
    ? 'Only a ruin, a god corpse, a crater or a burial ground can be dug'
    : open
      ? 'A dig is already under way here'
      : leader === null
        ? 'Choose who leads the dig'
        : null
  return (
    <ForgeCard
      icon={Shovel}
      tone='verdigris'
      title='Begin a dig'
      note='Send a leader, and a sponsor if you like, to dig this site stage by stage for what lies beneath.'
      columns={2}
      meta={<Chip icon={Shovel}>{`${site.digs.length} digs`}</Chip>}
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => begin.mutate()}
        >
          <Shovel />
          Break ground
        </Button>
      }
    >
      <ThingPicker
        label='Leader'
        value={leader}
        onChange={setLeader}
        blocked={busy}
        types={['mortal']}
      />
      <ThingPicker
        label='Sponsor'
        value={sponsor}
        onChange={setSponsor}
        blocked={busy}
      />
    </ForgeCard>
  )
}

function FeatureRow({
  feature,
  blocked,
}: {
  feature: FeatureView
  blocked: string | null
}) {
  const edit = useGatheringAction(
    'battlefield_feature:edit',
    (vars: Edit) => ({ feature_id: feature.id, ...vars }),
    'The battlefield is reshaped'
  )
  const remove = useGatheringAction(
    'battlefield_feature:delete',
    (_: void) => ({ feature_id: feature.id }),
    'The mark of battle fades'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const look = BATTLEFIELD_FEATURES[feature.feature]
  return (
    <RecordRow
      icon={look.icon}
      tone={look.tone}
      title={look.label}
      caption={`Laid in epoch ${feature.epoch}${feature.battle_id !== null ? ` by ${feature.battle_name ?? 'a battle'}` : ' by the gods'}`}
      aside={
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
      }
    >
      <Meter label='Strength' value={feature.strength} tone='warning' />
      <RecordEditor
        title='Reshape this mark'
        note='A strength you set is held until you release it.'
        fields={[
          {
            key: 'strength',
            label: 'Strength',
            kind: 'number',
            min: 0,
            max: SPAN,
          },
        ]}
        locked={feature.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function MarkBattlefield({
  siteId,
  blocked,
  place,
}: {
  siteId: number
  blocked: string | null
  place: boolean
}) {
  const [feature, setFeature] = useState<FeatureView['feature'] | ''>('')
  const create = useGatheringAction(
    'battlefield_feature:create',
    (_: void) => ({
      place_id: siteId,
      feature: feature === '' ? 'mass_grave' : feature,
      strength: 50,
    }),
    'The battlefield is marked'
  )
  const busy = why(blocked, create.isPending)
  const missing = !place
    ? 'Only a place can hold the marks of a battle'
    : feature === ''
      ? 'Choose the mark first'
      : null
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
      <MindPicker
        label='Mark of battle'
        value={feature}
        table={table(BATTLEFIELD_FEATURES)}
        blocked={
          busy ?? (place ? null : 'Only a place can hold the marks of a battle')
        }
        onPick={(value) => setFeature(value as FeatureView['feature'])}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || missing !== null}
        disabledReason={busy ?? missing ?? undefined}
        onClick={() => create.mutate()}
      >
        <Plus />
        Lay it
      </Button>
    </div>
  )
}

export function SiteSection({
  siteId,
  entityType,
  readOnlyReason = null,
}: {
  siteId: number
  entityType: string
  readOnlyReason?: string | null
}) {
  const query = useSite(siteId)
  const site = query.data
  const place = entityType === 'place'
  return (
    <Section
      id='section-site'
      title='The site within'
      description='Rooms walked one by one, those who have held the site, digs stage by stage and the marks battles left. Places, structures, settlements and vessels have an inside to walk, and the ruins and remains of earlier creations can be dug; other things have no inside of their own.'
      icon={Castle}
      tone='info'
    >
      <div data-surface='SiteSection' className='flex min-w-0 flex-col gap-3'>
        {query.isPending ? (
          <LoadingBlock label='Walking the site' />
        ) : query.isError ? (
          <EmptyState
            icon={Castle}
            size='inline'
            title='The site could not be read'
            description={query.error.message}
          />
        ) : site ? (
          <>
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              <Chip
                icon={DoorOpen}
              >{`${site.rooms.length} rooms, ${site.rooms.filter((room) => room.cleared_epoch !== null).length} cleared`}</Chip>
              <Chip
                icon={Shovel}
                variant={site.diggable ? 'success' : 'secondary'}
              >
                {site.diggable ? 'Can be dug' : 'Not a place for digging'}
              </Chip>
              <Chip icon={Castle} variant={site.roomed ? 'info' : 'secondary'}>
                {site.roomed ? 'Furnished with rooms' : 'No rooms laid out'}
              </Chip>
            </div>
            <Label variant='overline'>Rooms</Label>
            {site.rooms.length === 0 ? (
              <EmptyState
                icon={DoorOpen}
                size='inline'
                title='No room to walk yet'
                description='Open one below; a site of a roomed kind is furnished by the engine.'
              />
            ) : (
              <PagedList
                items={site.rooms}
                initial={6}
                noun={['room', 'rooms']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(row) => row.id}
              >
                {(row) => <RoomCard room={row} blocked={readOnlyReason} />}
              </PagedList>
            )}
            <Delve
              siteId={siteId}
              blocked={readOnlyReason}
              ready={site.rooms.length > 0}
            />
            <OpenRoom
              siteId={siteId}
              count={site.rooms.length}
              blocked={readOnlyReason}
            />
            <Holders site={site} blocked={readOnlyReason} />
            <Label variant='overline'>Digs</Label>
            {site.digs.length === 0 ? (
              <Muted variant='caption'>No one has dug here.</Muted>
            ) : (
              <PagedList
                items={site.digs}
                initial={3}
                noun={['dig', 'digs']}
                className='flex min-w-0 flex-col gap-2'
                itemKey={(row) => row.id}
              >
                {(row) => <DigCard dig={row} blocked={readOnlyReason} />}
              </PagedList>
            )}
            <BeginDig site={site} blocked={readOnlyReason} />
            <Label variant='overline'>Marks of battle</Label>
            {site.features.length === 0 ? (
              <Muted variant='caption'>No battle has marked this ground.</Muted>
            ) : (
              site.features.map((row) => (
                <FeatureRow
                  key={row.id}
                  feature={row}
                  blocked={readOnlyReason}
                />
              ))
            )}
            <MarkBattlefield
              siteId={siteId}
              blocked={readOnlyReason}
              place={place}
            />
          </>
        ) : null}
      </div>
    </Section>
  )
}
