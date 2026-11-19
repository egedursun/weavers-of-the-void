import { useState } from 'react'
import {
  Ban,
  Flag,
  Gem,
  Handshake,
  Hourglass,
  Landmark,
  Lock,
  Shovel,
  Sparkles,
  Trash2,
  Undo2,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Paged,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted } from '@/components/typography'
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
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'
import {
  type CouplingNodeView,
  useCouplingAction,
  useNodeCouplings,
} from './api'
import {
  AGREEMENT_KINDS,
  AGREEMENT_STATES,
  CARRION_ICON,
  CARRION_RESTS,
  COUPLINGS_ICON,
  RESTRAINTS,
  RITE_COMPONENTS,
  SEAL_ICON,
  SEAL_KINDS,
  SIGN_CAUSES,
  SOCIOLECT_KINDS,
  SPIRIT_ICON,
  TEACHING_KINDS,
  TEACHING_STATES,
} from './labels'

type View = CouplingNodeView
type Edit = {
  values: Record<string, number | string | boolean | null>
  release: string[]
}
type Props = { view: View; blocked: string | null }

const SHOWN = 5
const YES_NO = { true: 'Yes', false: 'No' }
const MOST_EPOCHS = 100000
const MOST_DEAD = 100000000

const SOCIOLECT_FIELDS: readonly Field[] = [
  {
    key: 'kind',
    label: 'Whose speech it is',
    kind: 'pick',
    table: table(SOCIOLECT_KINDS),
  },
  {
    key: 'prestige',
    label: 'Prestige, low to high',
    kind: 'number',
    min: -100,
    max: 100,
  },
  { key: 'secret', label: 'Kept from outsiders', kind: 'pick', table: YES_NO },
  {
    key: 'salience',
    label: 'How strongly it marks them',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'faded_epoch',
    label: 'Epoch it faded',
    kind: 'number',
    min: 0,
    max: MOST_EPOCHS,
  },
]
const SIGN_FIELDS: readonly Field[] = [
  {
    key: 'community_entity_id',
    label: 'Community that signs it',
    kind: 'node',
    types: ['people', 'settlement', 'cult', 'faction'],
  },
  {
    key: 'cause',
    label: 'Why they came to sign',
    kind: 'pick',
    table: table(SIGN_CAUSES),
  },
]
const CARRION_FIELDS: readonly Field[] = [
  {
    key: 'carrion',
    label: 'Unburied dead',
    kind: 'number',
    min: 0,
    max: MOST_DEAD,
  },
  {
    key: 'scavenged',
    label: 'Taken by scavengers',
    kind: 'number',
    min: 0,
    max: MOST_DEAD,
  },
  {
    key: 'preserved',
    label: 'Preserved where they lie',
    kind: 'pick',
    table: YES_NO,
  },
  {
    key: 'rest',
    label: 'How the dead lie',
    kind: 'pick',
    table: table(CARRION_RESTS),
  },
  {
    key: 'kept',
    label: 'Left unburied by your will',
    kind: 'pick',
    table: YES_NO,
  },
]
const TEACHING_FIELDS: readonly Field[] = [
  {
    key: 'kind',
    label: 'What was taught',
    kind: 'pick',
    table: table(TEACHING_KINDS),
  },
  {
    key: 'fidelity',
    label: 'How true it was',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'state',
    label: 'How it passed',
    kind: 'pick',
    table: table(TEACHING_STATES),
  },
  {
    key: 'price',
    label: 'Wealth paid for it',
    kind: 'number',
    min: 0,
    max: 100,
  },
]
const AGREEMENT_FIELDS: readonly Field[] = [
  {
    key: 'kind',
    label: 'Kind of agreement',
    kind: 'pick',
    table: table(AGREEMENT_KINDS),
  },
  {
    key: 'state',
    label: 'Whether it holds',
    kind: 'pick',
    table: table(AGREEMENT_STATES),
  },
  {
    key: 'term_epoch',
    label: 'Epoch it runs to',
    kind: 'number',
    min: 0,
    max: MOST_EPOCHS,
  },
  {
    key: 'honour',
    label: 'Honour pledged',
    kind: 'number',
    min: -100,
    max: 100,
  },
]
const SEAL_FIELDS: readonly Field[] = [
  {
    key: 'kind',
    label: 'What holds it',
    kind: 'pick',
    table: table(SEAL_KINDS),
  },
  { key: 'strength', label: 'Strength', kind: 'number', min: 0, max: 100 },
  { key: 'decay', label: 'Wear each epoch', kind: 'number', min: 0, max: 100 },
]
const NOVELTY_FIELDS: readonly Field[] = [
  { key: 'novelty', label: 'Freshness', kind: 'number', min: 0, max: 100 },
  {
    key: 'adoption',
    label: 'How widely it is taken up',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'revivals',
    label: 'Times it came back',
    kind: 'number',
    min: 0,
    max: 1000,
  },
]

