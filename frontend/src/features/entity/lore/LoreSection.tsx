import { useState } from 'react'
import {
  BadgeCheck,
  Book,
  BookOpen,
  CalendarDays,
  Check,
  Coins,
  Crown,
  Eye,
  Feather,
  Flag,
  Gauge,
  Gem,
  Hammer,
  Hand,
  HeartPulse,
  History,
  Hourglass,
  Languages,
  Megaphone,
  Mic,
  PenLine,
  Plus,
  Ruler,
  ScrollText,
  Shield,
  Sparkles,
  Sprout,
  Target,
  Trash2,
  TriangleAlert,
  User,
  Users,
  Wand2,
  Weight,
  X,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  ChangeChip,
  EmptyState,
  KpiTile,
  type KpiTone,
  MiniStat,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AdjustBlock,
  ChoicePicker,
  DictField,
  LoreAdjust,
  LoreCard,
  LoreFields,
  LoreHero,
  MeterList,
  MeterRow,
  NamedChip,
  RefChip,
  RoleRow,
  RowEditor,
  RowEditors,
  ShiftChips,
  TermChips,
  Who,
} from './LoreFields'
import { type LoreCard as LoreCardData, useLore } from './api'
import {
  ARCHETYPES,
  BACKLASHES,
  CLASSES,
  CURSES,
  DEEDS,
  EFFECTS,
  ITEM_CLASSES,
  KPI_GRID,
  LORE_GRID,
  LORE_KIND,
  type LoreKind,
  MAX_POWER,
  MEDIUMS,
  PERCENT,
  PREDICATES,
  PROPHECY_ARGS,
  PROPHECY_STATES,
  RITE_COSTS,
  SCHOOLS,
  SOURCES,
  SPEAKER_KINDS,
  TENETS,
  TRADITION_KINDS,
  TRADITION_TERMS,
  VALUES,
  busyOf,
  lookup,
  sentence,
} from './model'

type Card<K extends keyof LoreCardData> = NonNullable<LoreCardData[K]>
const COMMUNITIES = [
  'settlement',
  'people',
  'cult',
  'faction',
  'polity',
] as const
const COST_ONLY = Object.fromEntries(
  ['food', 'goods'].map((key) => [key, TRADITION_TERMS[key]])
)
const ENTITY_ARGS = new Set([
  'entity',
  'settlement',
  'house',
  'first',
  'second',
  'polity',
  'chosen',
])
const WORN = 20
const WEARING = 50

function percentHint(value: number, high: string, low: string) {
  return value >= PERCENT / 2 ? high : low
}

function average(values: number[]): number {
  if (values.length === 0) return 0
  return Math.round(
    values.reduce((sum, value) => sum + value, 0) / values.length
  )
}

