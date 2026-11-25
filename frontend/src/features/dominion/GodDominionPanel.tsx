import { useState } from 'react'
import {
  Crown,
  Eraser,
  Eye,
  Gem,
  Minus,
  PawPrint,
  Plus,
  RotateCcw,
  Scale,
  Sparkles,
  Wand2,
} from 'lucide-react'
import { domainValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EmptyState, KpiTile, PagedList } from '@/components/domain'
import { DOMAIN_GLYPH } from '@/components/domain/domainGlyphIcons'
import { Label, Muted, Text } from '@/components/typography'
import {
  Chip,
  Facts,
  ForgeCard,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { wordOf } from '@/features/entity/affairs/labels'
import { TextField } from '@/features/entity/economy/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import {
  type DivineScale,
  type GodDominionView,
  type ScaleView,
  useDominionAction,
} from './api'
import {
  ALIGNMENTS,
  MANIFESTATIONS,
  SCALES,
  STANCES,
  leaning,
  table,
} from './labels'
import { HOME_TYPES, why } from './model'
import {
  ClaimCard,
  CreatureCard,
  MiracleCard,
  NodePicker,
  SiteCard,
  ThroneCard,
} from './parts'

const SCALE_MIN = -3
const SCALE_MAX = 3

const DOMAINS = Object.fromEntries(
  Object.keys(DOMAIN_GLYPH).map((key) => [key, words(key)])
)

function words(value: string) {
  const plain = value.replaceAll('_', ' ')
  return plain.charAt(0).toUpperCase() + plain.slice(1)
}

function ScaleRow({
  godId,
  row,
  blocked,
}: {
  godId: number
  row: ScaleView
  blocked: string | null
}) {
  const set = useDominionAction(
    'god_scale:set',
    (value: number) => ({ god_id: godId, scale: row.scale, value, hold: true }),
    'The scale is held'
  )
  const reset = useDominionAction(
    'god_scale:delete',
    (_: void) => ({ god_id: godId, scale: row.scale }),
    'The scale returns to the middle'
  )
  const busy = why(blocked, set.isPending, reset.isPending)
  const pole = leaning(row.scale, row.value)
  const spec = SCALES[row.scale]
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-2.5'>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Chip icon={spec.icon}>{spec.label}</Chip>
        <Muted variant='caption'>against</Muted>
        <Chip icon={spec.opposite.icon}>{spec.opposite.label}</Chip>
        {row.locked.length > 0 && <Badge variant='outline'>Held</Badge>}
      </div>
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <Text weight='semibold'>
          {row.value === 0
            ? 'Balanced'
            : `${pole.label} ${Math.abs(row.value)}`}
        </Text>
        <div className='flex shrink-0 items-center gap-1'>
          <Button
            act={set}
            size='icon-sm'
            variant='outline'
            aria-label={`Lean ${spec.label.toLowerCase()} toward ${spec.opposite.label.toLowerCase()}`}
            disabled={busy !== null || row.value <= SCALE_MIN}
            disabledReason={
              busy ??
              (row.value <= SCALE_MIN ? 'Already at the far end' : undefined)
            }
            onClick={() => set.mutate(row.value - 1)}
          >
            <Minus />
          </Button>
          <Button
            act={set}
            size='icon-sm'
            variant='outline'
            aria-label={`Lean ${spec.opposite.label.toLowerCase()} toward ${spec.label.toLowerCase()}`}
            disabled={busy !== null || row.value >= SCALE_MAX}
            disabledReason={
              busy ??
              (row.value >= SCALE_MAX ? 'Already at the far end' : undefined)
            }
            onClick={() => set.mutate(row.value + 1)}
          >
            <Plus />
          </Button>
          <Button
            act={reset}
            size='icon-sm'
            variant='ghost'
            aria-label={`Return ${spec.label.toLowerCase()} to the middle`}
            disabled={busy !== null || !row.stored}
            disabledReason={
              busy ?? (row.stored ? undefined : 'This scale was never set')
            }
            onClick={() => reset.mutate()}
          >
            <RotateCcw />
          </Button>
        </div>
      </div>
    </li>
  )
}