function RiteParts({ view, blocked }: Props) {
  const setting = useCouplingAction(
    'rite_component:set',
    (vars: { component: keyof typeof RITE_COMPONENTS; present: boolean }) => ({
      rite_id: view.node.id,
      ...vars,
    }),
    'The rite’s parts are set'
  )
  return (
    <Section
      id='section-rite-parts'
      title='Parts of the rite'
      description='What the rite asks of the body that works it; a body or a captor’s hold that denies a part stops the rite.'
      icon={Sparkles}
      tone='verdigris'
    >
      <Bars
        chart='chart-rite-parts'
        title='Parts the rite asks for'
        legend={[{ text: 'Asked for', variant: 'success' }]}
        rows={view.rite_parts.map((part) => ({
          key: part,
          caption: RITE_COMPONENTS[part].label,
          segments: [{ value: 1, fill: 'fill-verdigris' }],
        }))}
        max={1}
        noun={['part', 'parts']}
        empty='The rite asks for no part of the body yet.'
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        {(Object.keys(RITE_COMPONENTS) as (keyof typeof RITE_COMPONENTS)[]).map(
          (component) => {
            const item = RITE_COMPONENTS[component]
            const present = view.rite_parts.includes(component)
            return (
              <StepButton
                key={component}
                icon={item.icon}
                label={`${present ? 'Asks for' : 'Does not ask for'} ${item.label.toLowerCase()}`}
                busy={why(blocked, setting.isPending)}
                onClick={() => setting.mutate({ component, present: !present })}
              />
            )
          }
        )}
      </div>
    </Section>
  )
}

function Restraints({ view, blocked }: Props) {
  const setting = useCouplingAction(
    'restraint:set',
    (vars: { restraint: keyof typeof RESTRAINTS; present: boolean }) => ({
      captive_id: view.captive_id ?? 0,
      ...vars,
    }),
    'The captive’s hold is set'
  )
  return (
    <Section
      id='section-restraints'
      title='How the captive is held'
      description='Gags, bound hands and blindfolds stop the rites that need speech, hands or sight.'
      icon={Lock}
      tone='danger'
    >
      <div className='flex min-w-0 flex-wrap gap-2'>
        {(Object.keys(RESTRAINTS) as (keyof typeof RESTRAINTS)[]).map(
          (restraint) => {
            const item = RESTRAINTS[restraint]
            const present = view.restraints.includes(restraint)
            return (
              <StepButton
                key={restraint}
                icon={item.icon}
                label={
                  present ? `Loose: ${item.label.toLowerCase()}` : item.label
                }
                busy={why(blocked, setting.isPending)}
                onClick={() => setting.mutate({ restraint, present: !present })}
              />
            )
          }
        )}
      </div>
    </Section>
  )
}

