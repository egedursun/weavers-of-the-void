import { useState } from 'react'
import {
  CalendarDays,
  Flame,
  HeartCrack,
  Hourglass,
  Scale,
  ScrollText,
  Skull,
  Swords,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  EntityLink,
  Medallion,
  MiniStat,
  StatBar,
  Paged,
  LoadingBlock,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { humanize } from '@/features/entity/actions/schema'
import { EntityPicker, Held, RecordButtons, TextField } from './controls'
import {
  FEUD_ACTIONS,
  FEUD_LEVEL,
  FEUD_PARTY,
  FEUD_STATUS,
  type Feud,
  nameOf,
  useFeuds,
} from './depth'
import { PERCENT, busyOf, cardGrid } from './labels'
import {
  Adjust,
  ChoiceField,
  FieldGrid,
  NumberField,
  Panel,
  Plain,
  Tag,
} from './parts'
import {
  type Values,
  numbersOf,
  useRecordActions,
  useRecordCreate,
} from './recordHooks'

const HOT = 60
const NUMBERS = ['intensity', 'grievance', 'generations'] as const
const PARTIES = ['house', 'people', 'settlement', 'faction', 'cult', 'polity']

function FeudCard({
  feud,
  scope,
  blocked,
}: {
  feud: Feud
  scope: number | null
  blocked: string | null
}) {
  const actions = useRecordActions('feud', feud.id, scope)
  const [draft, setDraft] = useState<Values>({})
  const value = (key: string) =>
    key in draft
      ? draft[key]
      : (feud as unknown as Record<string, unknown>)[key]
  const status = nameOf(FEUD_STATUS, feud.status)
  return (
    <li className='@container/mil flex min-w-0 flex-col gap-2.5 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion
          icon={feud.intensity >= HOT ? Flame : Swords}
          tone={feud.status === 'active' ? 'danger' : 'muted'}
        />
        <div className='flex min-w-0 flex-1 flex-wrap items-center gap-x-1.5'>
          {feud.first ? (
            <EntityLink kind='entity' id={String(feud.first.id)}>
              {feud.first.name}
            </EntityLink>
          ) : (
            <Text as='span'>Someone</Text>
          )}
          <Muted as='span' variant='caption'>
            against
          </Muted>
          {feud.second ? (
            <EntityLink kind='entity' id={String(feud.second.id)}>
              {feud.second.name}
            </EntityLink>
          ) : (
            <Text as='span'>someone</Text>
          )}
        </div>
        <Held locked={feud.locked} />
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Tag item={status} />
        <Tag item={nameOf(FEUD_PARTY, feud.party)} />
        <Tag item={nameOf(FEUD_LEVEL, feud.level)} />
        {feud.last_action && (
          <Plain
            icon={Swords}
          >{`Last: ${FEUD_ACTIONS[feud.last_action]?.label ?? humanize(feud.last_action)}${feud.last_epoch !== null ? `, epoch ${feud.last_epoch}` : ''}`}</Plain>
        )}
        {feud.mediator && (
          <Plain icon={Scale}>{`Mediated by ${feud.mediator.name}`}</Plain>
        )}
      </div>
      {feud.cause && <Muted variant='caption'>{feud.cause}</Muted>}
      <div className='grid min-w-0 grid-cols-1 gap-1.5 @sm/mil:grid-cols-2'>
        <StatBar
          framed
          label='Intensity'
          value={feud.intensity}
          max={PERCENT}
          icon={Flame}
          tone={feud.intensity >= HOT ? 'destructive' : 'warning'}
        />
        <StatBar
          framed
          label='Grievance'
          value={feud.grievance}
          max={PERCENT}
          icon={HeartCrack}
          tone='warning'
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
        <MiniStat
          icon={Hourglass}
          label='Generations'
          value={feud.generations}
          tone='info'
        />
        <MiniStat icon={Skull} label='Grief' value={feud.grief} tone='danger' />
        <MiniStat
          icon={CalendarDays}
          label='Since'
          value={feud.since_epoch}
          tone='muted'
        />
      </div>
      <div className='mt-auto'>
        <Adjust
          title='Stoke or quench the feud'
          note='Set how hot it burns, the grievance, the generations it has lasted and whether it still holds.'
        >
          <FieldGrid>
            <ChoiceField
              label='Standing'
              icon={Flame}
              value={String(value('status'))}
              table={FEUD_STATUS}
              blocked={blocked}
              onPick={(next) => setDraft({ ...draft, status: next })}
            />
            <ChoiceField
              label='Between'
              icon={Users}
              value={String(value('party'))}
              table={FEUD_PARTY}
              blocked={blocked}
              onPick={(next) => setDraft({ ...draft, party: next })}
            />
            <ChoiceField
              label='How far it has gone'
              icon={Flame}
              value={String(value('level'))}
              table={FEUD_LEVEL}
              blocked={blocked}
              onPick={(next) => setDraft({ ...draft, level: next })}
            />
            <EntityPicker
              label='Mediator'
              icon={Scale}
              types={['mortal']}
              value={
                (value('mediator_node_id') as number | null | undefined) ??
                feud.mediator?.id ??
                null
              }
              onChange={(next) =>
                setDraft({ ...draft, mediator_node_id: next })
              }
              blocked={blocked}
            />
            <NumberField
              label='Intensity'
              icon={Flame}
              value={String(value('intensity') ?? 0)}
              max={PERCENT}
              onChange={(next) => setDraft({ ...draft, intensity: next })}
            />
            <NumberField
              label='Grievance'
              icon={HeartCrack}
              value={String(value('grievance') ?? 0)}
              max={PERCENT}
              onChange={(next) => setDraft({ ...draft, grievance: next })}
            />
            <NumberField
              label='Generations'
              icon={Hourglass}
              value={String(value('generations') ?? 0)}
              onChange={(next) => setDraft({ ...draft, generations: next })}
            />
            <TextField
              label='Cause'
              icon={ScrollText}
              value={String(value('cause') ?? '')}
              onChange={(next) => setDraft({ ...draft, cause: next })}
            />
          </FieldGrid>
          <RecordButtons
            actions={actions}
            values={numbersOf(draft, NUMBERS)}
            locked={feud.locked}
            blocked={blocked}
            removeLabel='Forget the feud'
          />
        </Adjust>
      </div>
    </li>
  )
}

function StartFeud({
  entityId,
  blocked,
}: {
  entityId: number
  blocked: string | null
}) {
  const create = useRecordCreate('feud', entityId)
  const [other, setOther] = useState<number | null>(null)
  const [party, setParty] = useState('house')
  const [cause, setCause] = useState('')
  const busy = busyOf(blocked, create.isPending)
  return (
    <Adjust
      title='Swear a feud'
      note='Two houses or peoples take up a blood grudge; it burns until mediated, avenged or forgotten.'
      label='Swear a feud'
    >
      <FieldGrid>
        <EntityPicker
          label='Against'
          icon={Swords}
          types={PARTIES}
          value={other}
          onChange={setOther}
          blocked={blocked}
        />
        <ChoiceField
          label='Between'
          icon={Users}
          value={party}
          table={FEUD_PARTY}
          blocked={blocked}
          onPick={setParty}
        />
        <TextField
          label='Cause'
          icon={ScrollText}
          value={cause}
          onChange={setCause}
          placeholder='What began the feud'
        />
      </FieldGrid>
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null || other === null}
        disabledReason={
          busy ?? (other === null ? 'Choose the other side' : undefined)
        }
        onClick={() =>
          create.mutate({
            first_entity_id: entityId,
            second_entity_id: other,
            party,
            cause: cause.trim() || null,
          })
        }
      >
        <Flame />
        Swear it
      </Button>
    </Adjust>
  )
}

export function Vendettas({
  entityId,
  blocked,
}: {
  entityId: number | null
  blocked: string | null
}) {
  const query = useFeuds(entityId)
  const feuds = query.data ?? []
  const burning = feuds.filter((feud) => feud.status === 'active').length
  return (
    <div data-surface='Vendettas' className='flex min-w-0 flex-col gap-3'>
      <Panel
        title='Vendettas'
        icon={Flame}
        tone='danger'
        count={burning}
        hint='Feuds burn hotter with honour and grief, cool with marriages, shared enemies, mediation and the generations'
      >
        {query.isPending ? (
          <LoadingBlock label='Counting the old grudges' />
        ) : feuds.length === 0 ? (
          <EmptyState
            icon={Flame}
            title='No feuds'
            description='No house or people holds a blood grudge here.'
          />
        ) : (
          <ul className={cardGrid(feuds.length)}>
            <Paged items={feuds} as='li'>
              {(feud) => (
                <FeudCard
                  key={feud.id}
                  feud={feud}
                  scope={entityId}
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        )}
        {entityId !== null && (
          <StartFeud entityId={entityId} blocked={blocked} />
        )}
      </Panel>
    </div>
  )
}
