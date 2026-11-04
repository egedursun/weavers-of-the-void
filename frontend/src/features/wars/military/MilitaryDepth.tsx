import { Anchor, Drama } from 'lucide-react'
import { DeclareWar, RaiseArmy, UnitDesigns } from './Orders'
import { RecordPanel } from './RecordPanel'
import { Vendettas } from './Vendettas'
import { LayDownVessel } from './VesselCard'
import { COVER, FATE } from './labels'
import { Panel } from './parts'

const OWNER_KIND = {
  polity: { label: 'Realm', icon: Drama, tone: 'gold' as const },
  faction: { label: 'Faction', icon: Drama, tone: 'info' as const },
  cult: { label: 'Cult', icon: Drama, tone: 'verdigris' as const },
  community: { label: 'Community', icon: Drama, tone: 'muted' as const },
}

export function MilitaryDepth({
  entityId,
  kind,
  blocked,
}: {
  entityId: number
  kind: string
  blocked: string | null
}) {
  const community =
    kind === 'people' ||
    kind === 'settlement' ||
    kind === 'cult' ||
    kind === 'faction' ||
    kind === 'polity'
  return (
    <div
      data-surface='MilitaryDepth'
      className='@container/mil flex min-w-0 flex-col gap-3'
    >
      {community && <RaiseArmy communityId={entityId} blocked={blocked} />}
      {community && <DeclareWar attackerId={entityId} blocked={blocked} />}
      <Panel
        title='Ships'
        icon={Anchor}
        tone='info'
        hint='Lay down a vessel for this owner'
      >
        <LayDownVessel ownerId={entityId} blocked={blocked} />
      </Panel>
      <RecordPanel
        kind='spy_network'
        scope={entityId}
        title='Spy networks'
        tone='verdigris'
        blocked={blocked}
        presets={{ owner_entity_id: entityId }}
        choices={{ cover: COVER, owner_kind: OWNER_KIND }}
        hint='Found a network, set its target, cover, depth and intel'
      />
      <RecordPanel
        kind='spy_agent'
        scope={null}
        title='Named agents'
        tone='verdigris'
        blocked={blocked}
        choices={{ cover: COVER }}
        hint='Assign a mortal to a network under cover'
      />
      <RecordPanel
        kind='contract'
        scope={entityId}
        title='Mercenary contracts'
        tone='gold'
        blocked={blocked}
        presets={{ employer_entity_id: entityId }}
        hint='Companies sworn for pay, season by season'
      />
      <RecordPanel
        kind='captive_cohort'
        scope={entityId}
        title='Captives held'
        tone='warning'
        blocked={blocked}
        presets={{ captor_entity_id: entityId }}
        choices={{ fate: FATE }}
      />
      <RecordPanel
        kind='captive'
        scope={entityId}
        title='Named prisoners'
        tone='warning'
        blocked={blocked}
      />
      <RecordPanel
        kind='occupation'
        scope={entityId}
        title='Lands occupied'
        tone='danger'
        blocked={blocked}
        presets={{ occupier_entity_id: entityId }}
      />
      <Vendettas entityId={entityId} blocked={blocked} />
      <UnitDesigns blocked={blocked} />
    </div>
  )
}
