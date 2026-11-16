import { useId, useMemo, useState } from 'react'
import {
  Eye,
  Footprints,
  Gem,
  Save,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  Unlink,
  UserCheck,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Paged, PagedList } from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted } from '@/components/typography'
import {
  Chip,
  Facts,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { SCHOOLS } from '@/features/divine/labels'
import { useNames } from '@/features/entity/api/queries'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import {
  type ClaimView,
  type CreatureDeed,
  type CreatureView,
  type MagicSiteView,
  type MiracleView,
  type ThroneView,
  useDominionAction,
} from './api'
import { DEEDS, LESSONS, SITE_KINDS, THRONE_ICON, table } from './labels'
import { GOD_KINDS, why } from './model'

export function NodePicker({
  label,
  value,
  onChange,
  blocked,
  kinds = [],
  types,
}: {
  label: string
  value: number | null
  onChange: (value: number | null) => void
  blocked: string | null
  kinds?: readonly string[]
  types?: readonly string[]
}) {
  const id = useId()
  const names = useNames()
  const options = useMemo(
    () =>
      (names.data ?? [])
        .filter((entry) =>
          entry.kind === 'entity'
            ? types !== undefined &&
              entry.status !== 'dead' &&
              types.includes(entry.type)
            : kinds.includes(entry.kind)
        )
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint: (entry.kind === 'entity' ? entry.type : entry.kind).replaceAll(
            '_',
            ' '
          ),
        })),
    [names.data, kinds, types]
  )
  const sought = [...kinds, ...(types ?? [])]
    .map((kind) => kind.replaceAll('_', ' '))
    .join(', ')
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label as='label' htmlFor={id}>
        {label}
      </Label>
      <RecordCombobox
        id={id}
        options={options}
        value={value === null ? null : String(value)}
        onChange={(next) => onChange(next === null ? null : Number(next))}
        placeholder={`Search ${sought}`}
        disabled={blocked !== null || names.isPending}
        disabledReason={
          blocked ?? (names.isPending ? 'Reading the names' : undefined)
        }
        clearable
        aria-label={label}
      />
    </div>
  )
}

export function ClaimCard({
  claim,
  focus,
  blocked,
}: {
  claim: ClaimView
  focus: 'god' | 'region'
  blocked: string | null
}) {
  const [strength, setStrength] = useState('')
  const godId = claim.god?.id ?? 0
  const regionId = claim.region?.id ?? 0
  const set = useDominionAction(
    'dominion:set',
    (vars: { strength: number; hold: boolean }) => ({
      god_id: godId,
      region_id: regionId,
      ...vars,
    }),
    'The dominion is set'
  )
  const remove = useDominionAction(
    'dominion:delete',
    (_: void) => ({ god_id: godId, region_id: regionId }),
    'The dominion is lifted'
  )
  const busy = why(blocked, set.isPending, remove.isPending)
  const held = claim.locked.includes('strength')
  const typed = strength === '' ? null : Number(strength)
  const missing =
    typed === null || Number.isNaN(typed) ? 'Type a strength first' : null
  return (
    <RecordRow
      icon={THRONE_ICON}
      tone={claim.ruling ? 'gold' : 'info'}
      title={
        <Ref
          node={focus === 'god' ? claim.region : claim.god}
          empty='somewhere forgotten'
        />
      }
      caption={`${claim.ruling ? 'Rules this land' : 'Contends here'} · weighed in epoch ${claim.epoch}`}
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <Trash2 />
          Lift
        </Button>
      }
    >
      <Meter
        label='Dominion'
        value={claim.strength}
        tone={claim.ruling ? 'default' : 'info'}
        icon={THRONE_ICON}
      />
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {claim.ruling && <Chip variant='success'>Ruling</Chip>}
        {claim.trend < 0 && (
          <Chip variant='destructive'>{`Losing ground: ${claim.trend}`}</Chip>
        )}
        {claim.trend > 0 && (
          <Chip variant='info'>{`Gaining ground: +${claim.trend}`}</Chip>
        )}
        {held && <Badge variant='outline'>Held</Badge>}
      </div>
      <Facts
        items={[
          ['From temples', String(claim.temples)],
          ['From holy sites', String(claim.holy_sites)],
          ['From prophets', String(claim.prophets)],
          ['From miracles', String(claim.miracles)],
          ['From worship', String(claim.worship)],
          ['Spread from neighbours', String(claim.spread)],
        ]}
      />
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-3'>
        <NumberField
          label='Set the dominion'
          value={strength}
          min={0}
          max={100}
          disabled={busy !== null}
          onChange={setStrength}
        />
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => {
            set.mutate({ strength: typed ?? 0, hold: true })
            setStrength('')
          }}
        >
          <Save />
          Hold it
        </Button>
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <Muted variant='caption'>Held against the engine</Muted>
          <Switch
            aria-label='Hold this dominion'
            checked={held}
            disabled={busy !== null}
            onCheckedChange={(hold) =>
              set.mutate({ strength: claim.strength, hold })
            }
          />
        </div>
      </div>
    </RecordRow>
  )
}

