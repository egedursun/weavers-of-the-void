import { ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Toggle } from '@/components/ui/toggle'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { PagedList } from '@/components/domain'
import { Label, Stat, Text } from '@/components/typography'
import { IconMarker, LineMarker } from '@/features/map/SwatchMarker'
import { typeIcon } from '@/features/map/iconPaths'
import { type Family, ALL_FAMILIES, typeLabel } from './families'
import { type GraphNode } from './graphModel'
import { TONE_TOKEN } from './graphStyle'

type GraphLegendProps = {
  nodes: readonly GraphNode[]
  hiddenTypes: ReadonlySet<string>
  onHiddenTypes: (next: Set<string>) => void
  onHoverFamily: (family: string | null) => void
  typeLabels: ReadonlyMap<string, string>
}

const LINK_LEGEND = [
  {
    key: 'conflict',
    label: 'Conflict',
    token: TONE_TOKEN.conflict,
    width: 1.6,
  },
  {
    key: 'faith',
    label: 'Faith and narrative',
    token: TONE_TOKEN.faith,
    width: 1.6,
  },
  {
    key: 'route',
    label: 'Inter-world route',
    token: TONE_TOKEN.route,
    width: 2.4,
  },
  {
    key: 'inside',
    label: 'Inside (location)',
    token: TONE_TOKEN.inside,
    width: 1.2,
  },
  { key: 'other', label: 'Other links', token: TONE_TOKEN.other, width: 1.2 },
  {
    key: 'past',
    label: 'Past (ended) relation',
    token: TONE_TOKEN.inside,
    width: 1.2,
    dash: '1 3',
  },
] as const

type FamilyState = 'on' | 'partial' | 'off'

function stateOf(
  present: readonly string[],
  hidden: ReadonlySet<string>
): FamilyState {
  const hiddenCount = present.filter((type) => hidden.has(type)).length
  if (hiddenCount === 0) return 'on'
  return hiddenCount === present.length ? 'off' : 'partial'
}

export function GraphLegend({
  nodes,
  hiddenTypes,
  onHiddenTypes,
  onHoverFamily,
  typeLabels,
}: GraphLegendProps) {
  const counts = new Map<string, number>()
  for (const node of nodes)
    counts.set(node.type, (counts.get(node.type) ?? 0) + 1)
  const typesOf = (family: Family) =>
    [...counts.keys()].filter((type) => {
      const owner = nodes.find((node) => node.type === type)?.family
      return owner?.key === family.key
    })
  const present = ALL_FAMILIES.map((family) => ({
    family,
    types: typesOf(family),
  })).filter((entry) => entry.types.length > 0)
  const toggleTypes = (types: readonly string[], hide: boolean) => {
    const next = new Set(hiddenTypes)
    for (const type of types) {
      if (hide) next.add(type)
      else next.delete(type)
    }
    onHiddenTypes(next)
  }
  return (
    <div data-graph-legend className='flex min-w-0 flex-col gap-3'>
      <PagedList
        items={present}
        initial={12}
        noun={['entry', 'entries']}
        as='div'
        className='flex min-w-0 flex-wrap gap-1.5'
        itemKey={({ family }) => family.key}
      >
        {({ family, types }) => {
          const state = stateOf(types, hiddenTypes)
          const count = types.reduce(
            (sum, type) => sum + (counts.get(type) ?? 0),
            0
          )
          return (
            <Tooltip key={family.key}>
              <TooltipTrigger asChild>
                <Button
                  size='sm'
                  variant={state === 'off' ? 'ghost' : 'outline'}
                  aria-pressed={
                    state === 'on' ? true : state === 'off' ? false : 'mixed'
                  }
                  onClick={() => toggleTypes(types, state !== 'off')}
                  onMouseEnter={() => onHoverFamily(family.key)}
                  onMouseLeave={() => onHoverFamily(null)}
                  onFocus={() => onHoverFamily(family.key)}
                  onBlur={() => onHoverFamily(null)}
                  className={state === 'off' ? 'opacity-60' : undefined}
                >
                  <IconMarker
                    icon={typeIcon(family.types[0] ?? '')}
                    token={family.token}
                  />
                  {family.label}
                  <Stat value={count} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {types.map((type) => typeLabel(type, typeLabels)).join(', ')}
              </TooltipContent>
            </Tooltip>
          )
        }}
      </PagedList>
      <Collapsible className='flex min-w-0 flex-col gap-2'>
        <CollapsibleTrigger asChild>
          <Button variant='ghost' size='sm' className='group justify-between'>
            Types and links
            <ChevronDown className='transition-transform group-aria-expanded:rotate-180' />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
          {present.map(({ family, types }) => (
            <div key={family.key} className='flex min-w-0 flex-col gap-1.5'>
              <Label variant='overline'>{family.label}</Label>
              <PagedList
                items={types}
                initial={12}
                noun={['entry', 'entries']}
                as='div'
                className='flex min-w-0 flex-wrap gap-1'
                itemKey={(type) => type}
              >
                {(type) => (
                  <Toggle
                    key={type}
                    size='sm'
                    variant='outline'
                    pressed={!hiddenTypes.has(type)}
                    onPressedChange={(pressed) => toggleTypes([type], !pressed)}
                  >
                    <IconMarker icon={typeIcon(type)} token={family.token} />
                    {typeLabel(type, typeLabels)}
                    <Stat value={counts.get(type) ?? 0} />
                  </Toggle>
                )}
              </PagedList>
            </div>
          ))}
          <div className='flex min-w-0 flex-col gap-1.5'>
            <Label variant='overline'>Link colours</Label>
            <ul className='flex min-w-0 flex-col gap-1'>
              {LINK_LEGEND.map((item) => (
                <li key={item.key} className='flex min-w-0 items-center gap-2'>
                  <LineMarker
                    token={item.token}
                    width={item.width}
                    dash={'dash' in item ? item.dash : undefined}
                  />
                  <Text as='span'>{item.label}</Text>
                </li>
              ))}
            </ul>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}
