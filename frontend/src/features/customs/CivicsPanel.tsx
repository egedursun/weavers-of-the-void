import { useState } from 'react'
import { Gavel, Landmark, Minus, Plus, Scale, Shield } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { useJustice } from '@/features/entity/justice/api'
import { CRIMES } from '@/features/entity/justice/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type CustomsNodeView, useCustomsAction } from './api'
import { EVIDENCE_KINDS, MEMBERSHIPS, RELIEFS, RIGHTS } from './labels'
import { MANY, SPAN, useCustomsRow, useCustomsStep } from './model'

type View = CustomsNodeView
type Evidence = View['evidence'][number]
type Category = View['categories'][number]
type Border = NonNullable<View['border']>
type Relief = NonNullable<View['relief']>
type Measures = NonNullable<View['measures']>

const RIGHT_KEYS = Object.keys(RIGHTS) as (keyof typeof RIGHTS)[]

const NOT_A_REALM =
  'Only a realm keeps citizenship, borders, relief and measures'

function EvidenceCard({
  row,
  caseName,
  blocked,
}: {
  row: Evidence
  caseName: string | null
  blocked: string | null
}) {
  const action = useCustomsRow(
    'evidence:edit',
    'evidence:delete',
    { record_id: row.id },
    blocked
  )
  const kind = EVIDENCE_KINDS[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={row.forged ? 'danger' : kind.tone}
      title={`${kind.label}${row.forged ? ', forged' : ''}`}
      caption={`Before ${caseName ? `the case of ${caseName}` : 'a case'} · found in epoch ${row.found_epoch} · reliability ${row.reliability}`}
      removeLabel='Strike the evidence'
      editTitle='Set the evidence'
      note='Evidence weighs a case before its trial and fades as the case waits; only what points at the accused weighs against them.'
      fields={[
        {
          key: 'kind',
          label: 'Evidence',
          kind: 'pick',
          table: table(EVIDENCE_KINDS),
        },
        {
          key: 'points_to_node_id',
          label: 'Points to',
          kind: 'node',
          types: ['mortal'],
        },
        {
          key: 'reliability',
          label: 'Reliability',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'forged', label: 'Forged', kind: 'pick', table: YES_NO },
        {
          key: 'found_epoch',
          label: 'Found in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Points to', <Ref key='to' node={row.points_to} empty='no one' />],
        ]}
      />
    </Held>
  )
}

function CategoryCard({
  realm,
  row,
  blocked,
}: {
  realm: number
  row: Category
  blocked: string | null
}) {
  const action = useCustomsRow(
    'membership_category:edit',
    'membership_category:delete',
    { polity_id: realm, category: row.category },
    blocked
  )
  const [right, setRight] = useState('office')
  const held = row.rights.includes(right)
  const granting = useCustomsAction(
    'membership_category:right',
    (_: void) => ({
      polity_id: realm,
      category: row.category,
      right: right as never,
      granted: !held,
    }),
    held ? 'The right is taken away' : 'The right is granted'
  )
  const busy = why(blocked, granting.isPending)
  const category = MEMBERSHIPS[row.category]
  return (
    <Held
      icon={category.icon}
      tone={category.tone}
      title={category.label}
      caption={`${row.rights.length} rights`}
      removeLabel='Strike the category'
      editTitle='Set the category'
      note='Each category of folk holds its own rights: office, marriage, arms and the courts.'
      fields={RIGHT_KEYS.map((key) => ({
        key,
        label: `Right to ${RIGHTS[key].label.toLowerCase()}`,
        kind: 'pick' as const,
        table: YES_NO,
      }))}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='flex min-w-0 flex-wrap gap-1'>
        {row.rights.length ? (
          row.rights.map((item) => (
            <Badge key={item} size='sm' variant='secondary'>
              {RIGHTS[item as keyof typeof RIGHTS]?.label ?? item}
            </Badge>
          ))
        ) : (
          <Muted variant='caption'>It holds no rights.</Muted>
        )}
      </div>
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <MindPicker
          label='Right'
          value={right}
          table={table(RIGHTS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setRight}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => granting.mutate()}
        >
          {held ? <Minus /> : <Plus />}
          {held ? 'Take it away' : 'Grant it'}
        </Button>
      </div>
    </Held>
  )
}

