import { useState } from 'react'
import {
  BookOpenCheck,
  Brain,
  Ghost,
  Lock,
  RefreshCw,
  Save,
  Shield,
  ShieldOff,
  Sparkles,
  Unlock,
  UserPlus,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { traitKindValues, valueAxisValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Medallion,
  Paged,
  PagedList,
  RangeField,
  StatBar,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useSons } from '@/features/pantheon/api'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { goodBand, sentence } from '../realm/labels'
import {
  AdjustPanel,
  ChoiceGrid,
  Panel,
  RecordField,
  RefLink,
  Tag,
} from '../realm/parts'
import { type SoulCard } from './api'
import { ALIGNMENTS, DEEDS, LIVING_STATES, RITES, SOUL_FIELDS } from './labels'
import { PERCENT, STRESS_WORDS, busyOf, clampPercent } from './possessionParts'

const SPAN = 100
const NO_GOD = 'none'
const SEAL_WORDS: [string, string, string, string] = [
  'A thread',
  'A knot',
  'A chain',
  'Unbreakable',
]
const DEED_WORDS: [string, string, string, string] = [
  'Little',
  'Some',
  'Much',
  'Legendary',
]

export function SoulSeal({
  soul,
  blocked,
}: {
  soul: SoulCard
  blocked: string | null
}) {
  const id = soul.spirit?.id ?? 0
  const [strength, setStrength] = useState(
    soul.sealed ? soul.seal_strength : PERCENT
  )
  const act = useGodAction<boolean>({
    run: (sealed) =>
      unwrap(
        api.POST('/api/actions/soul:seal', {
          body: { spirit_id: id, sealed, strength: clampPercent(strength) },
        })
      ),
  })
  const busy = busyOf(blocked, act.isPending)
  return (
    <div
      data-surface='SoulSeal'
      className='flex min-w-0 flex-col gap-2 rounded-lg border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion
          icon={soul.sealed ? Lock : Unlock}
          tone={soul.sealed ? 'warning' : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='medium'>
            {soul.sealed ? 'Sealed against rebirth' : 'Free to return'}
          </Text>
          <Muted as='span' variant='caption'>
            {soul.sealed
              ? 'Only a stronger counter-rite breaks this seal'
              : 'A binding seal, a nameless burial or an outer being can seal it'}
          </Muted>
        </div>
      </div>
      {soul.sealed && (
        <StatBar
          label={`Seal: ${goodBand(soul.seal_strength, SEAL_WORDS).label}`}
          value={soul.seal_strength}
          max={PERCENT}
          icon={Lock}
          tone='muted'
        />
      )}
      <AdjustPanel
        trigger={soul.sealed ? 'Tend the seal' : 'Seal the soul'}
        title='The seal on the soul'
        note='A seal stops every gate of rebirth. A counter-rite must be stronger than the seal to break it.'
      >
        <RangeField
          label='Strength of the seal'
          icon={Lock}
          level={goodBand(strength, SEAL_WORDS).label}
          value={strength}
          min={0}
          max={PERCENT}
          lowLabel='A thread'
          highLabel='Unbreakable'
          onChange={setStrength}
        />
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => act.mutate(true)}
          >
            <Lock />
            {soul.sealed ? 'Set the seal' : 'Seal it'}
          </Button>
          {soul.sealed && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => act.mutate(false)}
            >
              <Unlock />
              Break the seal
            </Button>
          )}
        </div>
      </AdjustPanel>
    </div>
  )
}

