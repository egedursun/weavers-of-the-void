import { Anchor, Swords } from 'lucide-react'
import { UnitDesigns } from './Designs'
import { FoundNetwork } from './Intrigue'
import { DeclareWar, RaiseArmy } from './Orders'
import { MercenaryContracts, NamedPrisoners } from './Retinue'
import { Vendettas } from './Vendettas'
import { LayDownVessel } from './VesselCard'
import { Panel } from './parts'

const COMMUNITIES = new Set([
  'people',
  'settlement',
  'cult',
  'faction',
  'polity',
])

export function MilitaryDepth({
  entityId,
  kind,
  blocked,
}: {
  entityId: number
  kind: string
  blocked: string | null
}) {
  const community = COMMUNITIES.has(kind)
  return (
    <div
      data-surface='MilitaryDepth'
      className='@container/mil flex min-w-0 flex-col gap-3'
    >
      {community && (
        <Panel
          title='Call to arms'
          icon={Swords}
          tone='danger'
          hint='Raise a standing army, in war or in peace, or declare a war with its cause and aims'
        >
          <div className='flex min-w-0 flex-col gap-2'>
            <RaiseArmy communityId={entityId} blocked={blocked} />
            <DeclareWar attackerId={entityId} blocked={blocked} />
          </div>
        </Panel>
      )}
      {community && <UnitDesigns ownerId={entityId} blocked={blocked} />}
      {community && (
        <MercenaryContracts employerId={entityId} blocked={blocked} />
      )}
      <NamedPrisoners captorId={entityId} blocked={blocked} />
      {community && <FoundNetwork ownerId={entityId} blocked={blocked} />}
      <Panel
        title='Ships'
        icon={Anchor}
        tone='info'
        hint='Lay down a vessel for this owner'
      >
        <LayDownVessel ownerId={entityId} blocked={blocked} />
      </Panel>
      <Vendettas entityId={entityId} blocked={blocked} />
    </div>
  )
}
