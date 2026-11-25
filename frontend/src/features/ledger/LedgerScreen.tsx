import { useState } from 'react'
import { navItem } from '@/config/navigation'
import { Bookmark, NotebookPen, StickyNote } from 'lucide-react'
import { storedItem, storeItem, universeKey } from '@/lib/universeStorage'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader, Section } from '@/components/domain'
import { useNotifications } from '@/features/notifications/api'
import { ActionLedger } from './ActionLedger'
import { Bookmarks } from './Bookmarks'
import { MyNotes } from './MyNotes'
import { useFavorites, useNotes } from './api'

const ITEM = navItem('ledger')
const TAB_KEY = 'aerona.records-tab'
const NOTE_COUNT_LIMIT = 50
const TABS = ['ledger', 'notes', 'bookmarks'] as const
type RecordsTab = (typeof TABS)[number]

function storedTab(): RecordsTab {
  try {
    const value = storedItem(universeKey(TAB_KEY))
    return TABS.find((tab) => tab === value) ?? 'ledger'
  } catch {
    return 'ledger'
  }
}

export function LedgerScreen() {
  const [tab, setTab] = useState<RecordsTab>(storedTab)
  const favorites = useFavorites()
  const notes = useNotes()
  const selfNotes = useNotifications({
    category: 'note',
    unreadOnly: false,
    limit: NOTE_COUNT_LIMIT,
    before: null,
  })
  const noteCount =
    (notes.data?.entity_notes.length ?? 0) +
    (notes.data?.map_notes.length ?? 0) +
    (selfNotes.data?.items.length ?? 0)
  const choose = (value: string) => {
    const next = TABS.find((item) => item === value) ?? 'ledger'
    setTab(next)
    try {
      storeItem(universeKey(TAB_KEY), next)
    } catch {
      return
    }
  }
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
      />
      <Tabs
        value={tab}
        onValueChange={choose}
        className='flex min-w-0 flex-col gap-6'
      >
        <TabsList aria-label='Your records' className='w-full md:w-fit'>
          <TabsTrigger value='ledger'>
            <NotebookPen />
            Ledger
          </TabsTrigger>
          <TabsTrigger value='notes'>
            <StickyNote />
            Notes
            <Badge size='sm' variant='outline'>
              {noteCount}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value='bookmarks'>
            <Bookmark />
            Bookmarks
            <Badge size='sm' variant='outline'>
              {favorites.data?.length ?? 0}
            </Badge>
          </TabsTrigger>
        </TabsList>
        <TabsContent value='ledger'>
          <Section title='Action ledger' surface='card'>
            <ActionLedger />
          </Section>
        </TabsContent>
        <TabsContent value='notes'>
          <MyNotes />
        </TabsContent>
        <TabsContent value='bookmarks'>
          <Bookmarks />
        </TabsContent>
      </Tabs>
    </>
  )
}
