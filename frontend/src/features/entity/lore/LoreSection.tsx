import { useState } from 'react'
import {
  BookOpen,
  Check,
  Feather,
  Gem,
  Hammer,
  Languages,
  Lightbulb,
  Palette,
  Plus,
  ScrollText,
  Sparkles,
  Trash2,
  TriangleAlert,
  Users,
  Wand2,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  artMediumValues,
  backlashKindValues,
  curseKindValues,
  ideologyTenetValues,
  itemClassValues,
  legendArchetypeValues,
  magicSchoolValues,
  magicSourceValues,
  prophecyPredicateValues,
  riteEffectKindValues,
  traditionKindValues,
} from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { DictField, type FieldSpec, LoreFields } from './LoreFields'
import { type LoreCard, table, useLore, words } from './api'
import { type LoreKind, PERCENT, busyOf } from './model'

type Ref = { id: number; name: string } | null | undefined
type Card<K extends keyof LoreCard> = NonNullable<LoreCard[K]>
const COMMUNITIES = [
  'settlement',
  'people',
  'cult',
  'faction',
  'polity',
] as const
const VALUE_AXES = [
  'honour',
  'tradition',
  'hierarchy',
  'martial',
  'piety',
  'purity',
  'kinship',
  'mercy',
  'knowledge',
  'wealth',
  'nature',
  'superstition',
  'xenophilia',
  'death',
] as const

function Name({ item }: { item: Ref }) {
  if (!item) return <Muted as='span'>unknown</Muted>
  return (
    <EntityLink kind='entity' id={String(item.id)}>
      {item.name}
    </EntityLink>
  )
}

function NumberCell({
  label,
  value,
  blocked,
  onSave,
  min = 0,
  max = PERCENT,
}: {
  label: string
  value: number
  blocked: string | null
  onSave: (value: number) => void
  min?: number
  max?: number
}) {
  const [draft, setDraft] = useState(String(value))
  return (
    <div className='flex items-center gap-1'>
      <Input
        className='w-20'
        type='number'
        min={min}
        max={max}
        value={draft}
        aria-label={label}
        onChange={(event) => setDraft(event.target.value)}
      />
      <Button
        size='icon'
        variant='ghost'
        aria-label={`Set ${label}`}
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={() => onSave(Math.round(Number(draft) || 0))}
      >
        <Check />
      </Button>
    </div>
  )
}

function LanguagePanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'language'>
  blocked: string | null
}) {
  const [community, setCommunity] = useState<number | null>(null)
  const speakers = useGodAction<{
    community: number
    share: number
    kind: string
  }>({
    run: ({ community: target, share, kind }) =>
      unwrap(
        api.POST('/api/actions/language:speakers', {
          body: {
            community_id: target,
            language_id: id,
            kind: kind as 'second',
            share,
          },
        })
      ),
  })
  const kin = useGodAction<{ other: number; value: number }>({
    run: ({ other, value }) =>
      unwrap(
        api.POST('/api/actions/language:intelligibility', {
          body: { first_id: id, second_id: other, value },
        })
      ),
  })
  const busy = busyOf(blocked, speakers.isPending, kin.isPending)
  const fields: FieldSpec[] = [
    { key: 'prestige', kind: 'number', min: 0, max: PERCENT },
    { key: 'standardisation', kind: 'number', min: 0, max: PERCENT },
    { key: 'liturgical', kind: 'bool' },
    { key: 'lingua_franca', kind: 'bool' },
  ]
  return (
    <div
      data-surface='LanguageStanding'
      className='flex min-w-0 flex-col gap-3'
    >
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        <KpiTile
          label='Prestige'
          value={card.prestige}
          icon={Sparkles}
          meter={{ value: card.prestige, max: PERCENT, label: 'prestige' }}
        />
        <KpiTile
          label='Standard'
          value={card.standardisation}
          icon={BookOpen}
          tone='verdigris'
        />
        <KpiTile
          label='Speakers'
          value={card.speakers.length}
          icon={Users}
          tone='info'
        />
        <KpiTile
          label='Kin tongues'
          value={card.kin.length}
          icon={Languages}
          tone='muted'
        />
      </div>
      <ul data-surface='PrestigeParts' className='flex min-w-0 flex-wrap gap-2'>
        {Object.entries(card.prestige_parts).map(([part, value]) => (
          <li key={part}>
            <Badge variant='outline'>{`${part}: +${value}`}</Badge>
          </li>
        ))}
        {card.liturgical && <Badge variant='info'>liturgical</Badge>}
        {card.lingua_franca && <Badge variant='info'>lingua franca</Badge>}
      </ul>
      <LoreFields
        entityId={id}
        surface='LanguageForm'
        fields={fields}
        current={card}
        locked={card.locked}
        blocked={blocked}
      />
      <div
        data-surface='SpeakerCohorts'
        className='flex min-w-0 flex-col gap-2'
      >
        <Label variant='overline'>Who speaks it</Label>
        {card.speakers.length === 0 && (
          <Muted>No community has taken it as a second tongue.</Muted>
        )}
        <ul className='flex min-w-0 flex-col gap-2'>
          {card.speakers.map((row) => (
            <li
              key={`${row.community?.id}.${row.kind}`}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <Name item={row.community} />
              <Badge variant='outline'>{words(row.kind)}</Badge>
              <StatBar label='share' value={row.share} max={PERCENT} />
              <NumberCell
                label='share of speakers'
                value={row.share}
                blocked={busy}
                onSave={(share) =>
                  speakers.mutate({
                    community: row.community?.id ?? 0,
                    share,
                    kind: row.kind,
                  })
                }
              />
            </li>
          ))}
        </ul>
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <EntityPicker
            types={COMMUNITIES}
            value={community}
            onChange={setCommunity}
            placeholder='Teach it to…'
          />
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || community === null}
            disabledReason={
              busy ?? (community === null ? 'Choose a community' : undefined)
            }
            onClick={() =>
              speakers.mutate({
                community: community ?? 0,
                share: 10,
                kind: 'second',
              })
            }
          >
            <Plus />
            Teach the tongue
          </Button>
        </div>
      </div>
      <div
        data-surface='Intelligibility'
        className='flex min-w-0 flex-col gap-2'
      >
        <Label variant='overline'>Understood by</Label>
        <ul className='flex min-w-0 flex-col gap-2'>
          {card.kin.map((row) => (
            <li
              key={row.language?.id}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <Name item={row.language} />
              <StatBar label='understanding' value={row.value} max={PERCENT} />
              <NumberCell
                label='intelligibility'
                value={row.value}
                blocked={busy}
                onSave={(value) =>
                  kin.mutate({ other: row.language?.id ?? 0, value })
                }
              />
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function LegendPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'legend'>
  blocked: string | null
}) {
  return (
    <div data-surface='LegendCard' className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-3'>
        <KpiTile
          label='Believed'
          value={`${card.credence}%`}
          icon={Sparkles}
          meter={{ value: card.credence, max: PERCENT, label: 'credence' }}
        />
        <KpiTile
          label='Distorted'
          value={`${card.distortion}%`}
          icon={Feather}
          tone='warning'
        />
        <KpiTile
          label='Tellers'
          value={card.tellers.length}
          icon={Users}
          tone='info'
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge variant='info'>{words(card.archetype)}</Badge>
        {card.subject && (
          <Text as='span'>
            tells of <Name item={card.subject} />
          </Text>
        )}
        {card.fixed_in && (
          <Text as='span'>
            written down in <Name item={card.fixed_in} />
          </Text>
        )}
      </div>
      <ul className='flex min-w-0 flex-wrap gap-2'>
        {card.tellers.map((teller) => (
          <li key={teller.id}>
            <Name item={teller} />
          </li>
        ))}
      </ul>
      <LoreFields
        entityId={id}
        surface='LegendForm'
        fields={[
          { key: 'archetype', kind: 'enum', values: legendArchetypeValues },
          { key: 'credence', kind: 'number', min: 0, max: PERCENT },
          { key: 'distortion', kind: 'number', min: 0, max: PERCENT },
        ]}
        current={card}
        locked={card.locked}
        blocked={blocked}
      />
      <DictField
        entityId={id}
        spec={{
          key: 'moral',
          label: 'The moral it teaches',
          value: card.moral,
        }}
        blocked={blocked}
        suggestions={VALUE_AXES}
      />
    </div>
  )
}

function TraditionPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'tradition'>
  blocked: string | null
}) {
  const keep = useGodAction<{ community: number; value: number }>({
    run: ({ community, value }) =>
      unwrap(
        api.POST('/api/actions/tradition:participation', {
          body: {
            tradition_id: id,
            community_id: community,
            participation: value,
          },
        })
      ),
  })
  const busy = busyOf(blocked, keep.isPending)
  return (
    <div data-surface='TraditionCard' className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge variant='info'>{words(card.kind)}</Badge>
        {card.taboo_target && (
          <Badge variant='destructive'>{`taboo: ${words(card.taboo_target)}`}</Badge>
        )}
        {card.origin && (
          <Text as='span'>
            remembers <Name item={card.origin} />
          </Text>
        )}
      </div>
      <LoreFields
        entityId={id}
        surface='TraditionForm'
        fields={[
          { key: 'kind', kind: 'enum', values: traditionKindValues },
          { key: 'calendar_slot', kind: 'text', nullable: true },
          { key: 'taboo_target', kind: 'text', nullable: true },
        ]}
        current={card}
        locked={card.locked}
        blocked={blocked}
      />
      <DictField
        entityId={id}
        spec={{ key: 'cost', label: 'What it costs', value: card.cost }}
        blocked={blocked}
        suggestions={['food', 'goods']}
      />
      <DictField
        entityId={id}
        spec={{ key: 'effects', label: 'What it brings', value: card.effects }}
        blocked={blocked}
      />
      <div
        data-surface='TraditionKeepers'
        className='flex min-w-0 flex-col gap-2'
      >
        <Label variant='overline'>Kept by</Label>
        {card.keepers.length === 0 && <Muted>No one keeps it any more.</Muted>}
        <ul className='flex min-w-0 flex-col gap-2'>
          {card.keepers.map((row) => (
            <li
              key={row.community?.id}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <Name item={row.community} />
              <StatBar
                label='keeps it'
                value={row.participation}
                max={PERCENT}
              />
              {row.skipped > 0 && (
                <Badge variant='warning'>{`skipped ${row.skipped}`}</Badge>
              )}
              <NumberCell
                label='participation'
                value={row.participation}
                blocked={busy}
                onSave={(value) =>
                  keep.mutate({ community: row.community?.id ?? 0, value })
                }
              />
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function IdeologyPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'ideology'>
  blocked: string | null
}) {
  const [tenet, setTenet] = useState('')
  const [community, setCommunity] = useState<number | null>(null)
  const teach = useGodAction<{ tenet: string; held: boolean }>({
    run: ({ tenet: chosen, held }) =>
      unwrap(
        api.POST('/api/actions/creed:tenet', {
          body: { ideology_id: id, tenet: chosen as 'legalism', held },
        })
      ),
  })
  const adhere = useGodAction<{
    community: number
    strength: number
    state: boolean
  }>({
    run: ({ community: target, strength, state }) =>
      unwrap(
        api.POST('/api/actions/creed:adherent', {
          body: { ideology_id: id, community_id: target, strength, state },
        })
      ),
  })
  const busy = busyOf(blocked, teach.isPending, adhere.isPending)
  return (
    <div data-surface='IdeologyCard' className='flex min-w-0 flex-col gap-3'>
      {card.founder && (
        <Text as='span'>
          taught by <Name item={card.founder} />
        </Text>
      )}
      <ul data-surface='CreedTenets' className='flex min-w-0 flex-wrap gap-2'>
        {card.tenets.map((item) => (
          <li key={item} className='flex items-center gap-1'>
            <Badge variant='info'>{words(item)}</Badge>
            <Button
              size='icon'
              variant='ghost'
              aria-label={`Cast off ${words(item)}`}
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => teach.mutate({ tenet: item, held: false })}
            >
              <X />
            </Button>
          </li>
        ))}
      </ul>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <MindPicker
          label='Teach'
          value={tenet}
          table={table(
            ideologyTenetValues.filter((item) => !card.tenets.includes(item))
          )}
          blocked={busy}
          placeholder='Choose a tenet'
          onPick={setTenet}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || tenet === ''}
          disabledReason={busy ?? (tenet === '' ? 'Choose a tenet' : undefined)}
          onClick={() => teach.mutate({ tenet, held: true })}
        >
          <Plus />
          Teach it
        </Button>
      </div>
      <DictField
        entityId={id}
        spec={{
          key: 'value_delta',
          label: 'Values it presses',
          value: card.values,
        }}
        blocked={blocked}
        suggestions={VALUE_AXES}
      />
      <DictField
        entityId={id}
        spec={{ key: 'appeal', label: 'Who it calls to', value: card.appeal }}
        blocked={blocked}
        suggestions={[
          'farmer',
          'artisan',
          'merchant',
          'priest',
          'warrior',
          'scribe',
          'noble',
          'serf_or_slave',
          'outcast',
          'monastic',
        ]}
      />
      <div
        data-surface='CreedAdherents'
        className='flex min-w-0 flex-col gap-2'
      >
        <Label variant='overline'>Adherents</Label>
        <ul className='flex min-w-0 flex-col gap-2'>
          {card.adherents.map((row) => (
            <li
              key={row.community?.id}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <Name item={row.community} />
              <StatBar label='adherence' value={row.strength} max={PERCENT} />
              <label className='flex items-center gap-2'>
                <Switch
                  checked={row.state}
                  disabled={busy !== null}
                  aria-label='State creed'
                  onCheckedChange={(next) =>
                    adhere.mutate({
                      community: row.community?.id ?? 0,
                      strength: row.strength,
                      state: next,
                    })
                  }
                />
                <Text as='span'>state creed</Text>
              </label>
              <NumberCell
                label='adherence'
                value={row.strength}
                blocked={busy}
                onSave={(strength) =>
                  adhere.mutate({
                    community: row.community?.id ?? 0,
                    strength,
                    state: row.state,
                  })
                }
              />
            </li>
          ))}
        </ul>
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <EntityPicker
            types={COMMUNITIES}
            value={community}
            onChange={setCommunity}
            placeholder='Win over…'
          />
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || community === null}
            disabledReason={
              busy ?? (community === null ? 'Choose a community' : undefined)
            }
            onClick={() =>
              adhere.mutate({
                community: community ?? 0,
                strength: 25,
                state: false,
              })
            }
          >
            <Plus />
            Win them over
          </Button>
        </div>
      </div>
    </div>
  )
}

function RitePanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'rite'>
  blocked: string | null
}) {
  const [effect, setEffect] = useState('')
  const [caster, setCaster] = useState<number | null>(card.inventor?.id ?? null)
  const [target, setTarget] = useState<number | null>(null)
  const shape = useGodAction<{ effect: string; magnitude: number }>({
    run: ({ effect: chosen, magnitude }) =>
      unwrap(
        api.POST('/api/actions/rite:effect', {
          body: { rite_id: id, effect: chosen as 'heal', magnitude },
        })
      ),
  })
  const cast = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/rite:cast', {
          body: { rite_id: id, caster_id: caster ?? 0, target_id: target },
        })
      ),
  })
  const busy = busyOf(blocked, shape.isPending, cast.isPending)
  return (
    <div data-surface='RiteCard' className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        <KpiTile
          label='Power'
          value={card.power}
          icon={Wand2}
          meter={{ value: card.power, max: 10, label: 'power' }}
        />
        <KpiTile
          label='Backlash'
          value={`${card.backlash_chance}%`}
          icon={TriangleAlert}
          tone='danger'
          hint={words(card.backlash)}
        />
        <KpiTile
          label='School'
          value={words(card.school)}
          icon={Sparkles}
          tone='verdigris'
        />
        <KpiTile
          label='Drawn from'
          value={words(card.source)}
          icon={Gem}
          tone='info'
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        {card.holy && <Badge variant='info'>holy</Badge>}
        {card.heretical && <Badge variant='destructive'>heresy</Badge>}
        {Object.entries(card.cost).map(([key, value]) => (
          <Badge
            key={key}
            variant='outline'
          >{`costs ${value} ${words(key)}`}</Badge>
        ))}
        {Object.entries(card.requirements).map(([key, value]) => (
          <Badge
            key={key}
            variant='outline'
          >{`needs ${words(String(value))}`}</Badge>
        ))}
      </div>
      <LoreFields
        entityId={id}
        surface='RiteForm'
        fields={[
          { key: 'school', kind: 'enum', values: magicSchoolValues },
          { key: 'source', kind: 'enum', values: magicSourceValues },
          { key: 'backlash', kind: 'enum', values: backlashKindValues },
          { key: 'power', kind: 'number', min: 1, max: 10 },
          { key: 'backlash_chance', kind: 'number', min: 0, max: PERCENT },
          { key: 'holy', kind: 'bool' },
          { key: 'heretical', kind: 'bool' },
        ]}
        current={card}
        locked={card.locked}
        blocked={blocked}
      />
      <DictField
        entityId={id}
        spec={{ key: 'cost', label: 'Its price', value: card.cost }}
        blocked={blocked}
        suggestions={['ley', 'essence', 'blood', 'souls', 'reagents', 'sanity']}
      />
      <div data-surface='RiteEffects' className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>What it does</Label>
        <ul className='flex min-w-0 flex-col gap-2'>
          {card.effects.map((row) => (
            <li
              key={row.effect}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <Badge variant='info'>{words(row.effect)}</Badge>
              <NumberCell
                label='magnitude'
                value={row.magnitude}
                blocked={busy}
                onSave={(magnitude) =>
                  shape.mutate({ effect: row.effect, magnitude })
                }
              />
              <Button
                size='icon'
                variant='ghost'
                aria-label={`Remove ${words(row.effect)}`}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() =>
                  shape.mutate({ effect: row.effect, magnitude: 0 })
                }
              >
                <Trash2 />
              </Button>
            </li>
          ))}
        </ul>
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <MindPicker
            label='Add a working'
            value={effect}
            table={table(
              riteEffectKindValues.filter(
                (item) => !card.effects.some((row) => row.effect === item)
              )
            )}
            blocked={busy}
            placeholder='Choose'
            onPick={setEffect}
          />
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || effect === ''}
            disabledReason={
              busy ?? (effect === '' ? 'Choose a working' : undefined)
            }
            onClick={() => shape.mutate({ effect, magnitude: 3 })}
          >
            <Plus />
            Add
          </Button>
        </div>
      </div>
      <div
        data-surface='CastRite'
        className='flex min-w-0 flex-wrap items-end gap-2'
      >
        <EntityPicker
          types={['mortal', 'cult']}
          value={caster}
          onChange={setCaster}
          placeholder='Caster'
        />
        <EntityPicker
          types={['mortal', ...COMMUNITIES]}
          value={target}
          onChange={setTarget}
          placeholder='Target (optional)'
        />
        <Button
          size='sm'
          disabled={busy !== null || caster === null}
          disabledReason={
            busy ?? (caster === null ? 'Choose a caster' : undefined)
          }
          onClick={() => cast.mutate(undefined)}
        >
          <Wand2 />
          Work the rite
        </Button>
      </div>
      <div data-surface='Castings' className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Castings</Label>
        {card.castings.length === 0 ? (
          <Muted>It has never been worked.</Muted>
        ) : (
          <Timeline label='Castings'>
            {card.castings.map((row, index) => (
              <TimelineItem
                key={row.id}
                icon={row.succeeded ? Sparkles : TriangleAlert}
                tone={row.succeeded ? 'default' : 'destructive'}
                title={row.effect || 'worked'}
                timestamp={`epoch ${row.epoch}`}
                last={index === card.castings.length - 1}
              >
                <Muted>
                  {row.caster?.name ?? 'someone'}
                  {row.target ? ` against ${row.target.name}` : ''}
                  {row.backlash ? `, backlash: ${words(row.backlash)}` : ''}
                </Muted>
              </TimelineItem>
            ))}
          </Timeline>
        )}
      </div>
    </div>
  )
}

function ProphecyPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'prophecy'>
  blocked: string | null
}) {
  const settle = useGodAction<boolean>({
    run: (fulfilled) =>
      unwrap(
        api.POST('/api/actions/prophecy:resolve', {
          body: { prophecy_id: id, fulfilled },
        })
      ),
  })
  const busy = busyOf(blocked, settle.isPending)
  const pending = card.state === 'pending'
  return (
    <div data-surface='ProphecyCard' className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-3'>
        <KpiTile
          label='Foretells'
          value={words(card.predicate)}
          icon={ScrollText}
        />
        <KpiTile
          label='Pressure'
          value={`${card.pressure}%`}
          icon={Sparkles}
          tone='warning'
          meter={{ value: card.pressure, max: PERCENT, label: 'pressure' }}
        />
        <KpiTile
          label='Deadline'
          value={card.deadline_epoch ?? 'none'}
          icon={TriangleAlert}
          tone='muted'
          hint={words(card.state)}
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {card.seer && (
          <Text as='span'>
            seen by <Name item={card.seer} />
          </Text>
        )}
        {card.audience.map((item) => (
          <Name key={item.id} item={item} />
        ))}
      </div>
      <LoreFields
        entityId={id}
        surface='ProphecyForm'
        fields={[
          { key: 'predicate', kind: 'enum', values: prophecyPredicateValues },
          { key: 'deadline_epoch', kind: 'number', min: 0, nullable: true },
          { key: 'pressure', kind: 'number', min: 0, max: PERCENT },
        ]}
        current={card}
        locked={card.locked}
        blocked={blocked}
      />
      <DictField
        entityId={id}
        spec={{
          key: 'args',
          label: 'What exactly must happen',
          value: card.args,
        }}
        blocked={blocked}
      />
      {pending && (
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => settle.mutate(true)}
          >
            <Check />
            Let it come true
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => settle.mutate(false)}
          >
            <X />
            Let it fail
          </Button>
        </div>
      )}
    </div>
  )
}

function ItemPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'item'>
  blocked: string | null
}) {
  const [effect, setEffect] = useState('')
  const enchant = useGodAction<{ effect: string; strength: number }>({
    run: ({ effect: chosen, strength }) =>
      unwrap(
        api.POST('/api/actions/item:enchant', {
          body: { item_id: id, effect: chosen as 'ward', strength },
        })
      ),
  })
  const busy = busyOf(blocked, enchant.isPending)
  return (
    <div data-surface='ItemCard' className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        <KpiTile
          label='Quality'
          value={card.quality}
          icon={Hammer}
          meter={{ value: card.quality, max: PERCENT, label: 'quality' }}
        />
        <KpiTile
          label='Condition'
          value={card.condition}
          icon={TriangleAlert}
          tone={card.condition < 20 ? 'danger' : 'success'}
        />
        <KpiTile
          label='Renown'
          value={card.renown}
          icon={Sparkles}
          tone='gold'
          hint={card.symbol ? 'a symbol' : undefined}
        />
        <KpiTile label='Worth' value={card.value} icon={Gem} tone='info' />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge variant='info'>{words(card.item_class)}</Badge>
        {card.curse !== 'none' && (
          <Badge variant='destructive'>{`cursed: ${words(card.curse)}`}</Badge>
        )}
        {card.maker && (
          <Text as='span'>
            made by <Name item={card.maker} />
          </Text>
        )}
        {card.owner && (
          <Text as='span'>
            held by <Name item={card.owner} />
          </Text>
        )}
        {card.regalia_of && (
          <Text as='span'>
            regalia of <Name item={card.regalia_of} />
          </Text>
        )}
      </div>
      <LoreFields
        entityId={id}
        surface='ItemForm'
        fields={[
          { key: 'item_class', kind: 'enum', values: itemClassValues },
          { key: 'curse', kind: 'enum', values: curseKindValues },
          { key: 'material', kind: 'text', nullable: true },
          { key: 'quality', kind: 'number', min: 0, max: PERCENT },
          { key: 'condition', kind: 'number', min: 0, max: PERCENT },
          { key: 'renown', kind: 'number', min: 0, max: PERCENT },
          { key: 'value', kind: 'number', min: 0 },
          { key: 'reach', kind: 'number', min: 0 },
          { key: 'coverage', kind: 'number', min: 0 },
          { key: 'weight', kind: 'number', min: 0 },
          { key: 'symbol', kind: 'bool' },
        ]}
        current={card}
        locked={card.locked}
        blocked={blocked}
      />
      <div data-surface='Enchantments' className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Enchantments</Label>
        <ul className='flex min-w-0 flex-col gap-2'>
          {card.enchantments.map((row) => (
            <li
              key={row.effect}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <Badge variant='info'>{words(row.effect)}</Badge>
              <StatBar label='strength' value={row.strength} max={PERCENT} />
              <NumberCell
                label='strength'
                value={row.strength}
                blocked={busy}
                onSave={(strength) =>
                  enchant.mutate({ effect: row.effect, strength })
                }
              />
            </li>
          ))}
        </ul>
        <div className='flex min-w-0 flex-wrap items-end gap-2'>
          <MindPicker
            label='Enchant with'
            value={effect}
            table={table(
              riteEffectKindValues.filter(
                (item) => !card.enchantments.some((row) => row.effect === item)
              )
            )}
            blocked={busy}
            placeholder='Choose'
            onPick={setEffect}
          />
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || effect === ''}
            disabledReason={
              busy ?? (effect === '' ? 'Choose an enchantment' : undefined)
            }
            onClick={() => enchant.mutate({ effect, strength: 20 })}
          >
            <Sparkles />
            Enchant
          </Button>
        </div>
      </div>
      {card.contents.length > 0 && (
        <div
          data-surface='BookContents'
          className='flex min-w-0 flex-wrap items-center gap-2'
        >
          <Label variant='overline'>Written within</Label>
          {card.contents.map((item) => (
            <Name key={item.id} item={item} />
          ))}
        </div>
      )}
      <div data-surface='ItemHistory' className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Its story</Label>
        {card.history.length === 0 ? (
          <Muted>Nothing has befallen it yet.</Muted>
        ) : (
          <Timeline label='Item history'>
            {card.history.map((row, index) => (
              <TimelineItem
                key={`${row.epoch}.${index}`}
                icon={
                  row.deed === 'broken' || row.deed === 'lost'
                    ? TriangleAlert
                    : Gem
                }
                tone={
                  row.deed === 'broken' || row.deed === 'lost'
                    ? 'destructive'
                    : 'default'
                }
                title={words(row.deed)}
                timestamp={`epoch ${row.epoch}`}
                last={index === card.history.length - 1}
              >
                <Muted>{row.note}</Muted>
              </TimelineItem>
            ))}
          </Timeline>
        )}
      </div>
    </div>
  )
}

function ArtworkPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'artwork'>
  blocked: string | null
}) {
  return (
    <div data-surface='ArtworkCard' className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-3'>
        <KpiTile
          label='Quality'
          value={card.quality}
          icon={Palette}
          meter={{ value: card.quality, max: PERCENT, label: 'quality' }}
        />
        <KpiTile
          label='Copies'
          value={card.copies}
          icon={BookOpen}
          tone='info'
        />
        <KpiTile
          label='Translations'
          value={card.translations.length}
          icon={Languages}
          tone='verdigris'
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge variant='info'>{words(card.medium)}</Badge>
        {card.propaganda && <Badge variant='warning'>propaganda</Badge>}
        {card.author && (
          <Text as='span'>
            by <Name item={card.author} />
          </Text>
        )}
        {card.subject && (
          <Text as='span'>
            of <Name item={card.subject} />
          </Text>
        )}
        {card.patron && (
          <Text as='span'>
            for <Name item={card.patron} />
          </Text>
        )}
        {card.language && (
          <Text as='span'>
            in <Name item={card.language} />
          </Text>
        )}
      </div>
      <LoreFields
        entityId={id}
        surface='ArtworkForm'
        fields={[
          { key: 'medium', kind: 'enum', values: artMediumValues },
          { key: 'quality', kind: 'number', min: 0, max: PERCENT },
          { key: 'copies', kind: 'number', min: 0 },
          { key: 'performed', kind: 'bool' },
          { key: 'propaganda', kind: 'bool' },
        ]}
        current={card}
        locked={card.locked}
        blocked={blocked}
      />
      <DictField
        entityId={id}
        spec={{ key: 'message', label: 'What it stirs', value: card.message }}
        blocked={blocked}
        suggestions={VALUE_AXES}
      />
    </div>
  )
}

