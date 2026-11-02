import { APP_NAME, APP_SUBTITLE } from '@/config/brand'
import { RARITIES } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { RarityBadge, RarityIcon, Section, Sigil } from '@/components/domain'
import { Logo } from '@/components/layout/Logo'
import { Label, Muted, Text } from '@/components/typography'
import { Row, Specimen } from './Specimen'

type Swatch = {
  name: string
  token: string
  className: string
}

const CORE_PALETTE: Swatch[] = [
  { name: 'Night sky', token: '--background', className: 'bg-background' },
  { name: 'Vellum', token: '--card', className: 'bg-card' },
  { name: 'Ink', token: '--foreground', className: 'bg-foreground' },
  { name: 'Gold', token: '--primary', className: 'bg-primary' },
  {
    name: 'Pale gold',
    token: '--brand-gold-light',
    className: 'bg-brand-gold-light',
  },
  {
    name: 'Deep gold',
    token: '--brand-gold-deep',
    className: 'bg-brand-gold-deep',
  },
  {
    name: 'Lavender',
    token: '--brand-verdigris',
    className: 'bg-brand-verdigris',
  },
  {
    name: 'Royal violet',
    token: '--brand-violet',
    className: 'bg-brand-violet',
  },
  { name: 'Magenta', token: '--brand-magenta', className: 'bg-brand-magenta' },
  { name: 'Azure', token: '--brand-azure', className: 'bg-brand-azure' },
  { name: 'Void', token: '--brand-night', className: 'bg-brand-night' },
  {
    name: 'Mist',
    token: '--muted-foreground',
    className: 'bg-muted-foreground',
  },
]

const STATUS_PALETTE: Swatch[] = [
  { name: 'Success', token: '--success', className: 'bg-success' },
  { name: 'Warning', token: '--warning', className: 'bg-warning' },
  { name: 'Danger', token: '--destructive', className: 'bg-destructive' },
  { name: 'Info', token: '--info', className: 'bg-info' },
]

const RARITY_MEANING: Record<(typeof RARITIES)[number], string> = {
  common: 'Polished pebble',
  uncommon: 'Marquise leaf',
  rare: 'Table-cut sapphire',
  epic: 'Crystal cluster',
  legendary: 'Jewelled crown',
  mythic: 'Radiant brilliant',
}

const RARITY_CLASS: Record<(typeof RARITIES)[number], string> = {
  common: 'border-rarity-common text-rarity-common',
  uncommon: 'border-rarity-uncommon text-rarity-uncommon',
  rare: 'border-rarity-rare text-rarity-rare',
  epic: 'border-rarity-epic text-rarity-epic',
  legendary: 'border-rarity-legendary text-rarity-legendary',
  mythic: 'border-rarity-mythic text-rarity-mythic',
}

const RADII = [
  { name: 'Small', className: 'rounded-sm' },
  { name: 'Medium', className: 'rounded-md' },
  { name: 'Large', className: 'rounded-lg' },
  { name: 'Extra large', className: 'rounded-xl' },
]

const ELEVATIONS = [
  { name: 'Ground', className: 'bg-background' },
  { name: 'Card', className: 'bg-card shadow-sm' },
  { name: 'Popover', className: 'bg-popover shadow-xl ring-1 ring-border' },
]

const VOICE = [
  'Mythic, never ornate: one image per sentence.',
  'Name things; the world is specific, not generic.',
  'Speak to the Creator as an equal, not a user.',
  'Numbers are facts: always show where a rule sets them.',
]

function SwatchTile({ name, token, className }: Swatch) {
  return (
    <div className='flex min-w-0 flex-col overflow-hidden rounded-lg border bg-card'>
      <span className={`h-control-lg w-full border-b ${className}`} />
      <span className='grid min-w-0 gap-1 p-3'>
        <Text as='span' weight='medium' truncate>
          {name}
        </Text>
        <Label truncate>{token}</Label>
      </span>
    </div>
  )
}

