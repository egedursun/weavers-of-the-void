import { Anchor, ClipboardList, Swords } from 'lucide-react'
import { Muted } from '@/components/typography'
import { UnitDesigns } from './Designs'
import { CasusBelli, WarProduction } from './Grievances'
import { FoundNetwork } from './Intrigue'
import { DeclareWar, RaiseArmy } from './Orders'
import { MercenaryContracts, NamedPrisoners } from './Retinue'
import { ArmyTemplates } from './Templates'
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

const SHIP_OWNERS = new Set([
  'people',
  'settlement',
  'faction',
  'cult',
  'mortal',
  'species',
  'army',
  'beast',
])
const NO_SHIPS =
  'This kind of thing cannot own a ship; a realm holds its ships through its towns and peoples, so lay one down in a town of the realm'

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
      {kind === 'polity' ? (
        <ArmyTemplates polityId={entityId} blocked={blocked} />
      ) : (
        community && (
          <Panel
            title='Army templates'
            icon={ClipboardList}
            tone='muted'
            hint='Templates are kept by a realm; open the realm it belongs to'
          >
            <Muted variant='caption'>
              Its armies fill from the template its realm uses, so the realm's
              marshal keeps them, not this community.
            </Muted>
          </Panel>
        )
      )}
      {community && <CasusBelli holderId={entityId} blocked={blocked} />}
      {community && kind !== 'polity' && (
        <WarProduction communityId={entityId} blocked={blocked} />
      )}
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
        <LayDownVessel
          ownerId={entityId}
          blocked={SHIP_OWNERS.has(kind) ? blocked : NO_SHIPS}
        />
      </Panel>
      <Vendettas entityId={entityId} blocked={blocked} />
    </div>
  )
}
