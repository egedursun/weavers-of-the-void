import { useMemo, useState } from 'react'
import {
  Activity,
  Eye,
  Footprints,
  Handshake,
  HeartCrack,
  Link2,
  Plus,
  Save,
  Sparkles,
  Target,
  Trash2,
  TriangleAlert,
  Undo2,
  Users,
} from 'lucide-react'
import { type ActionBody, type EditValues } from '@/api/actions'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  LoadingBlock,
  Medallion,
  Paged,
  Section,
  StatBar,
} from '@/components/domain'
import { LineChart } from '@/components/domain/LineChart'
import { Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { busyOf } from '@/features/entity/lore/model'
import {
  AdjustPanel,
  Card,
  Group,
  Held,
  NumberField,
} from '@/features/entity/wilds/parts'
import { useForeignGods, useSons } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { useLabels } from '@/features/pantheon/labels'
import {
  type GodDivinity,
  type GoalView,
  type WoundView,
  useDivineAction,
  useGodDivinity,
} from './api'
import {
  EXISTENCE_MODES,
  GOAL_KINDS,
  GOAL_SOURCES,
  GOAL_STATES,
  WOUND_CAUSES,
  WOUND_KINDS,
  heldLabel,
  option,
} from './labels'
import { useGodTable } from './model'
import { NodeName, PickRow, RegardForm, StandingList } from './parts'

const SERIES_COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
] as const
const TARGET_TYPES: Record<string, readonly string[]> = {
  win_war: ['people', 'settlement', 'polity'],
  raise_hero: ['house'],
}
const PLACE_TYPES = ['people', 'settlement', 'region', 'cult'] as const

