import { GitHubLogoIcon, LinkedInLogoIcon } from '@radix-ui/react-icons'
import { DEVELOPER } from '@/config/developer'
import { Crown, Quote } from 'lucide-react'
import { RARITY_LABEL } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { RarityIcon } from '@/components/domain/RarityIcon'
import { Label, SectionTitle, Text } from '@/components/typography'

const DEVELOPER_LINKS = [
  { label: 'LinkedIn', href: DEVELOPER.links.linkedin, Icon: LinkedInLogoIcon },
  { label: 'GitHub', href: DEVELOPER.links.github, Icon: GitHubLogoIcon },
] as const

const DEVELOPER_STAT_TILES = [
  { value: '99', label: 'Level' },
  { value: '∞', label: 'Curiosity' },
] as const

export function AboutDeveloper() {
  return (
    <section
      aria-labelledby='about-developer'
      className='card-foil relative flex flex-col gap-8 overflow-hidden rounded-2xl border border-brand-gold/40 bg-linear-to-br from-brand-violet/25 via-card/60 to-brand-night/80 p-6 shadow-xl shadow-brand-violet/20 sm:p-8'
    >
      <div className='flex flex-col gap-8 md:flex-row'>
        <div className='flex shrink-0 flex-col items-center gap-3'>
          <div className='relative flex size-36 items-center justify-center'>
            <span className='about-sigil-ring' aria-hidden />
            <span className='flex size-32 items-center justify-center rounded-full bg-linear-to-br from-brand-night to-brand-violet/60 shadow-inner'>
              <span className='font-brand text-display text-brand-gold drop-shadow-lg'>
                {DEVELOPER.initials}
              </span>
            </span>
          </div>
          <Badge className='gap-1.5 border-rarity-mythic/60 bg-rarity-mythic/15 text-rarity-mythic'>
            <RarityIcon rarity='mythic' />
            {RARITY_LABEL.mythic}
          </Badge>
        </div>

        <div className='flex min-w-0 flex-1 flex-col gap-5'>
          <div className='flex flex-col gap-1 text-center md:text-start'>
            <Label variant='overline' className='text-brand-gold'>
              The Weaver behind the Void
            </Label>
            <SectionTitle
              id='about-developer'
              className='font-brand text-primary'
            >
              {DEVELOPER.name}
            </SectionTitle>
            <Text tone='muted' className='text-balance'>
              <Crown
                className='me-1.5 inline size-icon-sm align-text-bottom text-brand-gold'
                aria-hidden
              />
              {`${DEVELOPER.epithet} · ${DEVELOPER.role} @ ${DEVELOPER.organization}`}
            </Text>
          </div>

          <dl className='grid grid-cols-2 gap-2'>
            {DEVELOPER_STAT_TILES.map((stat) => (
              <div
                key={stat.label}
                className='flex flex-col items-center gap-0.5 rounded-lg border border-brand-gold/25 bg-background/40 px-2 py-3 text-center'
              >
                <dd className='font-brand text-title text-brand-gold'>
                  {stat.value}
                </dd>
                <dt>
                  <Label>{stat.label}</Label>
                </dt>
              </div>
            ))}
          </dl>

          <figure className='relative flex flex-col gap-3 rounded-xl border-s-2 border-brand-gold/60 bg-background/40 p-5'>
            <Quote
              className='absolute inset-e-4 top-4 size-icon-lg text-brand-gold/30'
              aria-hidden
            />
            <blockquote className='flex flex-col gap-2 pe-8'>
              {DEVELOPER.message.map((line) => (
                <Text key={line} italic className='text-foreground/90'>
                  {line}
                </Text>
              ))}
            </blockquote>
            <figcaption>
              <Text
                as='span'
                weight='semibold'
                className='font-brand text-primary'
              >
                {`- ${DEVELOPER.firstName}`}
              </Text>
            </figcaption>
          </figure>

          <div className='flex flex-wrap justify-center gap-2 md:justify-start'>
            {DEVELOPER_LINKS.map(({ label, href, Icon }) => (
              <Button key={label} variant='outline' asChild>
                <a href={href} target='_blank' rel='noopener noreferrer'>
                  <Icon />
                  {label}
                </a>
              </Button>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