function ClaimForm({
  godId,
  blocked,
}: {
  godId: number
  blocked: string | null
}) {
  const [region, setRegion] = useState<number | null>(null)
  const [strength, setStrength] = useState('50')
  const set = useDominionAction(
    'dominion:set',
    (_: void) => ({
      god_id: godId,
      region_id: region ?? 0,
      strength: Number(strength),
      hold: true,
    }),
    'The god claims the land'
  )
  const busy = why(blocked, set.isPending)
  const missing =
    region === null
      ? 'Choose a region first'
      : strength === '' || Number.isNaN(Number(strength))
        ? 'Type a strength'
        : null
  return (
    <ForgeCard
      icon={Crown}
      tone='gold'
      title='Claim a region'
      note='Set this god’s dominion over a region and hold it against the engine.'
      columns={2}
      action={
        <Button
          act={set}
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => {
            set.mutate()
            setRegion(null)
          }}
        >
          <Crown />
          Claim
        </Button>
      }
    >
      <NodePicker
        label='Region'
        value={region}
        onChange={setRegion}
        blocked={busy}
        types={['region']}
      />
      <NumberField
        label='Dominion'
        value={strength}
        min={0}
        max={100}
        disabled={busy !== null}
        onChange={setStrength}
      />
    </ForgeCard>
  )
}

