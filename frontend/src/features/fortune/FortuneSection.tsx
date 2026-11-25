import { useState } from 'react'
import { Activity, CirclePlus, Skull, Trash2, Zap } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  Chip,
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { MISHAP_KINDS } from '@/features/folkways/labels'
import { Ref } from '@/features/gatherings/parts'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type FortuneNodeView,
  type FortuneSourceView,
  useNodeFortune,
} from './api'
import { FORTUNE_ICON, LAWS, SOURCES } from './labels'

const SHOWN = 5
const HOLD =
  'Values you set are held against the engine until you release them.'
const LEVELS = {
  '1': { label: 'Small', icon: Activity, tone: 'info' as const },
  '2': { label: 'Grave', icon: Zap, tone: 'warning' as const },
  '3': { label: 'Deadly', icon: Skull, tone: 'danger' as const },
}

type Edit = { values: EditValues; release: string[] }

const PROFILE_FIELDS: readonly Field[] = [
  { key: 'fortune', label: 'Fortune now', kind: 'number', min: -100, max: 100 },
  {
    key: 'streak',
    label: 'Personal streak',
    kind: 'number',
    min: -100,
    max: 100,
  },
]

const SOURCE_FIELDS: readonly Field[] = [
  { key: 'kind', label: 'What turns it', kind: 'pick', table: table(SOURCES) },
  { key: 'strength', label: 'Strength', kind: 'number', min: -100, max: 100 },
  { key: 'giver_node_id', label: 'Given by', kind: 'node', types: [] },
  { key: 'until_epoch', label: 'Lasts until epoch', kind: 'number', min: 0 },
]

function tone(value: number) {
  return value > 0 ? 'success' : value < 0 ? 'danger' : 'muted'
}

