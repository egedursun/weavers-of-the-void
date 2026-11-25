import { useState } from 'react'
import {
  Check,
  Eye,
  EyeOff,
  Gauge,
  Gem,
  Lock,
  Pickaxe,
  SlidersHorizontal,
  Recycle,
  Save,
  Sparkles,
  Sprout,
  Trash2,
  TriangleAlert,
  UserRoundCog,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { type Permission } from '@/api/teamGate'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  IconStat,
  KpiTile,
  Medallion,
  Section,
  Paged,
  LoadingBlock,
  FieldTile,
} from '@/components/domain'
import { LineChart } from '@/components/domain/LineChart'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted, Text } from '@/components/typography'
import { RESOURCE_MECHANIC_WORDS } from '@/features/entity/affairs/labels'
import { useNames } from '@/features/entity/api/queries'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { RowAction } from '../actions/RowAction'
import { MindPicker } from '../mind/parts'
import {
  AdjustPanel,
  FIELD_GRID,
  NumberField,
  PartHeader,
} from './EntityEconomy'
import { ECONOMY_REFRESH, useResourceProfile } from './api'
import {
  COMMODITY,
  type CommodityKind,
  GOODS_FAMILY,
  type KnowledgeBranch,
  MATERIAL_KINDS,
  MATERIAL_LABEL,
  type MaterialKind,
  branch,
  qualityTier,
  EXTRACTIONS,
} from './labels'
import {
  NONE,
  WORKING,
  branchChoices,
  materialRef,
  useBusy,
  useKindChoices,
  useMaterialChoices,
  whole,
} from './model'
import { ChoiceSelect, ConfirmButton, HeldBadge, ReleaseButton } from './parts'

type Profile = components['schemas']['ResourceProfileView']

const PERCENT = 100
const LOW = 4
const OWNER_TYPES = new Set([
  'people',
  'settlement',
  'faction',
  'cult',
  'polity',
  'house',
])
const FIELDS = [
  { key: 'richness', label: 'Richness', max: PERCENT },
  { key: 'extraction_difficulty', label: 'Difficulty', max: PERCENT },
  { key: 'quality', label: 'Quality', max: PERCENT },
  { key: 'regeneration', label: 'Regrowth per epoch', max: undefined },
  { key: 'byproduct_pct', label: 'By-product share %', max: PERCENT },
  { key: 'initial_reserve', label: 'First reserve', max: undefined },
] as const
const NO_MATERIAL = 'none'
const MAX_LEVEL = 20
const WORKER_TYPES = new Set(['people', 'settlement'])
const COMMODITY_CHOICES = Object.fromEntries(
  Object.entries(COMMODITY).map(([key, item]) => [key, item.label])
)
const MATERIAL_CHOICES = {
  [NO_MATERIAL]: 'No material',
  ...Object.fromEntries(
    MATERIAL_KINDS.map((item) => [item, MATERIAL_LABEL[item]])
  ),
}

