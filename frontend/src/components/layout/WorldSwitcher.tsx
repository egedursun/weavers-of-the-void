import { useEffect } from 'react'
import { useLocation, useNavigate } from '@tanstack/react-router'
import { Globe } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { filteredRoute, useWorldFilter, worldSearch } from './worldFilter'

const WHOLE_COSMOS = 'cosmos'

export type WorldChoice = { id: number; name: string }

export function WorldSwitcher({
  worlds,
  compact = false,
}: {
  worlds: WorldChoice[]
  compact?: boolean
}) {
  const worldId = useWorldFilter((state) => state.worldId)
  const setWorldId = useWorldFilter((state) => state.setWorldId)
  const navigate = useNavigate()
  const pathname = useLocation({ select: (location) => location.pathname })
  const known = worldId !== null && worlds.some((world) => world.id === worldId)
  useEffect(() => {
    if (worlds.length > 0 && worldId !== null && !known) setWorldId(null)
  }, [known, setWorldId, worldId, worlds.length])
  if (worlds.length <= 1) return null
  const choose = (value: string) => {
    const next = value === WHOLE_COSMOS ? null : Number(value)
    setWorldId(next)
    const route = filteredRoute(pathname)
    if (route)
      void navigate({
        to: route,
        search: (previous: Record<string, unknown>) =>
          worldSearch(route, previous, next),
        replace: true,
      } as never)
  }
  return (
    <span data-layout='world-switcher' className='inline-flex min-w-0'>
      <Select
        value={known ? String(worldId) : WHOLE_COSMOS}
        onValueChange={choose}
      >
        <SelectTrigger
          size='sm'
          aria-label='World filter'
          className={cn(
            'max-w-52 rounded-lg bg-card/70',
            compact && 'w-auto *:data-[slot=select-value]:sr-only'
          )}
          data-active={known || undefined}
          title={compact ? 'World filter' : undefined}
        >
          <Globe className={cn(known && 'text-primary')} />
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>
              Map, atlas, network, chronicle and cosmos follow this world
            </SelectLabel>
          </SelectGroup>
          <SelectItem value={WHOLE_COSMOS}>Whole cosmos</SelectItem>
          {worlds.map((world) => (
            <SelectItem key={world.id} value={String(world.id)}>
              {world.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </span>
  )
}
