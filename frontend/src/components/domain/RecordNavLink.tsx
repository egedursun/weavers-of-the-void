import { type ComponentProps, type ReactNode } from 'react'
import { Link } from '@tanstack/react-router'
import {
  CloudSun,
  Globe,
  type LucideIcon,
  LibraryBig,
  Map as MapIcon,
  ScrollText,
  Waypoints,
} from 'lucide-react'
import { Button, type ButtonProps } from '@/components/ui/button'
import {
  type DrawerSearch,
  parseDrawerStack,
  pushDrawerEntry,
} from '@/components/layout/drawer/drawerEntries'
import { drawerSearchWith } from '@/components/layout/drawer/useDrawerStack'

export type NavTarget =
  | { view: 'map'; world?: number | null; focus?: number }
  | { view: 'network'; focus: number }
  | { view: 'world-map'; world: number }
  | { view: 'climate'; world?: number | null }
  | { view: 'atlas'; type: string }
  | { view: 'chronicle'; epoch?: number; line?: number; world?: number | null }

export type NavView = NavTarget['view']

const NAV_LABEL: Record<NavView, string> = {
  map: 'Show on map',
  network: 'Show in network',
  'world-map': 'Its world map',
  climate: 'Climate',
  atlas: 'In the atlas',
  chronicle: 'In the chronicle',
}

const NAV_ICON: Record<NavView, LucideIcon> = {
  map: MapIcon,
  network: Waypoints,
  'world-map': Globe,
  climate: CloudSun,
  atlas: LibraryBig,
  chronicle: ScrollText,
}

type RecordNavLinkProps = {
  to: NavTarget
  children?: ReactNode
  variant?: ButtonProps['variant']
  size?: ButtonProps['size']
}

function present(value: number | null | undefined): number | undefined {
  return value === null || value === undefined ? undefined : value
}

function TargetLink({
  destination: target,
  children,
  ...rest
}: { destination: NavTarget; children: ReactNode } & Omit<
  ComponentProps<'a'>,
  'href'
>) {
  const view = target.view
  if (view === 'map')
    return (
      <Link
        {...rest}
        to='/map'
        search={{ world: present(target.world), focus: target.focus }}
      >
        {children}
      </Link>
    )
  if (view === 'network')
    return (
      <Link {...rest} to='/network' search={{ focus: target.focus }}>
        {children}
      </Link>
    )
  if (view === 'world-map')
    return (
      <Link {...rest} to='/map' search={{ world: target.world }}>
        {children}
      </Link>
    )
  if (view === 'climate' && present(target.world) !== undefined)
    return (
      <Link
        {...rest}
        to='.'
        search={(previous: DrawerSearch) =>
          drawerSearchWith(
            previous,
            pushDrawerEntry(parseDrawerStack(previous.drawer), {
              kind: 'world',
              id: String(target.world),
            })
          )
        }
      >
        {children}
      </Link>
    )
  if (view === 'climate')
    return (
      <Link
        {...rest}
        to='/cosmos'
        search={{
          world: present(target.world),
          panel: 'command',
          section: 'climate',
        }}
      >
        {children}
      </Link>
    )
  if (view === 'atlas')
    return (
      <Link {...rest} to='/atlas' search={{ type: target.type }}>
        {children}
      </Link>
    )
  return (
    <Link
      {...rest}
      to='/chronicle'
      search={{
        epoch: target.epoch,
        line: target.line,
        world: present(target.world),
      }}
    >
      {children}
    </Link>
  )
}

export function RecordNavLink({
  to: target,
  children,
  variant = 'outline',
  size = 'sm',
}: RecordNavLinkProps) {
  const Icon = NAV_ICON[target.view]
  return (
    <Button variant={variant} size={size} asChild>
      <TargetLink destination={target}>
        <Icon />
        {children ?? NAV_LABEL[target.view]}
      </TargetLink>
    </Button>
  )
}