function WorkingForm({
  profile,
  worldId,
  busy,
}: {
  profile: Profile
  worldId: number | null
  busy: string | null
}) {
  const [craft, setCraft] = useState<string>(profile.required_branch ?? NONE)
  const [level, setLevel] = useState(String(profile.required_level))
  const [byproduct, setByproduct] = useState<string>(
    profile.byproduct_material ?? NONE
  )
  const [share, setShare] = useState(String(profile.byproduct_pct))
  const [sealed, setSealed] = useState(
    profile.sealed_until_epoch === null
      ? ''
      : String(profile.sealed_until_epoch)
  )
  const [substance, setSubstance] = useState<string>(
    profile.world_material_id === null
      ? NONE
      : `sub:${profile.world_material_id}`
  )
  const [hold, setHold] = useState(profile.held)
  const [method, setMethod] = useState<string>(profile.extraction)
  const kinds = useKindChoices(worldId)
  const substances = Object.fromEntries(
    Object.entries(useMaterialChoices(worldId)).filter(([key]) =>
      key.startsWith('sub:')
    )
  )
  const edit = useGodAction({
    writes: [{ lever: 'resource:edit' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:edit', {
          body: {
            resource_id: profile.resource_id,
            required_level: whole(level, MAX_LEVEL),
            byproduct_pct: whole(share, PERCENT),
            sealed_until_epoch: sealed.trim() === '' ? null : whole(sealed),
            unseal: sealed.trim() === '' && profile.sealed_until_epoch !== null,
            required_branch: craft === NONE ? null : (craft as KnowledgeBranch),
            clear_branch: craft === NONE && profile.required_branch !== null,
            byproduct_material:
              byproduct === NONE ? null : (byproduct as MaterialKind),
            clear_byproduct:
              byproduct === NONE && profile.byproduct_material !== null,
            world_material_id:
              substance === NONE
                ? profile.world_material_id === null
                  ? null
                  : 0
                : materialRef(substance).world_material_id,
            extraction:
              method === profile.extraction
                ? null
                : (method as Profile['extraction']),
            hold,
          },
        })
      ),
  })
  const blocked = busy ?? (edit.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Label variant='overline'>Craft, seal and by-product</Label>
        <SwitchToggle
          permission='lock_canon'
          label='Hold what I set'
          checked={hold}
          disabled={blocked !== null}
          onChange={setHold}
        />
      </div>
      <div className={cn(FIELD_GRID, 'grid-cols-2 @lg/res:grid-cols-3')}>
        <ChoiceSelect
          label='Craft to work it'
          value={craft}
          table={branchChoices('Anyone can work it')}
          blocked={blocked}
          onPick={setCraft}
        />
        <NumberField
          label='Level of that craft'
          aria='Required level'
          value={level}
          max={MAX_LEVEL}
          onChange={setLevel}
        />
        <ChoiceSelect
          label='By-product'
          value={byproduct}
          table={{
            [NONE]: { label: 'Nothing on the side', icon: Gem, tone: 'muted' },
            ...kinds,
          }}
          blocked={blocked}
          onPick={setByproduct}
        />
        <NumberField
          label='By-product share %'
          aria='By-product share'
          value={share}
          max={PERCENT}
          onChange={setShare}
        />
        <NumberField
          label='Sealed until epoch'
          aria='Sealed until epoch'
          value={sealed}
          onChange={setSealed}
        />
        <ChoiceSelect
          label='How it is worked'
          value={method}
          table={EXTRACTIONS}
          blocked={blocked}
          onPick={setMethod}
        />
        <ChoiceSelect
          label='Substance of this world'
          value={substance}
          table={{
            [NONE]: { label: 'A common material', icon: Gem, tone: 'muted' },
            ...substances,
          }}
          blocked={blocked}
          onPick={setSubstance}
        />
      </div>
      <Muted variant='caption'>
        Leave the seal empty to open the deposit; a craft and level keep it
        closed to peoples who do not know them yet.
      </Muted>
      <Button
        act={edit}
        size='sm'
        className='self-start'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={() => edit.mutate(undefined)}
      >
        <Save />
        Set the working
      </Button>
    </div>
  )
}

function WorkersForm({
  profile,
  busy,
}: {
  profile: Profile
  busy: string | null
}) {
  const names = useNames()
  const first = profile.workers.at(0)
  const [community, setCommunity] = useState<string | null>(
    first ? String(first.community_id) : null
  )
  const [workers, setWorkers] = useState(first ? String(first.workers) : '10')
  const [hold, setHold] = useState(true)
  const set = useGodAction({
    writes: [{ lever: 'resource:workers' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:workers', {
          body: {
            resource_id: profile.resource_id,
            community_id: Number(community),
            workers: whole(workers),
            hold,
          },
        })
      ),
  })
  const blocked =
    busy ??
    (set.isPending ? WORKING : null) ??
    (community === null ? 'Choose who works it first.' : null)
  const options = (names.data ?? [])
    .filter((row) => row.kind === 'entity' && WORKER_TYPES.has(row.type))
    .map((row) => ({
      value: String(row.id),
      label: row.name,
      hint: row.type,
    }))
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Label variant='overline'>Hands at work</Label>
        <SwitchToggle
          permission='lock_canon'
          label='Hold the hands'
          checked={hold}
          disabled={busy !== null}
          onChange={setHold}
        />
      </div>
      <div className={cn(FIELD_GRID, '@lg/res:grid-cols-3')}>
        <FieldTile label='Community'>
          <RecordCombobox
            options={options}
            value={community}
            onChange={(next) => setCommunity(next)}
            placeholder='Choose who works it'
            maxShown={Math.max(1, options.length)}
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            aria-label='Working community'
          />
        </FieldTile>
        <NumberField
          label='Workers'
          aria='Workers'
          value={workers}
          onChange={setWorkers}
        />
        <Button
          act={set}
          size='sm'
          variant='outline'
          className='justify-self-start'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => set.mutate(undefined)}
        >
          <Users />
          Set the hands
        </Button>
      </div>
    </div>
  )
}