function Sociolect({
  row,
  others,
  blocked,
}: {
  row: View['sociolects'][number]
  others: View['sociolects']
  blocked: string | null
}) {
  const kind = SOCIOLECT_KINDS[row.kind]
  const [target, setTarget] = useState(others[0] ? String(others[0].id) : '')
  const editing = useCouplingAction(
    'sociolect:edit',
    (vars: Edit) => ({ sociolect_id: row.id, ...vars }),
    'The way of speaking keeps its new values'
  )
  const removing = useCouplingAction(
    'sociolect:delete',
    (_: void) => ({ sociolect_id: row.id }),
    'The way of speaking is struck out'
  )
  const merging = useCouplingAction(
    'sociolect:merge',
    (_: void) => ({ kept_id: row.id, merged_id: Number(target) }),
    'The two ways of speaking become one'
  )
  const choices = Object.fromEntries(
    others.map((other) => [
      String(other.id),
      {
        label: `${SOCIOLECT_KINDS[other.kind].label} of ${other.holder?.name ?? 'a group'}`,
        icon: SOCIOLECT_KINDS[other.kind].icon,
        tone: 'info' as const,
      },
    ])
  )
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={`${kind.label}: ${row.holder?.name ?? 'a group'}`}
      caption={`Speaking ${row.language?.name ?? 'a language'}; salience ${row.salience}, prestige ${row.prestige}, since epoch ${row.since_epoch}${row.faded_epoch !== null ? `, faded in epoch ${row.faded_epoch}` : ''}`}
      aside={row.secret ? <Chip icon={Lock}>Secret</Chip> : undefined}
    >
      <RecordEditor
        title='Set this way of speaking'
        note='Values you set are held against the engine until you release them.'
        fields={SOCIOLECT_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <ChoiceField
          label='Merge with'
          icon={Users}
          value={target}
          table={choices}
          blocked={
            blocked ??
            (others.length
              ? null
              : 'No other way of speaking of this language here')
          }
          onPick={setTarget}
        />
        <StepButton
          icon={Users}
          label='Merge them'
          busy={why(
            blocked ??
              (others.length
                ? null
                : 'No other way of speaking of this language here'),
            merging.isPending
          )}
          onClick={() => merging.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Strike it out'
          busy={why(blocked, removing.isPending)}
          onClick={() => removing.mutate()}
        />
      </div>
    </RecordRow>
  )
}

function Sign({
  row,
  blocked,
}: {
  row: View['signs'][number]
  blocked: string | null
}) {
  const cause = SIGN_CAUSES[row.cause]
  const editing = useCouplingAction(
    'sign_origin:edit',
    (vars: Edit) => ({ language_id: row.language.id, ...vars }),
    'The signed language keeps its new values'
  )
  const removing = useCouplingAction(
    'sign_origin:delete',
    (_: void) => ({ language_id: row.language.id }),
    'Its origin is struck out'
  )
  return (
    <RecordRow
      icon={cause.icon}
      tone={cause.tone}
      title={row.language.name}
      caption={`Signed since epoch ${row.since_epoch}`}
      aside={<Chip icon={cause.icon}>{cause.label}</Chip>}
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Muted variant='caption'>Signed by</Muted>
        <Ref node={row.community} empty='a community no longer kept' />
      </div>
      <RecordEditor
        title='Set this signed language'
        note='Values you set are held against the engine until you release them.'
        fields={SIGN_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Strike out its origin'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Registers({ view, blocked }: Props) {
  const page = useShowMore(view.sociolects, SHOWN, SHOWN * 2)
  const [kind, setKind] = useState<keyof typeof SOCIOLECT_KINDS>('class')
  const [cause, setCause] = useState<keyof typeof SIGN_CAUSES>('deafness')
  const creating = useCouplingAction(
    'sociolect:create',
    (_: void) => ({ holder_id: view.node.id, kind }),
    'A way of speaking takes hold'
  )
  const signing = useCouplingAction(
    'sign_language:create',
    (_: void) => ({ community_id: view.node.id, cause }),
    'A signed language is born'
  )
  const notGroup = view.is_community
    ? null
    : 'Only a community, faction or realm speaks in its own way'
  return (
    <Section
      id='section-registers'
      title='Ways of speaking'
      description='The speech of classes, castes, trades, courts, crews and cants, and the signed languages of those who do not speak aloud.'
      icon={SOCIOLECT_KINDS.class.icon}
      tone='info'
    >
      <Bars
        chart='chart-registers'
        title='How strongly each way of speaking marks its group'
        legend={[{ text: 'Salience', variant: 'secondary' }]}
        rows={page.visible.map((row) => ({
          key: String(row.id),
          caption: `${SOCIOLECT_KINDS[row.kind].label}: ${row.holder?.name ?? 'a group'}`,
          segments: [{ value: row.salience, fill: 'fill-info' }],
        }))}
        max={100}
        noun={['way of speaking', 'ways of speaking']}
        empty='No group here speaks in a way of its own.'
      />
      {view.sociolects.length ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          {page.visible.map((row) => (
            <Sociolect
              key={row.id}
              row={row}
              others={view.sociolects.filter(
                (other) =>
                  other.id !== row.id && other.language?.id === row.language?.id
              )}
              blocked={blocked}
            />
          ))}
        </ul>
      ) : (
        <EmptyState
          icon={SOCIOLECT_KINDS.class.icon}
          size='inline'
          title='One way of speaking'
          description='No group here speaks in a way of its own.'
        />
      )}
      <ShowMore state={page} />
      {view.signs.length ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={view.signs} as='li'>
            {(row) => (
              <Sign key={row.language.id} row={row} blocked={blocked} />
            )}
          </Paged>
        </ul>
      ) : null}
      <ForgeCard
        icon={SOCIOLECT_KINDS.court.icon}
        tone='info'
        title='Give them a way of speaking'
        note='A way of speaking marks its group, carries prestige or stigma, and a cant keeps secrets.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              disabled={why(blocked ?? notGroup, creating.isPending) !== null}
              disabledReason={
                why(blocked ?? notGroup, creating.isPending) ?? undefined
              }
              onClick={() => creating.mutate()}
            >
              Give it
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={why(blocked ?? notGroup, signing.isPending) !== null}
              disabledReason={
                why(blocked ?? notGroup, signing.isPending) ?? undefined
              }
              onClick={() => signing.mutate()}
            >
              Give a signed language
            </Button>
          </div>
        }
      >
        <ChoiceField
          label='Whose speech'
          icon={Users}
          value={kind}
          table={SOCIOLECT_KINDS}
          blocked={blocked ?? notGroup}
          onPick={(value) => setKind(value as keyof typeof SOCIOLECT_KINDS)}
        />
        <ChoiceField
          label='Why they would sign'
          icon={Hourglass}
          value={cause}
          table={SIGN_CAUSES}
          blocked={blocked ?? notGroup}
          onPick={(value) => setCause(value as keyof typeof SIGN_CAUSES)}
        />
      </ForgeCard>
    </Section>
  )
}