function wear(condition: number): KpiTone {
  if (condition < WORN) return 'danger'
  if (condition < WEARING) return 'warning'
  return 'success'
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
  const parts = Object.entries(card.prestige_parts)
  const near = card.kin
    .filter((row) => row.value > 0)
    .sort((left, right) => right.value - left.value)
  const far = card.kin.filter((row) => row.value <= 0)
  return (
    <div
      data-surface='LanguageStanding'
      className='flex min-w-0 flex-col gap-4'
    >
      <LoreHero
        spec={LORE_KIND.language}
        kicker='A living tongue'
        title={
          card.lingua_franca
            ? 'Tongue of the trade roads'
            : card.liturgical
              ? 'Tongue of worship'
              : 'A spoken tongue'
        }
        hint='Prestige draws learners to it; kin tongues understand it without a teacher.'
      >
        {card.lingua_franca && (
          <NamedChip
            spec={{ label: 'Lingua franca', icon: Coins, tone: 'gold' }}
          />
        )}
        {card.liturgical && <NamedChip spec={SPEAKER_KINDS.liturgical} />}
        {!card.lingua_franca && !card.liturgical && (
          <NamedChip
            spec={{ label: 'Everyday speech', icon: Mic, tone: 'muted' }}
          />
        )}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Prestige'
          value={card.prestige}
          icon={Crown}
          hint='The power of its speakers, its literature and its holiness'
          meter={{ value: card.prestige, max: PERCENT, label: 'Prestige' }}
        />
        <KpiTile
          label='Standardisation'
          value={card.standardisation}
          icon={BookOpen}
          tone='verdigris'
          hint='Grammar schools fix its forms year by year'
          meter={{
            value: card.standardisation,
            max: PERCENT,
            label: 'Standardisation',
          }}
        />
        <KpiTile
          label='Speaking peoples'
          value={card.speakers.length}
          icon={Users}
          tone='info'
          hint='Communities that speak it as a first or second tongue'
        />
        <KpiTile
          label='Kin tongues'
          value={near.length}
          icon={Languages}
          tone={near.length > 0 ? 'verdigris' : 'muted'}
          hint={
            far.length > 0
              ? `Tongues that understand some of it; ${far.length} more share no word`
              : 'Tongues that understand some of it'
          }
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard
          title='Who speaks it'
          icon={Users}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.speakers.length}</Badge>}
        >
          {card.speakers.length === 0 ? (
            <Muted>No community has taken it as a second tongue.</Muted>
          ) : (
            <MeterList surface='SpeakerCohorts'>
              {card.speakers.map((row) => {
                const kind = lookup(SPEAKER_KINDS, row.kind)
                return (
                  <MeterRow
                    key={`${row.community?.id}.${row.kind}`}
                    item={row.community}
                    label={`Share of its people, since epoch ${row.since_epoch}`}
                    value={row.share}
                    icon={kind.icon}
                    tone={kind.tone}
                  >
                    <NamedChip spec={kind} />
                  </MeterRow>
                )
              })}
            </MeterList>
          )}
        </LoreCard>
        <LoreCard title='Where its prestige comes from' icon={Crown} wide>
          {parts.length === 0 ? (
            <Muted>Nothing lends it standing yet.</Muted>
          ) : (
            <ul
              data-surface='PrestigeParts'
              className='flex min-w-0 flex-wrap gap-1.5'
            >
              {parts.map(([part, value]) => (
                <li key={part}>
                  <ChangeChip value={value} label={sentence(part)} />
                </li>
              ))}
            </ul>
          )}
        </LoreCard>
        <LoreCard
          title='Understood by'
          icon={Languages}
          tone='verdigris'
          wide
          aside={<Badge variant='secondary'>{card.kin.length}</Badge>}
        >
          {card.kin.length === 0 ? (
            <Muted>No other tongue makes sense of it.</Muted>
          ) : (
            <div
              data-surface='Intelligibility'
              className='flex min-w-0 flex-col gap-3'
            >
              {near.length > 0 && (
                <MeterList surface='KinNear'>
                  {near.map((row) => (
                    <MeterRow
                      key={row.language?.id}
                      item={row.language}
                      label='How much its speakers understand'
                      value={row.value}
                      icon={Languages}
                      tone='verdigris'
                    />
                  ))}
                </MeterList>
              )}
              {far.length > 0 && (
                <div className='flex min-w-0 flex-col gap-1.5'>
                  <Label>{`No word in common with ${far.length}`}</Label>
                  <ul className='flex min-w-0 flex-wrap gap-1.5'>
                    {far.map((row) => (
                      <li key={row.language?.id}>
                        <RefChip
                          icon={Languages}
                          label=''
                          item={row.language}
                        />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='tongue'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='Standing' icon={Crown}>
          <LoreFields
            entityId={id}
            surface='LanguageForm'
            fields={[
              { key: 'prestige', kind: 'number', min: 0, max: PERCENT },
              { key: 'standardisation', kind: 'number', min: 0, max: PERCENT },
              { key: 'liturgical', kind: 'bool' },
              { key: 'lingua_franca', kind: 'bool' },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='Speakers' icon={Users}>
          {card.speakers.length > 0 && (
            <RowEditors>
              {card.speakers.map((row) => (
                <RowEditor
                  key={`${row.community?.id}.${row.kind}`}
                  label={`${row.community?.name ?? 'Unknown'} share`}
                  icon={lookup(SPEAKER_KINDS, row.kind).icon}
                  value={row.share}
                  max={PERCENT}
                  blocked={busy}
                  onSave={(share) =>
                    speakers.mutate({
                      community: row.community?.id ?? 0,
                      share,
                      kind: row.kind,
                    })
                  }
                />
              ))}
            </RowEditors>
          )}
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
        </AdjustBlock>
        {card.kin.length > 0 && (
          <AdjustBlock title='Understanding' icon={Languages}>
            <RowEditors>
              {card.kin.map((row) => (
                <RowEditor
                  key={row.language?.id}
                  label={`${row.language?.name ?? 'Unknown'} understanding`}
                  icon={Languages}
                  value={row.value}
                  max={PERCENT}
                  blocked={busy}
                  onSave={(value) =>
                    kin.mutate({ other: row.language?.id ?? 0, value })
                  }
                />
              ))}
            </RowEditors>
          </AdjustBlock>
        )}
      </LoreAdjust>
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
  const archetype = lookup(ARCHETYPES, card.archetype)
  return (
    <div data-surface='LegendCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero spec={archetype} kicker='A tale told'>
        <RefChip icon={Target} label='Tells of' item={card.subject} />
        {card.fixed_in ? (
          <RefChip icon={Book} label='Written in' item={card.fixed_in} />
        ) : (
          <NamedChip
            spec={{
              label: 'Only spoken, so it drifts',
              icon: Mic,
              tone: 'warning',
            }}
          />
        )}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Believed'
          value={`${card.credence}%`}
          icon={Sparkles}
          hint={percentHint(
            card.credence,
            'Widely held true; strong belief lets it take shape in the world',
            'Doubted; each telling adds belief, each quiet epoch takes some'
          )}
          meter={{ value: card.credence, max: PERCENT, label: 'Belief' }}
        />
        <KpiTile
          label='Distorted'
          value={`${card.distortion}%`}
          icon={Feather}
          tone='warning'
          hint='Grows with each telling among the unlettered; writing holds it'
          meter={{ value: card.distortion, max: PERCENT, label: 'Distortion' }}
        />
        <KpiTile
          label='Tellers'
          value={card.tellers.length}
          icon={Users}
          tone='info'
          hint='Peoples who tell it; its moral presses on them'
        />
        <KpiTile
          label='Kept as'
          value={card.fixed_in ? 'Written' : 'Spoken'}
          icon={card.fixed_in ? Book : Mic}
          tone={card.fixed_in ? 'success' : 'muted'}
          hint={
            card.fixed_in
              ? `Set down in ${card.fixed_in.name}`
              : 'No book holds it yet'
          }
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='The moral it teaches' icon={Sprout} tone='success'>
          <ShiftChips
            entries={card.moral}
            table={VALUES}
            empty='It teaches nothing in particular.'
          />
          <Muted variant='caption'>
            The more it is believed, the harder these values press on its
            tellers.
          </Muted>
        </LoreCard>
        <LoreCard
          title='Told by'
          icon={Users}
          tone='info'
          aside={<Badge variant='secondary'>{card.tellers.length}</Badge>}
        >
          {card.tellers.length === 0 ? (
            <Muted>No one tells it any more.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-wrap gap-1.5'>
              {card.tellers.map((teller) => (
                <li key={teller.id}>
                  <RefChip icon={Users} label='' item={teller} />
                </li>
              ))}
            </ul>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='legend'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The tale' icon={Feather}>
          <LoreFields
            entityId={id}
            surface='LegendForm'
            fields={[
              { key: 'archetype', kind: 'enum', table: ARCHETYPES },
              { key: 'credence', kind: 'number', min: 0, max: PERCENT },
              { key: 'distortion', kind: 'number', min: 0, max: PERCENT },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='The moral it teaches' icon={Sprout}>
          <DictField
            entityId={id}
            spec={{ key: 'moral', label: 'The moral', value: card.moral }}
            blocked={blocked}
            table={VALUES}
          />
        </AdjustBlock>
      </LoreAdjust>
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
  const kind = lookup(TRADITION_KINDS, card.kind)
  const skipped = card.keepers.reduce((sum, row) => sum + row.skipped, 0)
  const kept = card.keepers
    .map((row) => row.last_celebrated_epoch)
    .filter((epoch): epoch is number => epoch !== null)
  return (
    <div data-surface='TraditionCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero spec={kind} kicker='A custom kept'>
        {card.calendar_slot && (
          <NamedChip spec={{ label: '', icon: CalendarDays, tone: 'info' }}>
            {`Kept at ${card.calendar_slot}`}
          </NamedChip>
        )}
        {card.in_season === true && (
          <NamedChip spec={{ label: '', icon: CalendarDays, tone: 'success' }}>
            Kept in its season
          </NamedChip>
        )}
        {card.in_season === false && (
          <NamedChip spec={{ label: '', icon: CalendarDays, tone: 'warning' }}>
            Drifted off its season
          </NamedChip>
        )}
        {card.calendar_entity_id != null && (
          <NamedChip
            spec={{ label: '', icon: CalendarDays, tone: 'verdigris' }}
          >
            Date fixed by a calendar
          </NamedChip>
        )}
        {card.taboo_target && (
          <NamedChip spec={TRADITION_KINDS.taboo}>
            {`Forbids ${card.taboo_target.replaceAll('_', ' ')}`}
          </NamedChip>
        )}
        <RefChip icon={History} label='Remembers' item={card.origin} />
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Kept by'
          value={card.keepers.length}
          icon={Users}
          tone='info'
          hint='Communities that keep it'
        />
        <KpiTile
          label='Devotion'
          value={`${average(card.keepers.map((row) => row.participation))}%`}
          icon={HeartPulse}
          tone='success'
          hint='How many of its keepers take part, on average'
          meter={{
            value: average(card.keepers.map((row) => row.participation)),
            max: PERCENT,
            label: 'Devotion',
          }}
        />
        <KpiTile
          label='Skipped'
          value={skipped}
          icon={TriangleAlert}
          tone={skipped > 0 ? 'warning' : 'muted'}
          hint='Times it was skipped in hunger; each costs cohesion'
        />
        <KpiTile
          label='Last kept'
          value={kept.length > 0 ? `Epoch ${Math.max(...kept)}` : 'Never'}
          icon={CalendarDays}
          tone='verdigris'
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='What it costs' icon={Coins} tone='warning'>
          <TermChips
            entries={card.cost}
            table={TRADITION_TERMS}
            empty='It costs nothing to keep.'
          />
        </LoreCard>
        <LoreCard title='What it brings' icon={Sparkles} tone='success'>
          <TermChips
            entries={card.effects}
            table={TRADITION_TERMS}
            empty='It brings nothing but habit.'
            unit={(key, value) =>
              `${lookup(TRADITION_TERMS, key).label} +${value}`
            }
          />
        </LoreCard>
        <LoreCard
          title='Kept by'
          icon={Users}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.keepers.length}</Badge>}
        >
          {card.keepers.length === 0 ? (
            <Muted>No one keeps it any more.</Muted>
          ) : (
            <MeterList surface='TraditionKeepers'>
              {card.keepers.map((row) => (
                <MeterRow
                  key={row.community?.id}
                  item={row.community}
                  label={
                    row.last_celebrated_epoch !== null
                      ? `Takes part · last kept in epoch ${row.last_celebrated_epoch}`
                      : 'Takes part'
                  }
                  value={row.participation}
                  icon={kind.icon}
                  tone={kind.tone}
                >
                  {row.skipped > 0 && (
                    <Badge size='sm' variant='warning'>
                      {`Skipped ${row.skipped}×`}
                    </Badge>
                  )}
                </MeterRow>
              ))}
            </MeterList>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='tradition'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The custom' icon={kind.icon}>
          <LoreFields
            entityId={id}
            surface='TraditionForm'
            fields={[
              { key: 'kind', kind: 'enum', table: TRADITION_KINDS },
              { key: 'calendar_slot', kind: 'text', nullable: true },
              {
                key: 'season_position',
                kind: 'number',
                min: 0,
                nullable: true,
              },
              {
                key: 'calendar_entity_id',
                kind: 'number',
                min: 1,
                nullable: true,
              },
              { key: 'taboo_target', kind: 'text', nullable: true },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <div className={LORE_GRID}>
          <AdjustBlock title='What it costs' icon={Coins}>
            <DictField
              entityId={id}
              spec={{ key: 'cost', label: 'The cost', value: card.cost }}
              blocked={blocked}
              table={COST_ONLY}
            />
          </AdjustBlock>
          <AdjustBlock title='What it brings' icon={Sparkles}>
            <DictField
              entityId={id}
              spec={{
                key: 'effects',
                label: 'Its effects',
                value: card.effects,
              }}
              blocked={blocked}
              table={TRADITION_TERMS}
            />
          </AdjustBlock>
        </div>
        {card.keepers.length > 0 && (
          <AdjustBlock title='How many take part' icon={Users}>
            <RowEditors>
              {card.keepers.map((row) => (
                <RowEditor
                  key={row.community?.id}
                  label={row.community?.name ?? 'Unknown'}
                  icon={Users}
                  value={row.participation}
                  max={PERCENT}
                  blocked={busy}
                  onSave={(value) =>
                    keep.mutate({ community: row.community?.id ?? 0, value })
                  }
                />
              ))}
            </RowEditors>
          </AdjustBlock>
        )}
      </LoreAdjust>
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
  const states = card.adherents.filter((row) => row.state).length
  const appeal = Object.entries(card.appeal).sort(([, a], [, b]) => b - a)
  const lead = card.tenets[0]
    ? lookup(TENETS, card.tenets[0])
    : LORE_KIND.ideology
  return (
    <div data-surface='IdeologyCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero
        spec={{
          ...lead,
          label: card.tenets.length > 0 ? lead.label : 'An unformed creed',
        }}
        kicker='A creed of the mortals'
        hint='Its tenets press values on its adherents; a realm that takes it as its own leans its decisions toward it.'
      >
        <RefChip icon={PenLine} label='Taught by' item={card.founder} />
        {card.tenets.map((item) => (
          <NamedChip key={item} spec={lookup(TENETS, item)} />
        ))}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Adherents'
          value={card.adherents.length}
          icon={Users}
          tone='info'
          hint='Communities that hold it'
        />
        <KpiTile
          label='Adherence'
          value={`${average(card.adherents.map((row) => row.strength))}%`}
          icon={HeartPulse}
          tone='gold'
          hint='How firmly its adherents hold it, on average'
          meter={{
            value: average(card.adherents.map((row) => row.strength)),
            max: PERCENT,
            label: 'Adherence',
          }}
        />
        <KpiTile
          label='State creed of'
          value={states}
          icon={Crown}
          tone={states > 0 ? 'gold' : 'muted'}
          hint='Realms that have made it their own'
        />
        <KpiTile
          label='Tenets'
          value={card.tenets.length}
          icon={ScrollText}
          tone='verdigris'
          hint='The principles it holds'
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='Values it presses' icon={Sprout} tone='success'>
          <ShiftChips
            entries={card.values}
            table={VALUES}
            empty='It presses no value.'
          />
        </LoreCard>
        <LoreCard title='Who it calls to' icon={Megaphone} tone='verdigris'>
          {appeal.length === 0 ? (
            <Muted>It calls to no class in particular.</Muted>
          ) : (
            <div className='flex min-w-0 flex-col gap-2'>
              {appeal.map(([key, value]) => {
                const spec = lookup(CLASSES, key)
                return (
                  <StatBar
                    key={key}
                    label={spec.label}
                    value={value}
                    max={PERCENT}
                    icon={spec.icon}
                    tone='verdigris'
                  />
                )
              })}
            </div>
          )}
        </LoreCard>
        <LoreCard
          title='Adherents'
          icon={Users}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.adherents.length}</Badge>}
        >
          {card.adherents.length === 0 ? (
            <Muted>No community holds it yet.</Muted>
          ) : (
            <MeterList surface='CreedAdherents'>
              {card.adherents.map((row) => (
                <MeterRow
                  key={row.community?.id}
                  item={row.community}
                  label={`Adherence, since epoch ${row.since_epoch}`}
                  value={row.strength}
                  icon={row.state ? Crown : Users}
                  tone={row.state ? 'gold' : 'info'}
                >
                  {row.state && (
                    <Badge size='sm' variant='default'>
                      State creed
                    </Badge>
                  )}
                </MeterRow>
              ))}
            </MeterList>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='creed'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='Tenets' icon={ScrollText}>
          <ul
            data-surface='CreedTenets'
            className='flex min-w-0 flex-wrap gap-2'
          >
            {card.tenets.length === 0 && <Muted>It holds no tenet yet.</Muted>}
            {card.tenets.map((item) => {
              const spec = lookup(TENETS, item)
              const Icon = spec.icon
              return (
                <li
                  key={item}
                  className='flex items-center gap-1 rounded-md border bg-muted/30 py-0.5 pr-0.5 pl-2'
                >
                  <Icon
                    aria-hidden='true'
                    className='size-icon-xs text-muted-foreground'
                  />
                  <Text as='span' variant='caption' weight='medium'>
                    {spec.label}
                  </Text>
                  <Button
                    size='icon-sm'
                    variant='ghost'
                    aria-label={`Cast off ${spec.label}`}
                    disabled={busy !== null}
                    disabledReason={busy ?? undefined}
                    onClick={() => teach.mutate({ tenet: item, held: false })}
                  >
                    <X />
                  </Button>
                </li>
              )
            })}
          </ul>
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <div className='min-w-0 flex-1 basis-48'>
              <ChoicePicker
                label='Teach a tenet'
                value={tenet}
                table={Object.fromEntries(
                  Object.entries(TENETS).filter(
                    ([key]) => !card.tenets.includes(key as never)
                  )
                )}
                blocked={busy}
                placeholder='Choose a tenet'
                onPick={setTenet}
              />
            </div>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || tenet === ''}
              disabledReason={
                busy ?? (tenet === '' ? 'Choose a tenet' : undefined)
              }
              onClick={() => teach.mutate({ tenet, held: true })}
            >
              <Plus />
              Teach it
            </Button>
          </div>
        </AdjustBlock>
        <div className={LORE_GRID}>
          <AdjustBlock title='Values it presses' icon={Sprout}>
            <DictField
              entityId={id}
              spec={{
                key: 'value_delta',
                label: 'Its values',
                value: card.values,
              }}
              blocked={blocked}
              table={VALUES}
            />
          </AdjustBlock>
          <AdjustBlock title='Who it calls to' icon={Megaphone}>
            <DictField
              entityId={id}
              spec={{ key: 'appeal', label: 'Its appeal', value: card.appeal }}
              blocked={blocked}
              table={CLASSES}
            />
          </AdjustBlock>
        </div>
        <AdjustBlock title='Adherents' icon={Users}>
          {card.adherents.length > 0 && (
            <RowEditors>
              {card.adherents.map((row) => (
                <RowEditor
                  key={row.community?.id}
                  label={row.community?.name ?? 'Unknown'}
                  icon={Users}
                  value={row.strength}
                  max={PERCENT}
                  blocked={busy}
                  onSave={(strength) =>
                    adhere.mutate({
                      community: row.community?.id ?? 0,
                      strength,
                      state: row.state,
                    })
                  }
                >
                  <label className='flex h-control-md shrink-0 items-center gap-1.5'>
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
                    <Crown
                      aria-hidden='true'
                      className='size-icon-sm text-primary'
                    />
                  </label>
                </RowEditor>
              ))}
            </RowEditors>
          )}
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
        </AdjustBlock>
      </LoreAdjust>
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
  const school = lookup(SCHOOLS, card.school)
  const source = lookup(SOURCES, card.source)
  const backlash = lookup(BACKLASHES, card.backlash)
  const worked = card.castings.filter((row) => row.succeeded).length
  const needs = Object.entries(card.requirements)
  return (
    <div data-surface='RiteCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero
        spec={school}
        kicker='A working of magic'
        title={`Rite of ${school.label.toLowerCase()}`}
      >
        <NamedChip
          spec={source}
        >{`Drawn from ${source.label.toLowerCase()}`}</NamedChip>
        {card.holy && (
          <NamedChip spec={{ label: 'Holy', icon: Sparkles, tone: 'gold' }} />
        )}
        {card.heretical && (
          <NamedChip
            spec={{ label: 'Heresy', icon: TriangleAlert, tone: 'danger' }}
          />
        )}
        <RefChip icon={PenLine} label='Devised by' item={card.inventor} />
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Power'
          value={`${card.power}/${MAX_POWER}`}
          icon={Wand2}
          tone='verdigris'
          hint='Stronger rites cost more and risk more'
          meter={{ value: card.power, max: MAX_POWER, label: 'Power' }}
        />
        <KpiTile
          label='Backlash'
          value={`${card.backlash_chance}%`}
          icon={backlash.icon}
          tone='danger'
          hint={`When it goes wrong: ${backlash.label.toLowerCase()}`}
          meter={{
            value: card.backlash_chance,
            max: PERCENT,
            label: 'Backlash chance',
          }}
        />
        <KpiTile
          label='Workings'
          value={card.effects.length}
          icon={Sparkles}
          tone='gold'
          hint='What it does when worked'
        />
        <KpiTile
          label='Cast'
          value={card.castings.length}
          icon={History}
          tone='info'
          hint={
            card.castings.length > 0
              ? `${worked} of ${card.castings.length} took hold`
              : 'It has never been worked'
          }
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='What it does' icon={Sparkles}>
          {card.effects.length === 0 ? (
            <Muted>It does nothing yet.</Muted>
          ) : (
            <ul
              data-surface='RiteEffects'
              className='flex min-w-0 flex-col gap-2'
            >
              {card.effects.map((row) => {
                const spec = lookup(EFFECTS, row.effect)
                return (
                  <li key={row.effect}>
                    <StatBar
                      label={
                        row.detail
                          ? `${spec.label} · ${row.detail}`
                          : spec.label
                      }
                      value={row.magnitude}
                      max={MAX_POWER}
                      icon={spec.icon}
                      tone='verdigris'
                    />
                  </li>
                )
              })}
            </ul>
          )}
        </LoreCard>
        <LoreCard title='Its price' icon={Coins} tone='warning'>
          <TermChips
            entries={card.cost}
            table={RITE_COSTS}
            empty='It asks for nothing.'
          />
          {needs.length > 0 && (
            <div className='flex min-w-0 flex-col gap-1.5'>
              <Label>It needs</Label>
              <div className='flex min-w-0 flex-wrap gap-1.5'>
                {needs.map(([key, value]) => (
                  <NamedChip
                    key={key}
                    spec={{ label: '', icon: Check, tone: 'muted' }}
                  >
                    {`${sentence(key)}: ${sentence(String(value))}`}
                  </NamedChip>
                ))}
              </div>
            </div>
          )}
        </LoreCard>
        <LoreCard title='Work the rite' icon={Wand2} tone='verdigris' wide>
          <div
            data-surface='CastRite'
            className='flex min-w-0 flex-wrap items-end gap-2'
          >
            <div className='flex min-w-0 flex-1 basis-48 flex-col gap-1'>
              <Label>Caster</Label>
              <EntityPicker
                types={['mortal', 'cult']}
                value={caster}
                onChange={setCaster}
                placeholder='Caster'
              />
            </div>
            <div className='flex min-w-0 flex-1 basis-48 flex-col gap-1'>
              <Label>Target</Label>
              <EntityPicker
                types={['mortal', ...COMMUNITIES]}
                value={target}
                onChange={setTarget}
                placeholder='Target (optional)'
              />
            </div>
            <Button
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
        </LoreCard>
        <LoreCard
          title='Castings'
          icon={History}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.castings.length}</Badge>}
        >
          {card.castings.length === 0 ? (
            <Muted>It has never been worked.</Muted>
          ) : (
            <div data-surface='Castings'>
              <Timeline label='Castings'>
                {card.castings.map((row, index) => {
                  const spec = lookup(EFFECTS, row.effect)
                  return (
                    <TimelineItem
                      key={row.id}
                      icon={row.succeeded ? spec.icon : TriangleAlert}
                      tone={row.succeeded ? 'success' : 'destructive'}
                      title={
                        row.succeeded
                          ? `${spec.label} took hold`
                          : `${spec.label} failed`
                      }
                      timestamp={`Epoch ${row.epoch}`}
                      last={index === card.castings.length - 1}
                    >
                      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                        <RefChip icon={User} label='By' item={row.caster} />
                        <RefChip icon={Target} label='On' item={row.target} />
                        {row.backlash && (
                          <NamedChip spec={lookup(BACKLASHES, row.backlash)} />
                        )}
                      </div>
                    </TimelineItem>
                  )
                })}
              </Timeline>
            </div>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='rite'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The rite' icon={school.icon}>
          <LoreFields
            entityId={id}
            surface='RiteForm'
            fields={[
              { key: 'school', kind: 'enum', table: SCHOOLS },
              { key: 'source', kind: 'enum', table: SOURCES },
              { key: 'backlash', kind: 'enum', table: BACKLASHES },
              { key: 'power', kind: 'number', min: 1, max: MAX_POWER },
              { key: 'backlash_chance', kind: 'number', min: 0, max: PERCENT },
              { key: 'holy', kind: 'bool' },
              { key: 'heretical', kind: 'bool' },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='Its price' icon={Coins}>
          <DictField
            entityId={id}
            spec={{ key: 'cost', label: 'The price', value: card.cost }}
            blocked={blocked}
            table={RITE_COSTS}
          />
        </AdjustBlock>
        <AdjustBlock title='What it does' icon={Sparkles}>
          {card.effects.length > 0 && (
            <RowEditors>
              {card.effects.map((row) => {
                const spec = lookup(EFFECTS, row.effect)
                return (
                  <RowEditor
                    key={row.effect}
                    label={`${spec.label} magnitude`}
                    icon={spec.icon}
                    value={row.magnitude}
                    blocked={busy}
                    onSave={(magnitude) =>
                      shape.mutate({ effect: row.effect, magnitude })
                    }
                  >
                    <Button
                      size='icon'
                      variant='ghost'
                      aria-label={`Remove ${spec.label}`}
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() =>
                        shape.mutate({ effect: row.effect, magnitude: 0 })
                      }
                    >
                      <Trash2 />
                    </Button>
                  </RowEditor>
                )
              })}
            </RowEditors>
          )}
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <div className='min-w-0 flex-1 basis-48'>
              <ChoicePicker
                label='Add a working'
                value={effect}
                table={Object.fromEntries(
                  Object.entries(EFFECTS).filter(
                    ([key]) => !card.effects.some((row) => row.effect === key)
                  )
                )}
                blocked={busy}
                placeholder='Choose'
                onPick={setEffect}
              />
            </div>
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
        </AdjustBlock>
      </LoreAdjust>
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
  const predicate = lookup(PREDICATES, card.predicate)
  const state = lookup(PROPHECY_STATES, card.state)
  const terms = Object.entries(card.args)
  return (
    <div data-surface='ProphecyCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero
        spec={predicate}
        kicker='It is foretold'
        hint='Pressure bends the world toward it; it is weighed when its deadline comes.'
      >
        <NamedChip spec={state} />
        <RefChip icon={Eye} label='Seen by' item={card.seer} />
        {card.resolved_epoch !== null && (
          <NamedChip spec={{ label: '', icon: CalendarDays, tone: 'muted' }}>
            {`Settled in epoch ${card.resolved_epoch}`}
          </NamedChip>
        )}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Pressure'
          value={`${card.pressure}%`}
          icon={Gauge}
          tone='warning'
          hint='How hard it bends events toward itself'
          meter={{ value: card.pressure, max: PERCENT, label: 'Pressure' }}
        />
        <KpiTile
          label='State'
          value={state.label}
          icon={state.icon}
          tone={state.tone}
          hint={
            card.resolved_epoch !== null
              ? `Settled in epoch ${card.resolved_epoch}`
              : 'Not yet settled'
          }
        />
        <KpiTile
          label='Deadline'
          value={
            card.deadline_epoch !== null
              ? `Epoch ${card.deadline_epoch}`
              : 'None'
          }
          icon={Hourglass}
          tone='muted'
          hint={
            card.deadline_epoch !== null
              ? 'It must come true by then'
              : 'It waits without end'
          }
        />
        <KpiTile
          label='Heard by'
          value={card.audience.length}
          icon={Users}
          tone='info'
          hint='Those who know of it'
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard
          title='What must happen'
          icon={predicate.icon}
          tone={predicate.tone}
        >
          <Text weight='medium'>{predicate.label}</Text>
          {terms.length === 0 ? (
            <Muted>No further terms bind it.</Muted>
          ) : (
            <div className='flex min-w-0 flex-col gap-2'>
              {terms.map(([key, value]) => {
                const spec = lookup(PROPHECY_ARGS, key)
                return (
                  <RoleRow
                    key={key}
                    icon={spec.icon}
                    tone={spec.tone}
                    label={spec.label}
                  >
                    {ENTITY_ARGS.has(key) && typeof value === 'number' ? (
                      <Who item={{ id: value, name: `Record ${value}` }} />
                    ) : (
                      <Text as='span'>{sentence(String(value))}</Text>
                    )}
                  </RoleRow>
                )
              })}
            </div>
          )}
        </LoreCard>
        <LoreCard
          title='Who heard it'
          icon={Users}
          tone='info'
          aside={<Badge variant='secondary'>{card.audience.length}</Badge>}
        >
          {card.audience.length === 0 ? (
            <Muted>No one has heard it spoken.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-wrap gap-1.5'>
              {card.audience.map((item) => (
                <li key={item.id}>
                  <RefChip icon={Users} label='' item={item} />
                </li>
              ))}
            </ul>
          )}
        </LoreCard>
        {pending && (
          <LoreCard title='Decide its fate' icon={Sparkles} wide>
            <Muted>Settle it now instead of waiting for its deadline.</Muted>
            <div className='flex min-w-0 flex-wrap gap-2'>
              <Button
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => settle.mutate(true)}
              >
                <Check />
                Let it come true
              </Button>
              <Button
                variant='outline'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => settle.mutate(false)}
              >
                <X />
                Let it fail
              </Button>
            </div>
          </LoreCard>
        )}
      </div>
      <LoreAdjust
        entityId={id}
        noun='prophecy'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The foretelling' icon={predicate.icon}>
          <LoreFields
            entityId={id}
            surface='ProphecyForm'
            fields={[
              { key: 'predicate', kind: 'enum', table: PREDICATES },
              { key: 'deadline_epoch', kind: 'number', min: 0, nullable: true },
              { key: 'pressure', kind: 'number', min: 0, max: PERCENT },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='What exactly must happen' icon={ScrollText}>
          <DictField
            entityId={id}
            spec={{ key: 'args', label: 'Its terms', value: card.args }}
            blocked={blocked}
            table={PROPHECY_ARGS}
          />
        </AdjustBlock>
      </LoreAdjust>
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
  const kind = lookup(ITEM_CLASSES, card.item_class)
  const curse = lookup(CURSES, card.curse)
  return (
    <div data-surface='ItemCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero
        spec={kind}
        kicker='A made thing'
        hint={card.curse !== 'none' ? curse.hint : undefined}
      >
        {card.curse !== 'none' && (
          <NamedChip
            spec={curse}
          >{`Cursed: ${curse.label.toLowerCase()}`}</NamedChip>
        )}
        {card.material && (
          <NamedChip spec={{ label: '', icon: Hammer, tone: 'muted' }}>
            {`Made of ${card.material.replaceAll('_', ' ')}`}
          </NamedChip>
        )}
        {card.symbol && (
          <NamedChip
            spec={{ label: 'A symbol of its people', icon: Flag, tone: 'gold' }}
          />
        )}
        {card.damage_type && (
          <NamedChip spec={{ label: '', icon: Target, tone: 'muted' }}>
            {`Deals ${card.damage_type.replaceAll('_', ' ')}`}
          </NamedChip>
        )}
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Quality'
          value={card.quality}
          icon={Hammer}
          hint='The skill of its making'
          meter={{ value: card.quality, max: PERCENT, label: 'Quality' }}
        />
        <KpiTile
          label='Condition'
          value={card.condition}
          icon={Shield}
          tone={wear(card.condition)}
          hint={
            card.condition < WORN
              ? 'Near to breaking'
              : 'Wear from use and years'
          }
          meter={{ value: card.condition, max: PERCENT, label: 'Condition' }}
        />
        <KpiTile
          label='Renown'
          value={card.renown}
          icon={Sparkles}
          tone='verdigris'
          hint='Grows with every deed it is part of'
          meter={{ value: card.renown, max: PERCENT, label: 'Renown' }}
        />
        <KpiTile
          label='Worth'
          value={card.value}
          icon={Coins}
          tone='gold'
          hint='Its price in trade'
        />
      </div>
      <div className='grid min-w-0 grid-cols-3 gap-2'>
        <MiniStat icon={Ruler} label='Reach' value={card.reach} />
        <MiniStat icon={Shield} label='Coverage' value={card.coverage} />
        <MiniStat icon={Weight} label='Weight' value={card.weight} />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='Hands it has known' icon={Hand}>
          {!card.maker && !card.owner && !card.regalia_of ? (
            <Muted>No one is remembered with it.</Muted>
          ) : (
            <div className='flex min-w-0 flex-col gap-2.5'>
              {card.maker && (
                <RoleRow icon={Hammer} tone='gold' label='Made by'>
                  <Who item={card.maker} />
                </RoleRow>
              )}
              {card.owner && (
                <RoleRow icon={Hand} tone='info' label='Held by'>
                  <Who item={card.owner} />
                </RoleRow>
              )}
              {card.regalia_of && (
                <RoleRow icon={Crown} tone='gold' label='Regalia of'>
                  <Who item={card.regalia_of} />
                </RoleRow>
              )}
            </div>
          )}
        </LoreCard>
        <LoreCard
          title='Enchantments'
          icon={Sparkles}
          tone='verdigris'
          aside={<Badge variant='secondary'>{card.enchantments.length}</Badge>}
        >
          {card.enchantments.length === 0 ? (
            <Muted>No spell is bound into it.</Muted>
          ) : (
            <ul
              data-surface='Enchantments'
              className='flex min-w-0 flex-col gap-2'
            >
              {card.enchantments.map((row) => {
                const spec = lookup(EFFECTS, row.effect)
                return (
                  <li key={row.effect}>
                    <StatBar
                      label={spec.label}
                      value={row.strength}
                      max={PERCENT}
                      icon={spec.icon}
                      tone='verdigris'
                    />
                  </li>
                )
              })}
            </ul>
          )}
        </LoreCard>
        {card.contents.length > 0 && (
          <LoreCard title='Written within' icon={BookOpen} tone='info' wide>
            <ul
              data-surface='BookContents'
              className='flex min-w-0 flex-wrap gap-1.5'
            >
              {card.contents.map((item) => (
                <li key={item.id}>
                  <RefChip icon={ScrollText} label='' item={item} />
                </li>
              ))}
            </ul>
          </LoreCard>
        )}
        <LoreCard
          title='Its story'
          icon={History}
          tone='info'
          wide
          aside={<Badge variant='secondary'>{card.history.length}</Badge>}
        >
          {card.history.length === 0 ? (
            <Muted>Nothing has befallen it yet.</Muted>
          ) : (
            <div data-surface='ItemHistory'>
              <Timeline label='Item history'>
                {card.history.map((row, index) => {
                  const spec = lookup(DEEDS, row.deed)
                  return (
                    <TimelineItem
                      key={`${row.epoch}.${index}`}
                      icon={spec.icon}
                      tone={
                        spec.tone === 'danger'
                          ? 'destructive'
                          : spec.tone === 'gold'
                            ? 'primary'
                            : spec.tone === 'success'
                              ? 'success'
                              : spec.tone === 'warning'
                                ? 'warning'
                                : 'default'
                      }
                      title={spec.label}
                      timestamp={`Epoch ${row.epoch}`}
                      last={index === card.history.length - 1}
                    >
                      <div className='flex min-w-0 flex-col gap-1'>
                        {row.actor && (
                          <div>
                            <RefChip icon={User} label='By' item={row.actor} />
                          </div>
                        )}
                        {row.note && <Muted>{row.note}</Muted>}
                      </div>
                    </TimelineItem>
                  )
                })}
              </Timeline>
            </div>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='item'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The item' icon={kind.icon}>
          <LoreFields
            entityId={id}
            surface='ItemForm'
            fields={[
              { key: 'item_class', kind: 'enum', table: ITEM_CLASSES },
              { key: 'curse', kind: 'enum', table: CURSES },
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
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='Enchantments' icon={Sparkles}>
          {card.enchantments.length > 0 && (
            <RowEditors>
              {card.enchantments.map((row) => {
                const spec = lookup(EFFECTS, row.effect)
                return (
                  <RowEditor
                    key={row.effect}
                    label={`${spec.label} strength`}
                    icon={spec.icon}
                    value={row.strength}
                    max={PERCENT}
                    blocked={busy}
                    onSave={(strength) =>
                      enchant.mutate({ effect: row.effect, strength })
                    }
                  />
                )
              })}
            </RowEditors>
          )}
          <div className='flex min-w-0 flex-wrap items-end gap-2'>
            <div className='min-w-0 flex-1 basis-48'>
              <ChoicePicker
                label='Enchant with'
                value={effect}
                table={Object.fromEntries(
                  Object.entries(EFFECTS).filter(
                    ([key]) =>
                      !card.enchantments.some((row) => row.effect === key)
                  )
                )}
                blocked={busy}
                placeholder='Choose'
                onPick={setEffect}
              />
            </div>
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
        </AdjustBlock>
      </LoreAdjust>
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
  const medium = lookup(MEDIUMS, card.medium)
  return (
    <div data-surface='ArtworkCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero spec={medium} kicker='A work of art'>
        <NamedChip
          spec={
            card.performed
              ? { label: 'Performed aloud', icon: Mic, tone: 'info' }
              : { label: 'Kept as an object', icon: Gem, tone: 'muted' }
          }
        />
        {card.propaganda && (
          <NamedChip
            spec={{ label: 'Propaganda', icon: Megaphone, tone: 'warning' }}
          />
        )}
        <RefChip icon={Languages} label='In' item={card.language} />
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Quality'
          value={card.quality}
          icon={medium.icon}
          hint='The mastery in it'
          meter={{ value: card.quality, max: PERCENT, label: 'Quality' }}
        />
        <KpiTile
          label='Copies'
          value={card.copies}
          icon={BookOpen}
          tone='info'
          hint='Copies made carry it further'
        />
        <KpiTile
          label='Translations'
          value={card.translations.length}
          icon={Languages}
          tone='verdigris'
          hint='Tongues it has been carried into'
        />
        <KpiTile
          label='Propaganda'
          value={card.propaganda ? 'Yes' : 'No'}
          icon={Megaphone}
          tone={card.propaganda ? 'warning' : 'muted'}
          hint='Propaganda presses its message on all who hear it'
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='Its makers and subject' icon={PenLine}>
          {!card.author && !card.subject && !card.patron ? (
            <Muted>Its maker is forgotten.</Muted>
          ) : (
            <div className='flex min-w-0 flex-col gap-2.5'>
              {card.author && (
                <RoleRow icon={PenLine} tone='gold' label='By'>
                  <Who item={card.author} />
                </RoleRow>
              )}
              {card.subject && (
                <RoleRow icon={Target} tone='info' label='Of'>
                  <Who item={card.subject} />
                </RoleRow>
              )}
              {card.patron && (
                <RoleRow icon={Coins} tone='gold' label='For'>
                  <Who item={card.patron} />
                </RoleRow>
              )}
            </div>
          )}
        </LoreCard>
        <LoreCard title='What it stirs' icon={Sprout} tone='success'>
          <ShiftChips
            entries={card.message}
            table={VALUES}
            empty='It stirs no value.'
          />
          {card.translations.length > 0 && (
            <div className='flex min-w-0 flex-col gap-1.5'>
              <Label>Translated into</Label>
              <div className='flex min-w-0 flex-wrap gap-1.5'>
                {card.translations.map((item) => (
                  <RefChip
                    key={item.id}
                    icon={Languages}
                    label=''
                    item={item}
                  />
                ))}
              </div>
            </div>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='work'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The work' icon={medium.icon}>
          <LoreFields
            entityId={id}
            surface='ArtworkForm'
            fields={[
              { key: 'medium', kind: 'enum', table: MEDIUMS },
              { key: 'quality', kind: 'number', min: 0, max: PERCENT },
              { key: 'copies', kind: 'number', min: 0 },
              { key: 'performed', kind: 'bool' },
              { key: 'propaganda', kind: 'bool' },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='What it stirs' icon={Sprout}>
          <DictField
            entityId={id}
            spec={{ key: 'message', label: 'Its message', value: card.message }}
            blocked={blocked}
            table={VALUES}
          />
        </AdjustBlock>
      </LoreAdjust>
    </div>
  )
}

function Body({
  card,
  blocked,
}: {
  card: LoreCardData
  blocked: string | null
}) {
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
    <EmptyState
      icon={BadgeCheck}
      title='No story yet'
      description='The world has not yet given it a story; it will after the next epoch.'
    />
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
  const spec = LORE_KIND[kind]
  return (
    <Section
      id='section-lore'
      title={`The ${spec.label.toLowerCase()}'s story`}
      description='How it lives in the world. Open the shaping panel below to set any value.'
      icon={spec.icon}
      tone={spec.tone}
    >
      <div className='@container/lore flex min-w-0 flex-col gap-4'>
        {view.isPending && <Muted>Reading the record…</Muted>}
        {view.isError && (
          <EmptyState
            icon={TriangleAlert}
            title='The record could not be read'
            description={view.error.message}
          />
        )}
        {view.data && <Body card={view.data} blocked={blocked} />}
      </div>
    </Section>
  )
}