function DomainsCard({ view }: { view: GodDivinity }) {
  return (
    <Card
      title='Domains and their hooks'
      icon={Sparkles}
      tone='gold'
      hint='What each domain gives the faithful and what it feeds on'
      wide
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        {view.domains.map((domain) => (
          <div
            key={domain.domain}
            className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'
          >
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Text weight='semibold'>{domain.label}</Text>
              <Badge
                size='sm'
                variant='outline'
              >{`Feeds on ${domain.activity_label.toLowerCase()}`}</Badge>
              {domain.severed && (
                <Badge size='sm' variant='destructive'>
                  Severed: its hooks are silent
                </Badge>
              )}
            </div>
            <ul className='flex min-w-0 flex-col gap-1'>
              {domain.hooks.map((hook) => (
                <li key={hook.hook} className='flex min-w-0 items-center gap-2'>
                  <Badge
                    size='sm'
                    variant={hook.harmful ? 'warning' : 'secondary'}
                  >{`+${hook.pct}%`}</Badge>
                  <Text as='span' weight='medium'>
                    {hook.label}
                  </Text>
                  <Muted as='span' variant='caption' truncate>
                    {hook.effect}
                  </Muted>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      {view.synergy ? (
        <Badge size='sm' variant='default'>
          <Link2 aria-hidden='true' />
          {`${view.synergy.label} (${view.synergy.hook_label})`}
        </Badge>
      ) : (
        <Muted variant='caption'>
          These two domains have no shared working together.
        </Muted>
      )}
    </Card>
  )
}

function ActivityCard({ view }: { view: GodDivinity }) {
  const labels = useLabels()
  const series = useMemo(
    () =>
      view.domains.map((domain, index) => ({
        key: domain.domain,
        label: domain.label,
        color: SERIES_COLORS[index % SERIES_COLORS.length],
        points: view.activity
          .filter((row) => row.domain === domain.domain)
          .map((row) => ({ x: row.epoch, y: row.essence })),
      })),
    [view]
  )
  const latest =
    view.activity.length > 0
      ? Math.max(...view.activity.map((row) => row.epoch))
      : null
  return (
    <Card
      title='Where its essence comes from'
      icon={Activity}
      tone='verdigris'
      hint='Essence each domain earned from activity in the god’s worlds'
      wide
    >
      {view.activity.length === 0 ? (
        <EmptyState
          icon={Activity}
          title='No domain activity yet'
          description='After the next epoch the god earns essence from the battles, deaths, voyages and other deeds its domains feed on.'
        />
      ) : (
        <>
          <LineChart
            series={series}
            title='Essence by domain'
            label='Essence'
          />
          <div className='flex min-w-0 flex-wrap gap-2'>
            {view.activity
              .filter((row) => row.epoch === latest)
              .map((row) => (
                <Badge
                  key={`${row.epoch}-${row.domain}`}
                  size='sm'
                  variant='secondary'
                >
                  {`${labels.domain(row.domain)}: ${row.count} → ${row.essence} essence`}
                </Badge>
              ))}
          </div>
        </>
      )}
    </Card>
  )
}

function GoalRow({ goal, busy }: { goal: GoalView; busy: string | null }) {
  const labels = useLabels()
  const edit = useDivineAction(
    'god_goal:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      goal_id: goal.id,
      ...vars,
    })
  )
  const drop = useDivineAction('god_goal:drop', (_: void) => ({
    goal_id: goal.id,
  }))
  const [progress, setProgress] = useState('')
  const [state, setState] = useState('')
  const spec = GOAL_KINDS[goal.kind]
  const tone = GOAL_STATES[goal.state]
  const pending = busyOf(busy, edit.isPending, drop.isPending)
  const nothing =
    progress === '' && state === ''
      ? 'Change the progress or the state first'
      : null
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text weight='semibold'>{spec.label}</Text>
          <div className='flex min-w-0 flex-wrap items-center gap-1'>
            <Badge
              size='sm'
              variant={
                goal.state === 'done'
                  ? 'success'
                  : goal.state === 'failed'
                    ? 'destructive'
                    : 'secondary'
              }
            >
              {tone.label}
            </Badge>
            {goal.target && <NodeName item={goal.target} />}
            {goal.world && <NodeName item={goal.world} />}
            {goal.domain && (
              <Badge size='sm' variant='outline'>
                {labels.domain(goal.domain)}
              </Badge>
            )}
            {goal.amount > 0 && (
              <Badge size='sm' variant='outline'>{`Aim: ${goal.amount}`}</Badge>
            )}
          </div>
        </div>
        <Button
          size='sm'
          variant='ghost'
          disabled={pending !== null}
          disabledReason={pending ?? undefined}
          onClick={() => drop.mutate()}
        >
          <Trash2 />
          Set aside
        </Button>
      </div>
      <StatBar
        label='Progress'
        value={goal.progress}
        max={100}
        icon={Target}
        tone={goal.state === 'failed' ? 'destructive' : 'success'}
      />
      <Muted variant='caption'>{`${GOAL_SOURCES[goal.source]}, since epoch ${goal.since_epoch}${goal.closed_epoch ? `, closed in epoch ${goal.closed_epoch}` : ''}`}</Muted>
      <Held
        keys={goal.locked}
        label={heldLabel}
        busy={pending}
        onRelease={() => edit.mutate({ values: {}, release: goal.locked })}
      />
      <AdjustPanel
        title='Reshape this aim'
        note='Progress or a state you set is held: the world will not move it until you let it decide again.'
      >
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <NumberField
            label='Progress (%)'
            value={progress}
            min={0}
            max={100}
            disabled={pending !== null}
            onChange={setProgress}
          />
          <PickRow
            label='State'
            table={option(GOAL_STATES)}
            value={state}
            blocked={pending}
            onPick={setState}
          />
        </div>
        <Button
          size='sm'
          disabled={pending !== null || nothing !== null}
          disabledReason={pending ?? nothing ?? undefined}
          onClick={() => {
            const values: EditValues = {}
            if (progress !== '') values.progress = Number(progress)
            if (state !== '') values.state = state
            edit.mutate({ values, release: [] })
            setProgress('')
            setState('')
          }}
        >
          <Save />
          Hold the aim this way
        </Button>
      </AdjustPanel>
    </li>
  )
}

function GoalsCard({ view, busy }: { view: GodDivinity; busy: string | null }) {
  const [kind, setKind] = useState('')
  const [target, setTarget] = useState<number | null>(null)
  const [god, setGod] = useState('')
  const [world, setWorld] = useState<number | null>(null)
  const [domain, setDomain] = useState('')
  const [amount, setAmount] = useState('')
  const gods = useGodTable()
  const set = useDivineAction('god_goal:set', (_: void) => ({
    god_id: view.god.id,
    kind: kind as ActionBody<'god_goal:set'>['kind'],
    target_id: god !== '' ? Number(god) : target,
    world_id: world,
    domain:
      domain === '' ? null : (domain as ActionBody<'god_goal:set'>['domain']),
    amount: amount === '' ? 0 : Number(amount),
  }))
  const pending = busyOf(busy, set.isPending)
  const kinds = Object.fromEntries(
    view.goal_kinds.map((item) => [item, GOAL_KINDS[item].label])
  )
  const needsGod = [
    'destroy_rival',
    'awaken_god',
    'defeat_foreign_god',
  ].includes(kind)
  const needsEntity = kind in TARGET_TYPES
  const problem =
    kind === ''
      ? 'Choose an aim'
      : needsGod && god === ''
        ? 'Choose the god it names'
        : needsEntity && target === null
          ? 'Choose what it names'
          : null
  return (
    <Card
      title='Aims'
      icon={Target}
      tone='info'
      hint='Typed aims the god pursues; it gains experience and fame on reaching them'
      wide
    >
      {view.goals.length === 0 ? (
        <EmptyState
          icon={Target}
          title='No aim yet'
          description='Gods choose aims from their values and domains; you can give one.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={view.goals} as='li'>
            {(goal) => <GoalRow key={goal.id} goal={goal} busy={busy} />}
          </Paged>
        </ul>
      )}
      <Group title='Give an aim' icon={Plus}>
        <div className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
          <PickRow
            label='Aim'
            table={kinds}
            value={kind}
            blocked={pending}
            onPick={setKind}
          />
          {needsGod && (
            <PickRow
              label='God it names'
              table={gods}
              value={god}
              blocked={pending}
              onPick={setGod}
            />
          )}
          {needsEntity && (
            <EntityPicker
              types={TARGET_TYPES[kind] ?? []}
              value={target}
              onChange={setTarget}
              placeholder='What the aim names'
            />
          )}
          <EntityPicker
            types={['world']}
            value={world}
            onChange={setWorld}
            placeholder='World it names (optional)'
          />
          <PickRow
            label='Domain to spread'
            table={Object.fromEntries(
              view.domains.map((item) => [item.domain, item.label])
            )}
            value={domain}
            blocked={pending}
            onPick={setDomain}
          />
          <NumberField
            label='How many (optional)'
            value={amount}
            min={0}
            disabled={pending !== null}
            onChange={setAmount}
          />
        </div>
        <Button
          disabled={pending !== null || problem !== null}
          disabledReason={pending ?? problem ?? undefined}
          onClick={() => set.mutate()}
        >
          <Target />
          Give this aim
        </Button>
      </Group>
    </Card>
  )
}

function WoundRow({ wound, busy }: { wound: WoundView; busy: string | null }) {
  const edit = useDivineAction(
    'divine_wound:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      wound_id: wound.id,
      ...vars,
    })
  )
  const remove = useDivineAction('divine_wound:remove', (_: void) => ({
    wound_id: wound.id,
  }))
  const [healed, setHealed] = useState('')
  const [severity, setSeverity] = useState('')
  const [form, setForm] = useState('')
  const labels = useLabels()
  const spec = WOUND_KINDS[wound.kind]
  const shatters = wound.kind === 'shattered_manifestation'
  const pending = busyOf(busy, edit.isPending, remove.isPending)
  const nothing =
    healed === '' && severity === '' && form === ''
      ? 'Change the healing, the severity or the form first'
      : null
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text weight='semibold'>
            {wound.domain
              ? `${spec.label} (${labels.domain(wound.domain)})`
              : spec.label}
          </Text>
          <Muted variant='caption'>{`From ${WOUND_CAUSES[wound.cause]}${wound.cause_node ? `, ${wound.cause_node.name}` : ''}, epoch ${wound.epoch}`}</Muted>
        </div>
        <Button
          size='sm'
          variant='ghost'
          disabled={pending !== null}
          disabledReason={pending ?? undefined}
          onClick={() => remove.mutate()}
        >
          <HeartCrack />
          Heal at once
        </Button>
      </div>
      <StatBar
        label='Severity'
        value={wound.severity}
        max={100}
        tone='destructive'
      />
      <StatBar label='Healed' value={wound.healed} max={100} tone='success' />
      {shatters && (
        <Badge size='sm' variant='outline' className='self-start'>
          {`Its form is scattered; it returns ${wound.prior_mode ? `to ${EXISTENCE_MODES[wound.prior_mode].toLowerCase()}` : 'unshaped'} when healed`}
        </Badge>
      )}
      <Held
        keys={wound.locked}
        label={heldLabel}
        busy={pending}
        onRelease={() => edit.mutate({ values: {}, release: wound.locked })}
      />
      <AdjustPanel
        title='Reshape this wound'
        note='Healing or severity you set is held until you let the world decide again.'
      >
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <NumberField
            label='Healed (%)'
            value={healed}
            min={0}
            max={100}
            disabled={pending !== null}
            onChange={setHealed}
          />
          <NumberField
            label='Severity'
            value={severity}
            min={1}
            max={100}
            disabled={pending !== null}
            onChange={setSeverity}
          />
          <PickRow
            label='Form it returns to'
            table={Object.fromEntries(
              Object.entries(EXISTENCE_MODES).filter(
                ([key]) => key !== 'scattered'
              )
            )}
            value={form}
            blocked={
              shatters
                ? pending
                : 'Only a shattered manifestation scatters a form'
            }
            onPick={setForm}
          />
        </div>
        <Button
          size='sm'
          disabled={pending !== null || nothing !== null}
          disabledReason={pending ?? nothing ?? undefined}
          onClick={() => {
            const values: EditValues = {}
            if (healed !== '') values.healed = Number(healed)
            if (severity !== '') values.severity = Number(severity)
            if (form !== '') values.prior_mode = form
            edit.mutate({ values, release: [] })
            setHealed('')
            setSeverity('')
            setForm('')
          }}
        >
          <Save />
          Hold the wound this way
        </Button>
      </AdjustPanel>
    </li>
  )
}