function Carrion({ view, blocked }: Props) {
  const keeping = useCouplingAction(
    'carrion:keep',
    (_: void) => ({
      region_id: view.node.id,
      kept: !(view.carrion?.kept ?? false),
    }),
    'Your will for the dead is set'
  )
  const clearing = useCouplingAction(
    'carrion:clear',
    (_: void) => ({ region_id: view.node.id }),
    'The dead are cleared away'
  )
  const editing = useCouplingAction(
    'carrion:edit',
    (vars: Edit) => ({ region_id: view.node.id, ...vars }),
    'The carrion keeps its new values'
  )
  const row = view.carrion
  return (
    <Section
      id='section-carrion'
      title='The dead of this land'
      description='Mass deaths feed scavengers, vermin and predators, or lie preserved where nothing eats them; the unburied dead may not rest.'
      icon={CARRION_ICON}
      tone='muted'
    >
      <Bars
        chart='chart-carrion'
        title='The dead of this land'
        legend={[
          { text: 'Unburied', variant: 'destructive' },
          { text: 'Taken by scavengers', variant: 'success' },
        ]}
        rows={
          row
            ? [
                {
                  key: 'dead',
                  caption: CARRION_RESTS[row.rest].label,
                  segments: [
                    { value: row.carrion, fill: 'fill-destructive' },
                    { value: row.scavenged, fill: 'fill-verdigris' },
                  ],
                },
              ]
            : []
        }
        noun={['record', 'records']}
        empty='No mass death has left its dead in this land.'
      />
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4'>
        <KpiTile
          label='Unburied dead'
          value={String(row?.carrion ?? 0)}
          icon={CARRION_ICON}
          tone={row?.carrion ? 'danger' : 'muted'}
        />
        <KpiTile
          label='Taken by scavengers'
          value={String(row?.scavenged ?? 0)}
          icon={Shovel}
          tone='verdigris'
        />
        <KpiTile
          label='Preserved'
          value={row?.preserved ? 'Yes' : 'No'}
          icon={Hourglass}
          tone='info'
        />
        <KpiTile
          label='How they lie'
          value={row ? CARRION_RESTS[row.rest].label : 'No dead lie here'}
          icon={row ? CARRION_RESTS[row.rest].icon : CARRION_ICON}
          tone={row ? CARRION_RESTS[row.rest].tone : 'muted'}
        />
      </div>
      {row ? (
        <RecordEditor
          title='Set the carrion'
          note='Values you set are held against the engine until you release them.'
          fields={CARRION_FIELDS}
          locked={row.locked}
          busy={why(blocked, editing.isPending)}
          onSave={(values) => editing.mutate({ values, release: [] })}
          onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
        />
      ) : (
        <EmptyState
          icon={CARRION_ICON}
          size='inline'
          title='No unburied dead'
          description='No mass death has left its dead in this land.'
        />
      )}
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={row?.kept ? Undo2 : Ban}
          label={
            row?.kept
              ? 'Let the living bury them'
              : 'Leave the dead where they lie'
          }
          busy={why(blocked, keeping.isPending)}
          onClick={() => keeping.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Clear away the dead'
          busy={why(
            blocked ?? (row ? null : 'There are no dead to clear'),
            clearing.isPending
          )}
          onClick={() => clearing.mutate()}
        />
      </div>
    </Section>
  )
}

function Teaching({
  row,
  blocked,
}: {
  row: View['teachings'][number]
  blocked: string | null
}) {
  const kind = TEACHING_KINDS[row.kind]
  const state = TEACHING_STATES[row.state]
  const editing = useCouplingAction(
    'teaching:edit',
    (vars: Edit) => ({ teaching_id: row.id, ...vars }),
    'The teaching keeps its new values'
  )
  const removing = useCouplingAction(
    'teaching:delete',
    (_: void) => ({ teaching_id: row.id }),
    'The teaching is struck out'
  )
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={`${row.teacher?.name ?? 'A teacher'} to ${row.learner?.name ?? 'a learner'}: ${kind.label.toLowerCase()}`}
      caption={`Epoch ${row.epoch}, ${row.fidelity} of 100 true${row.price ? `, sold for ${row.price} wealth` : ''}`}
      aside={<Chip icon={state.icon}>{state.label}</Chip>}
    >
      {row.subject ? (
        <div className='flex min-w-0 items-center gap-2'>
          <Muted variant='caption'>What was taught</Muted>
          <Ref node={row.subject} />
        </div>
      ) : null}
      <RecordEditor
        title='Set this teaching'
        note='Values you set are held against the engine until you release them.'
        fields={TEACHING_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Strike it out'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

function Teachings({ view, blocked }: Props) {
  const page = useShowMore(view.teachings, SHOWN, SHOWN * 2)
  const [partner, setPartner] = useState(
    view.partners[0] ? String(view.partners[0].id) : ''
  )
  const [kind, setKind] = useState<keyof typeof TEACHING_KINDS>('rite')
  const teacherId = view.is_teacher ? view.node.id : Number(partner)
  const learnerId = view.is_teacher ? Number(partner) : view.node.id
  const granting = useCouplingAction(
    'teaching:grant',
    (_: void) => ({ teacher_id: teacherId, learner_id: learnerId, kind }),
    'The teaching is given'
  )
  const blocking = useCouplingAction(
    'teaching:block',
    (_: void) => ({ teacher_id: teacherId, learner_id: learnerId }),
    'That teacher teaches them no more'
  )
  const partners = Object.fromEntries(
    view.partners.map((node) => [
      String(node.id),
      { label: node.name, icon: SPIRIT_ICON, tone: 'info' as const },
    ])
  )
  const none = view.partners.length
    ? null
    : view.is_teacher
      ? 'No community lives near enough to be taught'
      : 'No spirit or beast near here can teach'
  return (
    <Section
      id='section-teachings'
      title='Teachings of spirits and beasts'
      description='The dead, place spirits, servitors and lore-keeping beasts teach the living what they know, with their own errors.'
      icon={SPIRIT_ICON}
      tone='verdigris'
    >
      <Bars
        chart='chart-teachings'
        title='How true each teaching was'
        legend={[{ text: 'Fidelity', variant: 'success' }]}
        rows={page.visible.map((row) => ({
          key: String(row.id),
          caption: `${row.teacher?.name ?? 'A teacher'}: ${TEACHING_KINDS[row.kind].label.toLowerCase()}`,
          segments: [{ value: row.fidelity, fill: 'fill-verdigris' }],
        }))}
        max={100}
        noun={['teaching', 'teachings']}
        empty='No spirit or beast has taught here.'
      />
      {view.teachings.length ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          {page.visible.map((row) => (
            <Teaching key={row.id} row={row} blocked={blocked} />
          ))}
        </ul>
      ) : (
        <EmptyState
          icon={SPIRIT_ICON}
          size='inline'
          title='Nothing taught yet'
          description='No spirit or beast has taught here.'
        />
      )}
      <ShowMore state={page} />
      <ForgeCard
        icon={SPIRIT_ICON}
        tone='verdigris'
        title='Grant or forbid a teaching'
        note='A teacher gives only what it knows and the learner lacks.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              disabled={why(blocked ?? none, granting.isPending) !== null}
              disabledReason={
                why(blocked ?? none, granting.isPending) ?? undefined
              }
              onClick={() => granting.mutate()}
            >
              Teach it
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={why(blocked ?? none, blocking.isPending) !== null}
              disabledReason={
                why(blocked ?? none, blocking.isPending) ?? undefined
              }
              onClick={() => blocking.mutate()}
            >
              Forbid it
            </Button>
          </div>
        }
      >
        <ChoiceField
          label={view.is_teacher ? 'Who learns' : 'Who teaches'}
          icon={Users}
          value={partner}
          table={partners}
          blocked={blocked ?? none}
          onPick={setPartner}
        />
        <ChoiceField
          label='What is taught'
          icon={TEACHING_KINDS.rite.icon}
          value={kind}
          table={TEACHING_KINDS}
          blocked={blocked ?? none}
          onPick={(value) => setKind(value as keyof typeof TEACHING_KINDS)}
        />
      </ForgeCard>
    </Section>
  )
}

function ElderMemory({ view, blocked }: Props) {
  const page = useShowMore(view.memories, SHOWN, SHOWN * 2)
  const [happening, setHappening] = useState(
    view.happenings[0] ? String(view.happenings[0].id) : ''
  )
  const [learner, setLearner] = useState(
    view.partners[0] ? String(view.partners[0].id) : ''
  )
  const granting = useCouplingAction(
    'beast_lore:grant',
    (_: void) => ({ beast_id: view.node.id, collection_id: Number(happening) }),
    'The beast remembers it now'
  )
  const revealing = useCouplingAction(
    'beast_lore:reveal',
    (_: void) => ({ beast_id: view.node.id, learner_id: Number(learner) }),
    'The beast tells what it remembers'
  )
  const happenings = Object.fromEntries(
    view.happenings.map((item) => [
      String(item.id),
      { label: item.name, icon: Hourglass, tone: 'muted' as const },
    ])
  )
  const learners = Object.fromEntries(
    view.partners.map((node) => [
      String(node.id),
      { label: node.name, icon: Users, tone: 'info' as const },
    ])
  )
  return (
    <Section
      id='section-elder-memory'
      title='The memory of an age'
      description='A long-lived beast remembers its age, teaches or sells that memory, and takes it with it when it dies.'
      icon={Hourglass}
      tone='gold'
    >
      <Bars
        chart='chart-elder-memory'
        title='How truly it remembers'
        legend={[{ text: 'Fidelity', variant: 'warning' }]}
        rows={page.visible.map((row) => ({
          key: String(row.id),
          caption: row.happening ?? 'A happening no longer kept',
          segments: [{ value: row.fidelity, fill: 'fill-gold' }],
        }))}
        max={100}
        noun={['memory', 'memories']}
        empty='This beast keeps no memory of its age yet.'
      />
      {view.memories.length ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          {page.visible.map((row) => (
            <RecordRow
              key={row.id}
              icon={Hourglass}
              tone='gold'
              title={row.happening ?? 'A happening no longer kept'}
              caption={`Remembered in epoch ${row.epoch}: ${row.fidelity} of 100 true, believed ${row.credence} of 100`}
            />
          ))}
        </ul>
      ) : (
        <EmptyState
          icon={Hourglass}
          size='inline'
          title='Nothing remembered'
          description='This beast keeps no memory of its age yet.'
        />
      )}
      <ShowMore state={page} />
      <ForgeCard
        icon={Hourglass}
        tone='gold'
        title='Give or draw out its memory'
        note='Draw out its memory for a community near it, or give it the memory of a happening.'
        columns={2}
        action={
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              disabled={
                why(
                  blocked ??
                    (view.happenings.length
                      ? null
                      : 'No happening on its world to remember'),
                  granting.isPending
                ) !== null
              }
              disabledReason={
                why(
                  blocked ??
                    (view.happenings.length
                      ? null
                      : 'No happening on its world to remember'),
                  granting.isPending
                ) ?? undefined
              }
              onClick={() => granting.mutate()}
            >
              Make it remember
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={
                why(
                  blocked ??
                    (view.partners.length
                      ? null
                      : 'No community lives near it'),
                  revealing.isPending
                ) !== null
              }
              disabledReason={
                why(
                  blocked ??
                    (view.partners.length
                      ? null
                      : 'No community lives near it'),
                  revealing.isPending
                ) ?? undefined
              }
              onClick={() => revealing.mutate()}
            >
              Have it tell
            </Button>
          </div>
        }
      >
        <ChoiceField
          label='Happening to remember'
          icon={Hourglass}
          value={happening}
          table={happenings}
          blocked={blocked ?? (view.happenings.length ? null : 'No happening')}
          onPick={setHappening}
        />
        <ChoiceField
          label='Who it tells'
          icon={Users}
          value={learner}
          table={learners}
          blocked={blocked ?? (view.partners.length ? null : 'No one near')}
          onPick={setLearner}
        />
      </ForgeCard>
    </Section>
  )
}

