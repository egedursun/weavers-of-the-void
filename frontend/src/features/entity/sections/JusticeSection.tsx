import { useState } from 'react'
import { Gavel, Lock, Plus, Save, Trash2, Unlock, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  Paged,
  Section,
  StatBar,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type CaseStage,
  type CrimeCase,
  type CrimeKind,
  type Justice,
  type LawKind,
  type LegitimacyBasis,
  type Proposal,
  type ProposalStance,
  type ProposalState,
  type Stance,
  type Deposition,
  type TrialKind,
  type Witness,
  useJustice,
} from '../justice/api'
import {
  BASES,
  CASE_ICON,
  CRIMES,
  JUSTICE_ICON,
  PROPOSAL_EVENTS,
  PROPOSAL_ICON,
  PROPOSAL_STATES,
  STAGES,
  STANCES,
  TESTIMONIES,
  TRIALS,
  VERDICTS,
  WITNESS_ICON,
  labelTable,
  spec,
} from '../justice/labels'
import {
  AddBar,
  ControlPanel,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'
import { LAW_KINDS, plain } from '../realm/labels'
import { type LawKindSpec, useLawKinds } from '../realm/lawKinds'
import { ParamField } from '../realm/lawTerms'
import { NumberField, RefLink, Tag } from '../realm/parts'

const SPAN = 100
const WORKING = 'Working on it.'
const VOICES = [
  'mortal',
  'faction',
  'cult',
  'people',
  'polity',
  'house',
  'son',
  'foreign_god',
]
const ROLES: Record<string, string> = {
  accused_id: 'Accused',
  culprit_id: 'True culprit',
  judge_id: 'Judge',
  investigator_id: 'Investigator',
}
type Terms = Record<string, string | number | boolean>
type Ctx = {
  view: Justice
  blocked: string | null
  hold: boolean
  kinds: LawKindSpec[]
}
type NodeRef = { id: number; kind: string; name: string }

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function Ref({
  node,
  empty = 'no one',
}: {
  node: NodeRef | null | undefined
  empty?: string
}) {
  if (!node) return <span>{empty}</span>
  return <RefLink node={node} />
}

function clamp(value: string): number {
  return Math.max(0, Math.min(SPAN, Math.round(Number(value) || 0)))
}

function TermsEditor({
  kind,
  terms,
  onChange,
  kinds,
  blocked,
}: {
  kind: string
  terms: Terms
  onChange: (terms: Terms) => void
  kinds: LawKindSpec[]
  blocked: string | null
}) {
  const found = kinds.find((item) => item.kind === kind)
  if (!found || found.params.length === 0)
    return (
      <Muted variant='caption'>This kind of law has no terms to set.</Muted>
    )
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-2'>
      {found.params.map((param) => (
        <ParamField
          key={param.key}
          spec={param}
          value={terms[param.key] ?? param.default}
          blocked={blocked}
          onChange={(value) => onChange({ ...terms, [param.key]: value })}
        />
      ))}
    </div>
  )
}

