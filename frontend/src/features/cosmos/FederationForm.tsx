import { useState } from 'react'
import { Handshake, Plus, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FormRow, Paged } from '@/components/domain'
import { MultiSelect } from '@/components/domain/MultiSelect'
import { Muted, Text } from '@/components/typography'
import { CosmicActionButton } from './CosmicActionButton'
import { type CosmosIndex } from './model/cosmosModel'
import { humanize } from './model/labels'
import { useCosmicAction } from './useCosmicAction'

const NAME_MAX = 80
const MIN_MEMBERS = 2

export function FederationForm({ index }: { index: CosmosIndex }) {
  const [members, setMembers] = useState<number[]>([])
  const [name, setName] = useState('')
  const multiWorld = index.worlds.length > 1
  const communities = [...index.data.communities].sort((a, b) =>
    a.name.localeCompare(b.name)
  )
  const byId = new Map(communities.map((item) => [item.id, item]))
  const toggle = (id: number) =>
    setMembers((current) =>
      current.includes(id)
        ? current.filter((member) => member !== id)
        : [...current, id]
    )
  const found = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/federations', {
          body: { member_ids: members, name: name.trim() },
        })
      ),
    success: 'Federation founded',
    onDone: () => {
      setMembers([])
      setName('')
    },
  })
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <FormRow label='Members' description='At least two living communities.'>
        {() => (
          <div className='flex min-w-0 flex-1 flex-col gap-2'>
            {members.length > 0 && (
              <ul className='flex min-w-0 flex-col gap-1'>
                <Paged items={members} as='li'>
                  {(id) => (
                    <li key={id} className='flex min-w-0 items-center gap-2'>
                      <Text as='span' truncate className='flex-1'>
                        {byId.get(id)?.name ?? 'Unnamed'}
                      </Text>
                      <Button
                        variant='ghost'
                        size='icon-sm'
                        aria-label={`Remove ${byId.get(id)?.name ?? id}`}
                        onClick={() => toggle(id)}
                      >
                        <X />
                      </Button>
                    </li>
                  )}
                </Paged>
              </ul>
            )}
            <MultiSelect
              label='Communities'
              min={MIN_MEMBERS}
              icon={<Plus />}
              className='justify-start'
              options={communities.map((item) => ({
                value: String(item.id),
                label: item.name,
                detail: multiWorld
                  ? `${humanize(item.entity_type)} · ${index.worldName(item.world_id)}`
                  : humanize(item.entity_type),
              }))}
              value={members.map(String)}
              onChange={(next) => setMembers(next.map(Number))}
              searchPlaceholder='Search community…'
              emptyText='No living community.'
            />
          </div>
        )}
      </FormRow>
      <FormRow label='Name' description='Optional.'>
        {(id) => (
          <Input
            id={id}
            value={name}
            maxLength={NAME_MAX}
            placeholder='The name of the federation'
            onChange={(event) => setName(event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <CosmicActionButton
          actionId='federation'
          label='Found the federation'
          icon={Handshake}
          variant='default'
          pending={found.isPending}
          blockedReason={
            members.length < MIN_MEMBERS
              ? 'Pick at least two communities for a federation.'
              : undefined
          }
          onRun={() => found.mutate()}
        />
      </div>
      <Muted variant='caption'>
        Members share defence and trade; Fate writes the union into the
        chronicle.
      </Muted>
    </div>
  )
}