export function ThroneCard({
  throne,
  blocked,
}: {
  throne: ThroneView
  blocked: string | null
}) {
  const [holder, setHolder] = useState<number | null>(null)
  const edit = useDominionAction(
    'throne:edit',
    (vars: { values: Record<string, number | null>; release: string[] }) => ({
      throne_id: throne.id,
      ...vars,
    }),
    'The throne is set'
  )
  const remove = useDominionAction(
    'throne:delete',
    (_: void) => ({ throne_id: throne.id }),
    'The throne is cast down'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  return (
    <RecordRow
      icon={THRONE_ICON}
      tone={throne.holder ? 'gold' : 'muted'}
      title={<Ref node={throne.place} empty='a lost place' />}
      caption={
        throne.holder
          ? `Held by ${throne.holder.name}${throne.since_epoch !== null ? ` since epoch ${throne.since_epoch}` : ''}`
          : 'Unclaimed'
      }
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <Trash2 />
          Cast down
        </Button>
      }
    >
      <Meter label='Power' value={throne.power} tone='default' />
      <Facts
        items={[
          ['World', <Ref key='world' node={throne.world} empty='no world' />],
          ['Holder', <Ref key='holder' node={throne.holder} empty='no god' />],
          [
            'Since',
            throne.since_epoch === null
              ? 'Never held'
              : `Epoch ${throne.since_epoch}`,
          ],
        ]}
      />
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-3'>
        <NodePicker
          label='Give the throne to'
          value={holder}
          onChange={setHolder}
          blocked={busy}
          kinds={GOD_KINDS}
        />
        <Button
          size='sm'
          disabled={busy !== null || holder === null}
          disabledReason={
            busy ?? (holder === null ? 'Choose a god first' : undefined)
          }
          onClick={() => {
            edit.mutate({ values: { holder_node_id: holder }, release: [] })
            setHolder(null)
          }}
        >
          <UserCheck />
          Seat this god
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || throne.holder === null}
          disabledReason={
            busy ?? (throne.holder === null ? 'No god holds it' : undefined)
          }
          onClick={() =>
            edit.mutate({
              values: { holder_node_id: null, since_epoch: null },
              release: [],
            })
          }
        >
          <Unlink />
          Empty the throne
        </Button>
      </div>
      <RecordEditor
        title='Reshape this throne'
        note='Values you set are held against the engine until you release them.'
        fields={[
          { key: 'power', label: 'Power', kind: 'number', min: 0, max: 100 },
        ]}
        locked={throne.locked}
        busy={busy}
        onSave={(values) =>
          edit.mutate({
            values: values as Record<string, number | null>,
            release: [],
          })
        }
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

export function SiteCard({
  site,
  blocked,
}: {
  site: MagicSiteView
  blocked: string | null
}) {
  const [holder, setHolder] = useState<number | null>(null)
  const [world, setWorld] = useState<number | null>(null)
  const [finder, setFinder] = useState<number | null>(null)
  const edit = useDominionAction(
    'magic_site:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ site_id: site.id, ...vars }),
    'The magic site is set'
  )
  const reveal = useDominionAction(
    'magic_site:reveal',
    (_: void) => ({ site_id: site.id, finder_id: finder }),
    'The magic site is found'
  )
  const remove = useDominionAction(
    'magic_site:delete',
    (_: void) => ({ site_id: site.id }),
    'The magic site fades'
  )
  const busy = why(blocked, edit.isPending, reveal.isPending, remove.isPending)
  const kind = SITE_KINDS[site.kind]
  const found = site.found_epoch !== null
  return (
    <RecordRow
      icon={kind.icon}
      tone={found ? kind.tone : 'muted'}
      title={`${kind.label} of ${SCHOOLS[site.school]}`}
      caption={
        found
          ? `Found in epoch ${site.found_epoch}${site.found_by ? ` by ${site.found_by.name}` : ''}`
          : 'Still hidden'
      }
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <Trash2 />
          Unmake
        </Button>
      }
    >
      <Meter
        label='Strength'
        value={site.strength}
        tone='verdigris'
        icon={Gem}
      />
      <Facts
        items={[
          ['Place', <Ref key='place' node={site.place} empty='a lost place' />],
          ['Holder', <Ref key='holder' node={site.holder} empty='no one' />],
          [
            'Found by',
            <Ref key='finder' node={site.found_by} empty='no one yet' />,
          ],
          ['Reagents each epoch', String(site.output)],
          [
            'Opens toward',
            <Ref key='world' node={site.target_world} empty='no other world' />,
          ],
        ]}
      />
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <NodePicker
          label='Found by'
          value={finder}
          onChange={setFinder}
          blocked={busy ?? (found ? 'This site is already found' : null)}
          types={['mortal', 'settlement', 'people', 'polity']}
        />
        <Button
          size='sm'
          disabled={busy !== null || found}
          disabledReason={
            busy ?? (found ? 'This site is already found' : undefined)
          }
          onClick={() => reveal.mutate()}
        >
          <Eye />
          Reveal it
        </Button>
        <NodePicker
          label='Give it to'
          value={holder}
          onChange={setHolder}
          blocked={busy}
          kinds={GOD_KINDS}
          types={['settlement', 'people', 'polity', 'cult', 'mortal']}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || holder === null}
          disabledReason={
            busy ?? (holder === null ? 'Choose a holder first' : undefined)
          }
          onClick={() => {
            edit.mutate({ values: { holder_node_id: holder }, release: [] })
            setHolder(null)
          }}
        >
          <UserCheck />
          Hand it over
        </Button>
        <NodePicker
          label='Open toward world'
          value={world}
          onChange={setWorld}
          blocked={
            busy ??
            (site.kind === 'gateway'
              ? null
              : 'Only a gateway opens toward a world')
          }
          kinds={['world']}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || world === null || site.kind !== 'gateway'}
          disabledReason={
            busy ??
            (site.kind !== 'gateway'
              ? 'Only a gateway opens toward a world'
              : world === null
                ? 'Choose a world first'
                : undefined)
          }
          onClick={() => {
            edit.mutate({ values: { target_world_id: world }, release: [] })
            setWorld(null)
          }}
        >
          <Footprints />
          Open the way
        </Button>
      </div>
      <RecordEditor
        title='Reshape this site'
        note='Values you set are held against the engine until you release them.'
        fields={[
          {
            key: 'kind',
            label: 'Kind',
            kind: 'pick',
            table: table(SITE_KINDS),
          },
          { key: 'school', label: 'School', kind: 'pick', table: SCHOOLS },
          {
            key: 'strength',
            label: 'Strength',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'output',
            label: 'Reagents each epoch',
            kind: 'number',
            min: 0,
          },
          {
            key: 'found_epoch',
            label: 'Found in epoch',
            kind: 'number',
            min: 0,
          },
        ]}
        locked={site.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function DeedRow({
  creature,
  deed,
  weight,
  blocked,
}: {
  creature: CreatureView
  deed: CreatureDeed
  weight: number
  blocked: string | null
}) {
  const [draft, setDraft] = useState('')
  const creatureId = creature.creature?.id ?? 0
  const teach = useDominionAction(
    'divine_creature:teach',
    (lesson: 'reward' | 'punish') => ({
      creature_id: creatureId,
      deed,
      lesson,
    })
  )
  const weigh = useDominionAction(
    'divine_creature:weight',
    (vars: { weight: number }) => ({
      creature_id: creatureId,
      deed,
      weight: vars.weight,
      hold: true,
    }),
    'The leaning is held'
  )
  const busy = why(blocked, teach.isPending, weigh.isPending)
  const spec = DEEDS[deed]
  const typed = draft === '' ? null : Number(draft)
  const missing =
    typed === null || Number.isNaN(typed) ? 'Type a leaning first' : null
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-2.5'>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Chip icon={spec.icon}>{spec.label}</Chip>
        <Muted variant='caption'>{`leaning ${weight}`}</Muted>
        {creature.last_deed === deed && <Chip variant='info'>Last chosen</Chip>}
      </div>
      <div className='grid min-w-0 grid-cols-2 items-end gap-2 sm:grid-cols-4'>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => teach.mutate('reward')}
        >
          <ThumbsUp />
          {LESSONS.reward.label}
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => teach.mutate('punish')}
        >
          <ThumbsDown />
          {LESSONS.punish.label}
        </Button>
        <NumberField
          label='Leaning'
          value={draft}
          min={0}
          max={1000}
          disabled={busy !== null}
          onChange={setDraft}
        />
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => {
            weigh.mutate({ weight: typed ?? 0 })
            setDraft('')
          }}
        >
          <Save />
          Hold
        </Button>
      </div>
    </li>
  )
}