function StanceRow({
  proposal,
  item,
  ctx,
}: {
  proposal: Proposal
  item: Stance
  ctx: Ctx
}) {
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/stance:remove', {
          body: { proposal_id: proposal.id, node_id: item.voice.id },
        })
      ),
  })
  const busy = why(ctx.blocked, strike.isPending)
  const look = spec(STANCES, item.stance)
  return (
    <ItemRow
      icon={look.icon}
      tone={look.tone}
      title={<Ref node={item.voice} />}
      meta={`${look.label}, weight ${item.weight}`}
      badges={
        <>
          {item.hooked && <Badge variant='secondary'>Bound by a hook</Badge>}
          {item.locked && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Silence ${item.voice.name} on this proposal`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel={`the voice of ${item.voice.name}`}
      editor={
        <AdjustStats
          id={`stance-${proposal.id}-${item.voice.id}`}
          inline
          groups={[
            {
              title: 'Voice',
              fields: [
                {
                  key: 'weight',
                  label: 'Weight',
                  value: item.weight,
                  min: 0,
                  max: SPAN,
                },
              ],
            },
          ]}
          run={({ value }) =>
            unwrap(
              api.POST('/api/actions/stance:set', {
                body: {
                  proposal_id: proposal.id,
                  node_id: item.voice.id,
                  stance: item.stance,
                  weight: value,
                  hold: ctx.hold,
                },
              })
            )
          }
        />
      }
    />
  )
}

function AddStance({ proposal, ctx }: { proposal: Proposal; ctx: Ctx }) {
  const [voice, setVoice] = useState<number | null>(null)
  const [stance, setStance] = useState('')
  const [weight, setWeight] = useState('30')
  const add = useGodAction({
    run: (voiceId: number) =>
      unwrap(
        api.POST('/api/actions/stance:set', {
          body: {
            proposal_id: proposal.id,
            node_id: voiceId,
            stance: stance as ProposalStance,
            weight: clamp(weight),
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setVoice(null)
      setStance('')
      return 'Voice set'
    },
  })
  const busy = why(ctx.blocked, add.isPending)
  const missing =
    voice === null
      ? 'Choose a voice.'
      : !stance
        ? 'Choose how it stands.'
        : null
  return (
    <AddBar
      title='Give a voice a stance'
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => voice !== null && add.mutate(voice)}
        >
          <Plus />
          Set
        </Button>
      }
    >
      <NodePicker
        label='Voice'
        types={VOICES}
        value={voice}
        onChange={setVoice}
        blocked={busy}
      />
      <MindPicker
        label='Stance'
        value={stance}
        table={labelTable(STANCES)}
        blocked={busy}
        onPick={setStance}
      />
      <NumberField
        label='Weight (0–100)'
        min={0}
        max={SPAN}
        value={weight}
        blocked={busy}
        onChange={setWeight}
      />
    </AddBar>
  )
}

function ProposalEditor({ row, ctx }: { row: Proposal; ctx: Ctx }) {
  const [terms, setTerms] = useState<Terms>({ ...row.params })
  const [state, setState] = useState<string>(row.state)
  const [champion, setChampion] = useState<number | null>(
    row.champion?.id ?? null
  )
  const edit = useGodAction({
    run: (body: Record<string, unknown>) =>
      unwrap(
        api.POST('/api/actions/proposal:edit', {
          body: {
            proposal_id: row.id,
            clear_champion: false,
            hold: ctx.hold,
            ...body,
          },
        })
      ),
  })
  const busy = why(ctx.blocked, edit.isPending)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <AdjustStats
        id={`proposal-${row.id}`}
        inline
        groups={[
          {
            title: 'Passage',
            fields: [
              {
                key: 'progress',
                label: 'Progress',
                value: row.progress,
                min: 0,
                max: SPAN,
              },
              {
                key: 'support',
                label: 'Support',
                value: row.support,
                min: 0,
                max: SPAN,
              },
              {
                key: 'opposition',
                label: 'Opposition',
                value: row.opposition,
                min: 0,
                max: SPAN,
              },
              {
                key: 'stalled_epochs',
                label: 'Epochs stalled',
                value: row.stalled_epochs,
                min: 0,
                max: SPAN,
              },
            ],
          },
        ]}
        run={({ key, value }) =>
          unwrap(
            api.POST('/api/actions/proposal:edit', {
              body: {
                proposal_id: row.id,
                clear_champion: false,
                [key]: value,
                hold: ctx.hold,
              },
            })
          )
        }
      />
      <Label variant='overline'>Terms</Label>
      <TermsEditor
        kind={row.kind}
        terms={terms}
        onChange={setTerms}
        kinds={ctx.kinds}
        blocked={busy}
      />
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => edit.mutate({ params: terms })}
        >
          <Save />
          Rewrite the terms
        </Button>
      </div>
      <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-2'>
        <MindPicker
          label='State'
          value={state}
          table={labelTable(PROPOSAL_STATES)}
          blocked={busy}
          onPick={setState}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || state === row.state}
          disabledReason={
            busy ?? (state === row.state ? 'Choose another state.' : undefined)
          }
          onClick={() => edit.mutate({ state: state as ProposalState })}
        >
          Set the state
        </Button>
        <NodePicker
          label='Champion'
          types={VOICES}
          value={champion}
          onChange={setChampion}
          blocked={busy}
        />
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || champion === null}
            disabledReason={
              busy ?? (champion === null ? 'Choose a champion.' : undefined)
            }
            onClick={() => edit.mutate({ champion_id: champion })}
          >
            Name the champion
          </Button>
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null || !row.champion}
            disabledReason={
              busy ?? (!row.champion ? 'It has no champion.' : undefined)
            }
            onClick={() => edit.mutate({ clear_champion: true })}
          >
            No champion
          </Button>
        </div>
      </div>
      {row.stances.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Voices</Label>
          <Paged items={row.stances} initial={4} noun={['voice', 'voices']}>
            {(item) => (
              <StanceRow
                key={item.voice.id}
                proposal={row}
                item={item}
                ctx={ctx}
              />
            )}
          </Paged>
        </div>
      )}
      <AddStance proposal={row} ctx={ctx} />
    </div>
  )
}

function ProposalRow({ row, ctx }: { row: Proposal; ctx: Ctx }) {
  const held = row.locked.length > 0
  const carry = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/proposal:pass', {
          body: { proposal_id: row.id },
        })
      ),
    success: () => 'Carried into law',
  })
  const hold = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/proposal:hold', {
          body: { proposal_id: row.id, hold: !held },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/proposal:delete', {
          body: { proposal_id: row.id },
        })
      ),
  })
  const busy = why(
    ctx.blocked,
    carry.isPending,
    hold.isPending,
    strike.isPending
  )
  const state = spec(PROPOSAL_STATES, row.state)
  const debating = row.state === 'debating'
  return (
    <ItemRow
      icon={PROPOSAL_ICON}
      tone={state.tone}
      title={row.law ? <Ref node={row.law} /> : row.title}
      meta={
        <>
          {`${plain(LAW_KINDS, row.kind)} in `}
          <Ref node={row.polity} empty='a fallen realm' />
          {', championed by '}
          <Ref node={row.champion} empty='the needs of the hour' />
          {`, since epoch ${row.proposed_epoch}`}
        </>
      }
      badges={
        <>
          <Tag spec={state} />
          <Tag spec={spec(BASES, row.basis)} />
          {row.last_event && (
            <Tag spec={spec(PROPOSAL_EVENTS, row.last_event)} />
          )}
          {row.amended && <Badge variant='secondary'>Amended</Badge>}
          {held && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={
              held
                ? 'Let the proposal move again'
                : 'Hold the proposal where it stands'
            }
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => hold.mutate()}
          >
            {held ? <Unlock /> : <Lock />}
          </Button>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Strike the proposal'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <Trash2 />
          </Button>
        </>
      }
      editLabel='the proposal'
      editor={<ProposalEditor row={row} ctx={ctx} />}
    >
      <StatBar
        label='Progress toward passage'
        value={row.progress}
        max={SPAN}
        icon={PROPOSAL_ICON}
        tone={debating ? 'info' : 'muted'}
      />
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        <StatBar
          label='Support'
          value={row.support}
          max={SPAN}
          tone='success'
        />
        <StatBar
          label='Opposition'
          value={row.opposition}
          max={SPAN}
          tone='destructive'
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Muted variant='caption'>
          {debating
            ? `Stalled ${row.stalled_epochs} of ${row.stall_limit} epochs before it fails; ${row.stances.length} voices weigh in.`
            : `Resolved in epoch ${row.resolved_epoch ?? row.proposed_epoch}.`}
        </Muted>
        <Button
          size='sm'
          disabled={busy !== null || !debating}
          disabledReason={
            busy ??
            (!debating
              ? 'Only a proposal under debate can be carried.'
              : undefined)
          }
          onClick={() => carry.mutate()}
        >
          <Gavel />
          Carry it into law
        </Button>
      </div>
    </ItemRow>
  )
}

function WitnessRow({
  crimeCase,
  item,
  ctx,
}: {
  crimeCase: CrimeCase
  item: Witness
  ctx: Ctx
}) {
  const [testimony, setTestimony] = useState<string>(item.testimony)
  const set = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/witness:set', {
          body: {
            case_id: crimeCase.id,
            witness_id: item.witness.id,
            testimony: testimony as Deposition,
            reliability: item.reliability,
            hold: ctx.hold,
          },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/witness:remove', {
          body: { case_id: crimeCase.id, witness_id: item.witness.id },
        })
      ),
  })
  const busy = why(ctx.blocked, set.isPending, strike.isPending)
  const look = spec(TESTIMONIES, item.testimony)
  return (
    <ItemRow
      icon={WITNESS_ICON}
      tone={look.tone}
      title={<Ref node={item.witness} />}
      meta={`${look.label} the accused, reliability ${item.reliability}`}
      badges={item.locked ? <Badge variant='outline'>Held</Badge> : undefined}
      actions={
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Strike the testimony of ${item.witness.name}`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <X />
        </Button>
      }
      editLabel={`the testimony of ${item.witness.name}`}
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <AdjustStats
            id={`witness-${crimeCase.id}-${item.witness.id}`}
            inline
            groups={[
              {
                title: 'Deposition',
                fields: [
                  {
                    key: 'reliability',
                    label: 'Reliability',
                    value: item.reliability,
                    min: 0,
                    max: SPAN,
                  },
                ],
              },
            ]}
            run={({ value }) =>
              unwrap(
                api.POST('/api/actions/witness:set', {
                  body: {
                    case_id: crimeCase.id,
                    witness_id: item.witness.id,
                    testimony: item.testimony,
                    reliability: value,
                    hold: ctx.hold,
                  },
                })
              )
            }
          />
          <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-2'>
            <MindPicker
              label='Deposition'
              value={testimony}
              table={labelTable(TESTIMONIES)}
              blocked={busy}
              onPick={setTestimony}
            />
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || testimony === item.testimony}
              disabledReason={
                busy ??
                (testimony === item.testimony
                  ? 'Choose another testimony.'
                  : undefined)
              }
              onClick={() => set.mutate()}
            >
              Change the testimony
            </Button>
          </div>
        </div>
      }
    />
  )
}