export function PossessionCard({
  soul,
  blocked,
}: {
  soul: SoulCard
  blocked: string | null
}) {
  const id = soul.spirit?.id ?? 0
  const held = soul.possession
  const [host, setHost] = useState<number | null>(null)
  const [stress, setStress] = useState(held?.stress ?? 0)
  const possess = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:possess', {
          body: { spirit_id: id, host_id: host ?? 0 },
        })
      ),
  })
  const edit = useGodAction<boolean>({
    run: (hold) =>
      unwrap(
        api.POST('/api/actions/soul:possession', {
          body: hold
            ? {
                host_id: held?.host?.id ?? 0,
                values: { stress: clampPercent(stress) },
                release: [],
              }
            : {
                host_id: held?.host?.id ?? 0,
                values: {},
                release: held?.locked ?? [],
              },
        })
      ),
  })
  const exorcise = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:exorcise', {
          body: { host_id: held?.host?.id ?? 0 },
        })
      ),
  })
  const busy = busyOf(
    blocked,
    possess.isPending,
    edit.isPending,
    exorcise.isPending
  )
  const overwritten = Object.entries(held?.host_values ?? {})
  return (
    <Panel
      title='Possession'
      icon={Ghost}
      tone={held ? 'danger' : 'muted'}
      hint={
        held
          ? 'Its imprint lies over the host’s own values'
          : 'It holds no living body'
      }
    >
      <div
        data-surface='PossessionCard'
        className='flex min-w-0 flex-col gap-3'
      >
        {held ? (
          <>
            <div className='flex min-w-0 items-center gap-2'>
              <Medallion icon={Ghost} tone='danger' size='sm' />
              <div className='flex min-w-0 flex-1 flex-col'>
                <Label>Possessing</Label>
                {held.host ? <RefLink node={held.host} /> : <Muted>Lost</Muted>}
              </div>
              <Muted
                as='span'
                variant='caption'
              >{`since ${held.since_epoch}`}</Muted>
              {held.locked.length > 0 && (
                <Tag spec={{ label: 'Held', icon: Lock, tone: 'info' }} />
              )}
            </div>
            <StatBar
              label={`Host’s stress: ${goodBand(held.stress, STRESS_WORDS).label}`}
              value={held.stress}
              max={PERCENT}
              icon={Brain}
              tone='destructive'
            />
            {overwritten.length > 0 && (
              <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                <Muted as='span' variant='caption'>
                  The host’s own values, waiting beneath
                </Muted>
                {overwritten.map(([key, value]) => (
                  <Badge
                    key={key}
                    size='sm'
                    variant='outline'
                  >{`${sentence(key)} ${value}`}</Badge>
                ))}
              </div>
            )}
            <AdjustPanel
              trigger='Adjust the possession'
              title='The grip on the host'
              note='Set the stress it lays on its host, or drive it out at once.'
            >
              <RangeField
                label='Stress on the host'
                icon={Brain}
                level={goodBand(stress, STRESS_WORDS).label}
                value={stress}
                min={0}
                max={PERCENT}
                lowLabel='Uneasy'
                highLabel='Breaking'
                onChange={setStress}
              />
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Button
                  size='sm'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => edit.mutate(true)}
                >
                  <Save />
                  Set and hold
                </Button>
                {held.locked.length > 0 && (
                  <Button
                    size='sm'
                    variant='outline'
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => edit.mutate(false)}
                  >
                    <Unlock />
                    Let it grow
                  </Button>
                )}
                <Button
                  size='sm'
                  variant='outline'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => exorcise.mutate(undefined)}
                >
                  <ShieldOff />
                  Drive it out
                </Button>
              </div>
            </AdjustPanel>
          </>
        ) : (
          <AdjustPanel
            trigger='Set it upon a host'
            title='Possess the living'
            note='The spirit lays its imprint over the host’s values until it is driven out.'
          >
            <div className='flex min-w-0 flex-wrap items-end gap-2'>
              <div className='min-w-48 flex-1'>
                <RecordField
                  label='Host'
                  types={['mortal']}
                  value={host}
                  onChange={setHost}
                  blocked={busy}
                  placeholder='Choose a living mortal'
                />
              </div>
              <Button
                size='sm'
                disabled={busy !== null || host === null}
                disabledReason={busy ?? 'Choose the host first.'}
                onClick={() => possess.mutate(undefined)}
              >
                <UserPlus />
                Take hold
              </Button>
            </div>
          </AdjustPanel>
        )}
      </div>
    </Panel>
  )
}

