import {
  CREATOR_PATH,
  GAME_PILLARS,
  GAME_PITCH,
  GAME_TAGLINE,
  RARITY_LADDER_TEXT,
  TECH_RUNES,
} from '@/config/about'
import { APP_NAME, APP_SUBTITLE, APP_VERSION } from '@/config/brand'
import { DEVELOPER } from '@/config/developer'
import {
  Compass,
  Flame,
  Gem,
  Hammer,
  Sparkles,
  WandSparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { RARITIES, RARITY_LABEL } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { RarityIcon } from '@/components/domain/RarityIcon'
import { Label, Text } from '@/components/typography'
import { Logo } from '../Logo'
import { AboutCosmos } from './AboutCosmos'
import { AboutDeveloper } from './AboutDeveloper'
import { AboutVision } from './AboutVision'
import { SectionHeading } from './aboutParts'
import { RARITY_TONE } from './aboutTone'

type AboutDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AboutDialog({ open, onOpenChange }: AboutDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className='max-h-[calc(100dvh-2rem)] gap-0 overflow-x-hidden overflow-y-auto border-brand-gold/30 bg-linear-to-b from-brand-night via-background to-brand-ink p-0 shadow-2xl sm:max-w-5xl'>
        <AboutHero />
        <div className='flex flex-col gap-14 px-5 pb-10 sm:px-10'>
          <AboutVision />
          <AboutCosmos />
          <GameLore />
          <CreatorPath />
          <RarityLadder />
          <AboutDeveloper />
          <TechRunes />
        </div>
        <footer className='flex flex-wrap items-center justify-center gap-2 border-t border-brand-gold/20 px-6 py-4 text-center'>
          <Flame className='size-icon-sm text-brand-gold' aria-hidden />
          <Label>{`Forged in the Void by ${DEVELOPER.name}`}</Label>
          <Label>·</Label>
          <Label className='font-mono'>{`v${APP_VERSION}`}</Label>
        </footer>
      </DialogContent>
    </Dialog>
  )
}

function AboutHero() {
  return (
    <header className='reveal-stage relative flex flex-col items-center gap-5 overflow-hidden px-6 pt-14 pb-10 text-center text-brand-gold'>
      <div
        className='pointer-events-none absolute inset-0 overflow-hidden mask-b-from-55%'
        aria-hidden
      >
        <div className='reveal-rays' />
        <div className='reveal-glow' />
      </div>
      <div className='reveal-float relative'>
        <Logo
          size='lg'
          title={APP_NAME}
          className='size-44 drop-shadow-2xl sm:size-64'
        />
      </div>
      <div className='reveal-rise relative flex flex-col items-center gap-2'>
        <DialogTitle className='font-brand text-display text-primary drop-shadow-lg'>
          {`${APP_NAME}®`}
        </DialogTitle>
        <DialogDescription className='text-foreground'>
          {GAME_TAGLINE}
        </DialogDescription>
      </div>
      <div className='reveal-rise-late relative flex flex-wrap items-center justify-center gap-2'>
        <Badge className='gap-1.5 border-brand-gold/50 bg-brand-gold/15 font-mono text-brand-gold'>
          <Sparkles aria-hidden />
          {`Codex v${APP_VERSION}`}
        </Badge>
        <Badge variant='outline'>{APP_SUBTITLE}</Badge>
      </div>
    </header>
  )
}

