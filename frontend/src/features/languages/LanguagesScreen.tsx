import { useCallback, useMemo, useState } from 'react'
import { getRouteApi } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import {
  BookA,
  BookPlus,
  BookText,
  Crown,
  Feather,
  FlaskConical,
  GitBranch,
  Languages,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  WholeWord,
} from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { MiniStat, PageHeader } from '@/components/domain'
import { Text } from '@/components/typography'
import { BOOK_URL } from '@/features/chronicle/api'
import {
  useKnowledge,
  useLanguageTree,
  useLanguageViews,
  useWorldState,
} from '@/features/entity/api/queries'
import { READ_ONLY_REASON } from '@/features/pantheon/gate'
import { Dictionary } from './Dictionary'
import { KnowledgeTree } from './KnowledgeTree'
import { LanguageTree } from './LanguageTree'
import { NameHealth } from './NameHealth'
import { TongueAtlas } from './TongueAtlas'
import { useEpochWords } from './api'
import { buildFamilies } from './languageFamilies'
import { COSMIC_BRANCHES, tierNumeral } from './languageIcons'
import { type LanguageViewKey, type LanguagesSearch } from './languagesSearch'
import { tierOf } from './treeLayout'

const ITEM = navItem('languages')
const route = getRouteApi('/_app/languages')
const EVERY_WORLD = '__every__'