export function SoulLedger({
  soul,
  blocked,
}: {
  soul: SoulCard
  blocked: string | null
}) {
  const id = soul.spirit?.id ?? 0
  const sons = useSons()
  const [deeds, setDeeds] = useState<Record<string, number>>(() =>
    Object.fromEntries(
      Object.keys(DEEDS).map((key) => [key, soul.deeds[key] ?? 0])
    )
  )
  const [imprint, setImprint] = useState<Record<string, number>>(() =>
    Object.fromEntries(
      valueAxisValues.map((axis) => [axis, soul.imprint[axis] ?? 0])
    )
  )
  const [traits, setTraits] = useState<string[]>(soul.traits)
  const [rite, setRite] = useState<string>(soul.rite)
  const [state, setState] = useState<string>(
    soul.state in LIVING_STATES ? soul.state : 'wandering'
  )
  const [patron, setPatron] = useState<string>(
    soul.patron_son_id === null ? NO_GOD : String(soul.patron_son_id)
  )
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:edit', {
          body: {
            spirit_id: id,
            values: {
              deeds: Object.fromEntries(
                Object.entries(deeds).map(([key, value]) => [
                  key,
                  clampPercent(value),
                ])
              ),
              imprint: Object.fromEntries(
                Object.entries(imprint).map(([key, value]) => [
                  key,
                  Math.max(-SPAN, Math.min(SPAN, Math.round(value))),
                ])
              ),
              traits,
              rite,
              ...(soul.state in LIVING_STATES ? { state } : {}),
              patron_son_id: patron === NO_GOD ? null : Number(patron),
            },
            release: [],
          },
        })
      ),
  })
  const release = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:edit', {
          body: { spirit_id: id, values: {}, release: soul.locked },
        })
      ),
  })
  const reread = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:reread_deeds', { body: { spirit_id: id } })
      ),
  })
  const busy = busyOf(
    blocked,
    save.isPending,
    release.isPending,
    reread.isPending
  )
  const toggleTrait = (trait: string) =>
    setTraits((current) =>
      current.includes(trait)
        ? current.filter((item) => item !== trait)
        : [...current, trait]
    )
  return (
    <AdjustPanel
      trigger='Rewrite the soul'
      title='Rewrite what the soul carries'
      note='Its deeds decide its judgement, its imprint is what it lays over a host or carries into a new life. What you write is held until you release it.'
    >
      <div data-surface='SoulLedger' className='flex min-w-0 flex-col gap-3'>
        <div className='grid min-w-0 grid-cols-1 gap-3 @xl/soul:grid-cols-2'>
          {Object.entries(DEEDS).map(([key, spec]) => (
            <RangeField
              key={key}
              label={spec.label}
              icon={spec.icon}
              level={goodBand(deeds[key] ?? 0, DEED_WORDS).label}
              value={deeds[key] ?? 0}
              min={0}
              max={PERCENT}
              lowLabel='None'
              highLabel='Legendary'
              onChange={(value) =>
                setDeeds((current) => ({ ...current, [key]: value }))
              }
            />
          ))}
        </div>
        <ChoiceGrid
          label='Funeral rite'
          table={RITES}
          value={rite}
          blocked={busy}
          onPick={setRite}
        />
        {soul.state in LIVING_STATES && (
          <ChoiceGrid
            label='Where it is'
            table={LIVING_STATES}
            value={state}
            blocked={busy}
            onPick={setState}
          />
        )}
        <MindPicker
          label='Patron god'
          value={patron}
          table={{
            [NO_GOD]: 'No god',
            ...Object.fromEntries(
              (sons.data ?? []).map((item) => [
                String(item.son.id),
                item.son.name,
              ])
            ),
          }}
          blocked={busy}
          onPick={setPatron}
        />
        <div className='flex min-w-0 flex-col gap-2'>
          <Label>Imprint of values</Label>
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/soul:grid-cols-2'>
            {valueAxisValues.map((axis) => (
              <RangeField
                key={axis}
                label={sentence(axis)}
                icon={Sparkles}
                level={String(imprint[axis] ?? 0)}
                value={imprint[axis] ?? 0}
                min={-SPAN}
                max={SPAN}
                lowLabel='Against'
                highLabel='For'
                onChange={(value) =>
                  setImprint((current) => ({ ...current, [axis]: value }))
                }
              />
            ))}
          </div>
        </div>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label>Traits carried</Label>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            {traitKindValues.map((trait) => (
              <Button
                key={trait}
                size='sm'
                variant={traits.includes(trait) ? 'default' : 'outline'}
                aria-pressed={traits.includes(trait)}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => toggleTrait(trait)}
              >
                {sentence(trait)}
              </Button>
            ))}
          </div>
        </div>
        {soul.locked.length > 0 && (
          <PagedList
            items={soul.locked}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap items-center gap-1.5'
            itemKey={(key) => key}
          >
            {(key) => (
              <Tag
                key={key}
                spec={{ label: key, icon: Lock, tone: 'info' }}
                text={`Holding ${(SOUL_FIELDS[key] ?? sentence(key)).toLowerCase()}`}
              />
            )}
          </PagedList>
        )}
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => save.mutate(undefined)}
          >
            <Save />
            Write and hold
          </Button>
          {soul.locked.length > 0 && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => release.mutate(undefined)}
            >
              <Unlock />
              Release every hold
            </Button>
          )}
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || !soul.origin}
            disabledReason={busy ?? 'This spirit was never a mortal.'}
            onClick={() => reread.mutate(undefined)}
          >
            <BookOpenCheck />
            Read its deeds again
          </Button>
        </div>
      </div>
    </AdjustPanel>
  )
}

