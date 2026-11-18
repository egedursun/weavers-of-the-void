import { useState } from 'react'
import { MapPin, ScrollText, UserPlus, X } from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  LoadingBlock,
  PagedList,
  Section,
  FieldTile,
} from '@/components/domain'
import { Text } from '@/components/typography'
import { Chip, ForgeCard } from '@/features/cosmography/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { HistoryById, HistoryCard } from './HistoryCard'
import {
  type CollectionKind,
  type CollectionRole,
  useGatheringAction,
  useHistory,
  useLifeLog,
} from './api'
import { useOpenHistory, why } from './history'
import { COLLECTION_KINDS, COLLECTION_ROLES, table } from './labels'
import { ThingPicker } from './parts'

const NAME_MAX = 120
const PLACE_TYPES = ['place', 'settlement', 'structure', 'region']

function ParentHistoryNote({ id }: { id: number | null }) {
  const parent = useHistory(id)
  const text =
    id === null
      ? 'Stands on its own.'
      : parent.isPending
        ? 'Looking for that history…'
        : parent.isError
          ? 'No history has that number.'
          : `Within ${parent.data.collection.name}.`
  return (
    <Text
      variant='caption'
      tone={id !== null && parent.isError ? 'destructive' : 'muted'}
    >
      {text}
    </Text>
  )
}

export function SetDownHistory({
  nodeId,
  blocked,
}: {
  nodeId?: number
  blocked: string | null
}) {
  const [kind, setKind] = useState<CollectionKind | ''>('')
  const [name, setName] = useState('')
  const [role, setRole] = useState<CollectionRole>('leader')
  const [other, setOther] = useState<number | null>(null)
  const [members, setMembers] = useState<
    { node_id: number; role: CollectionRole }[]
  >([])
  const [place, setPlace] = useState<number | null>(null)
  const [parent, setParent] = useState('')
  const create = useGatheringAction(
    'collection:create',
    (_: void) => ({
      kind: kind === '' ? 'ceremony' : kind,
      name: name.trim(),
      members: [
        ...(nodeId === undefined ? [] : [{ node_id: nodeId, role }]),
        ...members,
      ],
      places: place === null ? [] : [place],
      parent_id: parent === '' ? null : Number(parent),
    }),
    'The history is set down'
  )
  const busy = why(blocked, create.isPending)
  const count = members.length + (nodeId === undefined ? 0 : 1)
  const missing =
    kind === ''
      ? 'Choose a kind of history first'
      : count === 0
        ? 'Name at least one figure'
        : null
  return (
    <ForgeCard
      icon={ScrollText}
      tone='verdigris'
      title='Set down a history'
      note='Gather figures and places into a war, a pilgrimage, a feast or any other history; leave the name empty and one is given.'
      columns={3}
      meta={
        <Chip icon={UserPlus}>{`${plural(count, 'figure', 'figures')}`}</Chip>
      }
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => {
            create.mutate()
            setMembers([])
            setName('')
          }}
        >
          <ScrollText />
          Set it down
        </Button>
      }
    >
      <MindPicker
        label='Kind of history'
        value={kind}
        table={table(COLLECTION_KINDS)}
        blocked={busy}
        onPick={(value) => setKind(value as CollectionKind)}
      />
      <FieldTile id={`history-name-${nodeId ?? 'all'}`} label='History name'>
        <Input
          id={`history-name-${nodeId ?? 'all'}`}
          value={name}
          maxLength={NAME_MAX}
          placeholder='Given by the engine if left empty'
          disabled={busy !== null}
          onChange={(event) => setName(event.target.value)}
        />
      </FieldTile>
      {nodeId !== undefined && (
        <MindPicker
          label='Part this one plays'
          value={role}
          table={table(COLLECTION_ROLES)}
          blocked={busy}
          onPick={(value) => setRole(value as CollectionRole)}
        />
      )}
      <ThingPicker
        label='Another figure'
        value={other}
        onChange={setOther}
        blocked={busy}
      />
      <div className='flex min-w-0 flex-col justify-end gap-1'>
        <Button
          size='sm'
          variant='outline'
          disabled={
            busy !== null ||
            other === null ||
            other === nodeId ||
            members.some((row) => row.node_id === other)
          }
          disabledReason={
            busy ??
            (other === null
              ? 'Choose a figure first'
              : other === nodeId || members.some((row) => row.node_id === other)
                ? 'Already named'
                : undefined)
          }
          onClick={() => {
            if (other !== null)
              setMembers([...members, { node_id: other, role: 'member' }])
            setOther(null)
          }}
        >
          <UserPlus />
          Name them too
        </Button>
        {members.length > 0 && (
          <Badge variant='secondary'>
            {`${members.length} more named`}
            <Button
              size='icon-sm'
              variant='ghost'
              aria-label='Clear the named figures'
              onClick={() => setMembers([])}
            >
              <X />
            </Button>
          </Badge>
        )}
      </div>
      <ThingPicker
        label='Place'
        value={place}
        onChange={setPlace}
        blocked={busy}
        types={PLACE_TYPES}
      />
      <FieldTile
        id={`history-parent-${nodeId ?? 'all'}`}
        label='Within history number'
      >
        <Input
          id={`history-parent-${nodeId ?? 'all'}`}
          inputMode='numeric'
          value={parent}
          placeholder='None'
          disabled={busy !== null}
          onChange={(event) => setParent(event.target.value.replace(/\D/g, ''))}
        />
        <ParentHistoryNote id={parent === '' ? null : Number(parent)} />
      </FieldTile>
    </ForgeCard>
  )
}

export function HistoriesSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useLifeLog(nodeId)
  const opened = useOpenHistory()
  const entries = query.data?.entries ?? []
  const unfolding = entries.filter(
    (entry) => entry.collection.end_epoch === null
  ).length
  return (
    <Section
      id='section-histories'
      title='Histories'
      description='The wars, battles, journeys, feasts and every other history this one took part in, with the part they played.'
      icon={ScrollText}
      tone='verdigris'
    >
      <div
        data-surface='HistoriesSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {opened.open !== null &&
          !entries.some((entry) => entry.collection.id === opened.open) && (
            <HistoryById
              id={opened.open}
              blocked={readOnlyReason}
              onClose={opened.close}
              onOpen={opened.show}
            />
          )}
        {query.isPending ? (
          <LoadingBlock label='Reading the histories' />
        ) : query.isError ? (
          <EmptyState
            icon={ScrollText}
            size='inline'
            title='The histories could not be read'
            description={query.error.message}
          />
        ) : entries.length === 0 ? (
          <EmptyState
            icon={ScrollText}
            size='inline'
            title='No history names this one yet'
            description='Histories gather as the epochs pass; set one down below.'
          />
        ) : (
          <>
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              <Chip
                icon={ScrollText}
              >{`${plural(entries.length, 'history', 'histories')}`}</Chip>
              <Chip
                icon={MapPin}
                variant='warning'
              >{`${unfolding} still unfolding`}</Chip>
            </div>
            <PagedList
              items={entries}
              initial={5}
              noun={['history', 'histories']}
              className='flex min-w-0 flex-col gap-2'
              itemKey={(entry) => entry.collection.id}
            >
              {(entry) => (
                <HistoryCard
                  collection={entry.collection}
                  role={entry.role}
                  blocked={readOnlyReason}
                  open={opened.open === entry.collection.id}
                  onToggle={() => opened.toggle(entry.collection.id)}
                  onOpen={opened.show}
                />
              )}
            </PagedList>
          </>
        )}
        <SetDownHistory nodeId={nodeId} blocked={readOnlyReason} />
      </div>
    </Section>
  )
}