function AddWitness({ crimeCase, ctx }: { crimeCase: CrimeCase; ctx: Ctx }) {
  const [witness, setWitness] = useState<number | null>(null)
  const [testimony, setTestimony] = useState('')
  const [reliability, setReliability] = useState('60')
  const add = useGodAction({
    run: (witnessId: number) =>
      unwrap(
        api.POST('/api/actions/witness:set', {
          body: {
            case_id: crimeCase.id,
            witness_id: witnessId,
            testimony: testimony as Deposition,
            reliability: clamp(reliability),
            hold: ctx.hold,
          },
        })
      ),
    success: () => {
      setWitness(null)
      setTestimony('')
      return 'Witness heard'
    },
  })
  const busy = why(ctx.blocked, add.isPending)
  const missing =
    witness === null
      ? 'Choose a witness.'
      : !testimony
        ? 'Choose a testimony.'
        : null
  return (
    <AddBar
      title='Call a witness'
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => witness !== null && add.mutate(witness)}
        >
          <Plus />
          Call
        </Button>
      }
    >
      <NodePicker
        label='Witness'
        types={['mortal']}
        value={witness}
        onChange={setWitness}
        blocked={busy}
      />
      <MindPicker
        label='Deposition'
        value={testimony}
        table={labelTable(TESTIMONIES)}
        blocked={busy}
        onPick={setTestimony}
      />
      <NumberField
        label='Reliability (0–100)'
        min={0}
        max={SPAN}
        value={reliability}
        blocked={busy}
        onChange={setReliability}
      />
    </AddBar>
  )
}