function GameLore() {
  return (
    <section aria-labelledby='about-game' className='flex flex-col gap-5'>
      <SectionHeading
        id='about-game'
        icon={WandSparkles}
        eyebrow='What is this place?'
        title='The Realm'
      />
      <Text variant='prose' className='max-w-none text-foreground/90'>
        {GAME_PITCH}
      </Text>
      <ul className='grid gap-3 sm:grid-cols-2 lg:grid-cols-3'>
        {GAME_PILLARS.map(({ title, body, icon: Icon }) => (
          <li
            key={title}
            className='group flex items-start gap-3 rounded-md border surface-framed border-brand-violet/30 bg-card p-4 transition duration-200 hover:-translate-y-0.5 hover:border-brand-gold/50 hover:shadow-lg hover:shadow-brand-violet/20'
          >
            <span className='flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-violet/20 text-brand-gold transition group-hover:scale-110'>
              <Icon className='size-icon-md' aria-hidden />
            </span>
            <div className='flex min-w-0 flex-col gap-0.5'>
              <Text weight='semibold'>{title}</Text>
              <Text variant='caption' tone='muted'>
                {body}
              </Text>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}

function CreatorPath() {
  return (
    <section aria-labelledby='about-path' className='flex flex-col gap-6'>
      <SectionHeading
        id='about-path'
        icon={Compass}
        eyebrow='How to play'
        title="The Creator's Path"
      />
      <ol className='relative grid gap-4 md:grid-cols-5 md:gap-3'>
        <span
          className='absolute top-7 right-[10%] left-[10%] hidden h-px bg-linear-to-r from-brand-gold/0 via-brand-gold/60 to-brand-gold/0 md:block'
          aria-hidden
        />
        {CREATOR_PATH.map(({ title, body, icon: Icon }, index) => (
          <li
            key={title}
            className='group relative flex items-start gap-4 md:flex-col md:items-center md:text-center'
          >
            <span className='relative flex size-14 shrink-0 items-center justify-center rounded-full border-2 border-brand-gold/60 bg-brand-night text-brand-gold shadow-lg shadow-brand-gold/20 transition duration-200 group-hover:scale-110 group-hover:border-brand-gold'>
              <Icon className='size-icon-lg' aria-hidden />
              <span className='absolute -top-1 -right-1 flex size-6 items-center justify-center rounded-full bg-brand-gold font-mono text-caption font-semibold text-brand-night'>
                {index + 1}
              </span>
            </span>
            <div className='flex min-w-0 flex-col gap-1'>
              <Text weight='semibold' className='font-brand text-primary'>
                {title}
              </Text>
              <Text variant='caption' tone='muted'>
                {body}
              </Text>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

function RarityLadder() {
  return (
    <section aria-labelledby='about-rarity' className='flex flex-col gap-5'>
      <SectionHeading
        id='about-rarity'
        icon={Gem}
        eyebrow='Card rarities'
        title='From Spark to Titan'
      />
      <Text tone='muted'>{RARITY_LADDER_TEXT}</Text>
      <ol className='grid grid-cols-3 gap-3 sm:grid-cols-6'>
        {RARITIES.map((rarity, index) => {
          const tone = RARITY_TONE[rarity]
          return (
            <li
              key={rarity}
              className={cn(
                'group flex flex-col items-center gap-2 rounded-md border surface-framed border-gild/70 bg-card px-2 py-4 text-center transition duration-200 hover:-translate-y-1 hover:shadow-lg',
                tone.border,
                tone.glow,
                index >= RARITIES.length - 2 && 'card-foil'
              )}
            >
              <span
                className={cn(
                  'flex size-12 items-center justify-center rounded-full transition duration-200 group-hover:scale-110',
                  tone.wash,
                  tone.text
                )}
              >
                <RarityIcon rarity={rarity} className='size-icon-lg' />
              </span>
              <Label variant='overline' className={tone.text}>
                {RARITY_LABEL[rarity]}
              </Label>
            </li>
          )
        })}
      </ol>
    </section>
  )
}

function TechRunes() {
  return (
    <section aria-labelledby='about-tech' className='flex flex-col gap-5'>
      <SectionHeading
        id='about-tech'
        icon={Hammer}
        eyebrow='The anvil'
        title='Forged With'
      />
      <ul className='grid grid-cols-2 gap-2 sm:grid-cols-4'>
        {TECH_RUNES.map(({ name, role, icon: Icon }) => (
          <li
            key={name}
            className='group flex items-center gap-3 rounded-md border surface-sheen border-gild/60 bg-card px-3 py-2.5 transition duration-200 hover:border-brand-gold/50'
          >
            <Icon
              className='size-icon-md shrink-0 text-brand-gold transition group-hover:rotate-12'
              aria-hidden
            />
            <div className='flex min-w-0 flex-col'>
              <Text as='span' weight='medium' truncate>
                {name}
              </Text>
              <Label truncate>{role}</Label>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
