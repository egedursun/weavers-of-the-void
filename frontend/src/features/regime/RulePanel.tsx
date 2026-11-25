import { useState } from 'react'
import {
  Crown,
  Gauge,
  Hourglass,
  Landmark,
  Scale,
  UserMinus,
  UserPlus,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { clamp, SPAN } from '@/features/cycles/model'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type RegimeNodeView, useRegimeAction } from './api'
import {
  LEADERSHIP,
  LEGITIMACY_KINDS,
  PROOFING,
  ROUTINISATION,
  SELECTORATES,
} from './labels'
import { useRegimeRow, useRegimeStep } from './model'

type Regime = NonNullable<RegimeNodeView['regime']>
type Member = RegimeNodeView['members'][number]

const NOT_REALM = 'Only a realm is ruled by a selectorate and a coalition'
const EXTRACTION_MAX = 200

function LegitimacyMix({ regime }: { regime: Regime }) {
  const dominant = LEGITIMACY_KINDS[regime.dominant]
  const legacy = ROUTINISATION[regime.routinisation]
  return (
    <div
      id='regime-legitimacy-chart'
      className='flex min-w-0 flex-col gap-2'
      role='group'
      aria-label='Kinds of legitimacy'
    >
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Chip
          icon={dominant.icon}
        >{`Rests on ${dominant.label.toLowerCase()}`}</Chip>
        <Chip icon={legacy.icon}>{legacy.label}</Chip>
      </div>
      <Meter
        label={LEGITIMACY_KINDS.traditional.label}
        value={regime.traditional}
        tone='warning'
        icon={LEGITIMACY_KINDS.traditional.icon}
      />
      <Meter
        label={LEGITIMACY_KINDS.charismatic.label}
        value={regime.charismatic}
        tone='verdigris'
        icon={LEGITIMACY_KINDS.charismatic.icon}
      />
      <Meter
        label={LEGITIMACY_KINDS.rational.label}
        value={regime.rational}
        tone='info'
        icon={LEGITIMACY_KINDS.rational.icon}
      />
      <Facts
        items={[
          [
            'Founder',
            <Ref key='founder' node={regime.founder} empty='none marked' />,
          ],
          [
            'Ruler last seen',
            <Ref key='ruler' node={regime.ruler} empty='no ruler' />,
          ],
          [
            'Crisis of the legacy',
            regime.crisis_epoch === null
              ? 'none'
              : `epoch ${regime.crisis_epoch}`,
          ],
        ]}
      />
    </div>
  )
}