function SwitchToggle({
  label,
  permission,
  checked,
  disabled,
  onChange,
}: {
  label: string
  checked: boolean
  disabled?: boolean
  onChange: (value: boolean) => void
  permission?: Permission
}) {
  return (
    <label className='flex shrink-0 items-center gap-2'>
      <Switch
        permission={permission}
        checked={checked}
        disabled={disabled}
        onCheckedChange={onChange}
        aria-label={label}
      />
      <Text as='span'>{label}</Text>
    </label>
  )
}

function ProfileForm({
  profile,
  worldId,
  readOnlyReason,
}: {
  profile: Profile
  worldId: number | null
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const names = useNames()
  const [reserve, setReserve] = useState(String(profile.reserve))
  const [fields, setFields] = useState<Record<string, string>>(
    Object.fromEntries(
      FIELDS.map((field) => [field.key, String(profile[field.key])])
    )
  )
  const [commodity, setCommodity] = useState<string>(profile.commodity)
  const [material, setMaterial] = useState<string>(
    profile.material ?? NO_MATERIAL
  )
  const [owner, setOwner] = useState<string | null>(null)
  const save = useGodAction({
    writes: [{ lever: 'resource:set' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:set', {
          body: {
            resource_id: profile.resource_id,
            reserve: Math.max(0, Number(reserve) || 0),
            fields: Object.fromEntries(
              Object.entries(fields).map(([key, value]) => [
                key,
                Math.round(Number(value) || 0),
              ])
            ),
          },
        })
      ),
  })
  const retype = useGodAction({
    writes: [{ lever: 'resource:commodity' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:commodity', {
          body: {
            resource_id: profile.resource_id,
            commodity: commodity as CommodityKind,
            material:
              material === NO_MATERIAL ? null : (material as MaterialKind),
          },
        })
      ),
  })
  const reveal = useGodAction({
    writes: [{ lever: 'resource:reveal' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:reveal', {
          body: {
            resource_id: profile.resource_id,
            revealed: !profile.revealed,
          },
        })
      ),
  })
  const give = useGodAction({
    writes: [{ lever: 'resource:owner' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:owner', {
          body: {
            resource_id: profile.resource_id,
            owner_id: owner === null ? null : Number(owner),
          },
        })
      ),
  })
  const pending =
    save.isPending || retype.isPending || reveal.isPending || give.isPending
  const busy = readOnlyReason ?? reason() ?? (pending ? WORKING : null)
  const owners = (names.data ?? [])
    .filter((row) => row.kind === 'entity' && OWNER_TYPES.has(row.type))
    .map((row) => ({
      value: String(row.id),
      label: row.name,
      hint: row.type,
    }))
  return (
    <AdjustPanel
      acts={[save, reveal, retype, give]}
      label='Adjust the deposit'
      title='Shape this deposit'
      note='Set how much is left and how it is worked, change what it yields, reveal or hide it, or hand it to a new master. Every change goes into the ledger.'
    >
      <div className='flex min-w-0 flex-col gap-3'>
        <Label variant='overline'>Reserve and working</Label>
        <div className={cn(FIELD_GRID, 'grid-cols-2 @lg/res:grid-cols-4')}>
          <NumberField label='Reserve' value={reserve} onChange={setReserve} />
          {FIELDS.map((field) => (
            <NumberField
              key={field.key}
              label={field.label}
              value={fields[field.key]}
              max={field.max}
              onChange={(next) =>
                setFields((current) => ({ ...current, [field.key]: next }))
              }
            />
          ))}
        </div>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            act={save}
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => save.mutate(undefined)}
          >
            <Save />
            Save the reserve
          </Button>
          <Button
            act={reveal}
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => reveal.mutate(undefined)}
          >
            {profile.revealed ? <EyeOff /> : <Eye />}
            {profile.revealed ? 'Hide the deposit' : 'Reveal the deposit'}
          </Button>
        </div>
      </div>
      <div className='flex min-w-0 flex-col gap-3'>
        <Label variant='overline'>What it yields</Label>
        <div className={cn(FIELD_GRID, '@lg/res:grid-cols-3')}>
          <MindPicker
            label='It yields'
            value={commodity}
            table={COMMODITY_CHOICES}
            blocked={busy}
            onPick={setCommodity}
          />
          <MindPicker
            label='Material'
            value={material}
            table={MATERIAL_CHOICES}
            blocked={busy}
            onPick={setMaterial}
          />
          <Button
            act={retype}
            size='sm'
            variant='outline'
            className='justify-self-start'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => retype.mutate(undefined)}
          >
            <Pickaxe />
            Change what it yields
          </Button>
        </div>
      </div>
      <WorkingForm profile={profile} worldId={worldId} busy={busy} />
      <WorkersForm profile={profile} busy={busy} />
      <div className='flex min-w-0 flex-col gap-3'>
        <Label variant='overline'>Its master</Label>
        <div className={cn(FIELD_GRID, '@lg/res:grid-cols-2')}>
          <FieldTile label='New owner'>
            <RecordCombobox
              options={owners}
              value={owner}
              onChange={(next) => setOwner(next)}
              placeholder='No one: leave it unowned'
              clearable
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              aria-label='New owner'
            />
          </FieldTile>
          <Button
            act={give}
            size='sm'
            variant='outline'
            className='justify-self-start'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => give.mutate(undefined)}
          >
            <UserRoundCog />
            {owner === null ? 'Leave it unowned' : 'Give it away'}
          </Button>
        </div>
      </div>
    </AdjustPanel>
  )
}

