import { type ReactNode } from 'react'
import { NAV_GROUPS } from '@/config/navigation'
import { useLayout } from '@/context/layoutContext'
import { FrameCorners } from '@/components/ui/ornate'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from '@/components/ui/sidebar'
import { BrandTitle } from './BrandTitle'
import { NavGroup } from './NavGroup'
import { ThemeSwitch } from './ThemeSwitch'

export function AppSidebar({ footer }: { footer?: ReactNode }) {
  const { collapsible, variant } = useLayout()
  return (
    <Sidebar collapsible={collapsible} variant={variant}>
      {variant !== 'sidebar' && <FrameCorners frame='rail' />}
      <SidebarHeader>
        <BrandTitle />
      </SidebarHeader>
      <SidebarContent>
        {NAV_GROUPS.map((group) => (
          <NavGroup key={group.title} group={group} />
        ))}
      </SidebarContent>
      <SidebarFooter
        data-layout='sidebar-phone-tools'
        className='flex-row flex-wrap items-center gap-2 sm:hidden'
      >
        {footer}
        <ThemeSwitch />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