function SwatchGrid({ swatches }: { swatches: Swatch[] }) {
  return (
    <div className='grid min-w-0 grid-cols-2 gap-3 lg:grid-cols-4'>
      {swatches.map((swatch) => (
        <SwatchTile key={swatch.token} {...swatch} />
      ))}
    </div>
  )
}

export function BrandSpecimens() {
  return (
    <Section
      title='Brand'
      description='The mark, the palette and the voice of Weavers of the Void®.'
      level={3}
    >
      <Specimen name='Mark'>
        <Row>
          <Logo className='size-portrait-sm' />
          <Logo className='size-portrait-lg' />
          <Logo className='size-portrait-xl' size='md' />
          <Logo className='h-48 w-48' size='lg' />
        </Row>
      </Specimen>
      <Specimen name='Lockup'>
        <div className='flex min-w-0 flex-wrap items-center gap-6'>
          <div className='flex min-w-0 items-center gap-3'>
            <Logo className='size-portrait-lg' size='md' />
            <span className='grid min-w-0 gap-0.5'>
              <Text
                as='span'
                weight='semibold'
                truncate
                className='font-brand text-primary'
              >
                {`${APP_NAME}®`}
              </Text>
              <Label variant='overline'>{APP_SUBTITLE}</Label>
            </span>
          </div>
          <div className='dark flex items-center justify-center rounded-xl border bg-brand-night p-4'>
            <Logo className='size-portrait-xl' size='md' />
          </div>
          <div className='light flex items-center justify-center rounded-xl border bg-brand-gold-light p-4'>
            <Logo className='size-portrait-xl' size='md' />
          </div>
        </div>
        <Muted>
          Keep clear space of a quarter of the mark around it. Never recolour,
          crop, stretch or outline the mark.
        </Muted>
      </Specimen>
      <Specimen name='Core palette'>
        <SwatchGrid swatches={CORE_PALETTE} />
      </Specimen>
      <Specimen name='Status'>
        <SwatchGrid swatches={STATUS_PALETTE} />
        <Row>
          <Badge>Running</Badge>
          <Badge variant='success'>Done</Badge>
          <Badge variant='warning'>Asleep</Badge>
          <Badge variant='destructive'>Exiled</Badge>
          <Badge variant='info'>Queued</Badge>
          <Badge variant='solid'>Featured</Badge>
        </Row>
      </Specimen>
      <Specimen name='Rarity'>
        <div className='grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6'>
          {RARITIES.map((rarity) => (
            <div
              key={rarity}
              className={`flex min-w-0 flex-col items-center gap-3 rounded-xl border bg-card p-4 ${RARITY_CLASS[rarity]}`}
            >
              <RarityIcon rarity={rarity} className='size-portrait-lg' />
              <RarityBadge rarity={rarity} size='sm' />
              <span className='flex size-portrait-lg items-center justify-center'>
                <Sigil seed={`${rarity} son`} rarity={rarity} />
              </span>
              <Muted as='span' variant='caption' className='text-center'>
                {RARITY_MEANING[rarity]}
              </Muted>
            </div>
          ))}
        </div>
        <Muted>
          The icons climb from a polished pebble to a radiant brilliant; the
          sigil frame grows with the same ladder.
        </Muted>
      </Specimen>
      <Specimen name='Radius'>
        <Row>
          {RADII.map((radius) => (
            <div
              key={radius.name}
              className={`flex size-portrait-xl items-end border bg-card p-2 ${radius.className}`}
            >
              <Label truncate>{radius.name}</Label>
            </div>
          ))}
        </Row>
      </Specimen>
      <Specimen name='Elevation'>
        <Row>
          {ELEVATIONS.map((elevation) => (
            <div
              key={elevation.name}
              className={`flex size-portrait-xl items-end rounded-lg border p-2 ${elevation.className}`}
            >
              <Label truncate>{elevation.name}</Label>
            </div>
          ))}
        </Row>
      </Specimen>
      <Specimen name='Voice'>
        <ul className='flex min-w-0 flex-col gap-2'>
          {VOICE.map((line) => (
            <li key={line}>
              <Text>{line}</Text>
            </li>
          ))}
        </ul>
      </Specimen>
    </Section>
  )
}
