import { useState } from 'react'
import {
  Beef,
  BookOpen,
  Building,
  Check,
  ChevronDown,
  Dna,
  Hourglass,
  Link,
  Palette,
  Ship,
  Sprout,
  Swords,
  Users,
  Users2,
  type LucideIcon,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { EntityLink, Medallion, MiniStat, Paged } from '@/components/domain'
import { MultiSelect } from '@/components/domain/MultiSelect'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import { AIR_NEEDS } from '@/features/physics/labels'
import { useNames } from '../api/queries'
import { COMMODITY, type CommodityKind } from '../economy/labels'
import { BAND, named } from '../environment/labels'
import { BIOCHEMISTRY } from '../wilds/labels'
import {
  BODY_SPEC,
  DIET_SPEC,
  FOUND_ICON,
  FUNERAL_SPEC,
  IMMUNE_ICON,
  LANGUAGE_ICON,
  MOUNT_SPEC,
  RECORD_ICON,
  SIZE_CLASS_SPEC,
  TRADE_ICON,
  TRAIT_SPEC,
  type NaturalTrait,
  effectTone,
  folkLabel,
} from './folkLabels'
import {
  AESTHETIC_SPEC,
  INHERITANCE_SPEC,
  JOB_SPEC,
  MARRIAGE_SPEC,
  MARTIAL_SPEC,
  type Spec,
  fieldLabel,
} from './labels'
import {
  AdjustPanel,
  ChoiceEditor,
  EditorGroup,
  EditorTile,
  FlagEditor,
  HeldStrip,
  type NumberField,
  NumberEditor,
  Panel,
} from './parts'
import { WORKING } from './tones'

type Demography = components['schemas']['DemographyView']
type Biology = NonNullable<Demography['biology']>
type Culture = NonNullable<Demography['culture']>
type Value = number | string | boolean | number[] | string[] | null

const PERCENT = 100
const FERTILITY_MAX = 500
const RECORD_MAX = 100000
const POPULATION_MIN = 100
const POPULATION_MAX = 50000000
const NAME_MIN = 2
const NONE = 'none'
const LIFE_FIELDS = [
  { key: 'maturity_years', icon: Sprout, min: 1, max: 1000, unit: 'years' },
  { key: 'adult_years', icon: Users, min: 1, max: 10000, unit: 'years' },
  { key: 'elder_years', icon: Hourglass, min: 1, max: 10000, unit: 'years' },
  { key: 'fertility_pct', icon: Sprout, min: 0, max: FERTILITY_MAX, unit: '%' },
] as const
const GRAVITY_FIELDS = [
  {
    key: 'gravity_low',
    icon: Users,
    min: 1,
    max: 10000,
    unit: '% of a standard world',
  },
  {
    key: 'gravity_high',
    icon: Users,
    min: 1,
    max: 10000,
    unit: '% of a standard world',
  },
] as const
const SOCIETY_FIELDS = [
  { key: 'cohesion', icon: Users2, min: 0, max: PERCENT },
  { key: 'literacy', icon: BookOpen, min: 0, max: PERCENT },
  { key: 'urbanisation', icon: Building, min: 0, max: PERCENT },
] as const

function bandSpecs(): Record<string, Spec> {
  return Object.fromEntries(
    Object.entries(BAND).map(([key, item]) => [
      key,
      { label: item.label, icon: item.icon, tone: item.tone },
    ])
  )
}

function staplesSpecs(): Record<string, Spec> {
  return Object.fromEntries(
    Object.entries(COMMODITY).map(([key, item]) => [
      key,
      { label: item.label, icon: item.icon, tone: 'success' as const },
    ])
  )
}

function SpecChip({ spec }: { spec: Spec }) {
  const Icon = spec.icon
  return (
    <Badge size='sm' variant='secondary' title={spec.hint}>
      <Icon />
      {spec.label}
    </Badge>
  )
}

function useRecordOptions(type: string) {
  const names = useNames()
  return (names.data ?? [])
    .filter(
      (entry) =>
        entry.kind === 'entity' &&
        entry.type === type &&
        (!entry.status || entry.status === 'canon' || entry.status === 'dead')
    )
    .map((entry) => ({ value: String(entry.id), label: entry.name }))
}

export function FolkBody({ biology }: { biology: Biology }) {
  const body = BODY_SPEC[biology.body_plan]
  const size = SIZE_CLASS_SPEC[biology.size_class]
  const diet = DIET_SPEC[biology.diet]
  const band = named(BAND, biology.acclimatised)
  const mount = MOUNT_SPEC[biology.effects.mount] ?? MOUNT_SPEC.rides
  const effects = biology.effects
  const staple = COMMODITY[biology.staple as CommodityKind]
  return (
    <Panel
      title='Body and nature'
      icon={body.icon}
      tone={body.tone}
      hint={body.hint}
      aside={<SpecChip spec={size} />}
    >
      <div data-surface='PeopleBiology' className='flex min-w-0 flex-col gap-3'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @md/folk:grid-cols-2 @xl/folk:grid-cols-3'>
          <MiniStat
            icon={body.icon}
            label='Body'
            value={body.label}
            tone={body.tone}
            hint={body.hint}
          />
          <MiniStat
            icon={size.icon}
            label='Size'
            value={size.label}
            tone={size.tone}
          />
          <MiniStat
            icon={diet.icon}
            label='Diet'
            value={diet.label}
            tone={diet.tone}
            hint={diet.hint}
          />
          <MiniStat
            icon={band.icon}
            label='At home in'
            value={`${band.label} lands`}
            tone={band.tone ?? 'muted'}
            hint='Campaigns and migrations beyond their climate cost them'
          />
          <MiniStat
            icon={staple?.icon ?? Beef}
            label='Lives on'
            value={staple?.label ?? fieldLabel(biology.staple)}
            tone='success'
          />
          <MiniStat
            icon={mount.icon}
            label='In war'
            value={mount.label}
            tone={mount.tone}
          />
        </div>
        <div className='grid min-w-0 grid-cols-2 gap-2 @xl/folk:grid-cols-3'>
          <MiniStat
            icon={Beef}
            label='Food needed'
            value={`${effects.food_pct}%`}
            tone={effectTone(effects.food_pct, 'low')}
            hint='What one of them eats against an ordinary person'
          />
          <MiniStat
            icon={Building}
            label='Room needed'
            value={`${effects.room_pct}%`}
            tone={effectTone(effects.room_pct, 'low')}
            hint='How soon their land grows crowded'
          />
          <MiniStat
            icon={Swords}
            label='Strength in battle'
            value={`${effects.strength_pct}%`}
            tone={effectTone(effects.strength_pct, 'high')}
            hint='Before ground, weather and night are counted'
          />
          <MiniStat
            icon={IMMUNE_ICON}
            label='Plague deaths'
            value={`${effects.disease_pct}%`}
            tone={effectTone(effects.disease_pct, 'low')}
            hint='Body, gifts and funeral rite against an ordinary people'
          />
          <MiniStat
            icon={Ship}
            label='Share at sea'
            value={`${effects.fleet_pct}%`}
            tone={effectTone(effects.fleet_pct, 'high')}
            hint='How much of their levy takes to ships'
          />
          <MiniStat
            icon={diet.icon}
            label='Hunger now'
            value={`${effects.hunger_pct}%`}
            tone={
              effects.hunger_pct >= PERCENT / 2
                ? 'danger'
                : effects.hunger_pct > 0
                  ? 'warning'
                  : 'success'
            }
            hint='What their diet finds in the land against what they need'
          />
          <MiniStat
            icon={BIOCHEMISTRY[biology.biochemistry]?.icon ?? Dna}
            label='Body chemistry'
            value={
              BIOCHEMISTRY[biology.biochemistry]?.label ??
              fieldLabel(biology.biochemistry)
            }
            tone='info'
            hint='Worlds whose life is of another chemistry are hard for them to live on'
          />
          <MiniStat
            icon={AIR_NEEDS[biology.air].icon}
            label='Breath'
            value={AIR_NEEDS[biology.air].label}
            tone={AIR_NEEDS[biology.air].tone}
            hint='A world without the air they breathe cannot hold them unaided'
          />
          <MiniStat
            icon={Users}
            label='Gravity they bear'
            value={`${biology.gravity_low}% to ${biology.gravity_high}%`}
            tone='muted'
            hint='Of the pull of a standard world'
          />
          <MiniStat
            icon={Building}
            label='Habitability here'
            value={`${biology.habitability}%`}
            tone={
              biology.habitability >= PERCENT / 2
                ? 'success'
                : biology.habitability > 0
                  ? 'warning'
                  : 'danger'
            }
            hint='How well their world suits their body, air and gravity; growth and colonies follow it'
          />
        </div>
        {biology.traits.length > 0 && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Label variant='overline'>Natural gifts</Label>
            <Paged items={biology.traits}>
              {(trait) => <SpecChip key={trait} spec={TRAIT_SPEC[trait]} />}
            </Paged>
          </div>
        )}
        {effects.work.length > 0 && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Label variant='overline'>At work</Label>
            {effects.work.map((item) => {
              const job = JOB_SPEC[item.job]
              const Icon = job.icon
              return (
                <Badge
                  key={item.job}
                  size='sm'
                  variant={item.pct >= PERCENT ? 'secondary' : 'outline'}
                >
                  <Icon />
                  {`${job.label} ${item.pct}%`}
                </Badge>
              )
            })}
          </div>
        )}
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Label variant='overline'>Can eat</Label>
          {biology.edible.length === 0 ? (
            <Muted variant='caption'>Nothing grown; the sun feeds them</Muted>
          ) : (
            biology.edible.map((item) => {
              const good = COMMODITY[item]
              return (
                <SpecChip
                  key={item}
                  spec={{ label: good.label, icon: good.icon }}
                />
              )
            })
          )}
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Label variant='overline'>Hardened against</Label>
          {biology.immunities.length === 0 ? (
            <Muted variant='caption'>
              No sickness of their homeland spares them
            </Muted>
          ) : (
            <Paged items={biology.immunities}>
              {(item) => (
                <EntityLink
                  key={item.id}
                  kind='entity'
                  id={String(item.id)}
                  showIcon
                >
                  {item.name}
                </EntityLink>
              )}
            </Paged>
          )}
        </div>
      </div>
    </Panel>
  )
}

