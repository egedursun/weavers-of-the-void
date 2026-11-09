import { type ReactNode } from 'react'
import { Ghost, Globe2, Rocket, Sun, Wand } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState } from '@/components/domain'
import { CommandPanel } from './CommandPanel'
import { ForeignGodsPanel } from './ForeignGodsPanel'
import { StarCard } from './StarCard'
import { VoyagesPanel } from './VoyagesPanel'
import { WorldCard } from './WorldCard'
import { WorldChooser } from './WorldChooser'
import { type SonPublic, type TravelResource } from './api'
import { type CommandSection, type CosmosPanel } from './cosmosSearch'
import { type CosmosIndex, isUnderway } from './model/cosmosModel'
import { type RuleBook } from './model/rules'

function TabLabel({ text, compact }: { text: string; compact: boolean }) {
  return (
    <span
      className={compact ? 'sr-only @xl/cosmos-side:not-sr-only' : undefined}
    >
      {text}
    </span>
  )
}

type CosmosSidePanelProps = {
  index: CosmosIndex
  rules: RuleBook
  sons: SonPublic[]
  homeWorldId: number | undefined
  worldId: number | undefined
  starId: number | undefined
  panel: CosmosPanel
  section: CommandSection | undefined
  resource: TravelResource | null | undefined
  highlightedRouteId?: number
  onSelectWorld: (worldId: number) => void
  onOpenPanel: (panel: CosmosPanel, section?: CommandSection) => void
  onDescend: (worldId: number) => void
  galaxyPanel?: ReactNode
  galaxyId?: number
  onSelectGalaxy?: (galaxyId: number) => void
}

export function CosmosSidePanel({
  index,
  rules,
  sons,
  homeWorldId,
  worldId,
  starId,
  panel,
  section,
  resource,
  highlightedRouteId,
  onSelectWorld,
  onOpenPanel,
  onDescend,
  galaxyPanel,
  galaxyId,
  onSelectGalaxy,
}: CosmosSidePanelProps) {
  const star = index.star(starId)
  const active = panel === 'star' && !star ? 'world' : panel
  const underway = index.data.journeys.filter(isUnderway).length
  const selected = index.world(worldId) ?? index.worlds[0]
  return (
    <div className='@container/cosmos-side flex min-w-0 flex-col gap-4'>
      {galaxyPanel}
      <Tabs
        value={active}
        onValueChange={(value) => onOpenPanel(value as CosmosPanel)}
      >
        <TabsList aria-label='Cosmos panel' size='sm' className='w-full'>
          <TabsTrigger value='world'>
            <Globe2 />
            World
          </TabsTrigger>
          <TabsTrigger value='voyages' title='Voyages'>
            <Rocket />
            <TabLabel text='Voyages' compact={active !== 'voyages'} />
            {underway > 0 && (
              <Badge size='sm' variant='secondary'>
                {underway}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value='gods' title='Gods'>
            <Ghost />
            <TabLabel text='Gods' compact={active !== 'gods'} />
            {index.data.foreign_gods.length > 0 && (
              <Badge size='sm' variant='secondary'>
                {index.data.foreign_gods.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value='command'>
            <Wand />
            Command
          </TabsTrigger>
          {star && (
            <TabsTrigger value='star' title='Star'>
              <Sun />
              <TabLabel text='Star' compact={active !== 'star'} />
            </TabsTrigger>
          )}
        </TabsList>
        <TabsContent value='world' className='flex min-w-0 flex-col gap-4'>
          <WorldChooser
            index={index}
            worldId={selected?.world.id}
            onSelect={onSelectWorld}
          />
          {selected ? (
            <WorldCard
              key={selected.world.id}
              item={selected}
              index={index}
              rules={rules}
              sons={sons}
              isHome={selected.world.id === homeWorldId}
              highlightedRouteId={highlightedRouteId}
              onSelectWorld={onSelectWorld}
              onOpenCommand={(next) => onOpenPanel('command', next)}
              onDescend={onDescend}
            />
          ) : (
            <EmptyState
              icon={Globe2}
              size='compact'
              title='No world yet'
              description='Create the first world from the Command tab.'
            />
          )}
        </TabsContent>
        <TabsContent value='voyages'>
          <VoyagesPanel
            index={index}
            rules={rules}
            worldId={selected?.world.id}
          />
        </TabsContent>
        <TabsContent value='gods'>
          <ForeignGodsPanel index={index} onSelectWorld={onSelectWorld} />
        </TabsContent>
        <TabsContent value='command'>
          <CommandPanel
            galaxyId={galaxyId}
            onGalaxy={onSelectGalaxy}
            index={index}
            rules={rules}
            worldId={selected?.world.id}
            section={section}
            resource={resource}
          />
        </TabsContent>
        {star && (
          <TabsContent value='star'>
            <StarCard
              star={star}
              index={index}
              rules={rules}
              onSelectWorld={onSelectWorld}
            />
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}
