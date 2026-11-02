import { Link, Outlet, useLocation } from '@tanstack/react-router'
import { SETTINGS_TABS, navItem } from '@/config/navigation'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/domain'

const ITEM = navItem('settings')

export function SettingsPage() {
  const pathname = useLocation({ select: (location) => location.pathname })
  const active =
    SETTINGS_TABS.find((tab) => pathname.startsWith(tab.to)) ?? SETTINGS_TABS[0]
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
      />
      <Tabs value={active.to}>
        <TabsList aria-label='Settings sections' className='w-full md:w-fit'>
          {SETTINGS_TABS.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.to} asChild>
              <Link to={tab.to}>
                <tab.icon />
                {tab.title}
              </Link>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <Outlet />
    </>
  )
}