function Source({
  row,
  blocked,
}: {
  row: FortuneSourceView
  blocked: string | null
}) {
  const named = SOURCES[row.kind]
  const editing = useMadeAction(
    'fortune_source:edit',
    (vars: Edit) => ({
      source_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The source of fortune is set so'
  )
  const removing = useMadeAction(
    'fortune_source:delete',
    (_: void) => ({ source_id: row.id }),
    'The source of fortune is gone'
  )
  return (
    <RecordRow
      icon={named.icon}
      tone={tone(row.strength)}
      title={`${named.label} ${row.strength > 0 ? '+' : ''}${row.strength}`}
      caption={`since epoch ${row.since_epoch}${row.until_epoch !== null ? `, until epoch ${row.until_epoch}` : ', for good'}`}
    >
      <Ref node={row.giver} empty='given by no one named' />
      <RecordEditor
        act={editing}
        title='Set this source'
        note={HOLD}
        fields={SOURCE_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Take it away'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Law({
  view,
  blocked,
}: {
  view: FortuneNodeView
  blocked: string | null
}) {
  const [law, setLaw] = useState<string>(view.law)
  const setting = useMadeAction(
    'fortune_law:set',
    (_: void) => ({
      world_id: view.world_id ?? 0,
      law: law as FortuneNodeView['law'],
    }),
    'Fortune runs by a new law'
  )
  const noWorld =
    view.world_id === null
      ? 'This thing stands in no world whose law could be set'
      : null
  return (
    <ForgeCard
      icon={LAWS[view.law].icon}
      tone='info'
      title={`Fortune in its world: ${LAWS[view.law].label.toLowerCase()}`}
      note='The law of fortune sets whether luck comes only from causes, from a streak each being carries, from the gods alone, or from what peoples believe.'
      columns={2}
      action={
        <StepButton
          act={setting}
          icon={CirclePlus}
          label='Set the law'
          busy={why(blocked ?? noWorld, setting.isPending)}
          onClick={() => setting.mutate()}
        />
      }
    >
      <ChoiceField
        label='How fortune runs'
        value={law}
        table={LAWS}
        blocked={blocked ?? noWorld}
        onPick={setLaw}
      />
    </ForgeCard>
  )
}

export function FortuneSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeFortune(nodeId)
  const sources = useShowMore(query.data?.sources ?? [], SHOWN, SHOWN * 2)
  const mishaps = useShowMore(query.data?.mishaps ?? [], SHOWN, SHOWN * 2)
  const cohort = useShowMore(query.data?.cohort ?? [], SHOWN, SHOWN * 2)
  const [kind, setKind] = useState<string>('blessing')
  const [strength, setStrength] = useState('15')
  const [epochs, setEpochs] = useState('4')
  const [mishap, setMishap] = useState<string>('fall')
  const [level, setLevel] = useState<string>('1')
  const editing = useMadeAction(
    'fortune:edit',
    (vars: Edit) => ({
      node_id: nodeId,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'Its fortune is set so'
  )
  const giving = useMadeAction(
    'fortune_source:create',
    (_: void) => ({
      holder_id: nodeId,
      kind: kind as FortuneSourceView['kind'],
      strength: Math.min(100, Math.max(-100, Number(strength) || 0)),
      epochs: Math.max(0, Number(epochs) || 0),
    }),
    'Its fortune turns'
  )
  const striking = useMadeAction(
    'mishap:trigger',
    (_: void) => ({
      victim_id: nodeId,
      kind: mishap as FortuneNodeView['mishaps'][number]['kind'],
      level: Number(level),
    }),
    'A mishap befalls it'
  )
  const view = query.data
  const blocked = readOnlyReason
  const deadly = view?.mishaps.filter((row) => row.died).length ?? 0
  return (
    <Section
      id='section-fortune'
      title='Fortune: the luck it carries and the mishaps it has met'
      description='Fortune is the sum of what turns it: blessings, curses, charms, oaths, places and, where the world allows, a streak of its own; it shifts the mishaps of daily life and every draw a life depends on.'
      icon={FORTUNE_ICON}
      tone='gold'
    >
      <div
        data-surface='FortuneSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its fortune' />
        ) : query.isError ? (
          <EmptyState
            icon={FORTUNE_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-4'>
              <KpiTile
                label='Fortune'
                value={String(query.data.fortune)}
                icon={FORTUNE_ICON}
                tone={tone(query.data.fortune)}
              />
              <KpiTile
                label='Streak'
                value={String(query.data.streak)}
                icon={Activity}
                tone={tone(query.data.streak)}
              />
              <KpiTile
                label='Sources'
                value={String(query.data.sources.length)}
                icon={CirclePlus}
                tone='info'
              />
              <KpiTile
                label='Mishaps that took a life'
                value={String(deadly)}
                icon={Skull}
                tone={deadly ? 'danger' : 'muted'}
              />
            </div>
            <RecordRow
              icon={FORTUNE_ICON}
              tone={tone(query.data.fortune)}
              title={`Fortune ${query.data.fortune}, streak ${query.data.streak}`}
              caption={
                query.data.held_values.length
                  ? `Held: ${query.data.held_values.join(', ')}`
                  : 'Reckoned anew each epoch from its sources'
              }
            >
              <RecordEditor
                act={editing}
                title='Set its fortune'
                note={HOLD}
                fields={PROFILE_FIELDS}
                locked={query.data.held_values}
                busy={why(blocked, editing.isPending)}
                onSave={(values) => editing.mutate({ values, release: [] })}
                onRelease={(keys) =>
                  editing.mutate({ values: {}, release: keys })
                }
              />
            </RecordRow>
            {query.data.sources.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {sources.visible.map((row) => (
                    <Source key={row.id} row={row} blocked={blocked} />
                  ))}
                </ul>
                <ShowMore state={sources} />
              </div>
            ) : (
              <EmptyState
                icon={FORTUNE_ICON}
                size='inline'
                title='Nothing turns its fortune'
                description={`${query.data.node.name} carries only what its world's law gives it; turn it below.`}
              />
            )}
            <ForgeCard
              icon={CirclePlus}
              tone='gold'
              title='Turn its fortune'
              note='A source turns fortune for as many epochs as you give it.'
              columns={3}
              action={
                <StepButton
                  act={giving}
                  icon={CirclePlus}
                  label='Turn it'
                  variant='default'
                  busy={why(blocked, giving.isPending)}
                  onClick={() => giving.mutate()}
                />
              }
            >
              <ChoiceField
                label='What turns it'
                value={kind}
                table={SOURCES}
                blocked={blocked}
                onPick={setKind}
              />
              <NumberField
                label='Strength'
                value={strength}
                min={-100}
                max={100}
                onChange={setStrength}
              />
              <NumberField
                label='Epochs it lasts'
                value={epochs}
                min={0}
                onChange={setEpochs}
              />
            </ForgeCard>
            <Law view={query.data} blocked={blocked} />
            <ul className='flex min-w-0 flex-col gap-2'>
              {mishaps.visible.map((row) => (
                <li
                  key={row.id}
                  className='flex min-w-0 flex-wrap items-center gap-2'
                >
                  <Chip icon={MISHAP_KINDS[row.kind].icon}>
                    {MISHAP_KINDS[row.kind].label}, epoch {row.epoch}
                  </Chip>
                  <Chip icon={Activity}>
                    Severity {row.severity}
                    {row.died ? ', took a life' : ''}
                    {row.explained ? ', explained' : ', unexplained'}
                  </Chip>
                </li>
              ))}
            </ul>
            <ShowMore state={mishaps} />
            <ul className='flex min-w-0 flex-col gap-2'>
              {cohort.visible.map((row) => (
                <li
                  key={row.epoch}
                  className='flex min-w-0 flex-wrap items-center gap-2'
                >
                  <Chip icon={Skull}>
                    Epoch {row.epoch}: {row.dead} died and {row.injured} were
                    hurt by accident, a rate of {row.rate_pct}%
                  </Chip>
                </li>
              ))}
            </ul>
            <ShowMore state={cohort} />
            <ForgeCard
              icon={Zap}
              tone='danger'
              title='Let a mishap befall it'
              note='A mishap harms by its kind and its severity; it is told plainly and its folk judge its cause.'
              columns={2}
              action={
                <StepButton
                  act={striking}
                  icon={Zap}
                  label='Let it befall'
                  busy={why(blocked, striking.isPending)}
                  onClick={() => striking.mutate()}
                />
              }
            >
              <ChoiceField
                label='Kind of mishap'
                value={mishap}
                table={MISHAP_KINDS}
                blocked={blocked}
                onPick={setMishap}
              />
              <ChoiceField
                label='How grave'
                value={level}
                table={LEVELS}
                blocked={blocked}
                onPick={setLevel}
              />
            </ForgeCard>
          </>
        )}
      </div>
    </Section>
  )
}