export function FolkWays({ culture }: { culture: Culture }) {
  const funeral = FUNERAL_SPEC[culture.funeral_rite]
  const style = MARTIAL_SPEC[culture.martial_style]
  const current = culture.martial_record.find(
    (item) => item.style === culture.martial_style
  )
  return (
    <Panel
      title='Tongues, rites and war'
      icon={funeral.icon}
      tone={funeral.tone}
      hint='The tongues they pray and trade in, how they meet death and how their way of war has fared'
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/folk:grid-cols-2 @xl/folk:grid-cols-3'>
        <MiniStat
          icon={LANGUAGE_ICON}
          label='Tongue of prayer'
          value={culture.liturgical_language?.name ?? 'Their own'}
          tone='verdigris'
          hint='The old or holy tongue their priests keep alive'
        />
        <MiniStat
          icon={TRADE_ICON}
          label='Tongue of trade'
          value={culture.trade_language?.name ?? 'Their own'}
          tone='gold'
          hint='Shared with partners, it widens roads and carries knowledge'
        />
        <MiniStat
          icon={funeral.icon}
          label='Funeral rite'
          value={funeral.label}
          tone={funeral.tone}
          hint={funeral.hint}
        />
        <MiniStat
          icon={style.icon}
          label='Way of war'
          value={style.label}
          tone={style.tone}
          hint={
            culture.martial_net > 0
              ? 'Victories hold them to it'
              : culture.martial_net < 0
                ? 'Defeats may make them take up the victor’s way'
                : 'Land and knowledge shape it'
          }
        />
        <MiniStat
          icon={RECORD_ICON}
          label='Its record'
          value={`${current?.wins ?? 0} won · ${current?.losses ?? 0} lost`}
          tone={
            culture.martial_net > 0
              ? 'success'
              : culture.martial_net < 0
                ? 'danger'
                : 'muted'
          }
        />
        <MiniStat
          icon={Building}
          label='In towns'
          value={`${culture.urbanisation}%`}
          tone='verdigris'
          hint='Urban folk found towns, crowd into them and leave the fields'
        />
      </div>
      {culture.funeral_tradition && (
        <div className='flex min-w-0 items-center gap-1.5'>
          <Label variant='overline'>Kept as</Label>
          <EntityLink
            kind='entity'
            id={String(culture.funeral_tradition.id)}
            showIcon
          >
            {culture.funeral_tradition.name}
          </EntityLink>
        </div>
      )}
      {culture.martial_record.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Label variant='overline'>Ways of war tried</Label>
          <Paged items={culture.martial_record}>
            {(item) => {
              const spec = MARTIAL_SPEC[item.style]
              const Icon = spec.icon
              return (
                <Badge
                  key={item.style}
                  size='sm'
                  variant={
                    item.style === culture.martial_style ? 'default' : 'outline'
                  }
                >
                  <Icon />
                  {`${spec.label} ${item.wins}–${item.losses}`}
                </Badge>
              )
            }}
          </Paged>
        </div>
      )}
    </Panel>
  )
}