function Agreement({
  row,
  blocked,
}: {
  row: View['agreements'][number]
  blocked: string | null
}) {
  const kind = AGREEMENT_KINDS[row.kind]
  const state = AGREEMENT_STATES[row.state]
  const editing = useCouplingAction(
    'field_agreement:edit',
    (vars: Edit) => ({ agreement_id: row.id, ...vars }),
    'The agreement keeps its new values'
  )
  const voiding = useCouplingAction(
    'field_agreement:void',
    (_: void) => ({ agreement_id: row.id }),
    'The agreement is repudiated'
  )
  const removing = useCouplingAction(
    'field_agreement:delete',
    (_: void) => ({ agreement_id: row.id }),
    'The agreement is struck out'
  )
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={kind.label}
      caption={`Made in epoch ${row.epoch}${row.term_epoch !== null ? `, runs to epoch ${row.term_epoch}` : ''}, honour ${row.honour}`}
      aside={<Chip icon={state.icon}>{state.label}</Chip>}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Ref node={row.commander} empty='no named commander' />
        <Muted variant='caption'>with</Muted>
        <Ref node={row.counterpart} empty='no named counterpart' />
        <Muted variant='caption'>at</Muted>
        <Ref node={row.place} empty='the field' />
      </div>
      <RecordEditor
        title='Set this agreement'
        note='Values you set are held against the engine until you release them.'
        fields={AGREEMENT_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={Ban}
          label='Void it'
          busy={why(
            blocked ?? (row.state === 'kept' ? null : 'It no longer holds'),
            voiding.isPending
          )}
          onClick={() => voiding.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Strike it out'
          busy={why(blocked, removing.isPending)}
          onClick={() => removing.mutate()}
        />
      </div>
    </RecordRow>
  )
}

function Agreements({ view, blocked }: Props) {
  const page = useShowMore(view.agreements, SHOWN, SHOWN * 2)
  const [kind, setKind] = useState<keyof typeof AGREEMENT_KINDS>('truce')
  const [war, setWar] = useState(view.wars[0] ? String(view.wars[0].id) : '')
  const forcing = useCouplingAction(
    'field_agreement:force',
    (_: void) => ({
      kind,
      war_id: Number(war),
      commander_id: view.node.id,
      place_id: view.node.id,
    }),
    'The commanders come to terms'
  )
  const wars = Object.fromEntries(
    view.wars.map((item) => [
      String(item.id),
      { label: item.name, icon: Flag, tone: 'warning' as const },
    ])
  )
  const none = view.wars.length ? null : 'It is in no war'
  return (
    <Section
      id='section-field-agreements'
      title='Terms in the field'
      description='Parleys, truces, surrender terms, exchanges of captives and the dead, safe conducts and fraternisation.'
      icon={Handshake}
      tone='warning'
    >
      <Bars
        chart='chart-field-agreements'
        title='Honour pledged in each agreement'
        legend={[{ text: 'Honour', variant: 'warning' }]}
        rows={page.visible.map((row) => ({
          key: String(row.id),
          caption: AGREEMENT_KINDS[row.kind].label,
          segments: [
            {
              value: Math.abs(row.honour),
              fill: row.honour < 0 ? 'fill-destructive' : 'fill-warning',
            },
          ],
        }))}
        max={100}
        noun={['agreement', 'agreements']}
        empty='No agreement in the field touches it.'
      />
      {view.agreements.length ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          {page.visible.map((row) => (
            <Agreement key={row.id} row={row} blocked={blocked} />
          ))}
        </ul>
      ) : (
        <EmptyState
          icon={Handshake}
          size='inline'
          title='No terms made'
          description='No agreement in the field touches it.'
        />
      )}
      <ShowMore state={page} />
      <ForgeCard
        icon={Handshake}
        tone='warning'
        title='Force terms in the field'
        note='The commanders come to the terms you choose; breaking them is an atrocity.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={why(blocked ?? none, forcing.isPending) !== null}
            disabledReason={
              why(blocked ?? none, forcing.isPending) ?? undefined
            }
            onClick={() => forcing.mutate()}
          >
            Force them
          </Button>
        }
      >
        <ChoiceField
          label='Kind of agreement'
          icon={Handshake}
          value={kind}
          table={AGREEMENT_KINDS}
          blocked={blocked ?? none}
          onPick={(value) => setKind(value as keyof typeof AGREEMENT_KINDS)}
        />
        <ChoiceField
          label='In which war'
          icon={Flag}
          value={war}
          table={wars}
          blocked={blocked ?? none}
          onPick={setWar}
        />
      </ForgeCard>
    </Section>
  )
}