export function LanguagesScreen() {
  const search = route.useSearch()
  const navigate = route.useNavigate()
  const state = useWorldState()
  const languages = useLanguageViews()
  const tree = useLanguageTree()
  const knowledge = useKnowledge()
  const [world, setWorld] = useState<number | null>(null)
  const change = useCallback(
    (patch: Partial<LanguagesSearch>) =>
      void navigate({
        search: (previous) => ({ ...previous, ...patch }),
        replace: true,
      }),
    [navigate]
  )
  const worlds = state.data?.worlds ?? []
  const inWorld = useCallback(
    (worldId: number) => world === null || worldId === world,
    [world]
  )
  const shownLanguages = useMemo(
    () =>
      (languages.data ?? []).filter((item) => inWorld(item.language.world_id)),
    [languages.data, inWorld]
  )
  const shownNodes = useMemo(
    () => (tree.data ?? []).filter((item) => inWorld(item.language.world_id)),
    [tree.data, inWorld]
  )
  const shownKnowledge = useMemo(
    () =>
      (knowledge.data ?? []).filter((item) => inWorld(item.knowledge.world_id)),
    [knowledge.data, inWorld]
  )
  const covers = useMemo(
    () =>
      new Map(
        (languages.data ?? []).map((item) => [item.language.id, item.cover])
      ),
    [languages.data]
  )
  const words = shownLanguages.reduce((sum, item) => sum + item.word_total, 0)
  const familyCount = useMemo(
    () => buildFamilies(shownNodes).families.length,
    [shownNodes]
  )
  const written = shownNodes.filter((node) => node.writing_system).length
  const topTier = shownKnowledge.reduce(
    (best, item) => Math.max(best, tierOf(item)),
    0
  )
  const cosmic = new Set(
    shownKnowledge
      .map((item) => item.branch)
      .filter((branch) => branch !== null && COSMIC_BRANCHES.includes(branch))
  ).size
  const readOnlyReason = state.data?.read_only ? READ_ONLY_REASON : null
  const epochWords = useEpochWords()
  const view = search.view ?? 'dictionary'
  const failure = languages.error ?? tree.error ?? knowledge.error
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
        meta={
          <>
            <Badge variant='outline'>{`${formatInteger(shownLanguages.length)} languages`}</Badge>
            <Badge variant='outline'>{`${formatInteger(words)} words`}</Badge>
            <Badge variant='outline'>{`${formatInteger(shownKnowledge.length)} known arts`}</Badge>
          </>
        }
        actions={
          <>
            {worlds.length > 1 && (
              <Select
                value={world === null ? EVERY_WORLD : String(world)}
                onValueChange={(value) =>
                  setWorld(value === EVERY_WORLD ? null : Number(value))
                }
              >
                <SelectTrigger aria-label='World' size='sm'>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={EVERY_WORLD}>Every world</SelectItem>
                  {worlds.map((item) => (
                    <SelectItem key={item.id} value={String(item.id)}>
                      {item.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            <Button
              variant='outline'
              size='sm'
              disabled={readOnlyReason !== null || epochWords.isPending}
              disabledReason={readOnlyReason ?? 'Working on it.'}
              title="Tongues take in the names of this epoch's new records now, as they do when the epoch turns."
              onClick={() => epochWords.mutate(null)}
            >
              <BookPlus />
              {"Add this epoch's words"}
            </Button>
            <Button variant='outline' size='sm' asChild>
              <a href={BOOK_URL} target='_blank' rel='noreferrer'>
                <BookText />
                The book
              </a>
            </Button>
          </>
        }
      />
      {failure && <Text tone='destructive'>{failure.message}</Text>}
      <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6'>
        <MiniStat
          icon={Languages}
          label='Tongues'
          value={shownLanguages.length}
          tone='gold'
        />
        <MiniStat
          icon={GitBranch}
          label='Families'
          value={familyCount}
          tone='verdigris'
        />
        <MiniStat icon={WholeWord} label='Words' value={words} tone='gold' />
        <MiniStat
          icon={Feather}
          label='Written tongues'
          value={`${written}/${shownNodes.length}`}
          tone='info'
          hint='Tongues that have a script'
        />
        <MiniStat
          icon={TrendingUp}
          label='Highest tier'
          value={topTier ? tierNumeral(topTier) : '—'}
          tone='success'
          hint='The deepest tier any art has reached'
        />
        <MiniStat
          icon={Sparkles}
          label='Cosmic branches'
          value={`${cosmic}/${COSMIC_BRANCHES.length}`}
          tone={cosmic > 0 ? 'info' : 'muted'}
          hint='Branches of knowledge that open the ways between worlds'
        />
      </div>
      <Tabs
        value={view}
        onValueChange={(value) =>
          change({
            view:
              value === 'dictionary' ? undefined : (value as LanguageViewKey),
          })
        }
      >
        <TabsList aria-label='Languages view'>
          <TabsTrigger value='dictionary'>
            <BookA />
            Dictionary
          </TabsTrigger>
          <TabsTrigger value='tree'>
            <GitBranch />
            Language tree
          </TabsTrigger>
          <TabsTrigger value='knowledge'>
            <FlaskConical />
            Knowledge tree
          </TabsTrigger>
          <TabsTrigger value='names'>
            <ShieldCheck />
            Name health
          </TabsTrigger>
          <TabsTrigger value='tongues'>
            <Crown />
            Prestige
          </TabsTrigger>
        </TabsList>
        <TabsContent value='dictionary'>
          {languages.isPending ? (
            <Skeleton className='h-textarea w-full' />
          ) : (
            <Dictionary
              languages={shownLanguages}
              nodes={shownNodes}
              selected={search.language ?? null}
              onSelect={(id) => change({ language: id })}
              query={search.q ?? ''}
              onQuery={(q) => change({ q: q || undefined })}
            />
          )}
        </TabsContent>
        <TabsContent value='tree'>
          {tree.isPending ? (
            <Skeleton className='h-textarea w-full' />
          ) : (
            <LanguageTree
              nodes={shownNodes}
              covers={covers}
              selected={search.language ?? null}
              onSelect={(id) => change({ language: id })}
              onOpenDictionary={(id) =>
                change({ language: id, view: undefined })
              }
              readOnlyReason={readOnlyReason}
            />
          )}
        </TabsContent>
        <TabsContent value='knowledge'>
          {knowledge.isPending ? (
            <Skeleton className='h-textarea w-full' />
          ) : (
            <KnowledgeTree knowledge={shownKnowledge} />
          )}
        </TabsContent>
        <TabsContent value='names'>
          <NameHealth />
        </TabsContent>
        <TabsContent value='tongues'>
          <TongueAtlas worldId={world ?? worlds[0]?.id ?? null} />
        </TabsContent>
      </Tabs>
    </>
  )
}
