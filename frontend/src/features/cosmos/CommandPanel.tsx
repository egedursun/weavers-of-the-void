import { type ReactNode, useEffect, useRef, useState } from 'react'
import {
  ChevronDown,
  Cog,
  Coins,
  Compass,
  Gem,
  Globe2,
  Handshake,
  type LucideIcon,
  Route,
  ScrollText,
  Skull,
  Sparkles,
  Sun,
  Thermometer,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Medallion } from '@/components/domain'
import { BeyondForm } from './BeyondForm'
import { ClimateCycleForm } from './ClimateCycleForm'
import { CosmicOrdersForm } from './CosmicOrdersForm'
import { CosmicResourceForm } from './CosmicResourceForm'
import { CreateWorldForm } from './CreateWorldForm'
import { EconomyControls } from './EconomyControls'
import { FederationForm } from './FederationForm'
import { IgniteStarForm } from './IgniteStarForm'
import { LegendaryQuestForm } from './LegendaryQuestForm'
import { MechanicsControls } from './MechanicsControls'
import { OpenRouteForm } from './OpenRouteForm'
import { SkyEventForm } from './SkyEventForm'
import { type TravelResource } from './api'
import { type CommandSection } from './cosmosSearch'
import { type CosmosIndex } from './model/cosmosModel'
import { type RuleBook } from './model/rules'

const SECTION_TITLE: Record<CommandSection, string> = {
  world: 'Create a new world',
  star: 'Ignite a star in the void',
  route: 'Open a route between worlds',
  sky: 'Command the sky',
  quest: 'Proclaim a legendary quest',
  climate: "Climate cycle: each world's own climate",
  federation: 'Found a federation',
  resource: 'Cosmic travel resource',
  economy: 'Economy: resources, deposits and cravings',
  mechanics: 'World mechanics: run them now',
  orders: 'Cosmic orders: exile, souls, markets and stars',
  beyond: 'The Beyond: archive, plague, horrors and threads',
}

const SECTION_ICON: Record<CommandSection, LucideIcon> = {
  world: Globe2,
  star: Sun,
  route: Route,
  sky: Sparkles,
  quest: Compass,
  climate: Thermometer,
  federation: Handshake,
  resource: Gem,
  economy: Coins,
  mechanics: Cog,
  orders: ScrollText,
  beyond: Skull,
}

type CommandPanelProps = {
  index: CosmosIndex
  rules: RuleBook
  worldId: number | undefined
  section: CommandSection | undefined
  resource: TravelResource | null | undefined
  galaxyId?: number
  onGalaxy?: (galaxyId: number) => void
}

function CommandSectionBlock({
  id,
  title,
  open,
  onOpenChange,
  children,
}: {
  id: CommandSection
  title: string
  open: boolean
  onOpenChange: (open: boolean) => void
  children: ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  return (
    <Collapsible
      ref={ref}
      open={open}
      onOpenChange={onOpenChange}
      data-command-section={id}
      className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <CollapsibleTrigger asChild>
        <Button variant='ghost' className='w-full justify-between'>
          <span className='flex min-w-0 items-center gap-3'>
            <Medallion icon={SECTION_ICON[id]} size='sm' />
            <span className='min-w-0 truncate'>{title}</span>
          </span>
          <ChevronDown
            className={cn('transition-transform', open && 'rotate-180')}
          />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='px-1 pb-1'>{children}</CollapsibleContent>
    </Collapsible>
  )
}

export function CommandPanel({
  index,
  rules,
  worldId,
  section,
  resource,
  galaxyId,
  onGalaxy,
}: CommandPanelProps) {
  const [open, setOpen] = useState<Set<CommandSection>>(() => {
    const initial = new Set<CommandSection>([section ?? 'world'])
    if (!resource) initial.add('resource')
    return initial
  })
  const [focused, setFocused] = useState(section)
  if (section !== focused) {
    setFocused(section)
    if (section) setOpen((current) => new Set(current).add(section))
  }
  const container = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!section) return
    container.current
      ?.querySelector(`[data-command-section="${section}"]`)
      ?.scrollIntoView({ block: 'start' })
  }, [section])
  const toggle = (id: CommandSection) => (next: boolean) =>
    setOpen((current) => {
      const copy = new Set(current)
      if (next) copy.add(id)
      else copy.delete(id)
      return copy
    })
  const block = (id: CommandSection, children: ReactNode) => (
    <CommandSectionBlock
      id={id}
      title={SECTION_TITLE[id]}
      open={open.has(id)}
      onOpenChange={toggle(id)}
    >
      {children}
    </CommandSectionBlock>
  )
  return (
    <div ref={container} className='flex min-w-0 flex-col gap-3'>
      {block('world', <CreateWorldForm index={index} rules={rules} />)}
      {block(
        'star',
        <IgniteStarForm
          index={index}
          rules={rules}
          galaxyId={galaxyId}
          onGalaxy={onGalaxy}
        />
      )}
      {block(
        'route',
        <OpenRouteForm index={index} rules={rules} worldId={worldId} />
      )}
      {block(
        'sky',
        <SkyEventForm index={index} rules={rules} worldId={worldId} />
      )}
      {block('quest', <LegendaryQuestForm index={index} rules={rules} />)}
      {block('climate', <ClimateCycleForm index={index} rules={rules} />)}
      {block('federation', <FederationForm index={index} />)}
      {block(
        'resource',
        <CosmicResourceForm
          key={resource?.name ?? 'none'}
          index={index}
          resource={resource}
          worldId={worldId}
        />
      )}
      {block('economy', <EconomyControls />)}
      {block('mechanics', <MechanicsControls />)}
      {block(
        'orders',
        <CosmicOrdersForm index={index} rules={rules} worldId={worldId} />
      )}
      {block('beyond', <BeyondForm index={index} worldId={worldId} />)}
    </div>
  )
}
