import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  CirclePlus,
  Gavel,
  Landmark,
  ShieldOff,
  RotateCcw,
  Trash2,
  TriangleAlert,
} from 'lucide-react'
import { type ActionBody, type EditValues } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { Button } from '@/components/ui/button'
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
import { SwitchField } from '@/features/entity/wilds/parts'
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField } from '@/features/wars/military/parts'
import { type RulingView, useRulings } from './api'
import {
  COUNCIL_SEATS,
  ESCALATION_STEPS,
  MOTIONS,
  VOTING_RULES,
} from './labels'

type Schema = components['schemas']
type SeatView = Schema['DivineSeatView']
type ViolationView = Schema['CouncilViolationView']
type Edit = { values: EditValues; release: string[] }

const SHOWN = 5
const HOLD =
  'Values you set are held against the engine until you release them.'
const GODS = ['son', 'foreign_god'] as const
const NOT_GOD =
  'Only gods sit on the council and answer for breaking its rulings: sons by right, foreign gods by invitation, pact or recognition. Worlds, stars, the Creator and mortal things hold no seat, and the Creator speaks through its veto.'

const PROCEDURE_FIELDS: readonly Field[] = [
  {
    key: 'quorum_pct',
    label: 'Share of seats that must vote (%)',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'voting_rule',
    label: 'How a motion carries',
    kind: 'pick',
    table: table(VOTING_RULES),
  },
  {
    key: 'term_epochs',
    label: 'Epochs a lasting ruling holds',
    kind: 'number',
    min: 1,
    max: 200,
  },
]
const SEAT_FIELDS: readonly Field[] = [
  {
    key: 'seat',
    label: 'How it sits',
    kind: 'pick',
    table: table(COUNCIL_SEATS),
  },
  {
    key: 'excluded_until',
    label: 'Kept out until epoch',
    kind: 'number',
    min: 0,
  },
]
const VIOLATION_FIELDS: readonly Field[] = [
  {
    key: 'step',
    label: 'Step of the ladder',
    kind: 'pick',
    table: table(ESCALATION_STEPS),
  },
]

export function useCouncilOrder() {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'council-order'] as const,
    queryFn: () => unwrap(api.GET('/api/council/order')),
  })
}

