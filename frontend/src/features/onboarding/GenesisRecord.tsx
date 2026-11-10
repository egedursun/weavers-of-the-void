import {
  Activity,
  AudioLines,
  Cog,
  Languages,
  LayoutTemplate,
  Moon,
  Orbit,
  Quote,
  Sparkles,
  Sprout,
  Users,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, MiniStat, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { humanize } from '@/features/entity/actions/schema'
import { type SavedGenesis, useSavedGenesis } from './api'

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

function GenesisBody({ saved }: { saved: SavedGenesis }) {
  const settings = saved.settings
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
              value={settings.template ? humanize(settings.template) : 'None'}
              tone='verdigris'
            />
            <MiniStat
              icon={Sparkles}
              label='Magic'
              value={formatInteger(settings.magic)}
              tone='info'
            />
            <MiniStat
              icon={Moon}
              label='Darkness'
              value={formatInteger(settings.darkness)}
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
              icon={Orbit}
              label='Cosmos size'
              value={humanize(settings.cosmos_size)}
              tone='info'
            />
            <MiniStat
              icon={Activity}
              label='Storyteller'
              value={humanize(settings.storyteller)}
              tone='warning'
            />
          </>
        )}
      </div>
    </div>
  )
}

export function GenesisRecord() {
  const saved = useSavedGenesis()
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
      {saved.data && <GenesisBody saved={saved.data} />}
    </Section>
  )
}
