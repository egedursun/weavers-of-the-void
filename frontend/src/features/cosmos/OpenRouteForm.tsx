import { useState } from 'react'
import { Route as RouteIcon } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FormRow } from '@/components/domain'
import { useCosmographyCatalog } from '@/features/cosmography/api'
import { SCOPES } from '@/features/cosmography/labels'
import { CosmicActionButton } from './CosmicActionButton'
import { type TravelMethod } from './api'
import { type CosmosIndex } from './model/cosmosModel'
import { TRAVEL_METHODS, TRAVEL_METHOD_LABEL } from './model/labels'
import { type RuleBook, ruleText } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

type OpenRouteFormProps = {
  index: CosmosIndex
  rules: RuleBook
  worldId: number | undefined
}

export function OpenRouteForm({ index, rules, worldId }: OpenRouteFormProps) {
  const worlds = index.worlds.filter(
    (item) => item.world.discovery !== 'forgotten'
  )
  const [firstChoice, setFirst] = useState('')
  const [secondChoice, setSecond] = useState('')
  const [method, setMethod] = useState<TravelMethod>('ancient_gate')
  const reach = useCosmographyCatalog().data?.method_reach ?? {}
  const reachText = (value: TravelMethod) => {
    const scope = reach[value]
    return scope ? ` · reaches ${SCOPES[scope].label.toLowerCase()}` : ''
  }
  const first =
    firstChoice ||
    String(
      worlds.find((item) => item.world.id === worldId)?.world.id ??
        worlds[0]?.world.id ??
        ''
    )
  const second =
    secondChoice ||
    String(
      worlds.find((item) => String(item.world.id) !== first)?.world.id ?? ''
    )
  const open = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/routes', {
          body: {
            first_world_id: Number(first),
            second_world_id: Number(second),
            method,
          },
        })
      ),
    success: 'A new route was opened',
  })
  const blocked =
    worlds.length < 2
      ? 'Two remembered worlds are needed for a route.'
      : first === second
        ? 'Choose two different worlds.'
        : undefined
  const worldSelect = (
    value: string,
    onChange: (next: string) => void,
    id: string
  ) => (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className='w-full'>
        <SelectValue placeholder='Choose a world' />
      </SelectTrigger>
      <SelectContent>
        {worlds.map((item) => (
          <SelectItem key={item.world.id} value={String(item.world.id)}>
            {item.world.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <FormRow label='From'>{(id) => worldSelect(first, setFirst, id)}</FormRow>
      <FormRow label='To'>{(id) => worldSelect(second, setSecond, id)}</FormRow>
      <FormRow label='Travel method'>
        {(id) => (
          <Select
            value={method}
            onValueChange={(value) => setMethod(value as TravelMethod)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TRAVEL_METHODS.map((value) => (
                <SelectItem key={value} value={value}>
                  {`${TRAVEL_METHOD_LABEL[value]} · ${ruleText(rules.methodDuration(value))} epochs · danger ${ruleText(rules.methodDanger(value))}${reachText(value)}`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <CosmicActionButton
          actionId='route:open'
          label='Open the route'
          icon={RouteIcon}
          variant='default'
          pending={open.isPending}
          blockedReason={blocked}
          onRun={() => open.mutate()}
        />
      </div>
    </div>
  )
}
