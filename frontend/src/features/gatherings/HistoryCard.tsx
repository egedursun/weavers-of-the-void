import { useState } from 'react'
import {
  ChevronDown,
  ChevronUp,
  MapPin,
  ScrollText,
  Trash2,
  UserPlus,
  X,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState, LoadingBlock, PagedList } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import {
  Chip,
  Facts,
  NodeLink,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { useNames } from '@/features/entity/api/queries'
import { MindPicker } from '@/features/entity/mind/parts'
import {
  type CollectionRole,
  type CollectionView,
  type HistoryDetail,
  type MemberView,
  useGatheringAction,
  useHistory,
} from './api'
import { spanOf, why } from './history'
import { COLLECTION_KINDS, COLLECTION_ROLES, table } from './labels'
import { type NodeRef, Ref, ThingPicker } from './parts'

const PLACE_TYPES = ['place', 'settlement', 'structure', 'region']

type Edit = { values: EditValues; release: string[] }

function MemberRow({
  collectionId,
  member,
  blocked,
}: {
  collectionId: number
  member: MemberView
  blocked: string | null
}) {
  const nodeId = member.node?.id ?? 0
  const set = useGatheringAction(
    'collection_member:set',
    (role: CollectionRole) => ({
      collection_id: collectionId,
      node_id: nodeId,
      role,
    }),
    'The part they played is set'
  )
  const remove = useGatheringAction(
    'collection_member:remove',
    (_: void) => ({ collection_id: collectionId, node_id: nodeId }),
    'They are struck from this history'
  )
  const busy = why(blocked, set.isPending, remove.isPending)
  const role = COLLECTION_ROLES[member.role]
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 rounded-md border surface-framed border-gild/70 bg-card p-2.5 sm:grid-cols-3'>
      <div className='flex min-w-0 flex-col gap-1'>
        <span className='flex min-w-0 items-center gap-1.5'>
          <role.icon
            aria-hidden='true'
            className='size-icon-xs shrink-0 text-muted-foreground'
          />
          <Ref node={member.node} empty='someone forgotten' />
        </span>
        <Muted variant='caption'>{`${role.label} since epoch ${member.since_epoch}`}</Muted>
      </div>
      <MindPicker
        act={set}
        label='Part played'
        value={member.role}
        table={table(COLLECTION_ROLES)}
        blocked={busy}
        onPick={(value) => set.mutate(value as CollectionRole)}
      />
      <div className='flex justify-end'>
        <Button
          act={remove}
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <X />
          Strike
        </Button>
      </div>
    </div>
  )
}

function SiteChip({
  collectionId,
  site,
  blocked,
}: {
  collectionId: number
  site: NodeRef
  blocked: string | null
}) {
  const drop = useGatheringAction(
    'collection:place',
    (_: void) => ({
      collection_id: collectionId,
      place_id: site.id,
      present: false,
    }),
    'The place is struck from this history'
  )
  const busy = why(blocked, drop.isPending)
  return (
    <Badge variant='outline'>
      <MapPin />
      <Ref node={site} />
      <Button
        act={drop}
        size='icon-sm'
        variant='ghost'
        aria-label={`Strike ${site.name} from this history`}
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => drop.mutate()}
      >
        <X />
      </Button>
    </Badge>
  )
}

