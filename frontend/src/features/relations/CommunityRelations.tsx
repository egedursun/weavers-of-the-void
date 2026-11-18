import { useState } from 'react'
import { Flame, HeartHandshake, Save, Scale } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  EntityLink,
  FormRow,
  Section,
  Paged,
  FieldTile,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted, Text } from '@/components/typography'
import { type EntityContext } from '@/features/entity/actions/context'
import { optionsFor } from '@/features/entity/actions/pickers'
import { humanize } from '@/features/entity/actions/schema'
import { usePickerData } from '@/features/entity/actions/usePickerData'
import { MEMORY_ICONS, named } from '@/features/entity/mind/labels'
import { OpinionBreakdown } from '@/features/entity/sections/MemoriesSection'
import { RelationParts } from './RelationParts'
import {
  type RelationEntry,
  useEndFeud,
  useRelationPair,
  useRelations,
  useSetRelation,
  useStartFeud,
} from './api'

const RELATION_MIN = -100
const RELATION_MAX = 100

function signed(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}

function tone(
  entry: Pick<RelationEntry, 'value' | 'blood_feud_since_epoch'>
): 'success' | 'destructive' | 'secondary' {
  if (entry.blood_feud_since_epoch !== null || entry.value < 0)
    return 'destructive'
  return entry.value > 0 ? 'success' : 'secondary'
}

type RowProps = {
  entry: RelationEntry
  selfId: number
  readOnlyReason: string | null
}

function RelationRow({ entry, selfId, readOnlyReason }: RowProps) {
  const set = useSetRelation(selfId)
  const endFeud = useEndFeud(selfId)
  const [draft, setDraft] = useState(String(entry.value))
  const parsed = Number(draft)
  const invalid =
    draft.trim() === '' ||
    !Number.isInteger(parsed) ||
    parsed < RELATION_MIN ||
    parsed > RELATION_MAX
  const fail = (error: Error) => toast.error(error.message)
  return (
    <li
      data-relation={entry.other.id}
      className='flex min-w-0 flex-col gap-2 border-b py-3 last:border-b-0'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <EntityLink kind='entity' id={String(entry.other.id)}>
          {entry.other.name}
        </EntityLink>
        <Badge
          size='sm'
          variant={tone(entry)}
        >{`${humanize(entry.label)} ${signed(entry.value)}`}</Badge>
        {entry.blood_feud_since_epoch !== null && (
          <Badge
            size='sm'
            variant='destructive'
          >{`Blood feud since epoch ${entry.blood_feud_since_epoch}`}</Badge>
        )}
      </div>
      {entry.history.some((event) => event.holder_id === selfId) && (
        <ul className='flex min-w-0 flex-col gap-0.5'>
          <Paged
            items={entry.history.filter((event) => event.holder_id === selfId)}
            as='li'
          >
            {(event, index) => (
              <li key={`${event.epoch}-${index}`}>
                <Muted variant='caption'>{`Epoch ${event.epoch}: ${named(MEMORY_ICONS, event.kind).label.toLowerCase()} · ${event.event} (${signed(event.delta)})`}</Muted>
              </li>
            )}
          </Paged>
        </ul>
      )}
      <WhyToggle entityId={selfId} otherId={entry.other.id} />
      <RelationParts
        firstId={selfId}
        secondId={entry.other.id}
        blocked={readOnlyReason}
      />
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Input
          type='number'
          inputMode='numeric'
          min={RELATION_MIN}
          max={RELATION_MAX}
          aria-label={`New relation with ${entry.other.name}`}
          placeholder={`${RELATION_MIN} to ${RELATION_MAX}`}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          className='w-36'
        />
        <Button
          variant='outline'
          size='sm'
          disabled={invalid || set.isPending || readOnlyReason !== null}
          disabledReason={
            readOnlyReason ??
            (set.isPending
              ? 'Working'
              : `Enter a whole number from ${RELATION_MIN} to ${RELATION_MAX}`)
          }
          onClick={() =>
            set.mutate(
              { otherId: entry.other.id, value: parsed },
              {
                onSuccess: (result) => {
                  toast.success(result.message)
                  setDraft('')
                },
                onError: fail,
              }
            )
          }
        >
          <Save />
          Set relation
        </Button>
        {entry.blood_feud_since_epoch !== null && (
          <Button
            variant='outline'
            size='sm'
            disabled={endFeud.isPending || readOnlyReason !== null}
            disabledReason={readOnlyReason ?? 'Working'}
            onClick={() =>
              endFeud.mutate(entry.other.id, {
                onSuccess: (result) => toast.success(result.message),
                onError: fail,
              })
            }
          >
            <HeartHandshake />
            End the feud
          </Button>
        )}
      </div>
    </li>
  )
}