function RegimeCard({
  polityId,
  regime,
  blocked,
}: {
  polityId: number
  regime: Regime
  blocked: string | null
}) {
  const action = useRegimeRow(
    'regime:edit',
    'regime:delete',
    { polity_id: polityId },
    blocked
  )
  const selectorate = SELECTORATES[regime.selectorate]
  const leadership = LEADERSHIP[regime.leadership]
  const measures = (Object.keys(PROOFING) as (keyof typeof PROOFING)[]).filter(
    (key) => regime[key]
  )
  return (
    <Held
      icon={selectorate.icon}
      tone={selectorate.tone}
      title={`Chosen by ${selectorate.label.toLowerCase()}`}
      caption={`${leadership.label} · read in epoch ${regime.updated_epoch}`}
      removeLabel='Let it be read anew'
      editTitle='Set how the realm is ruled'
      note='The wider the circle that chooses the ruler, the more is spent on public goods, which raise the towns and content their farmers and craftsfolk; small circles are kept loyal with private gifts, which breed corruption, and a faction holding the balance of power narrows the circle. The ruler’s time horizon sets how hard the realm is taxed. Custom, charisma and law each hold the ruler up and each fails in its own way; victories, miracles and prophecies feed charisma. At a charismatic founder’s death the realm must turn charisma into a dynasty or rules, or split, and a split gives the founder’s kin a claim against the heir. Coup-proofing lowers the chance of a coup and the army’s quality at once.'
      fields={[
        {
          key: 'selectorate',
          label: 'Who chooses the ruler',
          kind: 'pick',
          table: table(SELECTORATES),
        },
        {
          key: 'selectorate_size',
          label: 'Size of the selectorate',
          kind: 'number',
          min: 0,
        },
        {
          key: 'coalition_size',
          label: 'Size of the winning coalition',
          kind: 'number',
          min: 0,
        },
        {
          key: 'coalition_loyalty',
          label: 'Loyalty of the coalition',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'public_share',
          label: 'Spent on public goods (%)',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'traditional',
          label: LEGITIMACY_KINDS.traditional.label,
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'charismatic',
          label: LEGITIMACY_KINDS.charismatic.label,
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'rational',
          label: LEGITIMACY_KINDS.rational.label,
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'founder_entity_id',
          label: 'Charismatic founder',
          kind: 'node',
          types: ['mortal'],
        },
        {
          key: 'routinisation',
          label: 'Fate of the founder’s charisma',
          kind: 'pick',
          table: table(ROUTINISATION),
        },
        {
          key: 'horizon',
          label: 'Time horizon',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'extraction',
          label: 'Extraction (% of the norm)',
          kind: 'number',
          min: 0,
          max: EXTRACTION_MAX,
        },
        {
          key: 'institutions',
          label: 'Strength of institutions',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'leadership',
          label: 'Leadership',
          kind: 'pick',
          table: table(LEADERSHIP),
        },
        {
          key: 'rotation',
          label: PROOFING.rotation.label,
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'parallel_guard',
          label: PROOFING.parallel_guard.label,
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'loyalty_promotion',
          label: PROOFING.loyalty_promotion.label,
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'hostages',
          label: PROOFING.hostages.label,
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={regime.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @xl/tiles:grid-cols-3'>
          <KpiTile
            label='Selectorate'
            value={regime.selectorate_size}
            icon={Users}
            tone='info'
          />
          <KpiTile
            label='Winning coalition'
            value={regime.coalition_size}
            icon={Crown}
            tone='gold'
          />
          <KpiTile
            label='Coalition loyalty'
            value={regime.coalition_loyalty}
            icon={Scale}
            tone='verdigris'
          />
        </div>
      </div>
      <Meter
        label='Spent on public goods'
        value={regime.public_share}
        tone='success'
        icon={Landmark}
      />
      <LegitimacyMix regime={regime} />
      <Meter
        label='Time horizon'
        value={regime.horizon}
        tone='info'
        icon={Hourglass}
      />
      <Meter
        label='Extraction against the norm'
        value={regime.extraction}
        max={EXTRACTION_MAX}
        tone={regime.extraction > SPAN ? 'destructive' : 'success'}
        icon={Gauge}
      />
      <Meter
        label='Strength of institutions'
        value={regime.institutions}
        tone='verdigris'
        icon={Landmark}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        {measures.length === 0 ? (
          <Muted variant='caption'>No guard against the army is kept.</Muted>
        ) : (
          measures.map((key) => (
            <Chip key={key} icon={PROOFING[key].icon}>
              {PROOFING[key].label}
            </Chip>
          ))
        )}
      </div>
    </Held>
  )
}

function MemberCard({ row, blocked }: { row: Member; blocked: string | null }) {
  const keys = { polity_id: row.polity.id, mortal_id: row.mortal.id }
  const action = useRegimeRow(
    'coalition:edit',
    'coalition:delete',
    keys,
    blocked
  )
  const purging = useRegimeStep('coalition:purge', keys, blocked, 'Cast out')
  return (
    <Held
      icon={Crown}
      tone='gold'
      title={`${row.mortal.name} in the circle of ${row.polity.name}`}
      caption={`Since epoch ${row.since_epoch}`}
      removeLabel='Strike from the circle'
      editTitle='Set the member'
      note='Members are rewarded with private goods; their loyalty follows their reward, their regard for the ruler and the offers of the strongest subjects. A purge casts them out of every seat they hold.'
      fields={[
        { key: 'reward', label: 'Reward', kind: 'number', min: 0, max: SPAN },
        { key: 'loyalty', label: 'Loyalty', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter label='Reward' value={row.reward} tone='warning' icon={Landmark} />
      <Meter label='Loyalty' value={row.loyalty} tone='success' icon={Scale} />
      <StepButton
        icon={UserMinus}
        label='Purge them'
        busy={purging.busy}
        onClick={purging.run}
      />
    </Held>
  )
}

function RegimeForge({
  polityId,
  isRealm,
  blocked,
}: {
  polityId: number
  isRealm: boolean
  blocked: string | null
}) {
  const [selectorate, setSelectorate] =
    useState<keyof typeof SELECTORATES>('nobles')
  const [leadership, setLeadership] = useState<keyof typeof LEADERSHIP>('state')
  const [share, setShare] = useState('50')
  const setting = useRegimeAction(
    'regime:set',
    (_: void) => ({
      polity_id: polityId,
      selectorate,
      leadership,
      public_share: clamp(share),
    }),
    'The realm’s rule is set'
  )
  const busy = why(isRealm ? blocked : NOT_REALM, setting.isPending)
  return (
    <ForgeCard
      icon={Crown}
      tone='gold'
      title='Set how the realm is ruled'
      note='Choose who has a say in choosing the ruler, how the ruler leads and how much goes to public goods.'
      columns={3}
      action={
        <Button
          act={setting}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Crown />
          Set it
        </Button>
      }
    >
      <MindPicker
        label='Who chooses the ruler'
        value={selectorate}
        table={table(SELECTORATES)}
        blocked={busy}
        onPick={(value) => setSelectorate(value as keyof typeof SELECTORATES)}
      />
      <MindPicker
        label='Leadership'
        value={leadership}
        table={table(LEADERSHIP)}
        blocked={busy}
        onPick={(value) => setLeadership(value as keyof typeof LEADERSHIP)}
      />
      <NumberField
        label='Public goods (%)'
        value={share}
        min={0}
        max={SPAN}
        blocked={busy}
        onChange={setShare}
      />
    </ForgeCard>
  )
}

function EnrolForge({
  polityId,
  isRealm,
  blocked,
}: {
  polityId: number
  isRealm: boolean
  blocked: string | null
}) {
  const [mortal, setMortal] = useState<number | null>(null)
  const [reward, setReward] = useState('20')
  const enrolling = useRegimeAction(
    'coalition:enrol',
    (_: void) => ({
      polity_id: polityId,
      mortal_id: mortal ?? 0,
      reward: clamp(reward),
    }),
    'They join the ruling circle'
  )
  const busy = why(
    isRealm ? (mortal === null ? 'Choose a mortal' : blocked) : NOT_REALM,
    enrolling.isPending
  )
  return (
    <ForgeCard
      icon={UserPlus}
      tone='verdigris'
      title='Bring someone into the ruling circle'
      note='Members are paid in private goods and decide whether the ruler keeps the throne.'
      columns={2}
      action={
        <Button
          act={enrolling}
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => enrolling.mutate()}
        >
          <UserPlus />
          Enrol them
        </Button>
      }
    >
      <NodePicker
        label='Member'
        value={mortal}
        onChange={setMortal}
        blocked={isRealm ? blocked : NOT_REALM}
        types={['mortal']}
      />
      <NumberField
        label='Reward'
        value={reward}
        min={0}
        max={SPAN}
        blocked={isRealm ? blocked : NOT_REALM}
        onChange={setReward}
      />
    </ForgeCard>
  )
}

export function RulePanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: RegimeNodeView
  blocked: string | null
}) {
  const isRealm = kind === 'polity'
  return (
    <div data-surface='RulePanel' className='flex min-w-0 flex-col gap-4'>
      {data.regime ? (
        <RegimeCard polityId={nodeId} regime={data.regime} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          {isRealm
            ? 'The rule of this realm has not been read yet.'
            : NOT_REALM}
        </Muted>
      )}
      <RegimeForge polityId={nodeId} isRealm={isRealm} blocked={blocked} />
      <Listed
        title='Ruling circle'
        items={data.members}
        empty='No one sits in a ruling circle here.'
        noun={['member', 'members']}
        itemKey={(item) => `${item.polity.id}-${item.mortal.id}`}
      >
        {(item) => <MemberCard row={item} blocked={blocked} />}
      </Listed>
      <EnrolForge polityId={nodeId} isRealm={isRealm} blocked={blocked} />
    </div>
  )
}