function AddToHistory({
  detail,
  blocked,
}: {
  detail: HistoryDetail
  blocked: string | null
}) {
  const id = detail.collection.id
  const [node, setNode] = useState<number | null>(null)
  const [role, setRole] = useState<CollectionRole>('member')
  const [place, setPlace] = useState<number | null>(null)
  const join = useGatheringAction(
    'collection_member:set',
    (_: void) => ({ collection_id: id, node_id: node ?? 0, role }),
    'They join this history'
  )
  const site = useGatheringAction(
    'collection:place',
    (_: void) => ({ collection_id: id, place_id: place ?? 0, present: true }),
    'The place joins this history'
  )
  const busy = why(blocked, join.isPending, site.isPending)
  const listed = detail.roster.some((row) => row.node?.id === node)
  const placed = detail.sites.some((row) => row.id === place)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-3'>
        <ThingPicker
          label='Add a figure'
          value={node}
          onChange={setNode}
          blocked={busy}
        />
        <MindPicker
          label='As'
          value={role}
          table={table(COLLECTION_ROLES)}
          blocked={busy}
          onPick={(value) => setRole(value as CollectionRole)}
        />
        <Button
          act={join}
          size='sm'
          variant='outline'
          disabled={busy !== null || node === null || listed}
          disabledReason={
            busy ??
            (node === null
              ? 'Choose a figure first'
              : listed
                ? 'Already part of this history'
                : undefined)
          }
          onClick={() => {
            join.mutate()
            setNode(null)
          }}
        >
          <UserPlus />
          Add
        </Button>
      </div>
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <ThingPicker
          label='Add a place'
          value={place}
          onChange={setPlace}
          blocked={busy}
          types={PLACE_TYPES}
        />
        <Button
          act={site}
          size='sm'
          variant='outline'
          disabled={busy !== null || place === null || placed}
          disabledReason={
            busy ??
            (place === null
              ? 'Choose a place first'
              : placed
                ? 'Already a place of this history'
                : undefined)
          }
          onClick={() => {
            site.mutate()
            setPlace(null)
          }}
        >
          <MapPin />
          Add the place
        </Button>
      </div>
    </div>
  )
}