function CaseEditor({ row, ctx }: { row: CrimeCase; ctx: Ctx }) {
  const [trial, setTrial] = useState<string>(row.trial ?? 'judge')
  const [stage, setStage] = useState<string>(row.stage)
  const [crime, setCrime] = useState<string>(row.crime)
  const [role, setRole] = useState('')
  const [person, setPerson] = useState<number | null>(null)
  const edit = useGodAction({
    run: (body: Record<string, unknown>) =>
      unwrap(
        api.POST('/api/actions/case:edit', {
          body: {
            case_id: row.id,
            clear_culprit: false,
            hold: ctx.hold,
            ...body,
          },
        })
      ),
    success: () => {
      setPerson(null)
      return 'Case set'
    },
  })
  const busy = why(ctx.blocked, edit.isPending)
  const changed =
    trial !== (row.trial ?? 'judge') ||
    stage !== row.stage ||
    crime !== row.crime
  const missing = !role
    ? 'Choose a role.'
    : person === null
      ? 'Choose a mortal.'
      : null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <AdjustStats
        id={`case-${row.id}`}
        inline
        groups={[
          {
            title: 'Evidence',
            fields: [
              {
                key: 'evidence',
                label: 'Weight of evidence',
                value: row.evidence,
                min: 0,
                max: SPAN,
              },
            ],
          },
        ]}
        run={({ value }) =>
          unwrap(
            api.POST('/api/actions/case:edit', {
              body: {
                case_id: row.id,
                clear_culprit: false,
                evidence: value,
                hold: ctx.hold,
              },
            })
          )
        }
      />
      <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-3'>
        <MindPicker
          label='Trial'
          value={trial}
          table={labelTable(TRIALS)}
          blocked={busy}
          onPick={setTrial}
        />
        <MindPicker
          label='Stage'
          value={stage}
          table={labelTable(STAGES)}
          blocked={busy}
          onPick={setStage}
        />
        <MindPicker
          label='Crime'
          value={crime}
          table={labelTable(CRIMES)}
          blocked={busy}
          onPick={setCrime}
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          disabled={busy !== null || !changed}
          disabledReason={
            busy ??
            (!changed ? 'Change the trial, stage or crime first.' : undefined)
          }
          onClick={() =>
            edit.mutate({
              trial: trial as TrialKind,
              stage: stage as CaseStage,
              crime: crime as CrimeKind,
            })
          }
        >
          <Save />
          Set the course
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null || !row.culprit}
          disabledReason={
            busy ?? (!row.culprit ? 'No true culprit is named.' : undefined)
          }
          onClick={() => edit.mutate({ clear_culprit: true })}
        >
          Name no culprit
        </Button>
      </div>
      <AddBar
        title='Name who plays a part'
        action={
          <Button
            size='sm'
            disabled={busy !== null || missing !== null}
            disabledReason={busy ?? missing ?? undefined}
            onClick={() => person !== null && edit.mutate({ [role]: person })}
          >
            Name
          </Button>
        }
      >
        <MindPicker
          label='Role'
          value={role}
          table={ROLES}
          blocked={busy}
          onPick={setRole}
        />
        <NodePicker
          label='Mortal'
          types={['mortal']}
          value={person}
          onChange={setPerson}
          blocked={busy}
        />
      </AddBar>
      {row.witnesses.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Witnesses</Label>
          <Paged
            items={row.witnesses}
            initial={4}
            noun={['witness', 'witnesses']}
          >
            {(item) => (
              <WitnessRow
                key={item.witness.id}
                crimeCase={row}
                item={item}
                ctx={ctx}
              />
            )}
          </Paged>
        </div>
      )}
      <AddWitness crimeCase={row} ctx={ctx} />
    </div>
  )
}