function WoundsCard({
  view,
  busy,
}: {
  view: GodDivinity
  busy: string | null
}) {
  const [kind, setKind] = useState('')
  const [domain, setDomain] = useState('')
  const [severity, setSeverity] = useState('50')
  const inflict = useDivineAction('divine_wound:inflict', (_: void) => ({
    god_id: view.god.id,
    kind: kind as ActionBody<'divine_wound:inflict'>['kind'],
    severity: Number(severity),
    domain:
      domain === ''
        ? null
        : (domain as ActionBody<'divine_wound:inflict'>['domain']),
  }))
  const pending = busyOf(busy, inflict.isPending)
  const problem = kind === '' ? 'Choose a wound' : null
  return (
    <Card
      title='Divine body'
      icon={HeartCrack}
      tone='danger'
      hint='Wounds of a god heal with faith and with the rites of its faithful'
      wide
    >
      {view.wounds.length === 0 ? (
        <EmptyState
          icon={HeartCrack}
          title='Unwounded'
          description='Gods are wounded in duels, wars of gods, by the death of a mortal form, by outer bargains or by you.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={view.wounds} as='li'>
            {(wound) => <WoundRow key={wound.id} wound={wound} busy={busy} />}
          </Paged>
        </ul>
      )}
      <Group title='Wound this god' icon={TriangleAlert}>
        <div className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-3'>
          <PickRow
            label='Wound'
            table={option(WOUND_KINDS)}
            value={kind}
            blocked={pending}
            onPick={setKind}
          />
          <PickRow
            label='Domain to sever'
            table={Object.fromEntries(
              view.domains.map((item) => [item.domain, item.label])
            )}
            value={domain}
            blocked={
              kind === 'severed_domain'
                ? pending
                : 'Only a severed domain names a domain'
            }
            onPick={setDomain}
          />
          <NumberField
            label='Severity'
            value={severity}
            min={1}
            max={100}
            disabled={pending !== null}
            onChange={setSeverity}
          />
        </div>
        <Button
          variant='destructive'
          disabled={pending !== null || problem !== null}
          disabledReason={pending ?? problem ?? undefined}
          onClick={() => inflict.mutate()}
        >
          <TriangleAlert />
          Inflict the wound
        </Button>
      </Group>
    </Card>
  )
}

