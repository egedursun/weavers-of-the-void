import { type ReactNode } from 'react'
import { Link } from '@tanstack/react-router'
import { cn } from '@/lib/utils'
import { type Rarity } from '@/constants/rarity'
import {
  type EntryRef,
  type EntrySearch,
  parseEntryStack,
  pushEntry,
} from '@/components/layout/entry/entryStack'
import { entrySearchWith } from '@/components/layout/entry/useEntryStack'
import { ENTRY_KIND_ICON } from './entryKindIcon'
import { RARITY_TEXT_CLASS } from './rarityClasses'

type EntityLinkProps = EntryRef & {
  children: ReactNode
  rarity?: Rarity
  showIcon?: boolean
  className?: string
}

export function EntityLink({
  kind,
  id,
  children,
  rarity,
  showIcon = false,
  className,
}: EntityLinkProps) {
  const Icon = ENTRY_KIND_ICON[kind]
  return (
    <Link
      to='.'
      search={(previous: EntrySearch) =>
        entrySearchWith(
          previous,
          pushEntry(parseEntryStack(previous.entry), { kind, id })
        )
      }
      data-entity-kind={kind}
      className={cn(
        'inline-flex max-w-full min-w-0 items-baseline gap-1 rounded-sm font-medium text-primary underline-offset-4 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50',
        rarity && RARITY_TEXT_CLASS[rarity],
        className
      )}
    >
      {showIcon && (
        <Icon
          aria-hidden='true'
          className='size-icon-sm shrink-0 self-center'
        />
      )}
      <span className='min-w-0 truncate'>{children}</span>
    </Link>
  )
}
