import { Link, useLocation } from '@tanstack/react-router'
import {
  GENESIS_ITEM,
  NAV_GROUPS,
  type NavItem,
  isNavItemActive,
} from '@/config/navigation'
import { ChevronRight } from 'lucide-react'

type Trail = {
  group: string
  section: NavItem | null
  item: NavItem
}

function trailOf(pathname: string): Trail | null {
  const found: Trail[] = []
  for (const group of NAV_GROUPS)
    for (const section of group.items) {
      if (isNavItemActive(pathname, section))
        found.push({ group: group.title, section: null, item: section })
      for (const child of section.children ?? [])
        if (isNavItemActive(pathname, child))
          found.push({ group: group.title, section, item: child })
    }
  if (isNavItemActive(pathname, GENESIS_ITEM))
    found.push({ group: 'Studio', section: null, item: GENESIS_ITEM })
  return (
    found.sort(
      (left, right) => right.item.to.length - left.item.to.length
    )[0] ?? null
  )
}

export function TopBarCrumb() {
  const pathname = useLocation({ select: (location) => location.pathname })
  const trail = trailOf(pathname)
  if (!trail) return null
  const Icon = trail.item.icon
  const deeper = pathname !== trail.item.to
  return (
    <nav
      aria-label='Breadcrumb'
      data-layout='top-bar-crumb'
      className='hidden min-w-0 items-center gap-2 @lg/topbar:flex'
    >
      <span
        title={trail.item.title}
        className='flex size-control-sm shrink-0 items-center justify-center rounded-md border border-primary/30 bg-primary/10 text-primary'
      >
        <Icon aria-hidden='true' className='size-icon-sm' />
      </span>
      <ol className='flex min-w-0 items-center gap-1.5 text-caption'>
        <li className='hidden shrink-0 tracking-wider text-muted-foreground uppercase @6xl/topbar:block'>
          {trail.group}
        </li>
        {trail.section && (
          <li className='hidden min-w-0 items-center gap-1.5 text-muted-foreground @6xl/topbar:flex'>
            <ChevronRight aria-hidden='true' className='size-icon-xs' />
            <Link
              to={trail.section.to}
              className='truncate hover:text-foreground'
            >
              {trail.section.title}
            </Link>
          </li>
        )}
        <li className='hidden max-w-56 min-w-0 items-center gap-1.5 @2xl/topbar:flex'>
          <ChevronRight
            aria-hidden='true'
            className='hidden size-icon-xs text-muted-foreground @6xl/topbar:block'
          />
          {deeper ? (
            <Link
              to={trail.item.to}
              className='truncate font-display text-body font-semibold text-foreground hover:text-primary'
            >
              {trail.item.title}
            </Link>
          ) : (
            <span
              aria-current='page'
              className='truncate font-display text-body font-semibold text-foreground'
            >
              {trail.item.title}
            </span>
          )}
        </li>
      </ol>
    </nav>
  )
}