function PairStanding({
  entityId,
  otherId,
}: {
  entityId: number
  otherId: number
}) {
  const pair = useRelationPair(entityId, otherId)
  if (pair.isPending) return <Skeleton className='h-control-lg w-full' />
  if (pair.isError) return <Text tone='destructive'>{pair.error.message}</Text>
  const data = pair.data
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Label>Now</Label>
        <Badge
          size='sm'
          variant={tone(data)}
        >{`${humanize(data.label)} ${signed(data.value)}`}</Badge>
        {data.blood_feud_since_epoch !== null && (
          <Badge
            size='sm'
            variant='destructive'
          >{`Blood feud since epoch ${data.blood_feud_since_epoch}`}</Badge>
        )}
      </div>
      {data.history.length === 0 && (
        <Muted variant='caption'>{`${data.first.name} and ${data.second.name} remember nothing of each other yet.`}</Muted>
      )}
      <div className='@container/mind flex min-w-0 flex-col gap-2'>
        <Paged items={data.opinions}>
          {(opinion) => (
            <OpinionBreakdown
              key={opinion.holder?.id ?? opinion.value}
              opinion={opinion}
            />
          )}
        </Paged>
      </div>
    </div>
  )
}

function WhyToggle({
  entityId,
  otherId,
}: {
  entityId: number
  otherId: number
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div>
        <Button
          size='sm'
          variant='ghost'
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          <Scale />
          {open ? 'Hide why' : 'Why?'}
        </Button>
      </div>
      {open && <PairStanding entityId={entityId} otherId={otherId} />}
    </div>
  )
}

function NewRelation({
  ctx,
  readOnlyReason,
}: {
  ctx: EntityContext
  readOnlyReason: string | null
}) {
  const data = usePickerData()
  const start = useStartFeud(ctx.entity.id)
  const set = useSetRelation(ctx.entity.id)
  const [otherId, setOtherId] = useState<number | null>(null)
  const [value, setValue] = useState('0')
  const parsed = Number(value)
  const valueInvalid =
    value.trim() === '' ||
    !Number.isInteger(parsed) ||
    parsed < RELATION_MIN ||
    parsed > RELATION_MAX
  const noTarget = otherId === null
  const fail = (error: Error) => toast.error(error.message)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <FieldTile group label='Change a relation'>
        <FormRow label='Other community'>
          {(id) => (
            <RecordCombobox
              id={id}
              options={optionsFor(
                {
                  source: 'entity',
                  types: ['people', 'settlement', 'faction', 'cult'],
                  sameType: false,
                },
                ctx,
                data
              )}
              value={otherId === null ? null : String(otherId)}
              onChange={(next) =>
                setOtherId(next === null ? null : Number(next))
              }
              placeholder='Choose a community'
              clearable
              aria-label='Other community'
            />
          )}
        </FormRow>
        {otherId !== null && (
          <PairStanding entityId={ctx.entity.id} otherId={otherId} />
        )}
        <FormRow
          label='Relation value'
          description={`From ${RELATION_MIN} to ${RELATION_MAX}`}
        >
          {(id) => (
            <Input
              id={id}
              type='number'
              inputMode='numeric'
              min={RELATION_MIN}
              max={RELATION_MAX}
              value={value}
              onChange={(event) => setValue(event.target.value)}
            />
          )}
        </FormRow>
      </FieldTile>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          disabled={
            noTarget || valueInvalid || set.isPending || readOnlyReason !== null
          }
          disabledReason={
            readOnlyReason ??
            (noTarget
              ? 'Choose a community'
              : valueInvalid
                ? 'Enter a whole number in range'
                : 'Working')
          }
          onClick={() =>
            otherId !== null &&
            set.mutate(
              { otherId, value: parsed },
              {
                onSuccess: (result) => toast.success(result.message),
                onError: fail,
              }
            )
          }
        >
          <Save />
          Set relation
        </Button>
        <Button
          variant='destructive'
          disabled={noTarget || start.isPending || readOnlyReason !== null}
          disabledReason={
            readOnlyReason ?? (noTarget ? 'Choose a community' : 'Working')
          }
          onClick={() =>
            otherId !== null &&
            start.mutate(otherId, {
              onSuccess: (result) => toast.success(result.message),
              onError: fail,
            })
          }
        >
          <Flame />
          Declare a blood feud
        </Button>
      </div>
    </div>
  )
}

export function CommunityRelations({
  ctx,
  readOnlyReason,
}: {
  ctx: EntityContext
  readOnlyReason: string | null
}) {
  const query = useRelations(ctx.entity.id)
  return (
    <Section
      id='section-community-relations'
      title='Community relations'
      description='How this community regards the others. Each relation comes from what both sides remember of each other, how close their values are and the bonds they share; set one here to add the will of the gods.'
    >
      {query.isPending && <Skeleton className='h-textarea w-full' />}
      {query.isError && <Text tone='destructive'>{query.error.message}</Text>}
      {query.data &&
        (query.data.relations.length === 0 ? (
          <EmptyState
            icon={HeartHandshake}
            title='No relations yet'
            description='Relations appear once this community meets another.'
          />
        ) : (
          <ul aria-label='Relations' className='flex min-w-0 flex-col'>
            <Paged items={query.data.relations} as='li'>
              {(entry) => (
                <RelationRow
                  key={entry.other.id}
                  entry={entry}
                  selfId={ctx.entity.id}
                  readOnlyReason={readOnlyReason}
                />
              )}
            </Paged>
          </ul>
        ))}
      <NewRelation ctx={ctx} readOnlyReason={readOnlyReason} />
    </Section>
  )
}