function useGodCouncil(nodeId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'council-order-of', nodeId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/council/order/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

export function VetoButton({
  ruling,
  busy,
}: {
  ruling: RulingView
  busy: string | null
}) {
  const order = useCouncilOrder()
  const vetoing = useMadeAction(
    'council:veto',
    (_: void) => ({ ruling_id: ruling.id }),
    'The Creator vetoed the ruling'
  )
  const procedure = order.data?.procedure
  const reason =
    busy ??
    (!ruling.active
      ? 'Only a ruling in force can be vetoed'
      : procedure && !procedure.creator_veto
        ? "The council's rules give the Creator no veto"
        : vetoing.isPending
          ? 'Working on it.'
          : null)
  return (
    <Button
      act={vetoing}
      size='sm'
      variant='outline'
      disabled={reason !== null}
      disabledReason={reason ?? undefined}
      onClick={() => vetoing.mutate()}
    >
      <ShieldOff />
      {procedure ? `Veto (${procedure.veto_cost} essence)` : 'Veto'}
    </Button>
  )
}

function Seat({ row, blocked }: { row: SeatView; blocked: string | null }) {
  const named = COUNCIL_SEATS[row.seat]
  const editing = useMadeAction(
    'divine_seat:edit',
    (vars: Edit) => ({
      god_id: row.god.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The seat is set'
  )
  const removing = useMadeAction(
    'divine_seat:delete',
    (_: void) => ({ god_id: row.god.id }),
    'The seat is taken away'
  )
  return (
    <RecordRow
      icon={named.icon}
      tone={row.sitting ? named.tone : 'muted'}
      title={`${row.god.name}: ${named.label.toLowerCase()}`}
      caption={`${row.is_son ? 'A son' : 'A foreign god'}, seated since epoch ${row.since_epoch}${row.sitting ? '' : `; kept out until epoch ${row.excluded_until}`}`}
    >
      <Ref node={row.god} empty='no god named' />
      <RecordEditor
        act={editing}
        title='Set the seat'
        note={HOLD}
        fields={SEAT_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Take the seat away'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Violation({
  row,
  blocked,
}: {
  row: ViolationView
  blocked: string | null
}) {
  const named = ESCALATION_STEPS[row.step]
  const editing = useMadeAction(
    'council_violation:edit',
    (vars: Edit) => ({
      violation_id: row.id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The breach is set'
  )
  const removing = useMadeAction(
    'council_violation:delete',
    (_: void) => ({ violation_id: row.id }),
    'The breach is struck'
  )
  return (
    <RecordRow
      icon={named.icon}
      tone={named.tone}
      title={`${row.violator.name} met ${named.label.toLowerCase()}`}
      caption={`epoch ${row.epoch}${row.ruling_motion ? `, for breaking the ruling: ${MOTIONS[row.ruling_motion].label.toLowerCase()}` : ', the ruling has since been struck'}`}
    >
      <Ref node={row.violator} empty='no god named' />
      <RecordEditor
        act={editing}
        title='Set the breach'
        note={HOLD}
        fields={VIOLATION_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Strike the breach'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function SeatForge({
  godId,
  blocked,
}: {
  godId: number | null
  blocked: string | null
}) {
  const [god, setGod] = useState<number | null>(godId)
  const [seat, setSeat] = useState<string>('invited')
  const seating = useMadeAction(
    'divine_seat:set',
    (_: void) => ({
      god_id: god ?? 0,
      seat: seat as ActionBody<'divine_seat:set'>['seat'],
    }),
    'The god takes a seat'
  )
  const missing = god === null ? 'Choose the god first' : null
  return (
    <ForgeCard
      icon={CirclePlus}
      tone='gold'
      title='Seat a god on the council'
      note='A seated god votes on every motion; sons sit by right, foreign gods by invitation, pact or recognition.'
      columns={2}
      action={
        <StepButton
          act={seating}
          icon={CirclePlus}
          label='Seat it'
          variant='default'
          busy={why(blocked ?? missing, seating.isPending)}
          onClick={() => seating.mutate()}
        />
      }
    >
      {godId === null ? (
        <ThingPicker
          label='God'
          value={god}
          onChange={setGod}
          blocked={blocked}
          kinds={GODS}
        />
      ) : null}
      <ChoiceField
        label='How it sits'
        value={seat}
        table={COUNCIL_SEATS}
        blocked={blocked}
        onPick={setSeat}
      />
    </ForgeCard>
  )
}

function ViolationForge({
  godId,
  blocked,
}: {
  godId: number | null
  blocked: string | null
}) {
  const rulings = useRulings()
  const [god, setGod] = useState<number | null>(godId)
  const [ruling, setRuling] = useState<string>('')
  const [step, setStep] = useState<string>('censure')
  const charging = useMadeAction(
    'council_violation:create',
    (_: void) => ({
      ruling_id: Number(ruling),
      violator_id: god ?? 0,
      step: step as ActionBody<'council_violation:create'>['step'],
    }),
    'The god answers for the breach'
  )
  const options = Object.fromEntries(
    (rulings.data?.rulings ?? [])
      .filter((row) => row.active)
      .map((row) => [
        String(row.id),
        {
          label: `${MOTIONS[row.motion].label}, epoch ${row.epoch}`,
          icon: MOTIONS[row.motion].icon,
          tone: MOTIONS[row.motion].tone,
        },
      ])
  )
  const noRulings = Object.keys(options).length
    ? null
    : 'No ruling is in force to break'
  const missing =
    noRulings ??
    (god === null
      ? 'Choose the god first'
      : ruling === ''
        ? 'Choose the ruling it broke'
        : null)
  return (
    <ForgeCard
      icon={Gavel}
      tone='danger'
      title='Hold a god to a ruling'
      note='The penalty of the chosen step falls at once: censure costs renown, a sanction essence, exclusion its seat for a time, a duel its standing with the council champion, and a war of gods sets it against the pantheon.'
      columns={godId === null ? 3 : 2}
      action={
        <StepButton
          act={charging}
          icon={Gavel}
          label='Charge the breach'
          busy={why(blocked ?? missing, charging.isPending)}
          onClick={() => charging.mutate()}
        />
      }
    >
      {godId === null ? (
        <ThingPicker
          label='God'
          value={god}
          onChange={setGod}
          blocked={blocked}
          kinds={GODS}
        />
      ) : null}
      <ChoiceField
        label='Ruling it broke'
        value={ruling}
        table={options}
        blocked={blocked ?? noRulings}
        onPick={setRuling}
      />
      <ChoiceField
        label='Step of the ladder'
        value={step}
        table={ESCALATION_STEPS}
        blocked={blocked}
        onPick={setStep}
      />
    </ForgeCard>
  )
}

export function CouncilOrderPanel({
  readOnlyReason = null,
}: {
  readOnlyReason?: string | null
}) {
  const query = useCouncilOrder()
  const seats = useShowMore(query.data?.seats ?? [], SHOWN, SHOWN * 2)
  const violations = useShowMore(query.data?.violations ?? [], SHOWN, SHOWN * 2)
  const blocked = readOnlyReason
  const editing = useMadeAction(
    'council_procedure:edit',
    (vars: Edit) => ({
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The council decides by new rules'
  )
  const resetting = useMadeAction(
    'council_procedure:reset',
    (_: void) => ({}),
    'The procedure returns to the rules of the world'
  )
  return (
    <Section
      id='section-council-order'
      title='How the council decides, who sits and who answers to it'
      description='The procedure sets the quorum, how a motion carries, the term of a lasting ruling and whether the Creator may veto. Sons sit by right and foreign gods by invitation, pact or recognition; a god that breaks a ruling climbs a ladder from censure to sanction, exclusion, a duel and a war of gods.'
      icon={Landmark}
      tone='gold'
    >
      <div
        data-surface='CouncilOrderPanel'
        className='flex min-w-0 flex-col gap-4'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the order of the council' />
        ) : query.isError ? (
          <EmptyState
            icon={TriangleAlert}
            size='inline'
            title='The order of the council could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <div className='grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-4'>
              <KpiTile
                label='Quorum'
                value={`${query.data.procedure.quorum_pct}%`}
                icon={Landmark}
                tone='info'
              />
              <KpiTile
                label='A motion carries by'
                value={VOTING_RULES[query.data.procedure.voting_rule].label}
                icon={VOTING_RULES[query.data.procedure.voting_rule].icon}
                tone='gold'
              />
              <KpiTile
                label='Seats'
                value={String(query.data.seats.length)}
                icon={COUNCIL_SEATS.by_right.icon}
                tone='gold'
              />
              <KpiTile
                label='Breaches'
                value={String(query.data.violations.length)}
                icon={Gavel}
                tone={query.data.violations.length ? 'danger' : 'muted'}
              />
            </div>
            <RecordRow
              icon={Landmark}
              tone='gold'
              title={`Rulings hold ${query.data.procedure.term_epochs} epochs; ${query.data.procedure.creator_veto ? `the Creator may veto for ${query.data.procedure.veto_cost} essence` : 'the Creator has no veto'}`}
              caption={
                query.data.procedure.locked.length
                  ? `Held: ${query.data.procedure.locked.join(', ')}`
                  : 'The council may change these by its own motion'
              }
            >
              <RecordEditor
                act={editing}
                title='Set the procedure'
                note={HOLD}
                fields={PROCEDURE_FIELDS}
                locked={query.data.procedure.locked}
                busy={why(blocked, editing.isPending)}
                onSave={(values) => editing.mutate({ values, release: [] })}
                onRelease={(keys) =>
                  editing.mutate({ values: {}, release: keys })
                }
              />
              <StepButton
                act={resetting}
                icon={RotateCcw}
                label='Return to the rules of the world'
                busy={why(blocked, resetting.isPending)}
                onClick={() => resetting.mutate()}
              />
              <SwitchField
                act={editing}
                label='The Creator may veto'
                checked={query.data.procedure.creator_veto}
                disabled={why(blocked, editing.isPending) !== null}
                onChange={(creator_veto) =>
                  editing.mutate({ values: { creator_veto }, release: [] })
                }
              />
            </RecordRow>
            {query.data.seats.length ? (
              <>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {seats.visible.map((row) => (
                    <Seat key={row.god.id} row={row} blocked={blocked} />
                  ))}
                </ul>
                <ShowMore state={seats} />
              </>
            ) : (
              <EmptyState
                icon={Landmark}
                size='inline'
                title='No seat is filled yet'
                description='Sons take their seats at the next epoch; seat a god below.'
              />
            )}
            <SeatForge godId={null} blocked={blocked} />
            {query.data.violations.length ? (
              <>
                <ul className='flex min-w-0 flex-col gap-2'>
                  {violations.visible.map((row) => (
                    <Violation key={row.id} row={row} blocked={blocked} />
                  ))}
                </ul>
                <ShowMore state={violations} />
              </>
            ) : (
              <EmptyState
                icon={Gavel}
                size='inline'
                title='No ruling has been broken'
                description='Breaches of truces, divided worlds and outlawed powers are found each epoch.'
              />
            )}
            <ViolationForge godId={null} blocked={blocked} />
          </>
        )}
      </div>
    </Section>
  )
}

export function GodCouncilSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useGodCouncil(nodeId)
  const violations = useShowMore(query.data?.violations ?? [], SHOWN, SHOWN)
  const blocked = readOnlyReason
  return (
    <Section
      id='section-god-council'
      title='The council: its seat and the rulings it has broken'
      description='A god sits on the Council of the Gods by right, invitation, pact or recognition, and climbs the ladder of penalties each time it breaks a ruling.'
      icon={Landmark}
      tone='gold'
    >
      <div
        data-surface='GodCouncilSection'
        className='flex min-w-0 flex-col gap-4'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its place on the council' />
        ) : query.isError ? (
          <EmptyState
            icon={TriangleAlert}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : !query.data.is_god ? (
          <EmptyState
            icon={Landmark}
            size='inline'
            title='No seat on the council'
            description={NOT_GOD}
          />
        ) : (
          <>
            {query.data.seat ? (
              <ul className='flex min-w-0 flex-col gap-2'>
                <Seat row={query.data.seat} blocked={blocked} />
              </ul>
            ) : (
              <Chip icon={Landmark}>Holds no seat on the council</Chip>
            )}
            <SeatForge godId={nodeId} blocked={blocked} />
            <ul className='flex min-w-0 flex-col gap-2'>
              {violations.visible.map((row) => (
                <Violation key={row.id} row={row} blocked={blocked} />
              ))}
            </ul>
            <ShowMore state={violations} />
            <ViolationForge godId={nodeId} blocked={blocked} />
          </>
        )}
      </div>
    </Section>
  )
}
