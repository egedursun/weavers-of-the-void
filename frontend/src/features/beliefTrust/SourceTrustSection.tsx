import { useState } from 'react'
import { CirclePlus, Trash2 } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import {
  EmptyState,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import {
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import { type SourceTrustView, useSourceTrust } from './api'
import { BELIEF_SOURCES, TRUST_ICON } from './labels'

const SPAN = 100
const SHOWN = 6
const DOUBTED = 30
const HOLD =
  'Values you set are held against the engine until you release them.'
const TRUST_FIELDS: readonly Field[] = [
  { key: 'trust', label: 'Trust', kind: 'number', min: 0, max: SPAN },
]

type Edit = { values: EditValues; release: string[] }

function Trust({
  row,
  nodeId,
  blocked,
}: {
  row: SourceTrustView
  nodeId: number
  blocked: string | null
}) {
  const named = BELIEF_SOURCES[row.source]
  const editing = useMadeAction(
    'source_trust:edit',
    (vars: Edit) => ({
      holder_id: nodeId,
      source: row.source,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'Trust is set'
  )
  const removing = useMadeAction(
    'source_trust:delete',
    (_: void) => ({ holder_id: nodeId, source: row.source }),
    'Trust starts afresh'
  )
  return (
    <RecordRow
      icon={named.icon}
      tone={
        row.trust < DOUBTED
          ? 'danger'
          : row.trust >= SPAN - DOUBTED
            ? 'success'
            : 'info'
      }
      title={`${named.label}: trusted ${row.trust}`}
      caption={`${row.right} right and ${row.wrong} wrong so far; weighed in epoch ${row.updated_epoch}`}
    >
      <RecordEditor
        act={editing}
        title='Set this trust'
        note={HOLD}
        fields={TRUST_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Start afresh'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

export function SourceTrustSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useSourceTrust(nodeId)
  const rows = useShowMore(query.data?.sources ?? [], SHOWN, SHOWN)
  const [source, setSource] = useState<string>('rumour')
  const [trust, setTrust] = useState('60')
  const blocked = readOnlyReason
  const setting = useMadeAction(
    'source_trust:set',
    (_: void) => ({
      holder_id: nodeId,
      source: source as SourceTrustView['source'],
      trust: Math.min(SPAN, Math.max(0, Number(trust) || 0)),
      hold: true,
    }),
    'Trust is set'
  )
  return (
    <Section
      id='section-source-trust'
      title='Trust in sources: whom it believes and how far'
      description='Each source earns or loses trust as what it told proves true or false; trusted sources sway belief more, and a source trusted too little is no longer heeded.'
      icon={TRUST_ICON}
      tone='info'
    >
      <div
        data-surface='SourceTrustSection'
        className='flex min-w-0 flex-col gap-4'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading whom it trusts' />
        ) : query.isError ? (
          <EmptyState
            icon={TRUST_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            {query.data.sources.length ? (
              <>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {rows.visible.map((row) => (
                    <Trust
                      key={row.source}
                      row={row}
                      nodeId={nodeId}
                      blocked={blocked}
                    />
                  ))}
                </ul>
                <ShowMore state={rows} />
              </>
            ) : (
              <EmptyState
                icon={TRUST_ICON}
                size='inline'
                title='No source weighed yet'
                description={`${query.data.node.name} has not yet learned whom to trust; set it below.`}
              />
            )}
            <ForgeCard
              icon={CirclePlus}
              tone='info'
              title='Set trust in a source'
              note='The trust you set is held until you release it.'
              columns={2}
              action={
                <StepButton
                  act={setting}
                  icon={CirclePlus}
                  label='Set it'
                  variant='default'
                  busy={why(blocked, setting.isPending)}
                  onClick={() => setting.mutate()}
                />
              }
            >
              <ChoiceField
                label='Source'
                value={source}
                table={BELIEF_SOURCES}
                blocked={blocked}
                onPick={setSource}
              />
              <NumberField
                label='Trust'
                value={trust}
                min={0}
                max={SPAN}
                onChange={setTrust}
              />
            </ForgeCard>
          </>
        )}
      </div>
    </Section>
  )
}