function Seal({
  row,
  blocked,
}: {
  row: View['seals'][number]
  blocked: string | null
}) {
  const kind = SEAL_KINDS[row.kind]
  const editing = useCouplingAction(
    'deep_seal:edit',
    (vars: Edit) => ({ seal_id: row.id, ...vars }),
    'The seal keeps its new values'
  )
  const breaking = useCouplingAction(
    'deep_seal:unseal',
    (_: void) => ({ seal_id: row.id }),
    'The seal is broken'
  )
  const removing = useCouplingAction(
    'deep_seal:delete',
    (_: void) => ({ seal_id: row.id }),
    'The seal is struck out'
  )
  return (
    <RecordRow
      icon={kind.icon}
      tone={kind.tone}
      title={kind.label}
      caption={`Strength ${row.strength}, wearing ${row.decay} each epoch, since epoch ${row.epoch}${row.broken_epoch !== null ? `, broken in epoch ${row.broken_epoch}` : ''}`}
    >
      {row.sealer ? (
        <div className='flex min-w-0 items-center gap-2'>
          <Muted variant='caption'>Sealed by</Muted>
          <Ref node={row.sealer} />
        </div>
      ) : null}
      <RecordEditor
        title='Set this seal'
        note='Values you set are held against the engine until you release them.'
        fields={SEAL_FIELDS}
        locked={row.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={SEAL_ICON}
          label='Break it'
          busy={why(
            blocked ??
              (row.broken_epoch === null ? null : 'It is already broken'),
            breaking.isPending
          )}
          onClick={() => breaking.mutate()}
        />
        <StepButton
          icon={Trash2}
          label='Strike it out'
          busy={why(blocked, removing.isPending)}
          onClick={() => removing.mutate()}
        />
      </div>
    </RecordRow>
  )
}

function Seals({ view, blocked }: Props) {
  const [kind, setKind] = useState<keyof typeof SEAL_KINDS>('divine')
  const [strength, setStrength] = useState('80')
  const sealing = useCouplingAction(
    'deep_seal:seal',
    (_: void) => ({
      place_id: view.node.id,
      kind,
      strength: Math.max(1, Number(strength) || 1),
    }),
    'The deep is sealed'
  )
  return (
    <Section
      id='section-seals'
      title='Seals over the deep'
      description='Walls, warding rites or a god’s hand hold back what lies below; they wear, are tested and can be dug through.'
      icon={Lock}
      tone='info'
    >
      <Bars
        chart='chart-seals'
        title='Strength of each seal'
        legend={[{ text: 'Strength', variant: 'secondary' }]}
        rows={view.seals.map((row) => ({
          key: String(row.id),
          caption: SEAL_KINDS[row.kind].label,
          segments: [{ value: row.strength, fill: 'fill-info' }],
        }))}
        max={100}
        noun={['seal', 'seals']}
        empty='Nothing seals the deep here.'
      />
      {view.seals.length ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={view.seals} as='li'>
            {(row) => <Seal key={row.id} row={row} blocked={blocked} />}
          </Paged>
        </ul>
      ) : (
        <EmptyState
          icon={Lock}
          size='inline'
          title='The deep is open'
          description='Nothing seals the deep here.'
        />
      )}
      <ForgeCard
        icon={Lock}
        tone='info'
        title='Seal the deep here'
        note='Nothing comes up and no one digs down while the seal holds.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={why(blocked, sealing.isPending) !== null}
            disabledReason={why(blocked, sealing.isPending) ?? undefined}
            onClick={() => sealing.mutate()}
          >
            Seal it
          </Button>
        }
      >
        <ChoiceField
          label='What holds it'
          icon={Lock}
          value={kind}
          table={SEAL_KINDS}
          blocked={blocked}
          onPick={(value) => setKind(value as keyof typeof SEAL_KINDS)}
        />
        <NumberField
          label='Strength'
          value={strength}
          min={1}
          max={100}
          onChange={setStrength}
        />
      </ForgeCard>
    </Section>
  )
}