const ICONS: Record<LoreKind, typeof Languages> = {
  language: Languages,
  legend: Feather,
  tradition: Users,
  ideology: Lightbulb,
  rite: Wand2,
  prophecy: ScrollText,
  item: Gem,
  artwork: Palette,
}

function Body({ card, blocked }: { card: LoreCard; blocked: string | null }) {
  const id = card.entity_id
  if (card.language)
    return <LanguagePanel id={id} card={card.language} blocked={blocked} />
  if (card.legend)
    return <LegendPanel id={id} card={card.legend} blocked={blocked} />
  if (card.tradition)
    return <TraditionPanel id={id} card={card.tradition} blocked={blocked} />
  if (card.ideology)
    return <IdeologyPanel id={id} card={card.ideology} blocked={blocked} />
  if (card.rite) return <RitePanel id={id} card={card.rite} blocked={blocked} />
  if (card.prophecy)
    return <ProphecyPanel id={id} card={card.prophecy} blocked={blocked} />
  if (card.item) return <ItemPanel id={id} card={card.item} blocked={blocked} />
  if (card.artwork)
    return <ArtworkPanel id={id} card={card.artwork} blocked={blocked} />
  return (
    <Muted>
      The world has not yet given it a story; it will after the next epoch.
    </Muted>
  )
}

export function LoreSection({
  entityId,
  kind,
  readOnlyReason,
}: {
  entityId: number
  kind: LoreKind
  readOnlyReason?: string | null
}) {
  const view = useLore(entityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  return (
    <Section
      id='section-lore'
      title={`The ${words(kind)}'s story`}
      description='How it lives in the world, and every value you may set.'
      icon={ICONS[kind]}
    >
      {view.isPending && <Muted>Reading the record…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The record could not be read'
          description={view.error.message}
        />
      )}
      {view.data && <Body card={view.data} blocked={blocked} />}
    </Section>
  )
}
