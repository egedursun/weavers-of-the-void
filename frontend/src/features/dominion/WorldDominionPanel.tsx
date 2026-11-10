import { Crown, Gem, Map } from 'lucide-react'
import { EmptyState, KpiTile, PagedList } from '@/components/domain'
import { Label } from '@/components/typography'
import {
  RuleCard,
  SiteForm,
  SiteList,
  ThroneForm,
  ThroneList,
} from './PlaceDominionPanel'
import { type WorldDominionView } from './api'

export function WorldDominionPanel({
  data,
  blocked,
}: {
  data: WorldDominionView
  blocked: string | null
}) {
  const gods = new Set(data.rules.map((rule) => rule.god?.id)).size
  const held = data.thrones.filter((throne) => throne.holder !== null).length
  return (
    <div
      data-surface='WorldDominionPanel'
      className='flex min-w-0 flex-col gap-3'
    >
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <KpiTile
          label='Regions ruled'
          value={data.rules.length}
          icon={Map}
          tone='gold'
        />
        <KpiTile label='Ruling gods' value={gods} icon={Crown} tone='info' />
        <KpiTile
          label='Thrones held'
          value={`${held} of ${data.thrones.length}`}
          icon={Crown}
          tone='warning'
        />
        <KpiTile
          label='Magic sites'
          value={data.sites.length}
          icon={Gem}
          tone='verdigris'
        />
      </div>
      <Label variant='overline'>Who rules which land</Label>
      {data.rules.length === 0 ? (
        <EmptyState
          icon={Map}
          size='inline'
          title='No god rules any land of this world yet'
          description='Dominion is weighed each epoch from temples, holy sites, thrones, prophets, miracles and worship.'
        />
      ) : (
        <PagedList
          items={data.rules}
          initial={6}
          noun={['region', 'regions']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(rule) => rule.region?.id ?? 0}
        >
          {(rule) => <RuleCard rule={rule} />}
        </PagedList>
      )}
      <Label variant='overline'>Thrones of power</Label>
      <ThroneList thrones={data.thrones} blocked={blocked} />
      <ThroneForm placeId={null} thrones={data.thrones} blocked={blocked} />
      <Label variant='overline'>Magic sites</Label>
      <SiteList sites={data.sites} blocked={blocked} />
      <SiteForm placeId={null} blocked={blocked} />
    </div>
  )
}
