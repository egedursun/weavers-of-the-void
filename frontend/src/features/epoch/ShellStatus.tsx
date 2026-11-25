import { type ReactNode } from 'react'
import { ChangeFeed } from '@/realtime/ChangeFeed'
import { WorldSwitcher } from '@/components/layout/WorldSwitcher'
import { type NavBadge, NavBadgeContext } from '@/components/layout/navBadges'
import { DiscoveryBanner } from '@/features/backups/DiscoveryBanner'
import { FeedCollector } from '@/features/feed/FeedCollector'
import { LiveFeedDock } from '@/features/feed/LiveFeedDock'
import { LiveFeedSheet } from '@/features/feed/LiveFeedSheet'
import { NotificationBell } from '@/features/notifications/NotificationBell'
import { OnboardingTracker } from '@/features/onboarding/OnboardingTracker'
import { useWorldState } from '@/features/overview/api'
import { ConflictDialog } from '@/features/team/ConflictDialog'
import { PresenceBeacon, PresentFaces } from '@/features/team/Presence'
import { QueueTray } from '@/features/team/Queue'
import { TeamViewOpener } from '@/features/team/TeamViewOpener'
import { UniverseSwitcher } from '@/features/universes/UniverseSwitcher'
import { WorkspaceSwitcher } from '@/features/workspaces/WorkspaceSwitcher'
import { WorldHeader } from '@/features/world-header/WorldHeader'
import { ActivityStrip } from './ActivityStrip'
import { JobsMenu } from './JobsMenu'

function ShellWorldSwitcher({ compact = false }: { compact?: boolean }) {
  const state = useWorldState()
  return <WorldSwitcher worlds={state.data?.worlds ?? []} compact={compact} />
}

export function ShellContext() {
  return (
    <>
      <span className='hidden min-w-0 @6xl/topbar:inline-flex'>
        <WorkspaceSwitcher compact />
      </span>
      <span className='hidden min-w-0 @4xl/topbar:inline-flex'>
        <UniverseSwitcher />
      </span>
      <span className='inline-flex min-w-0 @4xl/topbar:hidden'>
        <UniverseSwitcher compact />
      </span>
      <span className='hidden min-w-0 @5xl/topbar:inline-flex'>
        <ShellWorldSwitcher />
      </span>
      <span className='hidden sm:inline-flex @5xl/topbar:hidden'>
        <ShellWorldSwitcher compact />
      </span>
    </>
  )
}

export function ShellActions() {
  return (
    <>
      <PresentFaces />
      <QueueTray />
      <span className='hidden items-center gap-0.5 sm:inline-flex'>
        <JobsMenu />
        <LiveFeedSheet />
      </span>
      <NotificationBell />
    </>
  )
}

export function ShellNavBadges({ children }: { children: ReactNode }) {
  const state = useWorldState()
  const data = state.data
  const badges: Record<string, NavBadge> = data
    ? {
        prayers: { count: data.prayers_pending, tone: 'warning' },
        notifications: { count: data.notifications_unread, tone: 'primary' },
        epoch: { count: data.pending_son_ids.length, tone: 'info' },
      }
    : {}
  return <NavBadgeContext value={badges}>{children}</NavBadgeContext>
}

export function ShellSidebarTools() {
  return (
    <>
      <ShellWorldSwitcher />
      <JobsMenu />
      <LiveFeedSheet />
    </>
  )
}

export function ShellBanner() {
  return (
    <>
      <DiscoveryBanner />
      <ActivityStrip />
      <WorldHeader />
    </>
  )
}

export function ShellServices() {
  return (
    <>
      <FeedCollector />
      <ChangeFeed />
      <OnboardingTracker />
      <PresenceBeacon />
      <TeamViewOpener />
      <ConflictDialog />
    </>
  )
}

export function ShellAside() {
  return <LiveFeedDock />
}