function MultiEditor({
  label,
  hint,
  icon,
  values,
  table,
  held,
  blocked,
  onSet,
}: {
  label: string
  hint: string
  icon: LucideIcon
  values: string[]
  table: Record<string, Spec>
  held: boolean
  blocked: string | null
  onSet: (values: string[]) => void
}) {
  const [draft, setDraft] = useState<string[]>(values)
  const same =
    draft.length === values.length &&
    draft.every((item) => values.includes(item))
  return (
    <EditorTile
      icon={icon}
      tone={held ? 'gold' : 'muted'}
      label={label}
      hint={hint}
      held={held}
    >
      <div className='flex min-w-0 items-center gap-2'>
        <MultiSelect
          label={label}
          className='min-w-0 flex-1'
          options={Object.entries(table).map(([key, spec]) => ({
            value: key,
            label: spec.label,
            detail: spec.hint,
          }))}
          value={draft}
          onChange={setDraft}
        />
        <Button
          variant='outline'
          size='icon'
          aria-label={`Set ${label}`}
          disabled={blocked !== null || same}
          disabledReason={
            blocked ?? (same ? 'This is the present choice.' : undefined)
          }
          onClick={() => onSet(draft)}
        >
          <Check />
        </Button>
      </div>
    </EditorTile>
  )
}

