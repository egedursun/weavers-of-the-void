import { SearchIcon } from 'lucide-react'
import { useSearch } from '@/context/searchContext'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'

const isApplePlatform =
  typeof navigator !== 'undefined' &&
  /Mac|iPhone|iPad/.test(navigator.userAgent)

export function SearchButton() {
  const { setOpen } = useSearch()
  return (
    <>
      <Button
        variant='ghost'
        size='icon'
        className='@4xl/topbar:hidden'
        aria-label='Search'
        aria-keyshortcuts='Meta+K Control+K'
        onClick={() => setOpen(true)}
      >
        <SearchIcon />
      </Button>
      <Button
        variant='field'
        className='hidden w-full max-w-md justify-start text-muted-foreground hover:text-foreground @4xl/topbar:inline-flex'
        aria-keyshortcuts='Meta+K Control+K'
        onClick={() => setOpen(true)}
      >
        <SearchIcon />
        <span className='min-w-0 flex-1 truncate text-start'>
          Search sons, places and lore
        </span>
        <Kbd>{isApplePlatform ? '⌘K' : 'Ctrl K'}</Kbd>
      </Button>
    </>
  )
}