function CaseRow({ row, ctx }: { row: CrimeCase; ctx: Ctx }) {
  const held = row.locked.length > 0
  const tryNow = useGodAction({
    run: () =>
      unwrap(api.POST('/api/actions/case:try', { body: { case_id: row.id } })),
    success: () => 'The court has spoken',
  })
  const hold = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/case:hold', {
          body: { case_id: row.id, hold: !held },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/case:delete', { body: { case_id: row.id } })
      ),
  })
  const busy = why(
    ctx.blocked,
    tryNow.isPending,
    hold.isPending,
    strike.isPending
  )
  const crime = spec(CRIMES, row.crime)
  const closed = row.stage === 'closed'
  const cannotTry = closed
    ? 'The case is closed.'
    : !row.accused
      ? 'Name the accused first.'
      : null
  return (
    <ItemRow
      icon={crime.icon}
      tone={row.wrongful ? 'danger' : crime.tone}
      title={
        <>
          {`${crime.label}: `}
          <Ref node={row.accused} empty='no one yet' />
        </>
      }
      meta={
        <>
          {'In '}
          <Ref node={row.settlement} empty='a lost city' />
          {', judged by '}
          <Ref node={row.judge} />
          {', investigated by '}
          <Ref node={row.investigator} />
          {`, opened in epoch ${row.opened_epoch}`}
        </>
      }
      badges={
        <>
          <Tag spec={spec(STAGES, row.stage)} />
          {row.trial && <Tag spec={spec(TRIALS, row.trial)} />}
          {row.verdict && <Tag spec={spec(VERDICTS, row.verdict)} />}
          {row.wrongful && <Badge variant='destructive'>Wrongful</Badge>}
          {row.tortured && (
            <Badge variant='secondary'>Questioned under torture</Badge>
          )}
          {row.forged && <Badge variant='secondary'>Forged</Badge>}
          {held && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={held ? 'Let the case run' : 'Hold the case'}
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => hold.mutate()}
          >
            {held ? <Unlock /> : <Lock />}
          </Button>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Strike the case'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <Trash2 />
          </Button>
        </>
      }
      editLabel='the case'
      editor={<CaseEditor row={row} ctx={ctx} />}
    >
      <StatBar
        label={`Evidence (the court needs ${row.standard})`}
        value={row.evidence}
        max={SPAN}
        icon={CASE_ICON}
        tone={row.evidence >= row.standard ? 'warning' : 'info'}
      />
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Muted variant='caption'>
          {'The truth: '}
          <Ref node={row.culprit} empty='no true culprit' />
          {row.penalty ? `; sentence: ${row.penalty.replace('_', ' ')}` : ''}
          {`; ${row.witnesses.length} witnesses`}
        </Muted>
        <Button
          size='sm'
          disabled={busy !== null || cannotTry !== null}
          disabledReason={busy ?? cannotTry ?? undefined}
          onClick={() => tryNow.mutate()}
        >
          <Gavel />
          Try it now
        </Button>
      </div>
    </ItemRow>
  )
}