function BorderCard({
  realm,
  row,
  blocked,
}: {
  realm: number
  row: Border
  blocked: string | null
}) {
  const action = useCustomsRow(
    'border_control:edit',
    'border_control:delete',
    { polity_id: realm },
    blocked
  )
  return (
    <Held
      icon={Shield}
      tone='warning'
      title={`A border of ${row.delay} epochs' delay`}
      caption={`Fee ${row.fee} · enforcement ${row.enforcement} · corruption ${row.corruption}`}
      removeLabel='Open the border'
      editTitle='Set the border'
      note='A border slows trade into the realm by its delay and enforcement and fills its treasury with fees; corruption lets forged passes slip past them.'
      fields={[
        { key: 'fee', label: 'Fee', kind: 'number', min: 0, max: MANY },
        {
          key: 'delay',
          label: 'Delay (epochs)',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'enforcement',
          label: 'Enforcement',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'corruption',
          label: 'Corruption',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Enforcement (${row.enforcement} of ${SPAN})`}
        value={row.enforcement}
        tone='warning'
        icon={Shield}
      />
    </Held>
  )
}

function ReliefCard({
  realm,
  row,
  blocked,
}: {
  realm: number
  row: Relief
  blocked: string | null
}) {
  const action = useCustomsRow(
    'poor_relief:edit',
    'poor_relief:delete',
    { polity_id: realm },
    blocked
  )
  const kind = RELIEFS[row.kind]
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={kind.label}
      caption={`Budget ${row.budget} · reaches ${row.reach}% of the poor`}
      removeLabel='End the relief'
      editTitle='Set the relief'
      note='Relief is paid from the treasury each epoch; it eases the poverty of the towns it reaches and keeps their poor from theft. A treasury that cannot pay it narrows its reach.'
      fields={[
        { key: 'kind', label: 'Relief', kind: 'pick', table: table(RELIEFS) },
        { key: 'budget', label: 'Budget', kind: 'number', min: 0, max: MANY },
        { key: 'reach', label: 'Reach (%)', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function MeasuresCard({
  realm,
  row,
  blocked,
}: {
  realm: number
  row: Measures
  blocked: string | null
}) {
  const action = useCustomsRow(
    'measure_standard:edit',
    'measure_standard:delete',
    { polity_id: realm },
    blocked
  )
  return (
    <Held
      icon={Scale}
      tone='info'
      title={row.standard ? 'Standard measures' : 'No standard measures'}
      caption={`Since epoch ${row.adopted_epoch} · fraud ${row.fraud}`}
      removeLabel='Strike the standard'
      editTitle='Set the standard'
      note='Standard measures raise trade between towns that share them and the taxes a realm gathers; fraud with false measures brings merchants to court.'
      fields={[
        { key: 'standard', label: 'Standard', kind: 'pick', table: YES_NO },
        {
          key: 'adopted_epoch',
          label: 'Adopted in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'fraud', label: 'Fraud', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

export function CivicsPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: View
  blocked: string | null
}) {
  const realm = kind === 'polity'
  const [caseId, setCaseId] = useState('')
  const justice = useJustice(nodeId)
  const cases = justice.data?.cases ?? []
  const nameCase = (row: (typeof cases)[number], lower: boolean) => {
    const crime = CRIMES[row.crime]?.label ?? row.crime
    return `${lower ? crime.toLowerCase() : crime}${row.accused ? ` against ${row.accused.name}` : ''}`
  }
  const caseNames: Record<string, string> = Object.fromEntries(
    cases.map((row) => [String(row.id), nameCase(row, false)])
  )
  const caseCaptions: Record<string, string> = Object.fromEntries(
    cases.map((row) => [String(row.id), nameCase(row, true)])
  )
  const [evidenceKind, setEvidenceKind] = useState('trace')
  const [category, setCategory] = useState('subject')
  const [relief, setRelief] = useState('alms')
  const gate = blocked ?? (realm ? null : NOT_A_REALM)
  const laying = useCustomsAction(
    'evidence:create',
    (_: void) => ({
      case_id: Number(caseId || '0'),
      kind: evidenceKind as Evidence['kind'],
      points_to_node_id: kind === 'mortal' ? nodeId : null,
      reliability: 50,
    }),
    'The evidence is laid'
  )
  const keeping = useCustomsAction(
    'membership_category:set',
    (_: void) => ({
      polity_id: nodeId,
      category: category as Category['category'],
    }),
    'The category is kept'
  )
  const guarding = useCustomsAction(
    'border_control:set',
    (_: void) => ({ polity_id: nodeId, fee: 50, delay: 1, enforcement: 50 }),
    'The border is guarded'
  )
  const relieving = useCustomsAction(
    'poor_relief:set',
    (_: void) => ({
      polity_id: nodeId,
      kind: relief as Relief['kind'],
      budget: 50,
      reach: 40,
    }),
    'The poor are relieved'
  )
  const measuring = useCustomsAction(
    'measure_standard:set',
    (_: void) => ({ polity_id: nodeId, standard: true, fraud: 10 }),
    'The measures are set'
  )
  const running = useCustomsStep(
    'civics:run',
    {},
    blocked,
    'Civic life is read'
  )
  const evidenceBusy = why(
    blocked ??
      (!cases.length
        ? 'No case touches this'
        : !caseId
          ? 'Choose a case'
          : null),
    laying.isPending
  )
  return (
    <div data-surface='CivicsPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-civics'
        title='The weight of the evidence'
        legend={[
          { text: 'Sound', variant: 'success' },
          { text: 'Forged', variant: 'destructive' },
        ]}
        rows={data.evidence.map((row) => ({
          key: String(row.id),
          caption: `${EVIDENCE_KINDS[row.kind].label}: reliability ${row.reliability}`,
          segments: [
            {
              value: Math.min(SPAN, row.reliability),
              fill: row.forged ? 'fill-destructive' : 'fill-success',
            },
          ],
        }))}
        max={SPAN}
        noun={['piece of evidence', 'pieces of evidence']}
        empty='No evidence weighs on any case here.'
      />
      <Listed
        title='Evidence'
        items={data.evidence}
        empty='No evidence touches this.'
        noun={['piece of evidence', 'pieces of evidence']}
        itemKey={(item) => item.id}
      >
        {(item) => (
          <EvidenceCard
            row={item}
            caseName={caseCaptions[String(item.case_id)] ?? null}
            blocked={blocked}
          />
        )}
      </Listed>
      <Listed
        title='Categories of folk'
        items={data.categories}
        empty='It keeps no categories of folk.'
        noun={['category', 'categories']}
        itemKey={(item) => item.category}
      >
        {(item) => <CategoryCard realm={nodeId} row={item} blocked={blocked} />}
      </Listed>
      {data.border && (
        <BorderCard realm={nodeId} row={data.border} blocked={blocked} />
      )}
      {data.relief && (
        <ReliefCard realm={nodeId} row={data.relief} blocked={blocked} />
      )}
      {data.measures && (
        <MeasuresCard realm={nodeId} row={data.measures} blocked={blocked} />
      )}
      <ForgeCard
        icon={Gavel}
        tone='danger'
        title='Lay evidence'
        note='Evidence before a case, pointing to this mortal when it is one.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={evidenceBusy !== null}
            disabledReason={evidenceBusy ?? undefined}
            onClick={() => laying.mutate()}
          >
            <Plus />
            Lay it
          </Button>
        }
      >
        <MindPicker
          label='Case'
          value={caseId}
          table={caseNames}
          placeholder={cases.length ? 'Choose' : 'No case touches this'}
          blocked={blocked}
          onPick={setCaseId}
        />
        <MindPicker
          label='Evidence'
          value={evidenceKind}
          table={table(EVIDENCE_KINDS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setEvidenceKind}
        />
      </ForgeCard>
      <ForgeCard
        icon={Landmark}
        tone='gold'
        title='Order the realm'
        note='Keep a category of folk, guard the border, relieve the poor and set the measures.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Landmark}
              label='Read civic life now'
              busy={running.busy}
              onClick={running.run}
            />
            <Button
              size='sm'
              variant='outline'
              disabled={why(gate, keeping.isPending) !== null}
              disabledReason={why(gate, keeping.isPending) ?? undefined}
              onClick={() => keeping.mutate()}
            >
              <Plus />
              Category
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={
                why(
                  gate ??
                    (data.border
                      ? 'It guards its border; adjust it above'
                      : null),
                  guarding.isPending
                ) !== null
              }
              disabledReason={
                why(
                  gate ??
                    (data.border
                      ? 'It guards its border; adjust it above'
                      : null),
                  guarding.isPending
                ) ?? undefined
              }
              onClick={() => guarding.mutate()}
            >
              <Shield />
              Border
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={
                why(
                  gate ??
                    (data.relief
                      ? 'It relieves its poor; adjust it above'
                      : null),
                  relieving.isPending
                ) !== null
              }
              disabledReason={
                why(
                  gate ??
                    (data.relief
                      ? 'It relieves its poor; adjust it above'
                      : null),
                  relieving.isPending
                ) ?? undefined
              }
              onClick={() => relieving.mutate()}
            >
              <Plus />
              Relief
            </Button>
            <Button
              size='sm'
              disabled={
                why(
                  gate ??
                    (data.measures
                      ? 'It has its measures; adjust them above'
                      : null),
                  measuring.isPending
                ) !== null
              }
              disabledReason={
                why(
                  gate ??
                    (data.measures
                      ? 'It has its measures; adjust them above'
                      : null),
                  measuring.isPending
                ) ?? undefined
              }
              onClick={() => measuring.mutate()}
            >
              <Scale />
              Measures
            </Button>
          </div>
        }
      >
        <MindPicker
          label='Category'
          value={category}
          table={table(MEMBERSHIPS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setCategory}
        />
        <MindPicker
          label='Relief'
          value={relief}
          table={table(RELIEFS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setRelief}
        />
      </ForgeCard>
    </div>
  )
}
