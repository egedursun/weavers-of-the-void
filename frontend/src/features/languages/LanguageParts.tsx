import { ChevronRight, Signature } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { PagedList, Portrait } from '@/components/domain'
import { Sigil } from '@/components/domain/Sigil'
import { Label, Muted, Text } from '@/components/typography'
import { humanize } from '@/features/entity/actions/schema'
import { mediaUrl } from '@/features/pantheon/media'
import { type LanguageNode } from './languageFamilies'
import { SCRIPT_ICON, UNWRITTEN_ICON } from './languageIcons'

const COVER_WIDTH = { sm: 160, md: 160, lg: 320, xl: 640 } as const

export function LanguageSeal({
  name,
  size = 'md',
  active = false,
  cover = null,
}: {
  name: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  active?: boolean
  cover?: string | null
}) {
  if (cover)
    return (
      <Portrait
        name={name}
        src={mediaUrl(cover, COVER_WIDTH[size])}
        size={size}
        shape={size === 'xl' || size === 'lg' ? 'square' : 'circle'}
      />
    )
  return (
    <span
      className={cn(
        'flex shrink-0',
        size === 'sm' && 'size-portrait-sm',
        size === 'md' && 'size-portrait-md',
        size === 'lg' && 'size-portrait-lg',
        size === 'xl' && 'size-portrait-xl',
        active ? 'text-primary' : 'text-brand-verdigris'
      )}
    >
      <Sigil seed={name} label={`Seal of ${name}`} />
    </span>
  )
}

export function ScriptBadge({
  script,
}: {
  script: LanguageNode['writing_system']
}) {
  const Icon = script ? SCRIPT_ICON[script] : UNWRITTEN_ICON
  return (
    <Badge size='sm' variant={script ? 'info' : 'outline'}>
      <Icon />
      {script ? humanize(script) : 'Unwritten'}
    </Badge>
  )
}

export function LetterTiles({
  letters,
  label,
  emphasis = [],
}: {
  letters: string[]
  label: string
  emphasis?: string[]
}) {
  if (letters.length === 0) return null
  const strong = new Set(emphasis)
  return (
    <PagedList
      items={letters}
      initial={12}
      noun={['entry', 'entries']}
      as='ul'
      className='flex min-w-0 flex-wrap gap-1'
      listProps={{ 'aria-label': label }}
      itemKey={(letter, index) => `${letter}-${index}`}
    >
      {(letter, index) => (
        <li
          key={`${letter}-${index}`}
          className={cn(
            'flex size-control-sm items-center justify-center rounded-md border font-display',
            strong.has(letter)
              ? 'border-primary/40 bg-primary/12 text-primary'
              : 'bg-muted text-foreground'
          )}
        >
          {letter}
        </li>
      )}
    </PagedList>
  )
}

export function SoundSignature({
  signature,
}: {
  signature: LanguageNode['signature']
}) {
  if (!signature)
    return (
      <Muted variant='caption'>
        No sound signature yet; names are drawn from its world's dialect.
      </Muted>
    )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <LetterTiles
        letters={[...signature.consonants]}
        label='Favoured consonants'
        emphasis={[...signature.consonants]}
      />
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {signature.cluster && (
          <Badge
            size='sm'
            variant='outline'
          >{`Cluster ${signature.cluster}`}</Badge>
        )}
        {signature.ending && (
          <Badge
            size='sm'
            variant='outline'
          >{`Ending -${signature.ending}`}</Badge>
        )}
        <Badge size='sm' variant='outline'>
          {signature.length_bias > 0
            ? 'Long words'
            : signature.length_bias < 0
              ? 'Short words'
              : 'Even length'}
        </Badge>
      </div>
    </div>
  )
}

export function NameChips({ names }: { names: string[] }) {
  if (names.length === 0) return null
  return (
    <PagedList
      items={names}
      initial={12}
      noun={['entry', 'entries']}
      as='div'
      className='flex min-w-0 flex-wrap gap-1.5'
      itemKey={(name) => name}
    >
      {(name) => (
        <Badge key={name} variant='secondary'>
          <Signature />
          {name}
        </Badge>
      )}
    </PagedList>
  )
}

export function Lineage({
  chain,
  onSelect,
}: {
  chain: LanguageNode[]
  onSelect: (id: number) => void
}) {
  if (chain.length <= 1) return null
  return (
    <nav aria-label='Lineage' className='flex min-w-0 flex-col gap-1'>
      <Label variant='overline'>Lineage</Label>
      <PagedList
        items={chain}
        initial={12}
        noun={['entry', 'entries']}
        as='ol'
        className='flex min-w-0 flex-wrap items-center gap-1'
        itemKey={(node) => node.language.id}
      >
        {(node, index) => (
          <li
            key={node.language.id}
            className='flex min-w-0 items-center gap-1'
          >
            {index > 0 && (
              <ChevronRight
                aria-hidden='true'
                className='size-icon-xs shrink-0 text-muted-foreground'
              />
            )}
            {index === chain.length - 1 ? (
              <Text as='span' weight='semibold'>
                {node.language.name}
              </Text>
            ) : (
              <Button
                variant='link'
                size='sm'
                onClick={() => onSelect(node.language.id)}
              >
                {node.language.name}
              </Button>
            )}
          </li>
        )}
      </PagedList>
    </nav>
  )
}