function RecordEditor({
  label,
  hint,
  icon,
  value,
  options,
  held,
  blocked,
  onSet,
}: {
  label: string
  hint: string
  icon: LucideIcon
  value: number | null
  options: { value: string; label: string }[]
  held: boolean
  blocked: string | null
  onSet: (value: number | null) => void
}) {
  return (
    <EditorTile
      icon={icon}
      tone={held ? 'gold' : 'muted'}
      label={label}
      hint={hint}
      held={held}
    >
      <RecordCombobox
        aria-label={label}
        options={options}
        value={value === null ? null : String(value)}
        placeholder='None chosen'
        clearable
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onChange={(next) => onSet(next === null ? null : Number(next))}
      />
    </EditorTile>
  )
}

export function FolkControls({
  view,
  blocked,
}: {
  view: Demography
  blocked: string | null
}) {
  const biology = view.biology
  const culture = view.culture
  const locked = [...(biology?.locked ?? []), ...(culture?.locked ?? [])]
  const peopleId = view.people_id ?? view.entity_id
  const languages = useRecordOptions('language')
  const traditions = useRecordOptions('tradition')
  const diseases = useRecordOptions('disease')
  const edit = useGodAction({
    run: ({ key, value }: { key: string; value: Value }) =>
      unwrap(
        api.POST('/api/actions/people:edit', {
          body: { people_id: peopleId, values: { [key]: value }, release: [] },
        })
      ),
    success: (_result, change) => `${folkLabel(change.key)} held`,
  })
  const release = useGodAction({
    run: (keys: string[]) =>
      unwrap(
        api.POST('/api/actions/people:edit', {
          body: { people_id: peopleId, values: {}, release: keys },
        })
      ),
    success: 'They drift with the world again',
  })
  const busy = blocked ?? (edit.isPending || release.isPending ? WORKING : null)
  const set = (key: string) => (value: Value) => edit.mutate({ key, value })
  const held = (key: string) => locked.includes(key)
  const editor = (field: NumberField) => (
    <NumberEditor
      key={`${field.key}-${field.value}`}
      id={`people-${peopleId}`}
      field={field}
      held={held(field.key)}
      blocked={blocked}
      pending={edit.isPending && edit.variables?.key === field.key}
      onSet={set(field.key)}
    />
  )
  const current = culture?.martial_record.find(
    (item) => item.style === culture.martial_style
  )
  return (
    <AdjustPanel
      title='Shape these folk'
      note='Set their body, diet, climate, customs, tongues, rites and battle record. What you set is held against the drift of the world until you release it; every change can be undone from the ledger.'
    >
      <HeldStrip
        keys={locked}
        labelOf={folkLabel}
        blocked={busy}
        onRelease={(keys) => release.mutate(keys)}
      />
      {biology && (
        <EditorGroup title='A life' icon={Hourglass} pairs>
          {LIFE_FIELDS.map((field) =>
            editor({
              key: field.key,
              label: fieldLabel(field.key),
              icon: field.icon,
              value: biology[field.key],
              min: field.min,
              max: field.max,
              unit: field.unit,
            })
          )}
        </EditorGroup>
      )}
      {biology && (
        <EditorGroup title='Body and nature' icon={Dna}>
          <ChoiceEditor
            label='Body'
            hint='Their form, which sets mounts, fleets, work and battle ground'
            value={biology.body_plan}
            table={BODY_SPEC}
            held={held('body_plan')}
            blocked={busy}
            onPick={set('body_plan')}
          />
          <ChoiceEditor
            label='Size'
            hint='Bigger folk eat and crowd more, and hit harder'
            value={biology.size_class}
            table={SIZE_CLASS_SPEC}
            held={held('size_class')}
            blocked={busy}
            onPick={set('size_class')}
          />
          <ChoiceEditor
            label='Diet'
            hint='What the land must give them to eat'
            value={biology.diet}
            table={DIET_SPEC}
            held={held('diet')}
            blocked={busy}
            onPick={set('diet')}
          />
          <ChoiceEditor
            label='Home climate'
            hint='Lands far from it sicken their armies and repel their migrants'
            value={biology.acclimatised}
            table={bandSpecs()}
            held={held('acclimatised')}
            blocked={busy}
            onPick={set('acclimatised')}
          />
          <ChoiceEditor
            label='Staple'
            hint='The food they live on'
            value={biology.staple}
            table={staplesSpecs()}
            held={held('staple')}
            blocked={busy}
            onPick={set('staple')}
          />
          <ChoiceEditor
            label='Body chemistry'
            hint='The chemistry of their body; worlds of another chemistry suit them poorly'
            value={biology.biochemistry}
            table={BIOCHEMISTRY}
            held={held('biochemistry')}
            blocked={busy}
            onPick={set('biochemistry')}
          />
          <ChoiceEditor
            label='Breath'
            hint='The air they need; a world without it cannot hold them unaided'
            value={biology.air}
            table={AIR_NEEDS}
            held={held('air')}
            blocked={busy}
            onPick={set('air')}
          />
          <MultiEditor
            key={`traits-${biology.traits.join()}`}
            label='Natural gifts'
            hint='Each changes battle, work or sickness'
            icon={Sprout}
            values={biology.traits}
            table={TRAIT_SPEC}
            held={held('traits')}
            blocked={busy}
            onSet={(values) => set('traits')(values as NaturalTrait[])}
          />
          <MultiEditor
            key={`immune-${biology.immunities.map((item) => item.id).join()}`}
            label='Immunities'
            hint='Diseases that kill few of them'
            icon={IMMUNE_ICON}
            values={biology.immunities.map((item) => String(item.id))}
            table={Object.fromEntries(
              diseases.map((item) => [
                item.value,
                { label: item.label, icon: IMMUNE_ICON },
              ])
            )}
            held={held('immunities')}
            blocked={busy}
            onSet={(values) => set('immunities')(values.map(Number))}
          />
        </EditorGroup>
      )}
      {biology && (
        <EditorGroup title='Gravity they bear' icon={Users} pairs>
          {GRAVITY_FIELDS.map((field) =>
            editor({
              key: field.key,
              label: folkLabel(field.key),
              icon: field.icon,
              value: biology[field.key],
              min: field.min,
              max: field.max,
              unit: field.unit,
            })
          )}
        </EditorGroup>
      )}
      {culture && (
        <EditorGroup title='Society' icon={Users2}>
          {SOCIETY_FIELDS.map((field) =>
            editor({
              key: field.key,
              label: fieldLabel(field.key),
              icon: field.icon,
              value: culture[field.key],
              min: field.min,
              max: field.max,
            })
          )}
        </EditorGroup>
      )}
      {culture && (
        <EditorGroup title='Customs' icon={Palette} pairs>
          <ChoiceEditor
            label='Art'
            hint='What they find beautiful; their art moves them more'
            value={culture.aesthetic}
            table={AESTHETIC_SPEC}
            held={held('aesthetic')}
            blocked={busy}
            onPick={set('aesthetic')}
          />
          <ChoiceEditor
            label='Way of war'
            hint='How their levies fight'
            value={culture.martial_style}
            table={MARTIAL_SPEC}
            held={held('martial_style')}
            blocked={busy}
            onPick={set('martial_style')}
          />
          <ChoiceEditor
            label='Marriage'
            hint='How many spouses each may take'
            value={culture.marriage}
            table={MARRIAGE_SPEC}
            held={held('marriage')}
            blocked={busy}
            onPick={set('marriage')}
          />
          <ChoiceEditor
            label='Inheritance'
            hint='Who takes the throne and the estate'
            value={culture.inheritance}
            table={INHERITANCE_SPEC}
            held={held('inheritance')}
            blocked={busy}
            onPick={set('inheritance')}
          />
          <ChoiceEditor
            label='Funeral rite'
            hint='How they meet death: ghosts, ancestors, sickness'
            value={culture.funeral_rite}
            table={FUNERAL_SPEC}
            held={held('funeral_rite')}
            blocked={busy}
            onPick={set('funeral_rite')}
          />
          <FlagEditor
            label='Marry within'
            hint='Only their own people are taken as spouses; they resist assimilation'
            icon={Users2}
            tone='verdigris'
            checked={culture.endogamous}
            held={held('endogamous')}
            blocked={busy}
            onToggle={set('endogamous')}
          />
          <FlagEditor
            label='Slavery lawful'
            hint='They may hold others in bondage'
            icon={Link}
            tone='warning'
            checked={culture.slavery_lawful}
            held={held('slavery_lawful')}
            blocked={busy}
            onToggle={set('slavery_lawful')}
          />
          <MultiEditor
            key={`staples-${culture.staples.join()}`}
            label='Staples'
            hint='The foods of their table'
            icon={Beef}
            values={culture.staples}
            table={staplesSpecs()}
            held={held('staples')}
            blocked={busy}
            onSet={set('staples')}
          />
        </EditorGroup>
      )}
      {culture && (
        <EditorGroup title='Tongues and rites' icon={LANGUAGE_ICON} pairs>
          <RecordEditor
            label='Tongue of prayer'
            hint='The tongue their priests keep'
            icon={LANGUAGE_ICON}
            value={culture.liturgical_language?.id ?? null}
            options={languages}
            held={held('liturgical_language_id')}
            blocked={busy}
            onSet={set('liturgical_language_id')}
          />
          <RecordEditor
            label='Tongue of trade'
            hint='Shared with partners, it widens roads and carries knowledge'
            icon={TRADE_ICON}
            value={culture.trade_language?.id ?? null}
            options={languages}
            held={held('trade_language_id')}
            blocked={busy}
            onSet={set('trade_language_id')}
          />
          <RecordEditor
            label='Funeral tradition'
            hint='The tradition that keeps their rite'
            icon={FUNERAL_SPEC[culture.funeral_rite].icon}
            value={culture.funeral_tradition?.id ?? null}
            options={traditions}
            held={held('funeral_rite_id')}
            blocked={busy}
            onSet={set('funeral_rite_id')}
          />
        </EditorGroup>
      )}
      {culture && (
        <EditorGroup title='Battle record' icon={RECORD_ICON} pairs>
          {[
            { key: 'martial_wins', label: 'Victories', value: current?.wins },
            { key: 'martial_losses', label: 'Defeats', value: current?.losses },
          ].map((item) => (
            <NumberEditor
              key={`${item.key}-${item.value ?? 0}`}
              id={`people-${peopleId}`}
              field={{
                key: item.key,
                label: `${item.label} as ${MARTIAL_SPEC[culture.martial_style].label.toLowerCase()}`,
                icon: RECORD_ICON,
                value: item.value ?? 0,
                min: 0,
                max: RECORD_MAX,
              }}
              held={held('martial_record')}
              blocked={blocked}
              pending={edit.isPending && edit.variables?.key === item.key}
              onSet={set(item.key)}
            />
          ))}
        </EditorGroup>
      )}
    </AdjustPanel>
  )
}

