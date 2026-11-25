import {
  GENESIS_ITEM,
  NAV_GROUPS,
  type NavItem,
  isNavItemActive,
} from '@/config/navigation'

type Trail = {
  group: string
  section: NavItem | null
  item: NavItem
}

export function trailOf(pathname: string): Trail | null {
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

export function screenTitle(pathname: string): string | null {
  return trailOf(pathname)?.item.title ?? null
}
