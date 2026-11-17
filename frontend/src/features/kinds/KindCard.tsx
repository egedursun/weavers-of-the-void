import { useState } from 'react'
import {
  Archive,
  ArchiveRestore,
  Lock,
  LockOpen,
  Send,
  Trash2,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { Badge } from '@/components/ui/badge'
import {
  ExpandableText,
  PagedList,
  RangeField,
  StatBar,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import {
  type Field,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { RefLink } from '@/features/entity/realm/parts'
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField } from '@/features/wars/military/parts'
import { type KindConceptInfo, type KindRecord, type KindStance } from './api'
import { CONCEPT_ICONS, LINEAGE_ICON, STANCES } from './labels'

const HOLD = 'Values you set are held against the world until you release them.'
const PEOPLE_STANCES: KindStance[] = ['makes', 'uses', 'favours', 'forbids']
const ORIGIN_TYPES = [
  'people',
  'polity',
  'faction',
  'cult',
  'mortal',
  'settlement',
  'house',
] as const
const ORIGIN_KINDS = ['son', 'foreign_god', 'creator'] as const
const DEFAULT_STRENGTH = 50
const FULL = 100

type Edit = { values: EditValues; release: string[] }

function kindFields(
  info: KindConceptInfo,
  siblings: readonly KindRecord[],
  selfId: number | null
): Field[] {
  const parents = Object.fromEntries([
    ['none', 'Developed from nothing'],
    ...siblings
      .filter((row) => row.id !== selfId)
      .map((row) => [String(row.id), row.name]),
  ])
  return [
    { key: 'name', label: 'Name of the kind', kind: 'text' },
    { key: 'description', label: 'What it is', kind: 'text', long: true },
    {
      key: 'category',
      label: 'Category',
      kind: 'pick',
      table: Object.fromEntries(
        info.categories.map((item) => [item.key, item.label])
      ),
    },
    ...info.properties.map((item): Field =>
      item.options.length
        ? {
            key: item.column,
            label: item.label,
            kind: 'pick',
            table: Object.fromEntries(
              item.options.map((option) => [option.key, option.label])
            ),
          }
        : {
            key: item.column,
            label: item.label,
            kind: 'number',
            min: item.low,
            max: item.high,
          }
    ),
    {
      key: 'world_id',
      label: 'World it belongs to',
      kind: 'node',
      types: [],
      kinds: ['world'],
    },
    {
      key: 'origin_node_id',
      label: 'Who made it',
      kind: 'node',
      types: ORIGIN_TYPES,
      kinds: ORIGIN_KINDS,
    },
    {
      key: 'derived_from_id',
      label: 'Developed from',
      kind: 'pick',
      table: parents,
    },
  ]
}

function KindPassing({
  info,
  row,
  blocked,
}: {
  info: KindConceptInfo
  row: KindRecord
  blocked: string | null
}) {
  const [holder, setHolder] = useState<number | null>(null)
  const [stance, setStance] = useState<KindStance>('uses')
  const [strength, setStrength] = useState(DEFAULT_STRENGTH)
  const passing = useMadeAction(
    'authored_kind:spread',
    (_: void) => ({
      concept: info.concept,
      kind_id: row.id,
      holder_node_id: holder ?? 0,
      stance,
      strength,
    }),
    `${row.name} is given`
  )
  const reason =
    blocked ??
    (row.retired ? 'A retired kind cannot be given; restore it first' : null)
  const missing = holder === null ? 'Pick who receives it first' : null
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 rounded-md border surface-well border-gild/20 bg-muted/60 p-3 md:grid-cols-3'>
      <ThingPicker
        label='Who receives it'
        value={holder}
        onChange={setHolder}
        blocked={reason}
      />
      <ChoiceField
        label='How they hold it'
        value={stance}
        table={Object.fromEntries(
          PEOPLE_STANCES.map((key) => [key, STANCES[key]])
        )}
        blocked={reason}
        onPick={(value) => setStance(value as KindStance)}
      />
      <RangeField
        label='Strength of the hold'
        icon={STANCES[stance].icon}
        value={strength}
        min={0}
        max={FULL}
        level={`${strength} of ${FULL}`}
        lowLabel='Barely'
        highLabel='Wholly'
        onChange={setStrength}
        disabledReason={reason}
      />
      <div className='flex min-w-0 md:col-span-3'>
        <StepButton
          icon={Send}
          label='Give it to them'
          busy={why(reason ?? missing, passing.isPending)}
          onClick={() => passing.mutate()}
        />
      </div>
    </div>
  )
}

export function KindCard({
  info,
  row,
  siblings,
  blocked,
}: {
  info: KindConceptInfo
  row: KindRecord
  siblings: readonly KindRecord[]
  blocked: string | null
}) {
  const target = { concept: info.concept, kind_id: row.id }
  const held = row.locked.length > 0
  const editing = useMadeAction(
    'authored_kind:edit',
    (vars: Edit) => ({
      ...target,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    `${row.name} is set`
  )
  const holding = useMadeAction(
    'authored_kind:hold',
    (_: void) => ({ ...target, hold: !held }),
    held ? `${row.name} is free to change` : `${row.name} is held`
  )
  const retiring = useMadeAction(
    'authored_kind:retire',
    (_: void) => ({ ...target, retired: !row.retired }),
    row.retired ? `${row.name} is in use again` : `${row.name} is retired`
  )
  const removing = useMadeAction(
    'authored_kind:delete',
    (_: void) => target,
    `${row.name} is unmade`
  )
  const busy = why(
    blocked,
    editing.isPending,
    holding.isPending,
    retiring.isPending,
    removing.isPending
  )
  const caption = [
    row.category_label,
    `since epoch ${row.created_epoch}`,
    row.world ? `of ${row.world.name}` : 'known in every world',
  ].join(' · ')
  return (
    <RecordRow
      icon={CONCEPT_ICONS[row.concept]}
      tone={row.retired ? 'muted' : 'gold'}
      title={row.name}
      caption={caption}
      aside={
        <div className='flex min-w-0 flex-wrap gap-1'>
          {row.built_in && <Badge variant='info'>Built in</Badge>}
          {row.retired && <Badge variant='warning'>Retired</Badge>}
          {held && <Badge variant='secondary'>Held</Badge>}
        </div>
      }
    >
      {row.description ? (
        <ExpandableText lines={2} tone='muted'>
          {row.description}
        </ExpandableText>
      ) : (
        <Muted variant='caption'>No description written yet.</Muted>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        {row.values.map((value) => {
          const property = info.properties.find(
            (item) => item.column === value.column
          )
          if (property?.options.length) {
            return (
              <div
                key={value.column}
                className='flex min-w-0 flex-wrap items-center gap-2'
              >
                <Muted as='span' variant='caption'>
                  {property.label}
                </Muted>
                <Badge variant='outline'>
                  {value.option_label ?? 'not set'}
                </Badge>
              </div>
            )
          }
          return (
            <StatBar
              key={value.column}
              label={property?.label ?? info.label}
              value={value.value}
              max={property?.high ?? FULL}
            />
          )
        })}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Muted as='span' variant='caption'>
          Made by
        </Muted>
        <Ref node={row.origin} empty='no maker named' />
        {row.derived_from_name && (
          <Badge variant='outline'>
            <LINEAGE_ICON aria-hidden='true' />
            {`Developed from ${row.derived_from_name}`}
          </Badge>
        )}
      </div>
      {row.holders.length ? (
        <PagedList
          items={row.holders}
          initial={6}
          noun={['holder', 'holders']}
          className='flex min-w-0 flex-wrap gap-2'
          itemKey={(node) => node.id}
        >
          {(node) => <RefLink node={node} />}
        </PagedList>
      ) : (
        <Muted variant='caption'>No one holds it now.</Muted>
      )}
      <RecordEditor
        title={`Set ${row.name}`}
        note={HOLD}
        fields={kindFields(info, siblings, row.id)}
        locked={row.locked}
        busy={busy}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <KindPassing info={info} row={row} blocked={blocked} />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={held ? LockOpen : Lock}
          label={held ? 'Release it to the world' : 'Hold it against the world'}
          busy={busy}
          onClick={() => holding.mutate()}
        />
        <StepButton
          icon={row.retired ? ArchiveRestore : Archive}
          label={row.retired ? 'Bring it back into use' : 'Retire it'}
          busy={busy}
          onClick={() => retiring.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Unmake this kind'
          busy={busy}
          onClick={() => removing.mutate()}
        />
      </div>
    </RecordRow>
  )
}
