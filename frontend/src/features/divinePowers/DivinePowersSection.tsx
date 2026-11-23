import { useState } from 'react'
import { CirclePlus, Trash2, Wand2, X } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { domainHookValues, domainValues } from '@/api/generated/schema'
import {
  EmptyState,
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
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { wordOf } from '@/features/entity/affairs/labels'
import { words } from '@/features/entity/lore/api'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import { type DivinePowerView, useNodePowers } from './api'
import { COSTS, MODES, OBJECTS, POWER_ICON, SCOPES, VERBS } from './labels'

const DOMAINS_SHOWN = 6
const SHOWN = 4
const HOLD = 'Parts you set are held against the engine until you release them.'
const DOMAINS = Object.fromEntries(
  domainValues.map((value) => [
    value,
    {
      label: wordOf(domainValues, value).toLowerCase(),
      icon: Wand2,
      tone: 'verdigris' as const,
    },
  ])
)

type Edit = { values: EditValues; release: string[] }

const POWER_FIELDS: readonly Field[] = [
  { key: 'name', label: 'Name of the power', kind: 'text' },
  { key: 'verb', label: 'What it does', kind: 'pick', table: table(VERBS) },
  {
    key: 'object',
    label: 'What it acts on',
    kind: 'pick',
    table: table(OBJECTS),
  },
  { key: 'object_key', label: 'Which one, if named', kind: 'text' },
  {
    key: 'scope',
    label: 'How far it reaches',
    kind: 'pick',
    table: table(SCOPES),
  },
  { key: 'mode', label: 'When it acts', kind: 'pick', table: table(MODES) },
  { key: 'cost', label: 'What it costs', kind: 'pick', table: table(COSTS) },
  {
    key: 'cost_amount',
    label: 'How much it costs',
    kind: 'number',
    min: 0,
    max: 1000,
  },
  {
    key: 'cooldown',
    label: 'Epochs it rests',
    kind: 'number',
    min: 0,
    max: 100,
  },
  { key: 'strength', label: 'Strength', kind: 'number', min: 0, max: 100 },
]

function Power({
  row,
  blocked,
}: {
  row: DivinePowerView
  blocked: string | null
}) {
  const verb = VERBS[row.verb]
  const [target, setTarget] = useState<number | null>(null)
  const [domain, setDomain] = useState<string>(domainValues[0])
  const editing = useMadeAction(
    'divine_power:edit',
    (vars: Edit) => ({
      power_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The power is shaped so'
  )
  const using = useMadeAction(
    'divine_power:use',
    (_: void) => ({ power_id: row.id, target_id: target }),
    'The power acts'
  )
  const linking = useMadeAction(
    'divine_power:domains',
    (domains: string[]) => ({
      power_id: row.id,
      domains: domains as DivinePowerView['domains'],
    }),
    'The power draws on its domains'
  )
  const removing = useMadeAction(
    'divine_power:delete',
    (_: void) => ({ power_id: row.id }),
    'The power is revoked'
  )
  const resting = row.ready ? null : 'It is resting until its cooldown passes'
  const domains = row.domains as string[]
  const shownDomains = useShowMore(domains, DOMAINS_SHOWN, DOMAINS_SHOWN)
  const preset = row.son_preset ?? row.foreign_preset
  return (
    <RecordRow
      icon={verb.icon}
      tone={verb.tone ?? 'info'}
      title={`${row.name}: ${verb.label.toLowerCase()} ${OBJECTS[row.object].label.toLowerCase()}${row.object_key ? ` (${words(row.object_key)})` : ''}`}
      caption={`${SCOPES[row.scope].label}, ${MODES[row.mode].label.toLowerCase()}, strength ${row.strength}; costs ${row.cost_amount} ${COSTS[row.cost].label.toLowerCase()}, rests ${row.cooldown} epoch${row.cooldown === 1 ? '' : 's'}; granted in epoch ${row.granted_epoch}${row.last_used_epoch !== null ? `, last used in epoch ${row.last_used_epoch}` : ''}`}
    >
      {preset ? (
        <Chip icon={POWER_ICON}>
          From the old gift {wordOf(domainHookValues, preset).toLowerCase()}
        </Chip>
      ) : null}
      <div className='flex min-w-0 flex-wrap gap-2'>
        {shownDomains.visible.map((item) => (
          <StepButton
            key={item}
            icon={X}
            label={`Draws on ${words(item)}`}
            busy={why(blocked, linking.isPending)}
            onClick={() =>
              linking.mutate(domains.filter((other) => other !== item))
            }
          />
        ))}
      </div>
      <ShowMore state={shownDomains} />
      <RecordEditor
        title='Shape this power'
        note={HOLD}
        fields={POWER_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <ForgeCard
        icon={POWER_ICON}
        tone='gold'
        title='Wield it or link it to a domain'
        note='Wield it on a target, or on its faithful when no target is named.'
        columns={2}
        action={
          <StepButton
            icon={POWER_ICON}
            label='Wield it'
            variant='default'
            busy={why(blocked ?? resting, using.isPending)}
            onClick={() => using.mutate()}
          />
        }
      >
        <NodePicker
          label='Target'
          value={target}
          onChange={setTarget}
          blocked={blocked}
        />
        <ChoiceField
          label='Domain to draw on'
          value={domain}
          table={DOMAINS}
          blocked={blocked}
          onPick={setDomain}
        />
      </ForgeCard>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={CirclePlus}
          label='Draw on that domain'
          busy={why(
            blocked ??
              (domains.includes(domain)
                ? 'It already draws on that domain'
                : null),
            linking.isPending
          )}
          onClick={() => linking.mutate([...domains, domain])}
        />
        <StepButton
          icon={Trash2}
          label='Revoke it'
          busy={why(blocked, removing.isPending)}
          onClick={() => removing.mutate()}
        />
      </div>
    </RecordRow>
  )
}

export function DivinePowersSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodePowers(nodeId)
  const rows = useShowMore(query.data?.powers ?? [], SHOWN, SHOWN)
  const [name, setName] = useState('A new power')
  const [verb, setVerb] = useState<string>('bless')
  const [object, setObject] = useState<string>('stat')
  const [scope, setScope] = useState<string>('community')
  const [mode, setMode] = useState<string>('passive')
  const [strength, setStrength] = useState('20')
  const granting = useMadeAction(
    'divine_power:create',
    (_: void) => ({
      holder_id: nodeId,
      name,
      verb: verb as DivinePowerView['verb'],
      object: object as DivinePowerView['object'],
      scope: scope as DivinePowerView['scope'],
      mode: mode as DivinePowerView['mode'],
      strength: Math.min(100, Math.max(0, Number(strength) || 0)),
    }),
    'The power is granted'
  )
  const blocked = readOnlyReason
  return (
    <Section
      id='section-divine-powers'
      title='Divine powers: what it can do and how'
      description='A divine power is built from parts: what it does, what it acts on, how far it reaches, when it acts, what it costs and how long it rests; strength grows with the domains it draws on that its holder holds.'
      icon={POWER_ICON}
      tone='gold'
    >
      <div
        data-surface='DivinePowersSection'
        className='flex min-w-0 flex-col gap-4'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its powers' />
        ) : query.isError ? (
          <EmptyState
            icon={POWER_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            {query.data.powers.length ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {rows.visible.map((row) => (
                    <Power key={row.id} row={row} blocked={blocked} />
                  ))}
                </ul>
                <ShowMore state={rows} />
              </div>
            ) : (
              <EmptyState
                icon={POWER_ICON}
                size='inline'
                title='It holds no divine power'
                description={`${query.data.node.name} can be granted a power below.`}
              />
            )}
            <ForgeCard
              icon={CirclePlus}
              tone='gold'
              title='Grant a power'
              note='Choose what it does, on what, how far and when; shape the rest on the power itself.'
              columns={3}
              action={
                <StepButton
                  icon={CirclePlus}
                  label='Grant it'
                  variant='default'
                  busy={why(blocked, granting.isPending)}
                  onClick={() => granting.mutate()}
                />
              }
            >
              <ChoiceField
                label='What it does'
                value={verb}
                table={VERBS}
                blocked={blocked}
                onPick={setVerb}
              />
              <ChoiceField
                label='What it acts on'
                value={object}
                table={OBJECTS}
                blocked={blocked}
                onPick={setObject}
              />
              <ChoiceField
                label='How far it reaches'
                value={scope}
                table={SCOPES}
                blocked={blocked}
                onPick={setScope}
              />
              <ChoiceField
                label='When it acts'
                value={mode}
                table={MODES}
                blocked={blocked}
                onPick={setMode}
              />
              <NumberField
                label='Strength'
                value={strength}
                min={0}
                max={100}
                onChange={setStrength}
              />
              <TextField
                label='Name of the power'
                value={name}
                onChange={setName}
                blocked={blocked}
              />
            </ForgeCard>
          </>
        )}
      </div>
    </Section>
  )
}
