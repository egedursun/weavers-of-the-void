import { useQuery } from '@tanstack/react-query'
import { BookUser } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Section, Timeline } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { loreKeys } from '../api/keys'
import { IncidentEntry } from '../mechanics/parts'

export function BiographySection({
  nodeId,
  readOnlyReason,
}: {
  nodeId: number
  readOnlyReason: string | null
}) {
  const view = useQuery({
    queryKey: [...loreKeys.entity(nodeId), 'mechanics'] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/nodes/{node_id}/mechanics', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
  const incidents = view.data?.incidents ?? []
  const epochs = [...new Set(incidents.map((item) => item.epoch))].sort(
    (left, right) => right - left
  )
  return (
    <Section
      id='section-biography'
      title='Biography'
      description='Its life as a chain of causes: everything it took part in, epoch by epoch, with what led to each deed and the notes you kept.'
      icon={BookUser}
    >
      {view.isSuccess && incidents.length === 0 && (
        <Muted>Its story has not begun yet.</Muted>
      )}
      <div className='flex min-w-0 flex-col gap-4'>
        {epochs.map((epoch) => {
          const items = incidents.filter((item) => item.epoch === epoch)
          return (
            <div key={epoch} className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>{`Epoch ${epoch}`}</Label>
              <Timeline label={`Epoch ${epoch}`}>
                {items.map((incident, index) => (
                  <IncidentEntry
                    key={incident.id}
                    incident={incident}
                    last={index === items.length - 1}
                    blocked={readOnlyReason ?? undefined}
                  />
                ))}
              </Timeline>
            </div>
          )
        })}
      </div>
    </Section>
  )
}