export function CreatureCard({
  creature,
  blocked,
}: {
  creature: CreatureView
  blocked: string | null
}) {
  const creatureId = creature.creature?.id ?? 0
  const edit = useDominionAction(
    'divine_creature:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ creature_id: creatureId, ...vars }),
    'The creature is set'
  )
  const release = useDominionAction(
    'divine_creature:release',
    (_: void) => ({ creature_id: creatureId }),
    'The creature goes free'
  )
  const busy = why(blocked, edit.isPending, release.isPending)
  const last = creature.last_deed ? DEEDS[creature.last_deed] : null
  return (
    <RecordRow
      icon={last?.icon ?? Footprints}
      tone={last?.tone ?? 'verdigris'}
      title={<Ref node={creature.creature} empty='a vanished creature' />}
      caption={`Creature of ${creature.god?.name ?? 'a god'} since epoch ${creature.since_epoch} · ${plural(creature.deeds, 'deed', 'deeds')}`}
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => release.mutate()}
        >
          <Unlink />
          Set free
        </Button>
      }
    >
      <Meter label='Hunger' value={creature.hunger} tone='warning' />
      <Facts
        items={[
          ['God', <Ref key='god' node={creature.god} />],
          ['Last deed', last?.label ?? 'None yet'],
          ['Epochs neglected', String(creature.neglect_epochs)],
          ['Deeds done', String(creature.deeds)],
        ]}
      />
      <Label variant='overline'>Leanings and lessons</Label>
      <ul className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-2'>
        <Paged items={creature.weights} as='li'>
          {(row) => (
            <DeedRow
              key={row.deed}
              creature={creature}
              deed={row.deed}
              weight={row.weight}
              blocked={busy}
            />
          )}
        </Paged>
      </ul>
      <Label variant='overline'>{`Lessons taught (${creature.lessons.length})`}</Label>
      {creature.lessons.length === 0 ? (
        <Muted variant='caption'>
          Its god has not yet rewarded or punished it.
        </Muted>
      ) : (
        <PagedList
          items={creature.lessons}
          initial={6}
          noun={['lesson', 'lessons']}
          className='flex min-w-0 flex-col gap-1.5'
          itemKey={(lesson) => lesson.id}
        >
          {(lesson) => (
            <li className='flex min-w-0 flex-wrap items-center gap-1.5'>
              <Chip icon={LESSONS[lesson.lesson].icon}>
                {LESSONS[lesson.lesson].label}
              </Chip>
              <Chip icon={DEEDS[lesson.deed].icon}>
                {DEEDS[lesson.deed].label}
              </Chip>
              <Muted variant='caption'>{`strength ${lesson.strength} · epoch ${lesson.epoch}`}</Muted>
            </li>
          )}
        </PagedList>
      )}
      <RecordEditor
        title='Reshape this creature'
        note='Values you set are held against the engine until you release them.'
        fields={[
          { key: 'hunger', label: 'Hunger', kind: 'number', min: 0, max: 100 },
          {
            key: 'neglect_epochs',
            label: 'Epochs neglected',
            kind: 'number',
            min: 0,
          },
          {
            key: 'last_deed',
            label: 'Last deed',
            kind: 'pick',
            table: table(DEEDS),
          },
        ]}
        locked={creature.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(keys) => edit.mutate({ values: {}, release: keys })}
      />
    </RecordRow>
  )
}