function Fashion({ view, blocked }: Props) {
  const editing = useCouplingAction(
    'novelty:set',
    (vars: Edit) => ({ holder_id: view.node.id, ...vars }),
    'Its fashion is set'
  )
  const removing = useCouplingAction(
    'novelty:delete',
    (_: void) => ({ holder_id: view.node.id }),
    'Its fashion is forgotten'
  )
  const row = view.novelty
  return (
    <Section
      id='section-fashion'
      title='Fashion'
      description='A form wears out as everyone takes it up and grows fresh as it grows rare; its prestige follows its freshness.'
      icon={Gem}
      tone='gold'
    >
      <Bars
        chart='chart-fashion'
        title='Freshness against how widely it is taken up'
        legend={[
          { text: 'Freshness', variant: 'warning' },
          { text: 'Taken up', variant: 'secondary' },
        ]}
        rows={[
          {
            key: 'novelty',
            caption: 'Freshness',
            segments: [{ value: row?.novelty ?? 100, fill: 'fill-gold' }],
          },
          {
            key: 'adoption',
            caption: 'Taken up',
            segments: [{ value: row?.adoption ?? 0, fill: 'fill-info' }],
          },
        ]}
        max={100}
        noun={['measure', 'measures']}
        empty='It has no fashion kept yet.'
      />
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
        <KpiTile
          label='Freshness'
          value={String(row?.novelty ?? 100)}
          icon={Gem}
          tone='gold'
        />
        <KpiTile
          label='Taken up'
          value={`${row?.adoption ?? 0} of 100`}
          icon={Users}
          tone='info'
        />
        <KpiTile
          label='Revivals'
          value={String(row?.revivals ?? 0)}
          icon={Undo2}
          tone='verdigris'
        />
      </div>
      <Muted variant='caption'>
        {row?.peak_epoch != null
          ? `Most widely taken up in epoch ${row.peak_epoch}; its freshness last moved in epoch ${row.updated_epoch}.`
          : 'It has not yet been taken up widely.'}
      </Muted>
      <RecordEditor
        title='Set its fashion'
        note='Values you set are held against the engine until you release them.'
        fields={NOVELTY_FIELDS}
        locked={row?.locked ?? []}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        icon={Trash2}
        label='Forget its fashion'
        busy={why(
          blocked ?? (row ? null : 'It has no fashion kept yet'),
          removing.isPending
        )}
        onClick={() => removing.mutate()}
      />
    </Section>
  )
}