function ProposeCard({ ctx }: { ctx: Ctx }) {
  const [kind, setKind] = useState('')
  const [terms, setTerms] = useState<Terms>({})
  const [champion, setChampion] = useState<number | null>(null)
  const [basis, setBasis] = useState('council')
  const bring = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/proposal:create', {
          body: {
            polity_id: ctx.view.node_id,
            kind: kind as LawKind,
            params: terms,
            champion_id: champion,
            basis: basis as LegitimacyBasis,
          },
        })
      ),
    success: () => {
      setKind('')
      setTerms({})
      return 'Brought forward'
    },
  })
  const busy = why(ctx.blocked, bring.isPending)
  const kinds = Object.fromEntries(
    ctx.kinds.map((item) => [item.kind, plain(LAW_KINDS, item.kind)])
  )
  return (
    <AddBar
      title='Bring a law before the realm'
      action={
        <Button
          size='sm'
          disabled={busy !== null || !kind}
          disabledReason={busy ?? (!kind ? 'Choose a kind of law.' : undefined)}
          onClick={() => bring.mutate()}
        >
          <Plus />
          Bring it forward
        </Button>
      }
    >
      <MindPicker
        label='Kind of law'
        value={kind}
        table={kinds}
        blocked={busy}
        onPick={(value) => {
          setKind(value)
          setTerms({})
        }}
      />
      <MindPicker
        label='Basis'
        value={basis}
        table={labelTable(BASES)}
        blocked={busy}
        onPick={setBasis}
      />
      <NodePicker
        label='Champion'
        types={VOICES}
        value={champion}
        onChange={setChampion}
        blocked={busy}
      />
      {kind && (
        <TermsEditor
          kind={kind}
          terms={terms}
          onChange={setTerms}
          kinds={ctx.kinds}
          blocked={busy}
        />
      )}
    </AddBar>
  )
}

function ChargeCard({ ctx }: { ctx: Ctx }) {
  const view = ctx.view
  const [accused, setAccused] = useState<number | null>(
    view.is_mortal ? view.node_id : null
  )
  const [city, setCity] = useState<number | null>(
    view.is_city ? view.node_id : (view.home?.id ?? null)
  )
  const [crime, setCrime] = useState('')
  const [trial, setTrial] = useState('judge')
  const [evidence, setEvidence] = useState('50')
  const charge = useGodAction({
    run: ({ accusedId, cityId }: { accusedId: number; cityId: number }) =>
      unwrap(
        api.POST('/api/actions/case:open', {
          body: {
            settlement_id: cityId,
            accused_id: accusedId,
            crime: crime as CrimeKind,
            trial: trial as TrialKind,
            evidence: clamp(evidence),
          },
        })
      ),
    success: () => {
      setCrime('')
      return 'Brought to trial'
    },
  })
  const busy = why(ctx.blocked, charge.isPending)
  const missing =
    accused === null
      ? 'Choose the accused.'
      : city === null
        ? 'Choose the court’s city.'
        : !crime
          ? 'Choose a crime.'
          : null
  return (
    <AddBar
      title='Bring a charge'
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() =>
            accused !== null &&
            city !== null &&
            charge.mutate({ accusedId: accused, cityId: city })
          }
        >
          <Gavel />
          Bring to trial
        </Button>
      }
    >
      {!view.is_mortal && (
        <NodePicker
          label='Accused'
          types={['mortal']}
          value={accused}
          onChange={setAccused}
          blocked={busy}
        />
      )}
      {!view.is_city && (
        <NodePicker
          label='Court of'
          types={['settlement']}
          value={city}
          onChange={setCity}
          blocked={busy}
        />
      )}
      <MindPicker
        label='Crime'
        value={crime}
        table={labelTable(CRIMES)}
        blocked={busy}
        onPick={setCrime}
      />
      <MindPicker
        label='Trial'
        value={trial}
        table={labelTable(TRIALS)}
        blocked={busy}
        onPick={setTrial}
      />
      <NumberField
        label='Evidence (0–100)'
        min={0}
        max={SPAN}
        value={evidence}
        blocked={busy}
        onChange={setEvidence}
      />
    </AddBar>
  )
}