export function MiracleCard({
  miracle,
  blocked,
}: {
  miracle: MiracleView
  blocked: string | null
}) {
  const [credit, setCredit] = useState<number | null>(null)
  const edit = useDominionAction(
    'miracle_record:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({
      miracle_id: miracle.id,
      ...vars,
    }),
    'The miracle is remembered so'
  )
  const remove = useDominionAction(
    'miracle_record:delete',
    (_: void) => ({ miracle_id: miracle.id }),
    'The miracle is struck from memory'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const misread =
    miracle.credited !== null && miracle.credited.id !== miracle.god?.id
  return (
    <RecordRow
      icon={misread ? Unlink : Gem}
      tone={misread ? 'warning' : 'gold'}
      title={miracle.kind.replaceAll('_', ' ')}
      caption={`Epoch ${miracle.epoch} · ${plural(miracle.witnesses, 'witness', 'witnesses')} · belief ${miracle.belief}`}
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <Trash2 />
          Forget
        </Button>
      }
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <Meter label='Magnitude' value={miracle.magnitude} tone='default' />
        <Meter label='Need' value={miracle.need} tone='warning' />
        <Meter label='Novelty' value={miracle.novelty} tone='info' />
        <Meter label='Legibility' value={miracle.legibility} tone='verdigris' />
      </div>
      <Facts
        items={[
          ['Worked by', <Ref key='god' node={miracle.god} />],
          [
            'Credited to',
            <Ref key='credited' node={miracle.credited} empty='no god' />,
          ],
          ['Upon', <Ref key='target' node={miracle.target} empty='the land' />],
          [
            'Region',
            <Ref key='region' node={miracle.region} empty='no region' />,
          ],
          ['Witnesses', String(miracle.witnesses)],
          ['Belief won', String(miracle.belief)],
        ]}
      />
      {misread && (
        <Muted variant='caption'>
          Its witnesses gave the credit to another god.
        </Muted>
      )}
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <NodePicker
          label='Credit it to'
          value={credit}
          onChange={setCredit}
          blocked={busy}
          kinds={GOD_KINDS}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || credit === null}
          disabledReason={
            busy ?? (credit === null ? 'Choose a god first' : undefined)
          }
          onClick={() => {
            edit.mutate({ values: { credited_node_id: credit }, release: [] })
            setCredit(null)
          }}
        >
          <UserCheck />
          Give the credit
        </Button>
      </div>
      <RecordEditor
        title='Reshape this miracle'
        note='Values you set are held against the engine until you release them.'
        fields={[
          {
            key: 'magnitude',
            label: 'Magnitude',
            kind: 'number',
            min: 0,
            max: 100,
          },
          { key: 'witnesses', label: 'Witnesses', kind: 'number', min: 0 },
          { key: 'need', label: 'Need', kind: 'number', min: 0, max: 100 },
          {
            key: 'novelty',
            label: 'Novelty',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'legibility',
            label: 'Legibility',
            kind: 'number',
            min: 0,
            max: 100,
          },
          { key: 'belief', label: 'Belief won', kind: 'number', min: 0 },
        ]}
        locked={miracle.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}
