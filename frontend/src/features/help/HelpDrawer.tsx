import { useState } from 'react'
import { shortcutItems } from '@/config/navigation'
import {
  BookA,
  CircleHelp,
  CornerDownLeft,
  Keyboard,
  type LucideIcon,
  Search,
  X,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Input } from '@/components/ui/input'
import { Kbd } from '@/components/ui/kbd'
import { EmptyState, Paged, PageHeader, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { GLOSSARY } from './glossary'

type Shortcut = { key: string; label: string; keys: string; icon: LucideIcon }

const FIXED_SHORTCUTS: Shortcut[] = [
  {
    key: 'search',
    label: 'Search and run anything',
    keys: 'Ctrl K',
    icon: Search,
  },
  { key: 'help', label: 'This help', keys: '?', icon: CircleHelp },
  { key: 'close', label: 'Close the open window', keys: 'Esc', icon: X },
  {
    key: 'move',
    label: 'Move and open in search',
    keys: '↑ ↓ Enter',
    icon: CornerDownLeft,
  },
]

function ShortcutTile({ shortcut }: { shortcut: Shortcut }) {
  const Icon = shortcut.icon
  return (
    <li className='flex min-w-0 items-center gap-2.5 rounded-md border surface-framed border-gild/70 bg-card p-2.5'>
      <span className='flex size-control-sm shrink-0 items-center justify-center rounded-md border border-primary/25 bg-primary/10 text-primary'>
        <Icon aria-hidden='true' className='size-icon-sm' />
      </span>
      <Text as='span' truncate className='flex-1'>
        {shortcut.label}
      </Text>
      <Kbd>{shortcut.keys}</Kbd>
    </li>
  )
}

export function HelpDrawer() {
  const [query, setQuery] = useState('')
  const needle = query.trim().toLocaleLowerCase()
  const terms = GLOSSARY.filter(
    (term) =>
      !needle ||
      term.term.toLocaleLowerCase().includes(needle) ||
      term.meaning.toLocaleLowerCase().includes(needle)
  )
  const shortcuts: Shortcut[] = [
    ...FIXED_SHORTCUTS,
    ...shortcutItems().map((item) => ({
      key: item.id,
      label: item.title,
      keys: item.shortcut ?? '',
      icon: item.icon,
    })),
  ]
  return (
    <>
      <PageHeader
        title='Shortcuts and terms'
        eyebrow='Help'
        icon={CircleHelp}
      />
      <Section title='Keyboard shortcuts' level={3} icon={Keyboard}>
        <ul className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <Paged items={shortcuts} as='li'>
            {(shortcut) => (
              <ShortcutTile key={shortcut.key} shortcut={shortcut} />
            )}
          </Paged>
        </ul>
        <Muted variant='caption'>
          While you type in a text box, digits and ? are not shortcuts.
        </Muted>
      </Section>
      <Section
        title='Terms'
        description={`${plural(GLOSSARY.length, 'word', 'words')} of the game, explained.`}
        level={3}
        icon={BookA}
      >
        <Input
          type='search'
          leadingIcon={Search}
          placeholder='Find a term'
          aria-label='Find a term'
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {terms.length === 0 ? (
          <EmptyState
            size='compact'
            icon={BookA}
            title='No term matches'
            description='Try another word.'
          />
        ) : (
          <dl className='flex min-w-0 flex-col gap-2'>
            {terms.map((term) => (
              <div
                key={term.term}
                className='flex min-w-0 flex-col gap-1 rounded-md border surface-framed border-gild/70 bg-card p-3'
              >
                <Text as='dt' weight='semibold' className='font-display'>
                  {term.term}
                </Text>
                <Muted as='dd'>{term.meaning}</Muted>
              </div>
            ))}
          </dl>
        )}
      </Section>
    </>
  )
}
