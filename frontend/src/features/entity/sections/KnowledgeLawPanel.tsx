import { useState } from 'react'
import { Lightbulb, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { knowledgeBranchValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import {
  EntityLink,
  FormRow,
  KeyValueList,
  PagedList,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Muted, Text } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { type EntityContext, isThinking } from '../actions/context'
import { optionsFor } from '../actions/pickers'
import { usePickerData } from '../actions/usePickerData'
import { useLoreMutation } from '../api/mutations'
import { useKnowledge } from '../api/queries'
import { type NodeRef } from '../api/types'

const REFS_SHOWN = 12

function RefLinks({ refs, empty }: { refs: NodeRef[]; empty: string }) {
  const page = useShowMore(refs, REFS_SHOWN, REFS_SHOWN * 2)
  if (refs.length === 0) return <Muted as='span'>{empty}</Muted>
  return (
    <span className='flex min-w-0 flex-col gap-2'>
      <span className='flex min-w-0 flex-wrap gap-x-2 gap-y-1'>
        {page.visible.map((ref) =>
          ref.kind === 'entity' ? (
            <EntityLink key={ref.id} kind='entity' id={String(ref.id)}>
              {ref.name}
            </EntityLink>
          ) : ref.kind === 'son' ? (
            <EntityLink key={ref.id} kind='son' id={String(ref.id)}>
              {ref.name}
            </EntityLink>
          ) : (
            <Text as='span' key={ref.id}>
              {ref.name}
            </Text>
          )
        )}
      </span>
      <ShowMore state={page} />
    </span>
  )
}

export function KnowledgeLawPanel({
  ctx,
  readOnlyReason,
}: {
  ctx: EntityContext
  readOnlyReason: string | null
}) {
  const knowledge = useKnowledge()
  const data = usePickerData()
  const [chosen, setChosen] = useState<number | null>(null)
  const known = ctx.bonds.filter(
    (bond) => bond.kind === 'knows' && bond.outgoing && bond.state === 'active'
  )
  const own = knowledge.data?.find(
    (item) => item.knowledge.id === ctx.entity.id
  )
  const teach = useLoreMutation({
    writes: [{ lever: 'knowledge:set' }],
    run: (input: { knowledge_id: number; known: boolean }) =>
      unwrap(
        api.PUT('/api/entities/{entity_id}/knowledge', {
          params: { path: { entity_id: ctx.entity.id } },
          body: input,
        })
      ),
    onDone: () => setChosen(null),
  })
  const thinking = isThinking(ctx.type)
  if (!own && !thinking && known.length === 0) return null
  const blocked = readOnlyReason ?? (teach.isPending ? 'Working on it.' : null)
  const options = optionsFor(
    { source: 'knowledge', unknownOnly: true },
    ctx,
    data
  )
  return (
    <Section id='section-knowledge' title={own ? 'Knowledge' : 'What it knows'}>
      {own && (
        <KeyValueList
          items={[
            {
              label: 'Branch',
              value: `${own.branch ? wordOf(knowledgeBranchValues, own.branch) : 'Unsorted'}${own.level !== null ? ` · level ${own.level}` : ''}`,
            },
            ...(own.spread !== null
              ? [{ label: 'Spread', value: `${own.spread}` }]
              : []),
            {
              label: 'Found by',
              value: own.inventor ? (
                <RefLinks refs={[own.inventor]} empty='' />
              ) : (
                'Unknown'
              ),
            },
            {
              label: 'Needs first',
              value: <RefLinks refs={own.prerequisites} empty='Nothing' />,
            },
            {
              label: 'Known by',
              value: <RefLinks refs={own.knowers} empty='Nobody yet' />,
            },
          ]}
        />
      )}
      {thinking && (
        <div className='flex min-w-0 flex-col gap-3'>
          {known.length === 0 ? (
            <Muted>It knows nothing that has a name yet.</Muted>
          ) : (
            <PagedList
              items={known}
              initial={20}
              noun={['thing known', 'things known']}
              className='flex min-w-0 flex-wrap gap-2'
              itemKey={(bond) => bond.id}
            >
              {(bond) => (
                <li className='flex min-w-0 items-center gap-1 rounded-md border ps-2'>
                  {bond.other && (
                    <EntityLink kind='entity' id={String(bond.other.id)}>
                      {bond.other.name}
                    </EntityLink>
                  )}
                  <Button
                    act={teach}
                    variant='ghost'
                    size='icon-sm'
                    aria-label={`Make it forget ${bond.other?.name ?? 'this'}`}
                    disabled={blocked !== null}
                    disabledReason={blocked ?? undefined}
                    onClick={() =>
                      bond.other &&
                      teach.mutate({
                        knowledge_id: bond.other.id,
                        known: false,
                      })
                    }
                  >
                    <X />
                  </Button>
                </li>
              )}
            </PagedList>
          )}
          <FormRow
            label='Grant knowledge'
            description='Free; no essence, no chronicle line'
          >
            {(id) => (
              <div className='flex w-full min-w-0 flex-col gap-2 sm:flex-row'>
                <div className='min-w-0 sm:flex-1'>
                  <RecordCombobox
                    id={id}
                    options={options}
                    value={chosen === null ? null : String(chosen)}
                    onChange={(value) =>
                      setChosen(value === null ? null : Number(value))
                    }
                    placeholder={
                      options.length
                        ? 'Choose knowledge'
                        : 'It knows everything there is'
                    }
                    disabled={options.length === 0}
                    disabledReason='It already knows all knowledge in the world.'
                    aria-label='Knowledge to grant'
                  />
                </div>
                <Button
                  act={teach}
                  variant='outline'
                  disabled={blocked !== null || chosen === null}
                  disabledReason={blocked ?? 'Choose knowledge first.'}
                  onClick={() =>
                    chosen !== null &&
                    teach.mutate({ knowledge_id: chosen, known: true })
                  }
                >
                  <Lightbulb />
                  Grant
                </Button>
              </div>
            )}
          </FormRow>
        </div>
      )}
    </Section>
  )
}