function Summary({
  profile,
  readOnlyReason,
}: {
  profile: Profile
  readOnlyReason?: string | null
}) {
  const names = useNames()
  const release = useGodAction({
    writes: [{ lever: 'resource:release' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:release', {
          body: { resource_id: profile.resource_id },
        })
      ),
  })
  const remove = useGodAction({
    writes: [{ lever: 'resource:delete' }],
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:delete', {
          body: { resource_id: profile.resource_id },
        })
      ),
  })
  const freeWorker = useGodAction({
    writes: [{ lever: 'resource:workers' }],
    invalidate: ECONOMY_REFRESH,
    run: (community: number) =>
      unwrap(
        api.POST('/api/actions/resource:workers', {
          body: {
            resource_id: profile.resource_id,
            community_id: community,
            workers: null,
            hold: false,
          },
        })
      ),
  })
  const busy = useBusy(
    readOnlyReason,
    release.isPending,
    remove.isPending,
    freeWorker.isPending
  )
  const gated = profile.knowledge_gated ?? []
  const spec = COMMODITY[profile.commodity]
  const family = GOODS_FAMILY[spec.family]
  const tier = qualityTier(profile.quality)
  const low = profile.reserve * LOW < profile.initial_reserve
  const renewable = profile.regeneration > 0
  const needs = profile.required_branch ? branch(profile.required_branch) : null
  const title = `${profile.material_label ? `${profile.material_label} ` : ''}${spec.label.toLowerCase()}`
  const ownerName = (id: number) =>
    names.data?.find((row) => row.kind === 'entity' && row.id === id)?.name ??
    `Record ${id}`
  const meter = (value: number, label: string) => ({
    value,
    max: PERCENT,
    label,
  })
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='flex min-w-0 flex-wrap items-center gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'>
        <Medallion icon={spec.icon} tone={family.tone} />
        <div className='flex min-w-0 flex-1 basis-48 flex-col gap-1.5'>
          <Text weight='semibold' truncate>
            {title.charAt(0).toUpperCase() + title.slice(1)}
          </Text>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            {renewable ? (
              <Badge size='sm' variant='success'>
                <Recycle />
                Renewable
              </Badge>
            ) : (
              <Badge size='sm' variant='outline'>
                <Gauge />
                Finite
              </Badge>
            )}
            {profile.revealed ? (
              <Badge size='sm' variant='info'>
                <Eye />
                Known
              </Badge>
            ) : (
              <Badge size='sm' variant='warning'>
                <EyeOff />
                Hidden: no one knows of it yet
              </Badge>
            )}
            {profile.sealed_until_epoch !== null && (
              <Badge size='sm' variant='destructive'>
                <Lock />
                {`Sealed after a cave-in until epoch ${profile.sealed_until_epoch}`}
              </Badge>
            )}
            {needs && (
              <Badge size='sm' variant='outline'>
                <needs.icon />
                {`Needs ${needs.label.toLowerCase()} ${profile.required_level}`}
              </Badge>
            )}
            <HeldBadge held={profile.held} />
            {profile.byproduct_material && (
              <Badge size='sm' variant='default'>
                <Gem />
                {`${profile.byproduct_pct}% ${MATERIAL_LABEL[profile.byproduct_material].toLowerCase()} on the side`}
              </Badge>
            )}
          </div>
        </div>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <ReleaseButton
            act={release}
            held={profile.held}
            busy={busy}
            onRelease={() => release.mutate(undefined)}
          />
          <ConfirmButton
            act={remove}
            icon={Trash2}
            label='Unmake the deposit'
            title='Unmake this deposit?'
            description='It vanishes from the land: no one can work it again and what was left in it is lost.'
            confirm='Unmake it'
            busy={busy}
            onConfirm={() => remove.mutate(undefined)}
          />
        </div>
      </div>
      {gated.length > 0 && (
        <div
          role='status'
          className='flex min-w-0 items-start gap-3 rounded-md border surface-framed border-warning/40 bg-warning/5 p-3'
        >
          <TriangleAlert
            aria-hidden='true'
            className='size-icon-md shrink-0 text-warning'
          />
          <Text tone='warning'>
            {`${needs ? `Needs ${needs.label.toLowerCase()} ${profile.required_level}` : 'Needs a craft'} — the people of ${gated.map(ownerName).join(', ')} do not know it yet; it yields nothing to them.`}
          </Text>
        </div>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/res:grid-cols-2 @xl/res:grid-cols-3'>
        <KpiTile
          label='Reserve left'
          value={formatInteger(profile.reserve)}
          icon={Pickaxe}
          tone={low ? 'danger' : 'gold'}
          valueTone={low ? 'destructive' : 'default'}
          meter={{
            value: profile.reserve,
            max: Math.max(1, profile.initial_reserve),
            label: 'Reserve left',
          }}
          hint={`Of ${formatInteger(profile.initial_reserve)} when first found${low ? '; nearly worked out' : ''}`}
        />
        <KpiTile
          label='Taken last epoch'
          value={formatInteger(profile.last_output)}
          icon={Users}
          tone='info'
          hint={`${plural(
            profile.workers.reduce((sum, row) => sum + row.workers, 0),
            'hand',
            'hands'
          )} at work`}
        />
        <KpiTile
          label='Regrowth'
          value={formatInteger(profile.regeneration)}
          icon={Sprout}
          tone={renewable ? 'success' : 'muted'}
          hint={
            renewable ? 'Returns to the reserve each epoch' : 'Never grows back'
          }
        />
        <KpiTile
          label='Richness'
          value={profile.richness}
          icon={Sparkles}
          tone='gold'
          meter={meter(profile.richness, 'Richness')}
          hint='How much each pair of hands brings up'
        />
        <KpiTile
          label='Difficulty'
          value={profile.extraction_difficulty}
          icon={TriangleAlert}
          tone='danger'
          meter={meter(profile.extraction_difficulty, 'Difficulty')}
          hint='Hard seams slow the work and cave in'
        />
        <KpiTile
          label='Quality'
          value={tier.label}
          icon={Gem}
          tone={tier.tone}
          meter={meter(profile.quality, 'Quality')}
          hint={`${profile.quality} of 100 for what it yields`}
        />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @xl/res:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
          <PartHeader
            icon={Users}
            title='Who works it'
            tone='info'
            note={
              profile.workers.length === 0
                ? 'No one works it now.'
                : `${profile.workers.length} ${profile.workers.length === 1 ? 'community' : 'communities'} at work`
            }
          />
          <Paged items={profile.workers}>
            {(row) => (
              <div
                key={row.community_id}
                className='flex min-w-0 items-center gap-2'
              >
                <EntityLink
                  kind='entity'
                  id={String(row.community_id)}
                  className='min-w-0 flex-1 truncate'
                >
                  {row.community_name}
                </EntityLink>
                <IconStat
                  icon={Users}
                  label='Workers'
                  value={`${plural(row.workers, 'worker', 'workers')}`}
                  tone='info'
                />
                <HeldBadge held={row.held} />
                <ReleaseButton
                  act={freeWorker}
                  held={row.held}
                  busy={busy}
                  onRelease={() => freeWorker.mutate(row.community_id)}
                />
              </div>
            )}
          </Paged>
        </div>
        <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
          <PartHeader
            icon={UserRoundCog}
            title='Its masters'
            tone='gold'
            note={
              profile.owners.length === 0
                ? 'Unowned: any people may work it.'
                : 'Who holds the right to work it'
            }
          />
          <Paged items={profile.owners}>
            {(id) => (
              <div key={id} className='flex min-w-0 items-center gap-2'>
                <Check
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-primary'
                />
                <EntityLink kind='entity' id={String(id)}>
                  {ownerName(id)}
                </EntityLink>
              </div>
            )}
          </Paged>
        </div>
      </div>
    </div>
  )
}