function AvatarsCard({
  view,
  busy,
}: {
  view: GodDivinity
  busy: string | null
}) {
  const [place, setPlace] = useState<number | null>(null)
  const manifest = useDivineAction('avatar:manifest', (at: number) => ({
    god_id: view.god.id,
    place_id: at,
  }))
  const withdraw = useDivineAction('avatar:withdraw', (avatar: number) => ({
    avatar_id: avatar,
  }))
  const edit = useDivineAction(
    'avatar:edit',
    (vars: { avatar: number; values: EditValues; release: string[] }) => ({
      avatar_id: vars.avatar,
      values: vars.values,
      release: vars.release,
    })
  )
  const pending = busyOf(
    busy,
    manifest.isPending,
    withdraw.isPending,
    edit.isPending
  )
  const shattered = view.wounds.some(
    (item) => item.kind === 'shattered_manifestation' && item.healed < 100
  )
  const problem = shattered
    ? 'Its manifestation is shattered; heal it first'
    : place === null
      ? 'Choose where it walks'
      : null
  return (
    <Card
      title='Mortal forms'
      icon={Footprints}
      tone='gold'
      hint='A god may walk among mortals; if its form is killed its manifestation shatters'
      wide
    >
      {view.avatars.length === 0 ? (
        <EmptyState
          icon={Footprints}
          title='No mortal form'
          description='Give the god a mortal form to raise awe and love where it walks and win peoples to its faith.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={view.avatars} as='li'>
            {(row) => (
              <li
                key={row.avatar.id}
                className='flex min-w-0 items-center gap-2 rounded-lg border bg-muted/30 p-3'
              >
                <Medallion
                  icon={Eye}
                  tone={row.alive ? 'gold' : 'muted'}
                  size='sm'
                />
                <div className='flex min-w-0 flex-1 flex-col gap-1'>
                  <NodeName item={row.avatar} />
                  <Muted variant='caption'>{`Walking since epoch ${row.since_epoch}; ${plural(row.deeds, 'deed', 'deeds')}${row.locked.includes('deeds') ? ' (held)' : ''}`}</Muted>
                </div>
                <Button
                  size='sm'
                  variant='outline'
                  disabled={pending !== null}
                  disabledReason={pending ?? undefined}
                  onClick={() =>
                    edit.mutate({
                      avatar: row.avatar.id,
                      values: row.locked.includes('deeds')
                        ? {}
                        : { deeds: row.deeds },
                      release: row.locked.includes('deeds') ? ['deeds'] : [],
                    })
                  }
                >
                  {row.locked.includes('deeds') ? <Undo2 /> : <Save />}
                  {row.locked.includes('deeds')
                    ? 'Let its deeds count again'
                    : 'Hold its deeds'}
                </Button>
                <Button
                  size='sm'
                  variant='ghost'
                  disabled={pending !== null}
                  disabledReason={pending ?? undefined}
                  onClick={() => withdraw.mutate(row.avatar.id)}
                >
                  <Trash2 />
                  Call it back
                </Button>
              </li>
            )}
          </Paged>
        </ul>
      )}
      <Group title='Give it a mortal form' icon={Plus}>
        <EntityPicker
          types={PLACE_TYPES}
          value={place}
          onChange={setPlace}
          placeholder='The people, place or land it walks among'
        />
        <Button
          disabled={pending !== null || problem !== null}
          disabledReason={pending ?? problem ?? undefined}
          onClick={() => place !== null && manifest.mutate(place)}
        >
          <Footprints />
          Take a mortal form
        </Button>
      </Group>
    </Card>
  )
}

