import { useNavigate, useSearch } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import { BookOpenText, LibraryBig } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  AsideLayout,
  EmptyState,
  PageHeader,
  Section,
} from '@/components/domain'
import { DivineCrest } from '@/components/layout/divine-will/DivineCrest'
import { useWillDock } from '@/components/layout/divine-will/dockStore'
import { ArtifactBrowser } from './ArtifactBrowser'
import { ArtifactDetail } from './ArtifactDetail'
import { validateLibrarySearch } from './librarySearch'

const ITEM = navItem('library')

export function LibraryScreen() {
  const search = validateLibrarySearch(useSearch({ strict: false }))
  const navigate = useNavigate()
  const openWill = useWillDock((state) => state.setOpen)
  const setView = useWillDock((state) => state.setView)
  const selected = search.artifact ?? null
  const select = (id: number | null) =>
    void navigate({
      to: '.',
      search: (previous: Record<string, unknown>) => ({
        ...previous,
        artifact: id ?? undefined,
      }),
    })
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        actions={
          <Button
            variant='outline'
            onClick={() => {
              setView('chat')
              openWill(true)
            }}
          >
            <DivineCrest size='icon' />
            Open the Divine Will
          </Button>
        }
      />
      <AsideLayout
        side='start'
        aside={
          <Section title='Shelves' icon={LibraryBig} surface='card' level={3}>
            <ArtifactBrowser
              selected={selected}
              onSelect={(id) => select(id)}
              initialNodeId={search.subject ?? null}
            />
          </Section>
        }
      >
        <Section title='Reading' icon={BookOpenText} surface='card'>
          {selected === null ? (
            <EmptyState
              icon={BookOpenText}
              title='Choose a writing'
              description='Pick a writing from the shelves to read it, see its versions, export it or ask the Divine Will to revise it.'
            />
          ) : (
            <ArtifactDetail
              key={selected}
              artifactId={selected}
              onDeleted={() => select(null)}
            />
          )}
        </Section>
      </AsideLayout>
    </>
  )
}