function Workings({
  resourceId,
  params,
}: {
  resourceId: number
  params: components['schemas']['MechanicParamView'][]
}) {
  if (params.length === 0) return null
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>Workings</Label>
      <ul className='flex min-w-0 flex-col gap-2'>
        <Paged items={params} as='li'>
          {(param) => (
            <li
              key={param.mechanic}
              className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'
            >
              <SlidersHorizontal
                aria-hidden='true'
                className='size-icon-xs text-muted-foreground'
              />
              <Text as='span' weight='medium'>
                {RESOURCE_MECHANIC_WORDS[param.mechanic]}
              </Text>
              <Badge size='sm' variant='secondary'>
                {param.magnitude === null
                  ? 'Default strength'
                  : `Strength ${param.magnitude}`}
              </Badge>
              <Badge size='sm' variant='outline'>
                {param.epochs === null
                  ? 'Default pace'
                  : `Every ${plural(param.epochs, 'epoch', 'epochs')}`}
              </Badge>
              <RowAction
                path='/api/actions/resource:mechanic'
                icon={SlidersHorizontal}
                label='Tune this working'
                iconOnly
                fixed={{ resource_id: resourceId, mechanic: param.mechanic }}
                defaults={{
                  magnitude: param.magnitude,
                  epochs: param.epochs,
                }}
                labels={{
                  magnitude: 'Strength (empty for the rule default)',
                  epochs: 'Epochs between effects (empty for the rule default)',
                }}
              />
            </li>
          )}
        </Paged>
      </ul>
    </div>
  )
}

