import { type ReactNode, useState } from 'react'
import {
  Biohazard,
  FlaskConical,
  Plus,
  RotateCcw,
  Sparkles,
  Trash2,
  Unlock,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { LineChart } from '@/components/domain/LineChart'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { useEntityType } from '@/features/arcana/model'
import {
  Chip,
  Facts,
  ForgeCard,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { PACKAGE_LOOKS } from '@/features/entity/body/afflictionLabels'
import { MindPicker } from '@/features/entity/mind/parts'
import { STAGE } from '@/features/entity/wilds/labels'
import { Ref } from '@/features/gatherings/parts'
import {
  type CarrierView,
  type CureResearchView,
  type EvolvedTrait,
  type HerdRef,
  type KeystoneRole,
  type LandAct,
  type LineageMarkView,
  type NodeEvolutionView,
  type PlagueResponse,
  type PlagueResponseView,
  type ServiceView,
  type TraitView,
  useEvolutionAction,
  useNodeEvolution,
} from './api'
import {
  CYCLES,
  EVOLUTION_ICON,
  KEYSTONES,
  LAND_ACTS,
  LEVELS,
  MARK_ICONS,
  RESPONSES,
  STAGES,
  TRAITS,
} from './labels'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }

const BOOLEAN = { true: 'Yes', false: 'No' }
const COMMUNITY_TYPES = ['people', 'settlement']
const PACKAGES = Object.fromEntries(
  Object.entries(PACKAGE_LOOKS).map(([key, value]) => [key, value.label])
)
const KEYSTONE_CHOICES = { none: 'No keystone role', ...table(KEYSTONES) }
const STAGE_CHOICES = table(STAGES)

function TraitCard({
  trait,
  blocked,
}: {
  trait: TraitView
  blocked: string | null
}) {
  const keys = {
    species_id: trait.species?.id ?? 0,
    region_id: trait.region?.id ?? 0,
    trait: trait.trait,
  }
  const edit = useEvolutionAction(
    'species_trait:edit',
    (vars: Edit) => ({ ...keys, ...vars }),
    'The trait is set'
  )
  const remove = useEvolutionAction(
    'species_trait:delete',
    (_: void) => keys,
    'The trait is drawn anew'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const spec = TRAITS[trait.trait]
  return (
    <RecordRow
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={
        <>
          <Ref node={trait.species} empty='a lost kind' />
          {' in '}
          <Ref node={trait.region} empty='a lost land' />
          {` · moved in epoch ${trait.updated_epoch}`}
        </>
      }
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => remove.mutate()}
        >
          <RotateCcw />
          Draw anew
        </Button>
      }
    >
      <Meter label='Mean' value={trait.mean} tone='success' />
      <Chip>{`Spread ${trait.variance}`}</Chip>
      <RecordEditor
        title='Set the trait'
        note='A held trait no longer moves under selection.'
        fields={[
          { key: 'mean', label: 'Mean', kind: 'number', min: 0, max: 100 },
          {
            key: 'variance',
            label: 'Spread',
            kind: 'number',
            min: 0,
            max: 50,
          },
        ]}
        locked={trait.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function TraitForm({
  speciesId,
  regionId,
  blocked,
}: {
  speciesId: number | null
  regionId: number | null
  blocked: string | null
}) {
  const [species, setSpecies] = useState<number | null>(speciesId)
  const [region, setRegion] = useState<number | null>(regionId)
  const [trait, setTrait] = useState<EvolvedTrait>('speed')
  const [mean, setMean] = useState('60')
  const set = useEvolutionAction(
    'species_trait:set',
    (_: void) => ({
      species_id: species ?? 0,
      region_id: region ?? 0,
      trait,
      mean: Math.max(0, Math.min(100, Number(mean) || 0)),
    }),
    'The trait is set and held'
  )
  const missing =
    species === null || region === null
      ? 'Choose a species and the land its stock lives in'
      : null
  const busy = why(blocked ?? missing, set.isPending)
  return (
    <ForgeCard
      icon={TRAITS[trait].icon}
      tone='verdigris'
      title='Set a trait of a stock'
      note='Each land holds its own stock of a species, and each stock its own traits.'
      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => set.mutate()}
        >
          <Plus />
          Set it
        </Button>
      }
    >
      <NodePicker
        label='Species'
        value={species}
        onChange={setSpecies}
        blocked={blocked}
        types={['species']}
      />
      <NodePicker
        label='Land of the stock'
        value={region}
        onChange={setRegion}
        blocked={blocked}
        types={['region']}
      />
      <MindPicker
        label='Trait'
        value={trait}
        table={table(TRAITS)}
        blocked={blocked}
        onPick={(value) => setTrait(value as EvolvedTrait)}
      />
      <MindPicker
        label='Mean'
        value={mean}
        table={{ '20': '20', '40': '40', '60': '60', '80': '80', '100': '100' }}
        blocked={blocked}
        onPick={setMean}
      />
    </ForgeCard>
  )
}

function MarkCard({
  speciesId,
  mark,
  blocked,
}: {
  speciesId: number
  mark: LineageMarkView
  blocked: string | null
}) {
  const keys = { species_id: speciesId, package: mark.package }
  const edit = useEvolutionAction(
    'lineage:edit',
    (vars: Edit) => ({ ...keys, ...vars }),
    'The mark is set'
  )
  const remove = useEvolutionAction(
    'lineage:delete',
    (_: void) => keys,
    'The line is free of the mark'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  return (
    <RecordRow
      icon={mark.blessing ? MARK_ICONS.blessing : MARK_ICONS.taint}
      tone={mark.blessing ? 'gold' : 'danger'}
      title={PACKAGES[mark.package] ?? mark.package}
      caption={
        <>
          {mark.blessing ? 'A blessing' : 'A taint'}
          {` since epoch ${mark.epoch} · from `}
          <Ref node={mark.source} empty='the land itself' />
        </>
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
          Lift
        </Button>
      }
    >
      <RecordEditor
        title='Reshape the mark'
        note='Every young of the line, its breeds and the beasts born of it carry the mark.'
        fields={[
          {
            key: 'blessing',
            label: 'A blessing',
            kind: 'pick',
            table: BOOLEAN,
          },
          {
            key: 'source_node_id',
            label: 'Given by (node id)',
            kind: 'number',
            min: 1,
          },
        ]}
        locked={mark.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function MarkForm({
  speciesId,
  blocked,
}: {
  speciesId: number | null
  blocked: string | null
}) {
  const [species, setSpecies] = useState<number | null>(speciesId)
  const [mark, setMark] = useState('divine_blessing')
  const [blessing, setBlessing] = useState('true')
  const add = useEvolutionAction(
    'lineage:mark',
    (_: void) => ({
      species_id: species ?? 0,
      package: mark as LineageMarkView['package'],
      blessing: blessing === 'true',
    }),
    'The line carries the mark'
  )
  const busy = why(
    blocked ?? (species === null ? 'Choose a species to mark' : null),
    add.isPending
  )
  return (
    <ForgeCard
      icon={MARK_ICONS.blessing}
      tone='gold'
      title='Mark a line'
      note='The mark passes from parent to young.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => add.mutate()}
        >
          <Sparkles />
          Mark it
        </Button>
      }
    >
      <NodePicker
        label='Species'
        value={species}
        onChange={setSpecies}
        blocked={blocked}
        types={['species']}
      />
      <MindPicker
        label='Mark'
        value={mark}
        table={PACKAGES}
        blocked={blocked}
        onPick={setMark}
      />
      <MindPicker
        label='A blessing'
        value={blessing}
        table={BOOLEAN}
        blocked={blocked}
        onPick={setBlessing}
      />
    </ForgeCard>
  )
}

function SpeciesCard({
  speciesId,
  data,
  blocked,
}: {
  speciesId: number
  data: NonNullable<NodeEvolutionView['species']>
  blocked: string | null
}) {
  const edit = useEvolutionAction(
    'species_ecology:edit',
    (vars: Edit) => ({ species_id: speciesId, ...vars }),
    'The species is set'
  )
  const busy = why(blocked, edit.isPending)
  const role = data.keystone ? KEYSTONES[data.keystone] : null
  const level = data.trophic_level ? LEVELS[data.trophic_level] : null
  return (
    <RecordRow
      icon={role?.icon ?? EVOLUTION_ICON}
      tone={role?.tone ?? 'muted'}
      title={role ? `${role.label} of its lands` : 'No keystone role'}
      caption={
        level ? `${level.label} in the food chain` : 'Outside the food chain'
      }
    >
      <Facts
        items={[
          ['Kept stage', STAGE[data.stage]?.label ?? data.stage],
          [
            'Went feral',
            data.feral_epoch !== null && data.feral_epoch !== undefined
              ? `in epoch ${data.feral_epoch}`
              : 'never',
          ],
        ]}
      />
      <RecordEditor
        title='Reshape its place'
        note='A keystone serves every land its stock lives in; a feral kind steps back toward the wild.'
        fields={[
          {
            key: 'keystone',
            label: 'Keystone role',
            kind: 'pick',
            table: KEYSTONE_CHOICES,
          },
          {
            key: 'feral_epoch',
            label: 'Went feral in epoch',
            kind: 'number',
            min: 0,
          },
        ]}
        locked={data.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function ServiceCard({
  service,
  blocked,
}: {
  service: ServiceView
  blocked: string | null
}) {
  const keys = { region_id: service.region?.id ?? 0, role: service.role }
  const edit = useEvolutionAction(
    'ecosystem_service:edit',
    (vars: Edit) => ({ ...keys, ...vars }),
    'The service is set'
  )
  const remove = useEvolutionAction(
    'ecosystem_service:delete',
    (_: void) => keys,
    'The service is struck'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const spec = KEYSTONES[service.role]
  return (
    <RecordRow
      icon={spec.icon}
      tone={service.strength > 0 ? spec.tone : 'danger'}
      title={service.strength > 0 ? spec.label : `${spec.label} lost`}
      caption={
        <>
          <Ref node={service.region} empty='a lost land' />
          {' · by '}
          <Ref node={service.species} empty='no kind now' />
          {` · epoch ${service.epoch}`}
        </>
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
          Strike
        </Button>
      }
    >
      <Meter label='Strength' value={service.strength} tone='success' />
      <RecordEditor
        title='Set the service'
        note='A held service keeps its strength whatever the species do.'
        fields={[
          {
            key: 'strength',
            label: 'Strength',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'species_entity_id',
            label: 'Keystone species (id)',
            kind: 'number',
            min: 1,
          },
        ]}
        locked={service.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function ServiceForm({
  regionId,
  blocked,
}: {
  regionId: number | null
  blocked: string | null
}) {
  const [region, setRegion] = useState<number | null>(regionId)
  const [role, setRole] = useState<KeystoneRole>('pollinator')
  const [strength, setStrength] = useState('60')
  const set = useEvolutionAction(
    'ecosystem_service:set',
    (_: void) => ({ region_id: region ?? 0, role, strength: Number(strength) }),
    'The service is set'
  )
  const busy = why(
    blocked ?? (region === null ? 'Choose the land it serves' : null),
    set.isPending
  )
  return (
    <ForgeCard
      icon={KEYSTONES[role].icon}
      tone='verdigris'
      title='Give a land a service'
      note='Pollinators raise harvests, soil-makers the soil, dam-builders the wetland and scavengers keep sickness away.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => set.mutate()}
        >
          <Plus />
          Give it
        </Button>
      }
    >
      <NodePicker
        label='Land'
        value={region}
        onChange={setRegion}
        blocked={blocked}
        types={['region']}
      />
      <MindPicker
        label='Service'
        value={role}
        table={table(KEYSTONES)}
        blocked={blocked}
        onPick={(value) => setRole(value as KeystoneRole)}
      />
      <MindPicker
        label='Strength'
        value={strength}
        table={{ '20': '20', '40': '40', '60': '60', '80': '80', '100': '100' }}
        blocked={blocked}
        onPick={setStrength}
      />
    </ForgeCard>
  )
}

function HerdCard({
  herd,
  blocked,
}: {
  herd: HerdRef
  blocked: string | null
}) {
  const release = useEvolutionAction(
    'herd:release',
    (_: void) => ({
      community_id: herd.community?.id ?? 0,
      species_id: herd.species?.id ?? 0,
    }),
    'The herd goes loose'
  )
  const busy = why(blocked, release.isPending)
  return (
    <RecordRow
      icon={STAGE[herd.stage]?.icon ?? EVOLUTION_ICON}
      tone='verdigris'
      title={<Ref node={herd.species} empty='a lost kind' />}
      caption={
        <>
          {`${herd.head} head, ${STAGE[herd.stage]?.label ?? herd.stage}, kept by `}
          <Ref node={herd.community} />
        </>
      }
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => release.mutate()}
        >
          <Unlock />
          Loose it
        </Button>
      }
    />
  )
}

function LandCard({
  regionId,
  land,
  blocked,
}: {
  regionId: number
  land: NonNullable<NodeEvolutionView['land']>
  blocked: string | null
}) {
  const set = useEvolutionAction(
    'environment:set',
    (vars: { field: string; value: number | string }) => ({
      region_id: regionId,
      field: vars.field,
      value: vars.value,
      lock: true,
    }),
    'The land is set'
  )
  const unlock = useEvolutionAction(
    'environment:unlock',
    (field: string) => ({ region_id: regionId, field }),
    'The land follows the world again'
  )
  const busy = why(blocked, set.isPending, unlock.isPending)
  const stage = STAGES[land.succession]
  return (
    <RecordRow
      icon={stage.icon}
      tone={stage.tone}
      title={stage.label}
      caption={
        land.burned_epoch !== null && land.burned_epoch !== undefined
          ? `Last burned in epoch ${land.burned_epoch}`
          : 'Never burned'
      }
    >
      <Meter
        label='Toward its next stage'
        value={land.succession_progress}
        tone='success'
      />
      <Chip>{`Forest it can hold: ${land.stage_cover}`}</Chip>
      <RecordEditor
        title='Set the stage'
        note='A held stage does not grow, burn or get cleared.'
        fields={[
          {
            key: 'succession',
            label: 'Stage',
            kind: 'pick',
            table: STAGE_CHOICES,
          },
          {
            key: 'succession_progress',
            label: 'Toward the next stage',
            kind: 'number',
            min: 0,
            max: 100,
          },
        ]}
        locked={land.locked}
        busy={busy}
        onSave={(values) => {
          for (const [field, value] of Object.entries(values)) {
            if (value !== null && typeof value !== 'boolean')
              set.mutate({ field, value })
          }
        }}
        onRelease={(release) => {
          for (const field of release) unlock.mutate(field)
        }}
      />
    </RecordRow>
  )
}

function ShapeForm({
  regionId,
  blocked,
}: {
  regionId: number | null
  blocked: string | null
}) {
  const [act, setAct] = useState<LandAct>('raise_land')
  const [target, setTarget] = useState<number | null>(null)
  const [fiery, setFiery] = useState('false')
  const shape = useEvolutionAction(
    'land:reshape',
    (_: void) => ({
      region_id: regionId ?? 0,
      act,
      target_region_id: target,
      fiery: fiery === 'true',
    }),
    'The land is reshaped'
  )
  const busy = why(
    blocked ?? (regionId === null ? 'Only a land can be reshaped' : null),
    shape.isPending
  )
  return (
    <ForgeCard
      icon={LAND_ACTS[act].icon}
      tone='gold'
      title='Reshape the land'
      note='A raised or lowered land keeps the height you give it; its folk hold you in awe when you water or raise it and dread you when you drown or burn it.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => shape.mutate()}
        >
          <Sparkles />
          Do it
        </Button>
      }
    >
      <MindPicker
        label='Act'
        value={act}
        table={table(LAND_ACTS)}
        blocked={regionId === null ? 'Only a land can be reshaped' : blocked}
        onPick={(value) => setAct(value as LandAct)}
      />
      <NodePicker
        label='River flows into'
        value={target}
        onChange={setTarget}
        blocked={
          act === 'shift_river'
            ? blocked
            : 'Only a moved river needs a land to flow into'
        }
        types={['region']}
      />
      <MindPicker
        label='Fiery soil'
        value={fiery}
        table={BOOLEAN}
        blocked={
          act === 'enrich_soil' ? blocked : 'Only enriched soil can be fiery'
        }
        onPick={setFiery}
      />
    </ForgeCard>
  )
}

function PathogenCard({
  diseaseId,
  pathogen,
  blocked,
}: {
  diseaseId: number
  pathogen: NonNullable<NodeEvolutionView['pathogen']>
  blocked: string | null
}) {
  const edit = useEvolutionAction(
    'disease:edit',
    (vars: { values: Record<string, number>; release: string[] }) => ({
      disease_id: diseaseId,
      ...vars,
    }),
    'The sickness is set'
  )
  const busy = why(blocked, edit.isPending)
  return (
    <RecordRow
      icon={Biohazard}
      tone='danger'
      title='How it has changed'
      caption='Diseases bear the cold or heat of the lands they spread in and resist those who treat them'
    >
      <Meter
        label='Cold tolerance'
        value={pathogen.cold_tolerance}
        tone='info'
      />
      <Meter
        label='Heat tolerance'
        value={pathogen.heat_tolerance}
        tone='warning'
      />
      <Meter label='Resistance' value={pathogen.resistance} tone='warning' />
      <RecordEditor
        title='Reshape the sickness'
        note='Resistance blunts cures, hospitals and treatment.'
        fields={[
          {
            key: 'cold_tolerance',
            label: 'Cold tolerance',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'heat_tolerance',
            label: 'Heat tolerance',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'resistance',
            label: 'Resistance',
            kind: 'number',
            min: 0,
            max: 100,
          },
        ]}
        locked={pathogen.locked}
        busy={busy}
        onSave={(values) =>
          edit.mutate({
            values: Object.fromEntries(
              Object.entries(values).filter(
                (entry): entry is [string, number] =>
                  typeof entry[1] === 'number'
              )
            ),
            release: [],
          })
        }
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function CarrierCard({
  carrier,
  blocked,
}: {
  carrier: CarrierView
  blocked: string | null
}) {
  const keys = {
    mortal_id: carrier.mortal?.id ?? 0,
    disease_id: carrier.disease?.id ?? 0,
  }
  const edit = useEvolutionAction(
    'carrier:edit',
    (vars: Edit) => ({ ...keys, ...vars }),
    'The carrier is set'
  )
  const remove = useEvolutionAction(
    'carrier:delete',
    (_: void) => keys,
    'The carrier is freed'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  return (
    <RecordRow
      icon={Biohazard}
      tone={carrier.identified ? 'info' : 'danger'}
      title={<Ref node={carrier.mortal} empty='a lost mortal' />}
      caption={
        <>
          {'Carries '}
          <Ref node={carrier.disease} empty='a lost sickness' />
          {` since epoch ${carrier.since_epoch} · last seen near `}
          <Ref node={carrier.home_region} empty='no land' />
        </>
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
          Free
        </Button>
      }
    >
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Chip variant={carrier.identified ? 'success' : 'warning'}>
          {carrier.identified ? 'Found by physicians' : 'Unseen'}
        </Chip>
        <Chip>{`${carrier.seeded} outbreaks seeded`}</Chip>
      </div>
      <RecordEditor
        title='Reshape the carrier'
        note='A found carrier spreads the sickness no further.'
        fields={[
          {
            key: 'identified',
            label: 'Found by physicians',
            kind: 'pick',
            table: BOOLEAN,
          },
          {
            key: 'seeded',
            label: 'Outbreaks seeded',
            kind: 'number',
            min: 0,
          },
        ]}
        locked={carrier.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function CarrierForm({
  mortalId,
  diseaseId,
  blocked,
}: {
  mortalId: number | null
  diseaseId: number | null
  blocked: string | null
}) {
  const [mortal, setMortal] = useState<number | null>(mortalId)
  const [disease, setDisease] = useState<number | null>(diseaseId)
  const add = useEvolutionAction(
    'carrier:add',
    (_: void) => ({ mortal_id: mortal ?? 0, disease_id: disease ?? 0 }),
    'The mortal carries it unseen'
  )
  const busy = why(
    blocked ??
      (mortal === null || disease === null
        ? 'Choose a mortal and a sickness'
        : null),
    add.isPending
  )
  return (
    <ForgeCard
      icon={Biohazard}
      tone='danger'
      title='Make a carrier'
      note='A carrier falls ill of nothing and seeds the sickness wherever it travels.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => add.mutate()}
        >
          <Plus />
          Make it so
        </Button>
      }
    >
      <NodePicker
        label='Mortal'
        value={mortal}
        onChange={setMortal}
        blocked={blocked}
        types={['mortal']}
      />
      <NodePicker
        label='Sickness'
        value={disease}
        onChange={setDisease}
        blocked={blocked}
        types={['disease']}
      />
    </ForgeCard>
  )
}

function ResponseCard({
  response,
  blocked,
}: {
  response: PlagueResponseView
  blocked: string | null
}) {
  const keys = {
    community_id: response.community?.id ?? 0,
    disease_id: response.disease?.id ?? 0,
    response: response.response,
  }
  const edit = useEvolutionAction(
    'plague_response:edit',
    (vars: Edit) => ({ ...keys, ...vars }),
    'The answer is set'
  )
  const remove = useEvolutionAction(
    'plague_response:delete',
    (_: void) => keys,
    'The answer is lifted'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const spec = RESPONSES[response.response]
  return (
    <RecordRow
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={
        <>
          <Ref node={response.community} empty='a lost community' />
          {' against '}
          <Ref node={response.disease} empty='a lost sickness' />
          {` · since epoch ${response.since_epoch}${response.until_epoch !== null && response.until_epoch !== undefined ? `, until epoch ${response.until_epoch}` : ''}`}
        </>
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
          Lift
        </Button>
      }
    >
      <Meter label='Strength' value={response.strength} tone='success' />
      <RecordEditor
        title='Reshape the answer'
        note='A held answer does not lapse.'
        fields={[
          {
            key: 'strength',
            label: 'Strength',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'until_epoch',
            label: 'Lasts until epoch',
            kind: 'number',
            min: 0,
          },
        ]}
        locked={response.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function ResponseForm({
  communityId,
  diseaseId,
  blocked,
}: {
  communityId: number | null
  diseaseId: number | null
  blocked: string | null
}) {
  const [community, setCommunity] = useState<number | null>(communityId)
  const [disease, setDisease] = useState<number | null>(diseaseId)
  const [response, setResponse] = useState<PlagueResponse>('quarantine')
  const set = useEvolutionAction(
    'plague_response:set',
    (_: void) => ({
      community_id: community ?? 0,
      disease_id: disease ?? 0,
      response,
    }),
    'The community answers the sickness'
  )
  const busy = why(
    blocked ??
      (community === null || disease === null
        ? 'Choose a community and a sickness'
        : null),
    set.isPending
  )
  return (
    <ForgeCard
      icon={RESPONSES[response].icon}
      tone='info'
      title='Set an answer to a sickness'
      note='Each answer has its price: lost trade, riots, grief, stigma or crowds.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => set.mutate()}
        >
          <Plus />
          Set it
        </Button>
      }
    >
      <NodePicker
        label='Community'
        value={community}
        onChange={setCommunity}
        blocked={blocked}
        types={COMMUNITY_TYPES}
      />
      <NodePicker
        label='Sickness'
        value={disease}
        onChange={setDisease}
        blocked={blocked}
        types={['disease']}
      />
      <MindPicker
        label='Answer'
        value={response}
        table={table(RESPONSES)}
        blocked={blocked}
        onPick={(value) => setResponse(value as PlagueResponse)}
      />
    </ForgeCard>
  )
}

function ResearchCard({
  research,
  blocked,
}: {
  research: CureResearchView
  blocked: string | null
}) {
  const keys = {
    institution_id: research.institution?.id ?? 0,
    disease_id: research.disease?.id ?? 0,
  }
  const edit = useEvolutionAction(
    'cure_research:edit',
    (vars: Edit) => ({ ...keys, ...vars }),
    'The search is set'
  )
  const remove = useEvolutionAction(
    'cure_research:delete',
    (_: void) => keys,
    'The search is abandoned'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const cured =
    research.cured_epoch !== null && research.cured_epoch !== undefined
  return (
    <RecordRow
      icon={FlaskConical}
      tone={cured ? 'success' : 'info'}
      title={
        <>
          {'A cure for '}
          <Ref node={research.disease} empty='a lost sickness' />
        </>
      }
      caption={
        <>
          {'At '}
          <Ref node={research.institution} empty='a lost house of learning' />
          {` · begun in epoch ${research.started_epoch}${cured ? ` · found in epoch ${research.cured_epoch}` : ''}`}
        </>
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
          Abandon
        </Button>
      }
    >
      <Meter
        label={`Research of ${research.threshold}`}
        value={research.points}
        max={research.threshold}
        tone='success'
      />
      <Chip>{`${research.specimens} specimens studied`}</Chip>
      <RecordEditor
        title='Reshape the search'
        note='At the threshold the cure is found and belongs to the institution’s community.'
        fields={[
          { key: 'points', label: 'Research', kind: 'number', min: 0 },
          {
            key: 'specimens',
            label: 'Specimens',
            kind: 'number',
            min: 0,
          },
        ]}
        locked={research.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function ResearchForm({
  institutionId,
  diseaseId,
  blocked,
}: {
  institutionId: number | null
  diseaseId: number | null
  blocked: string | null
}) {
  const [institution, setInstitution] = useState<number | null>(institutionId)
  const [disease, setDisease] = useState<number | null>(diseaseId)
  const start = useEvolutionAction(
    'cure_research:start',
    (_: void) => ({
      institution_id: institution ?? 0,
      disease_id: disease ?? 0,
    }),
    'The learned take up the search'
  )
  const busy = why(
    blocked ??
      (institution === null || disease === null
        ? 'Choose a hospital, academy or monastery and a sickness'
        : null),
    start.isPending
  )
  return (
    <ForgeCard
      icon={FlaskConical}
      tone='success'
      title='Seek a cure'
      note='Scholars of medicine, specimens from outbreaks and a true theory of contagion speed the search.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => start.mutate()}
        >
          <Plus />
          Begin
        </Button>
      }
    >
      <NodePicker
        label='House of learning'
        value={institution}
        onChange={setInstitution}
        blocked={blocked}
        types={['structure']}
      />
      <NodePicker
        label='Sickness'
        value={disease}
        onChange={setDisease}
        blocked={blocked}
        types={['disease']}
      />
    </ForgeCard>
  )
}

function CycleCard({
  worldId,
  cycle,
  blocked,
}: {
  worldId: number | null
  cycle: NodeEvolutionView['cycle']
  blocked: string | null
}) {
  const edit = useEvolutionAction(
    'world_cycle:edit',
    (vars: Edit) => ({ world_id: worldId ?? 0, ...vars }),
    'The cycles are set'
  )
  const reset = useEvolutionAction(
    'world_cycle:reset',
    (_: void) => ({ world_id: worldId ?? 0 }),
    'The cycles return to balance'
  )
  const busy = why(
    blocked ?? (worldId === null ? 'Only a world has cycles of its own' : null),
    edit.isPending,
    reset.isPending
  )
  return (
    <RecordRow
      icon={CYCLES.carbon.icon}
      tone='info'
      title='Cycles of the world'
      caption={
        cycle
          ? `Turned in epoch ${cycle.updated_epoch}; 50 is balance`
          : 'In balance; the engine turns them from the next epoch'
      }
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null || !cycle}
          disabledReason={
            busy ?? (cycle ? undefined : 'The cycles are already in balance')
          }
          onClick={() => reset.mutate()}
        >
          <RotateCcw />
          Balance
        </Button>
      }
    >
      {cycle && (
        <>
          <Meter
            label={CYCLES.carbon.label}
            value={cycle.carbon}
            tone='warning'
          />
          <Meter label={CYCLES.water.label} value={cycle.water} tone='info' />
          <Meter
            label={CYCLES.nutrients.label}
            value={cycle.nutrients}
            tone='success'
          />
          <Facts
            items={[
              [
                'Carbon in and out',
                `${cycle.carbon_in} in, ${cycle.carbon_out} out`,
              ],
              [
                'Water in and out',
                `${cycle.water_in} in, ${cycle.water_out} out`,
              ],
              [
                'Nutrients in and out',
                `${cycle.nutrients_in} in, ${cycle.nutrients_out} out`,
              ],
            ]}
          />
        </>
      )}
      <RecordEditor
        title='Set the cycles'
        note='Carbon above balance warms every land, free water swells rain and seas, nutrients enrich the soil.'
        fields={[
          { key: 'carbon', label: 'Carbon', kind: 'number', min: 0, max: 100 },
          { key: 'water', label: 'Water', kind: 'number', min: 0, max: 100 },
          {
            key: 'nutrients',
            label: 'Nutrients',
            kind: 'number',
            min: 0,
            max: 100,
          },
        ]}
        locked={cycle?.locked ?? []}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function Listed<T>({
  title,
  items,
  empty,
  noun,
  itemKey,
  children,
}: {
  title: string
  items: T[]
  empty: string
  noun: [string, string]
  itemKey: (item: T) => string | number
  children: (item: T) => ReactNode
}) {
  return (
    <>
      <Label variant='overline'>{`${title} (${items.length})`}</Label>
      {items.length === 0 ? (
        <Muted variant='caption'>{empty}</Muted>
      ) : (
        <PagedList
          items={items}
          initial={3}
          noun={noun}
          className='flex min-w-0 flex-col gap-2'
          itemKey={itemKey}
        >
          {children}
        </PagedList>
      )}
    </>
  )
}

const HISTORY_COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
  'var(--color-info)',
  'var(--color-warning)',
  'var(--color-destructive)',
] as const
const PATHOGEN_TRAITS: Record<string, string> = {
  virulence: 'Virulence',
  lethality: 'Lethality',
  cold_tolerance: 'Cold tolerance',
  heat_tolerance: 'Heat tolerance',
  resistance: 'Resistance to treatment',
}

function traitLabel(trait: string): string {
  return (
    TRAITS[trait as keyof typeof TRAITS]?.label ??
    PATHOGEN_TRAITS[trait] ??
    trait.replaceAll('_', ' ')
  )
}

function TraitHistory({ history }: { history: NodeEvolutionView['history'] }) {
  const traits = [...new Set(history.map((point) => point.trait))]
  const epochs = new Set(history.map((point) => point.epoch))
  if (traits.length === 0)
    return (
      <Muted variant='caption'>
        Only species and sicknesses keep a record of how their traits changed.
      </Muted>
    )
  if (epochs.size < 2)
    return (
      <Muted variant='caption'>
        The record of its traits fills in as the epochs pass.
      </Muted>
    )
  return (
    <LineChart
      title='Traits over the epochs'
      label='Traits over the epochs'
      height={180}
      max={100}
      series={traits.map((trait, index) => ({
        key: trait,
        label: traitLabel(trait),
        color: HISTORY_COLORS[index % HISTORY_COLORS.length],
        points: history
          .filter((point) => point.trait === trait)
          .map((point) => ({ x: point.epoch, y: point.value })),
      }))}
    />
  )
}

function EvolutionBody({
  data,
  type,
  blocked,
}: {
  data: NodeEvolutionView
  type: string | null
  blocked: string | null
}) {
  const nodeId = data.node.id
  const isSpecies = type === 'species'
  const isRegion = type === 'region'
  const isDisease = type === 'disease'
  const isWorld = data.node.kind === 'world'
  const isCommunity = type !== null && COMMUNITY_TYPES.includes(type)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <KpiTile
          label='Traits carried'
          value={data.traits.length}
          icon={EVOLUTION_ICON}
          tone='verdigris'
        />
        <KpiTile
          label='Land services'
          value={data.services.length}
          icon={KEYSTONES.pollinator.icon}
          tone='gold'
        />
        <KpiTile
          label='Carriers'
          value={data.carriers.length}
          icon={Biohazard}
          tone='danger'
        />
        <KpiTile
          label='Searches for a cure'
          value={data.research.length}
          icon={FlaskConical}
          tone='success'
        />
      </div>
      <TraitHistory history={data.history} />
      {data.species ? (
        <SpeciesCard speciesId={nodeId} data={data.species} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          Keystone roles and feral pasts belong to species.
        </Muted>
      )}
      <Listed
        title='Traits of its stocks'
        items={data.traits}
        empty='No stock here carries traits of its own yet.'
        noun={['trait', 'traits']}
        itemKey={(row) => `${row.species?.id}-${row.region?.id}-${row.trait}`}
      >
        {(row) => <TraitCard trait={row} blocked={blocked} />}
      </Listed>
      <TraitForm
        speciesId={isSpecies ? nodeId : null}
        regionId={isRegion ? nodeId : null}
        blocked={blocked}
      />
      <Listed
        title='Marks on its line'
        items={data.marks}
        empty='Its line carries no blessing or taint.'
        noun={['mark', 'marks']}
        itemKey={(row) => row.package}
      >
        {(row) => <MarkCard speciesId={nodeId} mark={row} blocked={blocked} />}
      </Listed>
      <MarkForm speciesId={isSpecies ? nodeId : null} blocked={blocked} />
      <Listed
        title='Services to the land'
        items={data.services}
        empty='No keystone serves here.'
        noun={['service', 'services']}
        itemKey={(row) => `${row.region?.id}-${row.role}`}
      >
        {(row) => <ServiceCard service={row} blocked={blocked} />}
      </Listed>
      <ServiceForm regionId={isRegion ? nodeId : null} blocked={blocked} />
      <Listed
        title='Food chain'
        items={data.trophic}
        empty='The food chain is counted for lands.'
        noun={['level', 'levels']}
        itemKey={(row) => row.level}
      >
        {(row) => (
          <RecordRow
            icon={LEVELS[row.level].icon}
            tone={row.biomass > row.cap ? 'danger' : LEVELS[row.level].tone}
            title={LEVELS[row.level].label}
            caption={`Counted in epoch ${row.epoch}${row.biomass > row.cap ? ' · above its bound, it starves' : ''}`}
          >
            <Meter
              label={`Life of ${row.cap} it can hold`}
              value={row.biomass}
              max={Math.max(row.cap, row.biomass, 1)}
              tone='success'
            />
          </RecordRow>
        )}
      </Listed>
      {data.land ? (
        <LandCard regionId={nodeId} land={data.land} blocked={blocked} />
      ) : (
        <Muted variant='caption'>Stages of growth belong to lands.</Muted>
      )}
      <ShapeForm regionId={isRegion ? nodeId : null} blocked={blocked} />
      <Listed
        title='Herds'
        items={data.herds}
        empty='No herd is kept here.'
        noun={['herd', 'herds']}
        itemKey={(row) => `${row.community?.id}-${row.species?.id}`}
      >
        {(row) => <HerdCard herd={row} blocked={blocked} />}
      </Listed>
      {data.pathogen ? (
        <PathogenCard
          diseaseId={nodeId}
          pathogen={data.pathogen}
          blocked={blocked}
        />
      ) : (
        <Muted variant='caption'>
          Tolerance and resistance belong to sicknesses.
        </Muted>
      )}
      <Listed
        title='Carriers'
        items={data.carriers}
        empty='No one carries a sickness unseen here.'
        noun={['carrier', 'carriers']}
        itemKey={(row) => `${row.mortal?.id}-${row.disease?.id}`}
      >
        {(row) => <CarrierCard carrier={row} blocked={blocked} />}
      </Listed>
      <CarrierForm
        mortalId={type === 'mortal' ? nodeId : null}
        diseaseId={isDisease ? nodeId : null}
        blocked={blocked}
      />
      <Listed
        title='Answers to sickness'
        items={data.responses}
        empty='No community answers a sickness here.'
        noun={['answer', 'answers']}
        itemKey={(row) =>
          `${row.community?.id}-${row.disease?.id}-${row.response}`
        }
      >
        {(row) => <ResponseCard response={row} blocked={blocked} />}
      </Listed>
      <ResponseForm
        communityId={isCommunity ? nodeId : null}
        diseaseId={isDisease ? nodeId : null}
        blocked={blocked}
      />
      <Listed
        title='Searches for a cure'
        items={data.research}
        empty='No house of learning seeks a cure here.'
        noun={['search', 'searches']}
        itemKey={(row) => `${row.institution?.id}-${row.disease?.id}`}
      >
        {(row) => <ResearchCard research={row} blocked={blocked} />}
      </Listed>
      <ResearchForm
        institutionId={type === 'structure' ? nodeId : null}
        diseaseId={isDisease ? nodeId : null}
        blocked={blocked}
      />
      <CycleCard
        worldId={isWorld ? nodeId : null}
        cycle={data.cycle}
        blocked={blocked}
      />
    </div>
  )
}

export function EvolutionSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeEvolution(nodeId)
  const type = useEntityType(nodeId)
  return (
    <Section
      id='section-evolution'
      title='Evolution and sickness'
      description='Traits of each stock, niches and food chains, keystone services, feral herds and marked lines; how sicknesses change, who carries them, how folk answer them and the search for cures; the stages of each land and the cycles of each world.'
      icon={EVOLUTION_ICON}
      tone='verdigris'
    >
      <div
        data-surface='EvolutionSection'
        className='flex min-w-0 flex-col gap-3'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the living world' />
        ) : query.isError ? (
          <EmptyState
            icon={EVOLUTION_ICON}
            size='inline'
            title='The living world could not be read'
            description={query.error.message}
          />
        ) : (
          <EvolutionBody
            data={query.data}
            type={type}
            blocked={readOnlyReason}
          />
        )}
      </div>
    </Section>
  )
}
