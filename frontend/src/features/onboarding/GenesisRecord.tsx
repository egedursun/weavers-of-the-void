import {
  Activity,
  AudioLines,
  Cloudy,
  Cog,
  Droplets,
  Globe,
  Hourglass,
  Languages,
  Layers,
  LayoutTemplate,
  Mountain,
  Orbit,
  Quote,
  ShieldAlert,
  Sparkles,
  Sprout,
  Thermometer,
  Users,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, MiniStat, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { humanize } from '@/features/entity/actions/schema'
import {
  type SavedGenesis,
  type WizardOptions,
  useSavedGenesis,
  useWizardOptions,
} from './api'

const SEED_CHOSE = 'Chosen by the seed'

function percentOr(value: number | null | undefined): string {
  return value === null || value === undefined
    ? SEED_CHOSE
    : `${formatInteger(value)}%`
}

function Quoted({ label, text }: { label: string; text: string | null }) {
  return (
    <div className='flex min-w-0 flex-col gap-1 rounded-xl border bg-background p-3'>
      <Label variant='overline'>{label}</Label>
      {text ? (
        <div className='flex min-w-0 items-start gap-2'>
          <Quote
            aria-hidden='true'
            className='size-icon-sm shrink-0 text-primary'
          />
          <Text italic>{text}</Text>
        </div>
      ) : (
        <Muted variant='caption'>Not given</Muted>
      )}
    </div>
  )
}

function GenesisBody({
  saved,
  options,
}: {
  saved: SavedGenesis
  options: WizardOptions | undefined
}) {
  const settings = saved.settings
  const template = settings?.template
    ? (options?.templates.find((item) => item.key === settings.template)
        ?.name ?? humanize(settings.template))
    : 'None'
  const worldKind = settings?.world_type
    ? (options?.world_types.find(
        (item) => item.world_type === settings.world_type
      )?.label ?? humanize(settings.world_type))
    : SEED_CHOSE
  const climate = settings?.climate_era
    ? (options?.climate_eras.find((item) => item.era === settings.climate_era)
        ?.label ?? humanize(settings.climate_era))
    : SEED_CHOSE
  const age = settings?.world_age
    ? (options?.world_ages[settings.world_age] ?? humanize(settings.world_age))
    : SEED_CHOSE
  const shape = settings
    ? (options?.shapes.find((item) => item.shape === settings.cosmos_shape)
        ?.label ?? humanize(settings.cosmos_shape))
    : ''
  const layer =
    settings?.cosmos_shape !== 'layered'
      ? 'None'
      : settings.layer_kind
        ? (options?.layer_kinds.find(
            (item) => item.kind === settings.layer_kind
          )?.label ?? humanize(settings.layer_kind))
        : SEED_CHOSE
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
        <Quoted label='Seed idea' text={saved.seed_idea ?? null} />
        <Quoted label='Tone' text={saved.tone ?? null} />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-2 md:grid-cols-4'>
        <MiniStat
          icon={Languages}
          label='Lore language'
          value={humanize(saved.lore_language)}
          tone='gold'
        />
        {settings && (
          <>
            <MiniStat
              icon={LayoutTemplate}
              label='Template'
              value={template}
              tone='verdigris'
            />
            <MiniStat
              icon={Sparkles}
              label='Magic'
              value={formatInteger(settings.magic)}
              tone='info'
            />
            <MiniStat
              icon={ShieldAlert}
              label='Danger'
              value={formatInteger(settings.danger)}
              tone='danger'
            />
            <MiniStat
              icon={Cog}
              label='Technology'
              value={humanize(settings.technology)}
              tone='muted'
            />
            <MiniStat
              icon={AudioLines}
              label='Language texture'
              value={humanize(settings.language_texture)}
              tone='verdigris'
            />
            <MiniStat
              icon={Users}
              label='First peoples'
              value={formatInteger(settings.peoples)}
              tone='success'
            />
            <MiniStat
              icon={Hourglass}
              label='Prehistory'
              value={
                settings.prehistory_epochs
                  ? plural(settings.prehistory_epochs, 'epoch')
                  : 'None'
              }
              tone='info'
            />
            <MiniStat
              icon={Orbit}
              label='Cosmos size'
              value={humanize(settings.cosmos_size)}
              tone='info'
            />
            <MiniStat
              icon={Orbit}
              label='Shape of the cosmos'
              value={shape}
              tone='info'
            />
            <MiniStat
              icon={Layers}
              label='Second layer'
              value={layer}
              tone='verdigris'
            />
            <MiniStat
              icon={Activity}
              label='Storyteller'
              value={humanize(settings.storyteller)}
              tone='warning'
            />
            <MiniStat
              icon={Globe}
              label='Kind of the first world'
              value={worldKind}
              tone='gold'
            />
            <MiniStat
              icon={Droplets}
              label='Water'
              value={percentOr(settings.sea_pct)}
              tone='info'
            />
            <MiniStat
              icon={Mountain}
              label='High ground'
              value={percentOr(settings.mountains_pct)}
              tone='muted'
            />
            <MiniStat
              icon={Cloudy}
              label='Moisture'
              value={
                settings.moisture_pct === null ||
                settings.moisture_pct === undefined
                  ? SEED_CHOSE
                  : formatInteger(settings.moisture_pct)
              }
              tone='verdigris'
            />
            <MiniStat
              icon={Thermometer}
              label='Climate age'
              value={climate}
              tone='warning'
            />
            <MiniStat
              icon={Hourglass}
              label='Age at the first epoch'
              value={age}
              tone='muted'
            />
          </>
        )}
      </div>
    </div>
  )
}

export function GenesisRecord() {
  const saved = useSavedGenesis()
  const options = useWizardOptions()
  return (
    <Section
      title='How this world was born'
      description='The choices made in the genesis wizard, kept with the world. They are a record; the world now grows on its own.'
      surface='card'
      icon={Sprout}
      tone='success'
    >
      {saved.isPending && <Skeleton className='h-24 w-full' />}
      {saved.isError && (
        <EmptyState
          size='compact'
          icon={Sprout}
          title='No genesis record'
          description={saved.error.message}
        />
      )}
      {saved.data && <GenesisBody saved={saved.data} options={options.data} />}
    </Section>
  )
}