function StandingCard({
  view,
  busy,
}: {
  view: GodDivinity
  busy: string | null
}) {
  const save = useDivineAction(
    'divine_standing:set',
    (vars: { community: number; values: EditValues; release: string[] }) => ({
      community_id: vars.community,
      god_id: view.god.id,
      values: vars.values,
      release: vars.release,
    })
  )
  const clear = useDivineAction(
    'divine_standing:clear',
    (community: number) => ({ community_id: community, god_id: view.god.id })
  )
  const pending = busyOf(busy, save.isPending, clear.isPending)
  return (
    <Card
      title='How each people regards it'
      icon={Users}
      tone='verdigris'
      hint='Awe, love, fear and neglect among the god’s peoples'
      wide
    >
      {view.standing.length === 0 && (
        <EmptyState
          icon={Users}
          title='No people regards it yet'
          description='Peoples that worship the god form a regard of it after the next epoch.'
        />
      )}
      <StandingList
        rows={view.standing}
        focus='god'
        busy={pending}
        onSave={(row, values, release) =>
          save.mutate({ community: row.community.id, values, release })
        }
        onClear={(row) => clear.mutate(row.community.id)}
      />
      <RegardForm
        busy={pending}
        onSave={(community, values) =>
          save.mutate({ community, values, release: [] })
        }
      />
    </Card>
  )
}