export function ResourceProfile({
  resourceId,
  worldId = null,
  readOnlyReason,
}: {
  resourceId: number
  worldId?: number | null
  readOnlyReason?: string | null
}) {
  const view = useResourceProfile(resourceId)
  return (
    <Section
      id='section-resource-profile'
      title='Reserve and extraction'
      description='How much is left, who works it, how hard and dangerous it is, and what each epoch took out.'
      icon={Pickaxe}
    >
      {view.isPending && <LoadingBlock label='Loading the reserve' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The reserve could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='ResourceProfile'
          className='@container/res flex min-w-0 flex-col gap-5'
        >
          <Summary profile={view.data} readOnlyReason={readOnlyReason} />
          <Workings resourceId={resourceId} params={view.data.params} />
          {view.data.runs.length > 1 ? (
            <LineChart
              title='Taken out per epoch'
              label='Taken out per epoch'
              height={120}
              series={[
                {
                  key: 'output',
                  label: 'Taken out',
                  color: 'var(--chart-1)',
                  points: view.data.runs.map((run) => ({
                    x: run.epoch,
                    y: run.quantity,
                  })),
                },
              ]}
            />
          ) : (
            <Muted variant='caption'>
              The yield chart appears after two epochs of work.
            </Muted>
          )}
          <ProfileForm
            key={`${view.data.reserve}-${view.data.commodity}-${view.data.revealed}-${view.data.held}-${view.data.required_level}-${view.data.required_branch}-${view.data.sealed_until_epoch}-${view.data.byproduct_material}-${view.data.world_material_id}`}
            profile={view.data}
            worldId={worldId}
            readOnlyReason={readOnlyReason}
          />
        </div>
      )}
    </Section>
  )
}