function OfficesMade({ view }: { view: View }) {
  return (
    <Section
      id='section-offices-made'
      title='Offices made for rising elites'
      description='Offices the realm made to hold its aspirants; they cost the treasury and are abolished when it runs short. Create and abolish offices from the realm’s offices.'
      icon={Landmark}
      tone='gold'
    >
      <Bars
        chart='chart-offices-made'
        title='When each office was made'
        legend={[{ text: 'Epoch made', variant: 'warning' }]}
        rows={view.sinecures.map((row) => ({
          key: String(row.id),
          caption: row.holder?.name ?? 'Vacant',
          segments: [{ value: row.since_epoch, fill: 'fill-gold' }],
        }))}
        noun={['office', 'offices']}
        empty='The realm has made no office to hold its aspirants.'
      />
      {view.sinecures.length ? (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={view.sinecures} as='li'>
            {(row) => (
              <RecordRow
                key={row.id}
                icon={Landmark}
                tone='gold'
                title={row.holder?.name ?? 'Vacant'}
                caption={`Made in epoch ${row.since_epoch}`}
              />
            )}
          </Paged>
        </ul>
      ) : (
        <EmptyState
          icon={Landmark}
          size='inline'
          title='No offices made'
          description='The realm has made no office to hold its aspirants.'
        />
      )}
    </Section>
  )
}

function Body({ view, blocked }: Props) {
  const anything =
    view.is_rite ||
    view.captive_id !== null ||
    view.is_community ||
    view.sociolects.length ||
    view.signs.length ||
    view.is_region ||
    view.is_teacher ||
    view.teachings.length ||
    view.is_beast ||
    view.agreements.length ||
    view.wars.length ||
    view.is_place ||
    view.is_fashion ||
    view.is_realm
  return (
    <div
      data-surface='CouplingsSection'
      className='flex min-w-0 flex-col gap-6'
    >
      <Muted variant='caption'>
        Each part appears for the kinds of thing it belongs to: rites have
        parts, captives are held, communities speak and are taught, regions keep
        their dead, spirits and beasts teach, beasts remember, sides of a war
        come to terms, places are sealed, art forms and dishes go in and out of
        fashion, and realms make offices.
      </Muted>
      {view.is_rite ? <RiteParts view={view} blocked={blocked} /> : null}
      {view.captive_id !== null ? (
        <Restraints view={view} blocked={blocked} />
      ) : null}
      {view.is_community || view.sociolects.length || view.signs.length ? (
        <Registers view={view} blocked={blocked} />
      ) : null}
      {view.is_region ? <Carrion view={view} blocked={blocked} /> : null}
      {view.is_teacher || view.is_community || view.teachings.length ? (
        <Teachings view={view} blocked={blocked} />
      ) : null}
      {view.is_beast ? <ElderMemory view={view} blocked={blocked} /> : null}
      {view.agreements.length || view.wars.length ? (
        <Agreements view={view} blocked={blocked} />
      ) : null}
      {view.is_place ? <Seals view={view} blocked={blocked} /> : null}
      {view.is_fashion ? <Fashion view={view} blocked={blocked} /> : null}
      {view.is_realm ? <OfficesMade view={view} /> : null}
      {anything ? null : (
        <EmptyState
          icon={COUPLINGS_ICON}
          size='inline'
          title='Nothing of these kinds'
          description='This kind of thing has no rite parts, speech, dead, teachings, terms, seals, fashion or offices of its own.'
        />
      )}
    </div>
  )
}

export function CouplingsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeCouplings(nodeId)
  return (
    <Section
      id='section-couplings'
      title='Speech, the dead, teachers, terms and seals'
      description='How bodies, speech, the dead, teachers, armies, the deep and fashion bear on this thing, each part yours to set.'
      icon={COUPLINGS_ICON}
      tone='info'
    >
      {query.isPending ? (
        <LoadingBlock label='Reading how it is bound to the world' />
      ) : query.isError ? (
        <EmptyState
          icon={COUPLINGS_ICON}
          size='inline'
          title='This could not be read'
          description={query.error.message}
        />
      ) : (
        <Body view={query.data} blocked={readOnlyReason} />
      )}
    </Section>
  )
}