function PactCard({ view, busy }: { view: GodDivinity; busy: string | null }) {
  const sons = useSons()
  const gods = useForeignGods()
  const [other, setOther] = useState('')
  const [epochs, setEpochs] = useState('')
  const isSon = view.god.kind === 'son'
  const isForeign = view.god.kind === 'foreign_god'
  const table = useMemo(
    () =>
      Object.fromEntries(
        isSon
          ? (gods.data ?? []).map((god) => [String(god.id), god.name])
          : (sons.data ?? []).map((row) => [String(row.son.id), row.son.name])
      ),
    [isSon, gods.data, sons.data]
  )
  const seal = useDivineAction(
    'divine_pact:seal',
    (_: void) => ({
      son_id: isSon ? view.god.id : Number(other),
      god_id: isSon ? Number(other) : view.god.id,
      epochs: epochs === '' ? null : Number(epochs),
    }),
    () => setOther('')
  )
  const reason =
    busy ??
    (!isSon && !isForeign
      ? 'Only a son and a foreign god can seal a pact with each other'
      : other === ''
        ? `Choose the ${isSon ? 'foreign god' : 'son'} to bind`
        : seal.isPending
          ? 'Sealing the pact'
          : null)
  return (
    <Card
      title='A pact between gods'
      icon={Handshake}
      tone='gold'
      hint='A son and a foreign god bound by a sealed treaty, for a span of epochs or for good'
      wide
    >
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-3'>
        <PickRow
          label={isSon ? 'Foreign god' : 'Son'}
          table={table}
          value={other}
          blocked={
            busy ?? (!isSon && !isForeign ? 'Not a son or a foreign god' : null)
          }
          onPick={setOther}
        />
        <NumberField
          label='Lasting epochs (empty for good)'
          value={epochs}
          min={1}
          disabled={busy !== null || (!isSon && !isForeign)}
          onChange={setEpochs}
        />
        <Button
          size='sm'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => seal.mutate()}
        >
          <Handshake />
          Seal the pact
        </Button>
      </div>
    </Card>
  )
}

export function GodDivinitySection({
  godId,
  readOnlyReason,
}: {
  godId: number
  readOnlyReason?: string | null
}) {
  const view = useGodDivinity(godId)
  const { reason } = useGodGate()
  const busy = readOnlyReason ?? reason()
  return (
    <Section
      id='section-divinity'
      title='Divinity'
      description='Domains and their hooks, the essence they earn, aims, wounds, mortal forms and the regard of peoples. Only gods have these; mortals, places and worlds hold a god in regard instead.'
      icon={Sparkles}
      tone='gold'
    >
      {view.isPending && <LoadingBlock label='Reading this god’s divinity' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Its divinity could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='GodDivinity'
          className='@container/wild grid min-w-0 grid-cols-1 gap-3 @xl/wild:grid-cols-2'
        >
          <DomainsCard view={view.data} />
          <ActivityCard view={view.data} />
          <GoalsCard view={view.data} busy={busy} />
          <WoundsCard view={view.data} busy={busy} />
          <AvatarsCard view={view.data} busy={busy} />
          <StandingCard view={view.data} busy={busy} />
          <PactCard view={view.data} busy={busy} />
        </div>
      )}
    </Section>
  )
}