export function FoundPeoplePanel({
  view,
  blocked,
}: {
  view: Demography
  blocked: string | null
}) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [region, setRegion] = useState<string | null>(null)
  const [species, setSpecies] = useState<string | null>(null)
  const [population, setPopulation] = useState('1000')
  const [body, setBody] = useState<string>(
    view.biology?.body_plan ?? 'humanoid'
  )
  const [size, setSize] = useState<string>(view.biology?.size_class ?? 'medium')
  const [diet, setDiet] = useState<string>(view.biology?.diet ?? 'omnivore')
  const [style, setStyle] = useState<string>(
    view.culture?.martial_style ?? 'shieldwall'
  )
  const [rite, setRite] = useState<string>(
    view.culture?.funeral_rite ?? 'burial'
  )
  const [marriage, setMarriage] = useState<string>(
    view.culture?.marriage ?? 'monogamy'
  )
  const [inheritance, setInheritance] = useState<string>(
    view.culture?.inheritance ?? 'primogeniture'
  )
  const [aesthetic, setAesthetic] = useState<string>(
    view.culture?.aesthetic ?? 'austere'
  )
  const regions = useRecordOptions('region')
  const kinds = useRecordOptions('species')
  const found = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/people:found', {
          body: {
            name: name.trim(),
            region_id: Number(region),
            population: Number(population),
            species_id: species === null ? null : Number(species),
            values: {
              body_plan: body,
              size_class: size,
              diet,
              martial_style: style,
              funeral_rite: rite,
              marriage,
              inheritance,
              aesthetic,
            },
          },
        })
      ),
    success: `${name.trim()} rose as a new people`,
    onDone: () => {
      setName('')
      setOpen(false)
    },
  })
  const count = Number(population)
  const problem =
    blocked ??
    (name.trim().length < NAME_MIN
      ? 'Give them a name.'
      : region === null
        ? 'Choose the land they rise in.'
        : !Number.isInteger(count) ||
            count < POPULATION_MIN ||
            count > POPULATION_MAX
          ? `They number from ${formatInteger(POPULATION_MIN)} to ${formatInteger(POPULATION_MAX)}.`
          : found.isPending
            ? WORKING
            : null)
  const choices: {
    label: string
    value: string
    table: Record<string, Spec>
    onPick: (value: string) => void
  }[] = [
    { label: 'Body', value: body, table: BODY_SPEC, onPick: setBody },
    { label: 'Size', value: size, table: SIZE_CLASS_SPEC, onPick: setSize },
    { label: 'Diet', value: diet, table: DIET_SPEC, onPick: setDiet },
    {
      label: 'Way of war',
      value: style,
      table: MARTIAL_SPEC,
      onPick: setStyle,
    },
    {
      label: 'Funeral rite',
      value: rite,
      table: FUNERAL_SPEC,
      onPick: setRite,
    },
    {
      label: 'Marriage',
      value: marriage,
      table: MARRIAGE_SPEC,
      onPick: setMarriage,
    },
    {
      label: 'Inheritance',
      value: inheritance,
      table: INHERITANCE_SPEC,
      onPick: setInheritance,
    },
    {
      label: 'Art',
      value: aesthetic,
      table: AESTHETIC_SPEC,
      onPick: setAesthetic,
    },
  ]
  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      data-surface='FoundPeople'
      className='flex min-w-0 flex-col rounded-md sealed-well'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-3 p-3'>
        <Medallion icon={FOUND_ICON} tone='gold' size='sm' />
        <div className='flex min-w-0 flex-1 basis-48 flex-col gap-0.5'>
          <Text weight='semibold'>Found a new people</Text>
          <Muted variant='caption'>
            Raise a people of your own in any land, with its body, diet and
            customs held as you set them. It can be undone from the ledger.
          </Muted>
        </div>
        <CollapsibleTrigger asChild>
          <Button size='sm' variant={open ? 'secondary' : 'outline'}>
            <FOUND_ICON />
            {open ? 'Close' : 'Found a people'}
            <ChevronDown
              className={cn('transition-transform', open && 'rotate-180')}
            />
          </Button>
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent className='@container flex min-w-0 flex-col gap-4 border-t border-dashed p-3'>
        <div className='grid min-w-0 grid-cols-1 gap-3 @md:grid-cols-2'>
          <div className='flex min-w-0 flex-col gap-1.5'>
            <FieldLabel htmlFor='found-people-name'>Name</FieldLabel>
            <Input
              id='found-people-name'
              value={name}
              placeholder='The name they call themselves'
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className='flex min-w-0 flex-col gap-1.5'>
            <FieldLabel htmlFor='found-people-count'>How many</FieldLabel>
            <Input
              id='found-people-count'
              type='number'
              inputMode='numeric'
              min={POPULATION_MIN}
              max={POPULATION_MAX}
              value={population}
              onChange={(event) => setPopulation(event.target.value)}
            />
          </div>
          <div className='flex min-w-0 flex-col gap-1.5'>
            <Label>Land they rise in</Label>
            <RecordCombobox
              aria-label='Land they rise in'
              options={regions}
              value={region}
              placeholder='Choose a land'
              onChange={(next) => setRegion(next)}
            />
          </div>
          <div className='flex min-w-0 flex-col gap-1.5'>
            <Label>Kind they spring from</Label>
            <RecordCombobox
              aria-label='Kind they spring from'
              options={[
                { value: NONE, label: 'No kind; a folk of their own' },
                ...kinds,
              ]}
              value={species ?? NONE}
              placeholder='A folk of their own'
              onChange={(next) => setSpecies(next === NONE ? null : next)}
            />
          </div>
        </div>
        <div className='grid min-w-0 grid-cols-1 gap-3 @md:grid-cols-2 @4xl:grid-cols-4'>
          {choices.map((item) => (
            <ChoiceEditor
              key={item.label}
              label={item.label}
              hint={item.table[item.value]?.hint ?? 'Held as you set it'}
              value={item.value}
              table={item.table}
              held={false}
              blocked={found.isPending ? WORKING : null}
              onPick={item.onPick}
            />
          ))}
        </div>
        <div className='flex min-w-0 justify-end'>
          <Button
            disabled={problem !== null}
            disabledReason={problem ?? undefined}
            onClick={() => found.mutate()}
          >
            <FOUND_ICON />
            Found them
          </Button>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
