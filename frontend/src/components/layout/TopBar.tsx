import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { ControlCluster } from './ControlCluster'
import { RealtimeIndicator } from './RealtimeIndicator'
import { SearchButton } from './SearchButton'
import { ThemeSwitch } from './ThemeSwitch'
import { TopBarCrumb } from './TopBarCrumb'
import { useCollapseOnScroll } from './useCollapseOnScroll'

type TopBarProps = {
  context?: ReactNode
  actions?: ReactNode
  account?: ReactNode
}

export function TopBar({ context, actions, account }: TopBarProps) {
  const collapsed = useCollapseOnScroll()
  return (
    <header
      data-layout='top-bar'
      data-collapsed={collapsed || undefined}
      className={cn(
        '@container/topbar sticky top-0 z-30 flex h-topbar shrink-0 items-center gap-2 bg-background/85 px-2 backdrop-blur-md transition-transform duration-200 motion-reduce:transition-none sm:gap-3 sm:px-3 md:px-4 md:group-has-data-[variant=inset]/sidebar-wrapper:rounded-t-xl',
        collapsed && '-translate-y-full'
      )}
    >
      <div className='flex min-w-0 shrink-0 items-center gap-2'>
        <SidebarTrigger />
        <Separator
          orientation='vertical'
          className='data-[orientation=vertical]:h-5'
        />
        <TopBarCrumb />
      </div>
      <div className='flex min-w-0 flex-1 items-center justify-center'>
        <SearchButton />
      </div>
      <div className='flex shrink-0 items-center gap-2'>
        {context}
        <ControlCluster>
          <RealtimeIndicator />
          <Separator
            orientation='vertical'
            className='mx-0.5 data-[orientation=vertical]:h-5'
          />
          {actions}
          <span className='hidden items-center gap-0.5 @lg/topbar:inline-flex'>
            <Separator
              orientation='vertical'
              className='mx-0.5 data-[orientation=vertical]:h-5'
            />
            <ThemeSwitch />
          </span>
        </ControlCluster>
        {account}
      </div>
    </header>
  )
}