function HistoryBody({
  detail,
  blocked,
  onOpen,
}: {
  detail: HistoryDetail
  blocked: string | null
  onOpen: (id: number) => void
}) {
  const collection = detail.collection
  const names = useNames()
  const worldName =
    names.data?.find(
      (entry) => entry.kind === 'world' && entry.id === collection.world_id
    )?.name ?? 'Unnamed world'
  const edit = useGatheringAction(
    'collection:edit',
    (vars: Edit) => ({ collection_id: collection.id, ...vars }),
    'The history is rewritten'
  )
  const busy = why(blocked, edit.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Facts
        items={[
          ['Span', spanOf(collection)],
          [
            'World',
            collection.world_id === null ? (
              'Across the heavens'
            ) : (
              <NodeLink
                key='world'
                kind='world'
                id={collection.world_id}
                name={worldName}
              />
            ),
          ],
          ['Figures', String(collection.members)],
          ['Places', String(collection.places)],
          [
            'Within',
            detail.parent ? (
              <Button
                key='parent'
                size='sm'
                variant='link'
                onClick={() => onOpen(detail.parent?.id ?? 0)}
              >
                {detail.parent.name}
              </Button>
            ) : (
              'No greater history'
            ),
          ],
        ]}
      />
      {collection.note && <Muted variant='caption'>{collection.note}</Muted>}
      {detail.children.length > 0 && (
        <div className='flex min-w-0 flex-col gap-1.5'>
          <Label variant='overline'>Histories within it</Label>
          <PagedList
            items={detail.children}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap gap-1.5'
            itemKey={(child) => child.id}
          >
            {(child) => {
              const look = COLLECTION_KINDS[child.kind]
              return (
                <Button
                  key={child.id}
                  size='sm'
                  variant='outline'
                  onClick={() => onOpen(child.id)}
                >
                  <look.icon />
                  {child.name}
                </Button>
              )
            }}
          </PagedList>
        </div>
      )}
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>{`Figures (${detail.roster.length})`}</Label>
        {detail.roster.length === 0 ? (
          <Muted variant='caption'>No figure is named in it.</Muted>
        ) : (
          <PagedList
            items={detail.roster}
            initial={6}
            noun={['figure', 'figures']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(row) => row.node?.id ?? 0}
          >
            {(row) => (
              <MemberRow
                collectionId={collection.id}
                member={row}
                blocked={busy}
              />
            )}
          </PagedList>
        )}
      </div>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <Label variant='overline'>{`Places (${detail.sites.length})`}</Label>
        {detail.sites.length === 0 ? (
          <Muted variant='caption'>It is tied to no place.</Muted>
        ) : (
          <PagedList
            items={detail.sites}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap gap-1.5'
            itemKey={(site) => site.id}
          >
            {(site) => (
              <SiteChip
                key={site.id}
                collectionId={collection.id}
                site={site}
                blocked={busy}
              />
            )}
          </PagedList>
        )}
      </div>
      <AddToHistory detail={detail} blocked={busy} />
      <div className='flex min-w-0 flex-col gap-1.5'>
        <Label variant='overline'>{`What happened (${detail.incidents.length})`}</Label>
        {detail.incidents.length === 0 ? (
          <Muted variant='caption'>No incident is told in it yet.</Muted>
        ) : (
          <PagedList
            items={detail.incidents}
            initial={8}
            noun={['incident', 'incidents']}
            className='flex min-w-0 flex-col gap-1'
            itemKey={(row) => row.id}
          >
            {(row) => (
              <div className='flex min-w-0 items-baseline gap-2 border-b border-dashed pb-1'>
                <Chip>{`E${row.epoch}`}</Chip>
                <Text className='min-w-0'>
                  {row.text ?? `Incident #${row.id}`}
                </Text>
              </div>
            )}
          </PagedList>
        )}
      </div>
      <RecordEditor
        act={edit}
        title='Rewrite this history'
        note='Values you set are held: the engine will not rename, close or reopen it until you release them.'
        fields={[
          { key: 'name', label: 'Name', kind: 'text' },
          {
            key: 'kind',
            label: 'Kind',
            kind: 'pick',
            table: table(COLLECTION_KINDS),
          },
          {
            key: 'start_epoch',
            label: 'Began in epoch',
            kind: 'number',
            min: 0,
          },
          { key: 'end_epoch', label: 'Ended in epoch', kind: 'number', min: 0 },
          {
            key: 'parent_id',
            label: 'Within history number',
            kind: 'number',
            min: 1,
          },
          { key: 'note', label: 'Note', kind: 'text', long: true },
        ]}
        locked={collection.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </div>
  )
}

export function HistoryCard({
  collection,
  role,
  blocked,
  open,
  onToggle,
  onOpen,
}: {
  collection: CollectionView
  role?: CollectionRole
  blocked: string | null
  open: boolean
  onToggle: () => void
  onOpen: (id: number) => void
}) {
  const detail = useHistory(open ? collection.id : null)
  const remove = useGatheringAction(
    'collection:delete',
    (_: void) => ({ collection_id: collection.id }),
    'The history is gone from the record'
  )
  const busy = why(blocked, remove.isPending)
  const look = COLLECTION_KINDS[collection.kind]
  return (
    <RecordRow
      icon={look.icon}
      tone={look.tone}
      title={collection.name}
      caption={`${look.label} · ${spanOf(collection)}${role ? ` · ${COLLECTION_ROLES[role].label.toLowerCase()}` : ''}`}
      aside={
        <div className='flex shrink-0 flex-wrap items-center gap-1'>
          <Button
            size='sm'
            variant='outline'
            aria-expanded={open}
            onClick={onToggle}
          >
            {open ? <ChevronUp /> : <ChevronDown />}
            {open ? 'Close' : 'Open'}
          </Button>
          <Button
            act={remove}
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
        <Chip icon={look.icon}>{look.label}</Chip>
        <Chip>{`${plural(collection.members, 'figure', 'figures')}`}</Chip>
        <Chip
          icon={MapPin}
        >{`${plural(collection.places, 'place', 'places')}`}</Chip>
        {collection.end_epoch === null && (
          <Chip variant='warning'>Unfolding</Chip>
        )}
        {collection.locked.length > 0 && <Badge variant='outline'>Held</Badge>}
      </div>
      {open &&
        (detail.isPending ? (
          <LoadingBlock label='Reading this history' />
        ) : detail.isError ? (
          <EmptyState
            icon={ScrollText}
            size='inline'
            title='This history could not be read'
            description={detail.error.message}
          />
        ) : (
          <HistoryBody detail={detail.data} blocked={busy} onOpen={onOpen} />
        ))}
    </RecordRow>
  )
}

export function HistoryById({
  id,
  blocked,
  onClose,
  onOpen,
}: {
  id: number
  blocked: string | null
  onClose: () => void
  onOpen: (id: number) => void
}) {
  const detail = useHistory(id)
  if (detail.isPending) return <LoadingBlock label='Reading this history' />
  if (detail.isError)
    return (
      <EmptyState
        icon={ScrollText}
        size='inline'
        title='This history could not be read'
        description={detail.error.message}
      />
    )
  return (
    <HistoryCard
      collection={detail.data.collection}
      blocked={blocked}
      open
      onToggle={onClose}
      onOpen={onOpen}
    />
  )
}
