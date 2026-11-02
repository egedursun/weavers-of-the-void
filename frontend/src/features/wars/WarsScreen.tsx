import { useState } from 'react'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { navItem } from '@/config/navigation'
import { Coins, Flag, Flame, Lock, Swords } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { KpiTile, PageHeader } from '@/components/domain'
import { WarFocus } from './WarFocus'
import { WarsPanel } from './WarsPanel'
import { CaptivesList, TributesList } from './WarsTables'
import { type WarStatus, useCaptives, useTributes, useWars } from './api'
import { WARS_TABS, type WarsTab } from './warsTabs'

const ITEM = navItem('wars')

function WarsTab({ status }: { status: WarStatus | null }) {
  const [offset, setOffset] = useState(0)
  return (
    <WarsPanel
      query={useWars(status, offset)}
      offset={offset}
      onOffset={setOffset}
    />
  )
}

function WarsOverview() {
  const ongoing = useWars('ongoing', 0).data?.total ?? 0
  const ended = useWars('ended', 0).data?.total ?? 0
  const captives = useCaptives(null, 'held', 0).data?.total ?? 0
  const tributes = useTributes(null, 'active', 0).data?.total ?? 0
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4'>
      <KpiTile
        label='Wars raging'
        icon={Flame}
        tone={ongoing > 0 ? 'danger' : 'success'}
        value={ongoing}
        hint={ongoing > 0 ? 'Every war advances the doom clock' : 'Peace holds'}
      />
      <KpiTile
        label='Wars ended'
        icon={Flag}
        tone='muted'
        value={ended}
        hint='Victories, conquests, tributes and peaces'
      />
      <KpiTile
        label='Captives held'
        icon={Lock}
        tone={captives > 0 ? 'warning' : 'muted'}
        value={captives}
        hint='Ransomed, rescued or escaped in time'
      />
      <KpiTile
        label='Tributes paid'
        icon={Coins}
        tone='gold'
        value={tributes}
        hint='Defeated communities paying their victors'
      />
    </div>
  )
}

export function WarsScreen() {
  const search = useSearch({ from: '/_app/wars' })
  const tab: WarsTab = search.tab ?? 'ongoing'
  const navigate = useNavigate({ from: '/wars' })
  const setTab = (next: string) =>
    void navigate({
      search: { tab: WARS_TABS.find((item) => item === next) },
    })
  return (
    <>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon ?? Swords}
      />
      <WarsOverview />
      {search.war !== undefined && (
        <WarFocus key={search.war} warId={search.war} />
      )}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList aria-label='Wars sections'>
          <TabsTrigger value='ongoing'>
            <Flame />
            Ongoing
          </TabsTrigger>
          <TabsTrigger value='ended'>
            <Flag />
            Ended
          </TabsTrigger>
          <TabsTrigger value='captives'>
            <Lock />
            Captives
          </TabsTrigger>
          <TabsTrigger value='tributes'>
            <Coins />
            Tributes
          </TabsTrigger>
        </TabsList>
        <TabsContent value='ongoing'>
          {tab === 'ongoing' && <WarsTab status='ongoing' />}
        </TabsContent>
        <TabsContent value='ended'>
          {tab === 'ended' && <WarsTab status='ended' />}
        </TabsContent>
        <TabsContent value='captives'>
          {tab === 'captives' && <CaptivesList communityId={null} />}
        </TabsContent>
        <TabsContent value='tributes'>
          {tab === 'tributes' && <TributesList communityId={null} />}
        </TabsContent>
      </Tabs>
    </>
  )
}
