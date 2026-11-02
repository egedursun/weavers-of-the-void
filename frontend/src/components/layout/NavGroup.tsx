import { Link, useLocation } from '@tanstack/react-router'
import {
  type NavGroup as NavGroupData,
  type NavItem,
  type NavSection,
  isNavItemActive,
} from '@/config/navigation'
import { ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Kbd } from '@/components/ui/kbd'
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  useSidebar,
} from '@/components/ui/sidebar'
import { useNavBadge } from './navBadges'

function isSectionActive(pathname: string, section: NavSection): boolean {
  return (
    isNavItemActive(pathname, section) ||
    (section.children ?? []).some((child) => isNavItemActive(pathname, child))
  )
}

export function NavGroup({ group }: { group: NavGroupData }) {
  const { state, isMobile } = useSidebar()
  const pathname = useLocation({ select: (location) => location.pathname })
  return (
    <SidebarGroup>
      <SidebarGroupLabel>{group.title}</SidebarGroupLabel>
      <SidebarMenu>
        {group.items.map((item) => {
          if (!item.children)
            return <NavLinkItem key={item.id} item={item} pathname={pathname} />
          if (state === 'collapsed' && !isMobile)
            return (
              <NavCollapsedSection
                key={item.id}
                section={item}
                pathname={pathname}
              />
            )
          return (
            <NavExpandedSection
              key={item.id}
              section={item}
              pathname={pathname}
            />
          )
        })}
      </SidebarMenu>
    </SidebarGroup>
  )
}

const BADGE_CAP = 99

const BADGE_CLASS = {
  primary: 'bg-primary text-primary-foreground',
  warning: 'bg-warning text-background',
  info: 'bg-info text-background',
} as const

function NavCount({ id }: { id: string }) {
  const badge = useNavBadge(id)
  if (!badge) return null
  return (
    <>
      <span
        data-nav-badge={id}
        className={cn(
          'flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full px-1.5 text-overline font-semibold tabular-nums group-data-[collapsible=icon]:hidden',
          BADGE_CLASS[badge.tone]
        )}
      >
        {badge.count > BADGE_CAP ? `${BADGE_CAP}+` : badge.count}
      </span>
      <span
        aria-hidden='true'
        className={cn(
          'absolute top-1 right-1 hidden size-2 rounded-full group-data-[collapsible=icon]:block',
          BADGE_CLASS[badge.tone]
        )}
      />
    </>
  )
}

function NavLinkItem({ item, pathname }: { item: NavItem; pathname: string }) {
  const { setOpenMobile } = useSidebar()
  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        asChild
        isActive={isNavItemActive(pathname, item)}
        tooltip={item.title}
      >
        <Link to={item.to} onClick={() => setOpenMobile(false)}>
          <item.icon />
          <span className='min-w-0 flex-1 truncate'>{item.title}</span>
          <NavCount id={item.id} />
          {item.shortcut && (
            <Kbd className='group-data-[collapsible=icon]:hidden max-md:hidden'>
              {item.shortcut}
            </Kbd>
          )}
        </Link>
      </SidebarMenuButton>
    </SidebarMenuItem>
  )
}

function NavExpandedSection({
  section,
  pathname,
}: {
  section: NavSection
  pathname: string
}) {
  const { setOpenMobile } = useSidebar()
  return (
    <Collapsible
      asChild
      defaultOpen={isSectionActive(pathname, section)}
      className='group/collapsible'
    >
      <SidebarMenuItem>
        <CollapsibleTrigger asChild>
          <SidebarMenuButton tooltip={section.title}>
            <section.icon />
            <span className='min-w-0 flex-1 truncate'>{section.title}</span>
            <ChevronRight className='transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90 rtl:rotate-180' />
          </SidebarMenuButton>
        </CollapsibleTrigger>
        <CollapsibleContent className='CollapsibleContent'>
          <SidebarMenuSub>
            {(section.children ?? []).map((child) => (
              <SidebarMenuSubItem key={child.id}>
                <SidebarMenuSubButton
                  asChild
                  isActive={isNavItemActive(pathname, child)}
                >
                  <Link to={child.to} onClick={() => setOpenMobile(false)}>
                    <child.icon />
                    <span className='min-w-0 flex-1 truncate'>
                      {child.title}
                    </span>
                    <NavCount id={child.id} />
                  </Link>
                </SidebarMenuSubButton>
              </SidebarMenuSubItem>
            ))}
          </SidebarMenuSub>
        </CollapsibleContent>
      </SidebarMenuItem>
    </Collapsible>
  )
}

function NavCollapsedSection({
  section,
  pathname,
}: {
  section: NavSection
  pathname: string
}) {
  return (
    <SidebarMenuItem>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <SidebarMenuButton
            tooltip={section.title}
            isActive={isSectionActive(pathname, section)}
          >
            <section.icon />
            <span className='min-w-0 flex-1 truncate'>{section.title}</span>
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent side='right' align='start' sideOffset={4}>
          <DropdownMenuLabel>{section.title}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {(section.children ?? []).map((child) => (
            <DropdownMenuItem key={child.id} asChild>
              <Link
                to={child.to}
                data-active={isNavItemActive(pathname, child)}
                className='data-[active=true]:bg-accent'
              >
                <child.icon />
                <span className='min-w-0 truncate'>{child.title}</span>
              </Link>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  )
}
