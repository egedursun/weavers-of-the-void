import { useState } from 'react'
import { Plus, Utensils, Wheat } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type FolkwaysNodeView, useFolkwaysAction } from './api'
import { DIET_SHARES, NUTRIENTS } from './labels'
import { SPAN, useFolkwaysRow, useFolkwaysStep, withNone } from './model'

type Diet = NonNullable<FolkwaysNodeView['diet']>
type Nutrition = NonNullable<FolkwaysNodeView['nutrition']>
type Need = FolkwaysNodeView['needs'][number]

const SHARE_FIELDS = DIET_SHARES.map(({ key, label }) => ({
  key,
  label: `${label} (share)`,
  kind: 'number' as const,
  min: 0,
  max: SPAN,
}))

function DietCard({
  nodeId,
  row,
  blocked,
}: {
  nodeId: number
  row: Diet
  blocked: string | null
}) {
  const action = useFolkwaysRow(
    'diet:edit',
    'diet:delete',
    { holder_id: nodeId },
    blocked
  )
  return (
    <Held
      icon={Utensils}
      tone='gold'
      title='What it eats'
      caption={`Read in epoch ${row.updated_epoch} · energy ${row.energy} of ${SPAN}`}
      removeLabel='Forget the diet'
      editTitle='Set the diet'
      note='A diet is read each epoch from the stores of a town: staples from grain, bread and tubers, protein from meat, fish and eggs, fats from milk and cheese, fresh food from fruit and herbs, minerals from fish and herbs. Energy falls with hunger. A share you set stays as you set it.'
      fields={[
        ...SHARE_FIELDS,
        { key: 'energy', label: 'Energy', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Energy (${row.energy} of ${SPAN})`}
        value={row.energy}
        tone='warning'
        icon={Wheat}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @md/tiles:grid-cols-4'>
          {DIET_SHARES.map(({ key, label, icon }) => (
            <KpiTile key={key} label={label} value={row[key]} icon={icon} />
          ))}
        </div>
      </div>
    </Held>
  )
}

function NutritionCard({
  nodeId,
  row,
  blocked,
}: {
  nodeId: number
  row: Nutrition
  blocked: string | null
}) {
  const action = useFolkwaysRow(
    'nutrition_score:edit',
    'nutrition_score:delete',
    { holder_id: nodeId },
    blocked
  )
  const lacking = row.deficiency ? NUTRIENTS[row.deficiency] : null
  return (
    <Held
      icon={Wheat}
      tone={
        row.score >= 70 ? 'success' : row.score >= 40 ? 'warning' : 'danger'
      }
      title={`Fed ${row.score} of ${SPAN}`}
      caption={`Energy ${row.energy} · balance ${row.balance}${row.childhood !== null ? ` · fed ${row.childhood} as a child` : ''}${row.grown ? ' · grown' : ''}`}
      removeLabel='Forget the score'
      editTitle='Set how well it is fed'
      note='How well a thing is fed: energy and the balance of the nutrients its body needs. A body below being well fed resists disease and heals worse and bears fewer children; what a child was fed sets the strength and toughness of the adult. The elite eat better than their town and the lowest worse.'
      fields={[
        { key: 'energy', label: 'Energy', kind: 'number', min: 0, max: SPAN },
        { key: 'balance', label: 'Balance', kind: 'number', min: 0, max: SPAN },
        { key: 'score', label: 'Score', kind: 'number', min: 0, max: SPAN },
        {
          key: 'deficiency',
          label: 'Short of',
          kind: 'pick',
          table: withNone(table(NUTRIENTS), 'Nothing'),
        },
        {
          key: 'childhood',
          label: 'Fed as a child',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'grown', label: 'Grown', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={lacking ? <Tag item={lacking} /> : undefined}
    >
      <Meter
        label={`Balance of nutrients (${row.balance} of ${SPAN})`}
        value={row.balance}
        tone='success'
        icon={Utensils}
      />
    </Held>
  )
}

function NeedCard({
  people,
  row,
  blocked,
}: {
  people: number
  row: Need
  blocked: string | null
}) {
  const action = useFolkwaysRow(
    'nutrient_need:edit',
    'nutrient_need:delete',
    { people_id: people, nutrient: row.nutrient },
    blocked
  )
  const spec = NUTRIENTS[row.nutrient]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={`Weight ${row.weight} of ${SPAN}`}
      removeLabel='Strike the need'
      editTitle='Set the need'
      note="A need of the people's bodies, read from their biology: what they eat by, and whether they live from light, stone or essence. Its weight is how much its lack hurts."
      fields={[
        { key: 'weight', label: 'Weight', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

export function DietPanel({
  nodeId,
  data,
  blocked,
}: {
  nodeId: number
  data: FolkwaysNodeView
  blocked: string | null
}) {
  const people = data.people?.id ?? null
  const [nutrient, setNutrient] = useState('protein')
  const [weight, setWeight] = useState('50')
  const setting = useFolkwaysAction(
    'diet:set',
    (_: void) => ({ holder_id: nodeId, values: {} }),
    'The diet is set'
  )
  const scoring = useFolkwaysAction(
    'nutrition_score:set',
    (_: void) => ({ holder_id: nodeId, values: {} }),
    'The nutrition is set'
  )
  const needing = useFolkwaysAction(
    'nutrient_need:set',
    (_: void) => ({
      people_id: people ?? 0,
      nutrient: nutrient as Need['nutrient'],
      weight: Number(weight || '0'),
    }),
    'The need is set'
  )
  const feeding = useFolkwaysStep(
    'nutrition:feed',
    {},
    blocked,
    'Every life is fed'
  )
  const dietBusy = why(
    blocked ?? (data.diet ? 'It already has a diet; adjust it above' : null),
    setting.isPending
  )
  const scoreBusy = why(
    blocked ??
      (data.nutrition ? 'It is already scored; adjust it above' : null),
    scoring.isPending
  )
  const needBusy = why(
    blocked ??
      (people === null
        ? 'Only a people, or a thing of a people, has bodies with needs'
        : null),
    needing.isPending
  )
  return (
    <div data-surface='DietPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-diet'
        title='What it eats'
        legend={[
          { text: 'Food', variant: 'success' },
          { text: 'Energy', variant: 'warning' },
        ]}
        rows={
          data.diet
            ? [
                ...DIET_SHARES.map(({ key, label }) => ({
                  key,
                  caption: `${label}: ${data.diet?.[key] ?? 0}`,
                  segments: [
                    { value: data.diet?.[key] ?? 0, fill: 'fill-success' },
                  ],
                })),
                {
                  key: 'energy',
                  caption: `Energy: ${data.diet.energy}`,
                  segments: [{ value: data.diet.energy, fill: 'fill-warning' }],
                },
              ]
            : []
        }
        max={SPAN}
        noun={['share', 'shares']}
        empty='No diet is read for this thing.'
      />
      {data.diet && (
        <DietCard nodeId={nodeId} row={data.diet} blocked={blocked} />
      )}
      {data.nutrition ? (
        <NutritionCard nodeId={nodeId} row={data.nutrition} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          It is not scored for nutrition; towns, peoples and lives are scored
          each epoch.
        </Muted>
      )}
      <Listed
        title={`Needs of ${data.people?.name ?? 'its people'}`}
        items={data.needs}
        empty='No needs are read for its people.'
        noun={['need', 'needs']}
        itemKey={(item) => item.nutrient}
      >
        {(item) => (
          <NeedCard people={people ?? 0} row={item} blocked={blocked} />
        )}
      </Listed>
      <ForgeCard
        icon={Utensils}
        tone='gold'
        title='Feed and read'
        note='Give it a diet or a score to hold by hand, or read every diet and feed every life now.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <StepButton
              icon={Wheat}
              label='Feed every life now'
              busy={feeding.busy}
              onClick={feeding.run}
            />
            <Button
              size='sm'
              variant='outline'
              disabled={dietBusy !== null}
              disabledReason={dietBusy ?? undefined}
              onClick={() => setting.mutate()}
            >
              <Utensils />
              Give it a diet
            </Button>
            <Button
              size='sm'
              disabled={scoreBusy !== null}
              disabledReason={scoreBusy ?? undefined}
              onClick={() => scoring.mutate()}
            >
              <Wheat />
              Score its nutrition
            </Button>
          </div>
        }
      >
        <Muted variant='caption'>
          {data.diet
            ? `Its diet was read in epoch ${data.diet.updated_epoch}.`
            : 'It holds no diet yet.'}
        </Muted>
        <Muted variant='caption'>
          {data.nutrition
            ? `Its nutrition was read in epoch ${data.nutrition.updated_epoch}.`
            : 'It holds no nutrition score yet.'}
        </Muted>
      </ForgeCard>
      <ForgeCard
        icon={Plus}
        tone='info'
        title='Give its people a need'
        note="A need of the people's bodies; its weight is how much its lack hurts."
        columns={2}
        action={
          <Button
            size='sm'
            disabled={needBusy !== null}
            disabledReason={needBusy ?? undefined}
            onClick={() => needing.mutate()}
          >
            <Plus />
            Set the need
          </Button>
        }
      >
        <MindPicker
          label='Nutrient'
          value={nutrient}
          table={table(NUTRIENTS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setNutrient}
        />
        <NumberField
          label='Weight'
          value={weight}
          min={0}
          max={SPAN}
          blocked={blocked}
          onChange={setWeight}
        />
      </ForgeCard>
    </div>
  )
}
