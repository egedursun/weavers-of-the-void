import { useState } from 'react'
import { Footprints } from 'lucide-react'
import { EmptyState, LoadingBlock } from '@/components/domain'
import { StepButton } from '@/features/cycles/parts'
import { AccountDigest } from './AccountDigest'
import { useNodeHistory } from './api'

function Unfolded({ nodeId, kind }: { nodeId: number; kind: string | null }) {
  const history = useNodeHistory(nodeId, { role: null, kind, limit: 1 })
  if (history.isPending) return <LoadingBlock label='Finding how it unfolded' />
  if (history.isError)
    return (
      <EmptyState
        icon={Footprints}
        size='inline'
        title='How it unfolded could not be read'
        description={history.error.message}
      />
    )
  const first = history.data.incidents[0]
  if (!first)
    return (
      <EmptyState
        icon={Footprints}
        size='inline'
        title='No account of it is kept'
        description='It was set down before the world kept how happenings unfold.'
      />
    )
  return <AccountDigest incidentId={first.incident_id} />
}

export function ReportSteps({
  nodeId,
  kind = null,
  label = 'How it unfolded',
}: {
  nodeId: number | null
  kind?: string | null
  label?: string
}) {
  const [open, setOpen] = useState(false)
  if (nodeId === null) return null
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <StepButton
        icon={Footprints}
        label={open ? `Hide ${label.toLowerCase()}` : label}
        variant='ghost'
        busy={null}
        onClick={() => setOpen((current) => !current)}
      />
      {open && <Unfolded nodeId={nodeId} kind={kind} />}
    </div>
  )
}