export function JusticeSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const query = useJustice(nodeId)
  const kinds = useLawKinds()
  const view = query.data
  if (query.isError)
    return (
      <Section id='section-justice' title='Laws and courts' icon={JUSTICE_ICON}>
        <EmptyState
          icon={JUSTICE_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view) return null
  const ctx: Ctx = { view, blocked: reason(), hold, kinds: kinds.data ?? [] }
  const debating = view.proposals.filter(
    (row) => row.state === 'debating'
  ).length
  const passed = view.proposals.filter((row) => row.state === 'passed').length
  const open = view.cases.filter((row) => row.stage !== 'closed').length
  const wrongful = view.cases.filter((row) => row.wrongful).length
  const canCharge = view.is_city || view.is_mortal
  return (
    <Section
      id='section-justice'
      title='Laws and courts'
      description='Laws brought before a realm and the voices for and against them, and cases at law with their witnesses, evidence, trials and verdicts.'
      icon={JUSTICE_ICON}
    >
      <div className='@container/mind flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-2 gap-3 @xl/mind:grid-cols-4'>
          <KpiTile
            label='Under debate'
            value={debating}
            icon={PROPOSAL_ICON}
            tone='info'
          />
          <KpiTile
            label='Laws carried'
            value={passed}
            icon={PROPOSAL_ICON}
            tone='success'
          />
          <KpiTile
            label='Open cases'
            value={open}
            icon={CASE_ICON}
            tone='warning'
          />
          <KpiTile
            label='Wrongful convictions'
            value={wrongful}
            icon={CASE_ICON}
            tone='danger'
          />
        </div>
        <div className='grid min-w-0 grid-cols-1 gap-4 @xl/mind:grid-cols-2'>
          <MindCard
            title='Laws before the realm'
            icon={PROPOSAL_ICON}
            hint='A law passes when its progress reaches 100. Each epoch it moves by its support over its opposition under the realm’s way of deciding; estates with a council seat obstruct, hooks turn votes, and a proposal that stalls too long fails and shames its champion.'
          >
            {view.proposals.length === 0 ? (
              <Muted variant='caption'>
                {view.is_realm
                  ? 'No law stands before this realm.'
                  : 'It champions no law and has no voice on one.'}
              </Muted>
            ) : (
              <Paged
                items={view.proposals}
                initial={3}
                noun={['proposal', 'proposals']}
              >
                {(row) => <ProposalRow key={row.id} row={row} ctx={ctx} />}
              </Paged>
            )}
            {view.is_realm && <ProposeCard ctx={ctx} />}
          </MindCard>
          <MindCard
            title='Cases at law'
            icon={CASE_ICON}
            hint='Witnesses testify by their regard for the accused; the investigator weighs testimony, skill and known secrets and may question under torture where the law and their ethics allow; a weak case may find a scapegoat. A trial before a judge, a jury, by combat or by ordeal decides, and a wrongful conviction breeds grievance.'
          >
            {view.cases.length === 0 ? (
              <Muted variant='caption'>No case at law touches it.</Muted>
            ) : (
              <Paged items={view.cases} initial={3} noun={['case', 'cases']}>
                {(row) => <CaseRow key={row.id} row={row} ctx={ctx} />}
              </Paged>
            )}
            {canCharge ? (
              <ChargeCard ctx={ctx} />
            ) : (
              <Muted variant='caption'>
                Charges are brought against mortals, before the court of a city.
              </Muted>
            )}
          </MindCard>
        </div>
        <ControlPanel
          title='Hold what you set'
          note='Terms, voices, evidence, roles and testimony you set are held against the world while the switch is on. Every change goes into the ledger and can be undone.'
          hold={hold}
          onHold={setHold}
        >
          {null}
        </ControlPanel>
      </div>
    </Section>
  )
}