function DesignCard({
  godId,
  data,
  blocked,
}: {
  godId: number
  data: GodDominionView
  blocked: string | null
}) {
  const edit = useDominionAction(
    'god_design:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({
      god_id: godId,
      ...vars,
    }),
    'The design is set'
  )
  const remove = useDominionAction(
    'god_design:delete',
    (_: void) => ({ god_id: godId }),
    'The design will be weighed anew'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const design = data.design
  return (
    <RecordRow
      icon={Scale}
      tone='info'
      title='Design'
      caption={
        design
          ? `Weighed in epoch ${design.checked_epoch} · rank ${design.rank}`
          : 'Not weighed yet; the next epoch weighs it'
      }
      aside={
        <Button
          act={remove}
          size='sm'
          variant='ghost'
          disabled={busy !== null || design === null}
          disabledReason={
            busy ??
            (design === null ? 'There is no design to weigh anew' : undefined)
          }
          onClick={() => remove.mutate()}
        >
          <Eraser />
          Weigh anew
        </Button>
      }
    >
      {design && (
        <>
          <Meter
            label='Budget spent'
            value={design.spent}
            max={Math.max(design.budget, 1)}
            tone='warning'
          />
          <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
            <Meter
              label='Dominion strength'
              value={design.dominion_strength}
              tone='default'
              icon={Crown}
            />
            <Meter
              label='Magic aptitude'
              value={design.magic_aptitude}
              tone='verdigris'
              icon={Sparkles}
            />
            <Meter
              label='Manifestation'
              value={design.manifestation_strength}
              tone='info'
              icon={Eye}
            />
          </div>
          <Facts
            items={[
              ['Budget', String(design.budget)],
              ['Spent', String(design.spent)],
              ['Powers kept', `${design.stats_pct}% of their full measure`],
              ['Divine rank', String(design.rank)],
            ]}
          />
        </>
      )}
      <RecordEditor
        act={edit}
        title='Reshape the design'
        note='What the design spends is weighed by fate each epoch; values you set are held.'
        fields={[
          { key: 'budget', label: 'Budget', kind: 'number', min: 0 },
          {
            key: 'dominion_strength',
            label: 'Dominion strength',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'magic_aptitude',
            label: 'Magic aptitude',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'manifestation_strength',
            label: 'Manifestation',
            kind: 'number',
            min: 0,
            max: 100,
          },
          { key: 'rank', label: 'Divine rank', kind: 'number', min: 0 },
        ]}
        locked={design?.locked ?? []}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function ImageCard({
  godId,
  data,
  blocked,
}: {
  godId: number
  data: GodDominionView
  blocked: string | null
}) {
  const edit = useDominionAction(
    'god_image:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({
      god_id: godId,
      ...vars,
    }),
    'The image is set'
  )
  const remove = useDominionAction(
    'god_image:delete',
    (_: void) => ({ god_id: godId }),
    'The image will be read anew'
  )
  const busy = why(blocked, edit.isPending, remove.isPending)
  const image = data.image
  const alignment = image ? ALIGNMENTS[image.believed_alignment] : null
  const look = image ? MANIFESTATIONS[image.manifestation] : null
  const stance = image ? STANCES[image.stance] : null
  return (
    <RecordRow
      icon={alignment?.icon ?? Eye}
      tone={alignment?.tone ?? 'muted'}
      title='The image its peoples hold'
      caption={
        image
          ? `Read in epoch ${image.epoch}`
          : 'No people holds an image of this god yet'
      }
      aside={
        <Button
          act={remove}
          size='sm'
          variant='ghost'
          disabled={busy !== null || image === null}
          disabledReason={
            busy ??
            (image === null ? 'There is no image to read anew' : undefined)
          }
          onClick={() => remove.mutate()}
        >
          <Eraser />
          Read anew
        </Button>
      }
    >
      {image && alignment && look && stance && (
        <>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Chip icon={alignment.icon}>{alignment.label}</Chip>
            <Chip
              icon={look.icon}
            >{`Seen as ${look.label.toLowerCase()}`}</Chip>
            <Chip icon={stance.icon}>{stance.label}</Chip>
            {image.believed_domain && (
              <Chip icon={DOMAIN_GLYPH[image.believed_domain]}>
                {`Believed a god of ${wordOf(domainValues, image.believed_domain).toLowerCase()}`}
              </Chip>
            )}
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            <Meter
              label='Believed wrath'
              value={image.believed_wrath}
              tone='destructive'
            />
            <Meter
              label='Believed mercy'
              value={image.believed_mercy}
              tone='success'
            />
            <Meter
              label='Intensity of belief'
              value={image.intensity}
              tone='info'
            />
            <Meter
              label='Share that worships'
              value={image.worship_share}
              tone='default'
            />
            <Meter label='Crisis' value={image.crisis} tone='warning' />
            <Meter
              label='Malleability'
              value={image.malleability}
              tone='verdigris'
            />
          </div>
          <Facts
            items={[
              ['Pull each epoch', `${image.pull}%`],
              [
                'Pressure toward the believed domain',
                String(image.domain_pressure),
              ],
            ]}
          />
        </>
      )}
      <RecordEditor
        act={edit}
        title='Reshape the image'
        note='Set what the peoples believe and how the god meets it; values you set are held.'
        fields={[
          {
            key: 'believed_alignment',
            label: 'Believed alignment',
            kind: 'pick',
            table: table(ALIGNMENTS),
          },
          {
            key: 'believed_wrath',
            label: 'Believed wrath',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'believed_mercy',
            label: 'Believed mercy',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'believed_domain',
            label: 'Believed domain',
            kind: 'pick',
            table: { none: 'None', ...DOMAINS },
          },
          {
            key: 'manifestation',
            label: 'Manifestation',
            kind: 'pick',
            table: table(MANIFESTATIONS),
          },
          {
            key: 'stance',
            label: 'Stance toward belief',
            kind: 'pick',
            table: table(STANCES),
          },
        ]}
        locked={image?.locked ?? []}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function RaiseForm({
  godId,
  blocked,
}: {
  godId: number
  blocked: string | null
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [home, setHome] = useState<number | null>(null)
  const raise = useDominionAction(
    'divine_creature:raise',
    (_: void) => ({
      god_id: godId,
      name: name.trim(),
      description: description.trim(),
      home_id: home ?? 0,
    }),
    'A divine creature rises'
  )
  const busy = why(blocked, raise.isPending)
  const missing =
    name.trim() === ''
      ? 'Name the creature first'
      : home === null
        ? 'Choose its home'
        : null
  return (
    <ForgeCard
      icon={PawPrint}
      tone='verdigris'
      title='Raise a divine creature'
      note='A creature of this god that learns from its rewards and punishments which deeds to choose.'
      columns={3}
      action={
        <Button
          act={raise}
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => {
            raise.mutate()
            setName('')
            setDescription('')
            setHome(null)
          }}
        >
          <Wand2 />
          Raise
        </Button>
      }
    >
      <TextField
        label='Creature name'
        value={name}
        disabled={busy !== null}
        onChange={setName}
      />
      <TextField
        label='What it is'
        value={description}
        disabled={busy !== null}
        onChange={setDescription}
      />
      <NodePicker
        label='Home'
        value={home}
        onChange={setHome}
        blocked={busy}
        types={HOME_TYPES}
      />
    </ForgeCard>
  )
}

export function GodDominionPanel({
  data,
  blocked,
}: {
  data: GodDominionView
  blocked: string | null
}) {
  const godId = data.node.id
  const ruled = data.claims.filter((claim) => claim.ruling).length
  const total = data.claims.reduce((sum, claim) => sum + claim.strength, 0)
  const scales: Record<DivineScale, ScaleView> = Object.fromEntries(
    data.scales.map((row) => [row.scale, row])
  ) as Record<DivineScale, ScaleView>
  return (
    <div
      data-surface='GodDominionPanel'
      className='flex min-w-0 flex-col gap-3'
    >
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <KpiTile label='Regions ruled' value={ruled} icon={Crown} tone='gold' />
        <KpiTile label='Dominion held' value={total} icon={Gem} tone='info' />
        <KpiTile
          label='Thrones held'
          value={data.thrones.length}
          icon={Crown}
          tone='warning'
        />
        <KpiTile
          label='Divine creatures'
          value={data.creatures.length}
          icon={PawPrint}
          tone='verdigris'
        />
      </div>
      <Label variant='overline'>Dominion over the land</Label>
      {data.claims.length === 0 ? (
        <EmptyState
          icon={Crown}
          size='inline'
          title='No dominion anywhere yet'
          description='Temples, holy sites, prophets, miracles and worship give a god dominion; claim a region below.'
        />
      ) : (
        <PagedList
          items={data.claims}
          initial={4}
          noun={['region', 'regions']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(claim) => claim.region?.id ?? 0}
        >
          {(claim) => <ClaimCard claim={claim} focus='god' blocked={blocked} />}
        </PagedList>
      )}
      <ClaimForm godId={godId} blocked={blocked} />
      <Label variant='overline'>Scales its rule leans the land toward</Label>
      <ul className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3'>
        {Object.keys(SCALES).map((scale) => (
          <ScaleRow
            key={scale}
            godId={godId}
            row={
              scales[scale as DivineScale] ?? {
                scale: scale as DivineScale,
                value: 0,
                stored: false,
                locked: [],
              }
            }
            blocked={blocked}
          />
        ))}
      </ul>
      <DesignCard godId={godId} data={data} blocked={blocked} />
      <ImageCard godId={godId} data={data} blocked={blocked} />
      <Label variant='overline'>{`Miracles worked (${data.miracles.length})`}</Label>
      {data.miracles.length === 0 ? (
        <Muted variant='caption'>
          No miracle of this god is remembered yet.
        </Muted>
      ) : (
        <PagedList
          items={data.miracles}
          initial={3}
          noun={['miracle', 'miracles']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.id}
        >
          {(row) => <MiracleCard miracle={row} blocked={blocked} />}
        </PagedList>
      )}
      <Label variant='overline'>{`Miracles of other gods credited to it (${data.credited.length})`}</Label>
      {data.credited.length === 0 ? (
        <Muted variant='caption'>
          No one has given it the credit for another god’s work.
        </Muted>
      ) : (
        <PagedList
          items={data.credited}
          initial={3}
          noun={['miracle', 'miracles']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.id}
        >
          {(row) => <MiracleCard miracle={row} blocked={blocked} />}
        </PagedList>
      )}
      <Label variant='overline'>Divine creatures</Label>
      {data.creatures.length === 0 ? (
        <Muted variant='caption'>This god has raised no creature yet.</Muted>
      ) : (
        <PagedList
          items={data.creatures}
          initial={2}
          noun={['creature', 'creatures']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.creature?.id ?? 0}
        >
          {(row) => <CreatureCard creature={row} blocked={blocked} />}
        </PagedList>
      )}
      <RaiseForm godId={godId} blocked={blocked} />
      <Label variant='overline'>Thrones of power held</Label>
      {data.thrones.length === 0 ? (
        <Muted variant='caption'>
          It holds no throne; its dominion must rule a throne’s land to seat it.
        </Muted>
      ) : (
        <PagedList
          items={data.thrones}
          initial={3}
          noun={['throne', 'thrones']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.id}
        >
          {(row) => <ThroneCard throne={row} blocked={blocked} />}
        </PagedList>
      )}
      <Label variant='overline'>Magic sites held</Label>
      {data.sites.length === 0 ? (
        <Muted variant='caption'>It holds no magic site.</Muted>
      ) : (
        <PagedList
          items={data.sites}
          initial={3}
          noun={['site', 'sites']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(row) => row.id}
        >
          {(row) => <SiteCard site={row} blocked={blocked} />}
        </PagedList>
      )}
    </div>
  )
}
