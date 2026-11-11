import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useEntityType } from '@/features/arcana/model'
import { CrowdPanel } from './CrowdPanel'
import { GenerationPanel } from './GenerationPanel'
import { HistoryPanel } from './HistoryPanel'
import { NormPanel } from './NormPanel'
import { DatingPanel, DesignPanel, HeraldryPanel } from './RecordsPanels'
import { StoryletPanel } from './StoryletPanel'
import { useNodeCollective } from './api'
import { COLLECTIVE_ICON } from './labels'

export function CollectiveSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeCollective(nodeId)
  const type = useEntityType(nodeId)
  return (
    <Section
      id='section-collective'
      title='Crowds, memory, customs and craft'
      description='The town’s mood and the cascades, mobs and movements it breeds; the accounts kept of every event and how far they stray from the truth; storylets; customs and roles; generations, diasporas and the balance of the people; how years are counted; arms; and the designs that hulls and engines are built to.'
      icon={COLLECTIVE_ICON}
      tone='gold'
    >
      <div
        data-surface='CollectiveSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the crowds and the chronicles' />
        ) : query.isError ? (
          <EmptyState
            icon={COLLECTIVE_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <CrowdPanel
              nodeId={nodeId}
              isTown={type === 'settlement'}
              data={query.data}
              blocked={readOnlyReason}
            />
            <HistoryPanel
              nodeId={nodeId}
              type={type}
              data={query.data}
              blocked={readOnlyReason}
            />
            <StoryletPanel data={query.data} blocked={readOnlyReason} />
            <NormPanel
              nodeId={nodeId}
              type={type}
              data={query.data}
              blocked={readOnlyReason}
            />
            <GenerationPanel
              nodeId={nodeId}
              type={type}
              data={query.data}
              blocked={readOnlyReason}
            />
            <DatingPanel
              nodeId={nodeId}
              type={type}
              data={query.data}
              blocked={readOnlyReason}
            />
            <HeraldryPanel
              nodeId={nodeId}
              name={query.data.node.name}
              type={type}
              data={query.data}
              blocked={readOnlyReason}
            />
            <DesignPanel
              nodeId={nodeId}
              type={type}
              data={query.data}
              blocked={readOnlyReason}
            />
          </>
        )}
      </div>
    </Section>
  )
}