export function RaiseSoul({
  regionId,
  blocked,
}: {
  regionId: number
  blocked: string | null
}) {
  const [mortal, setMortal] = useState<number | null>(null)
  const [alignment, setAlignment] = useState<string>('neutral')
  const raise = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/soul:raise', {
          body: {
            mortal_id: mortal ?? 0,
            alignment: alignment as SoulCard['alignment'],
            place_id: regionId,
          },
        })
      ),
  })
  const busy = busyOf(blocked, raise.isPending)
  return (
    <AdjustPanel
      trigger='Call up a soul'
      title='Call up the soul of the dead'
      note='A dead mortal’s soul walks again here, carrying its deeds, values and traits.'
    >
      <ChoiceGrid
        label='Temper'
        table={ALIGNMENTS}
        value={alignment}
        blocked={busy}
        onPick={setAlignment}
      />
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='min-w-48 flex-1'>
          <RecordField
            label='The dead'
            types={['mortal']}
            value={mortal}
            onChange={setMortal}
            blocked={busy}
            placeholder='Choose a dead mortal'
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null || mortal === null}
          disabledReason={busy ?? 'Choose the dead first.'}
          onClick={() => raise.mutate(undefined)}
        >
          <Ghost />
          Call it up
        </Button>
      </div>
    </AdjustPanel>
  )
}

export function RealmGods({
  gods,
}: {
  gods: { son_id: number; name: string; souls: number }[]
}) {
  if (gods.length === 0) return null
  const most = Math.max(1, ...gods.map((god) => god.souls))
  return (
    <Panel
      title='Souls by god'
      icon={Shield}
      tone='gold'
      hint='Each god’s faithful dead; death gods draw strength from them'
    >
      <ul data-surface='RealmGods' className='flex min-w-0 flex-col gap-2'>
        <Paged items={gods} as='li'>
          {(god) => (
            <li key={god.son_id} className='min-w-0'>
              <StatBar
                label={god.name}
                value={god.souls}
                max={most}
                icon={RefreshCw}
              />
            </li>
          )}
        </Paged>
      </ul>
    </Panel>
  )
}
