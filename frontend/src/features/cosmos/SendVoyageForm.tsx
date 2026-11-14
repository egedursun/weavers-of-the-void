import { useMemo, useState } from 'react'
import { Send } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { plural } from '@/lib/units'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FormRow } from '@/components/domain'
import { Muted } from '@/components/typography'
import { CosmicActionButton } from './CosmicActionButton'
import { type JourneyIntent } from './api'
import {
  type CosmosIndex,
  isUnderway,
  otherEnd,
  routeState,
} from './model/cosmosModel'
import {
  JOURNEY_INTENTS,
  JOURNEY_INTENT_LABEL,
  TRAVEL_METHOD_LABEL,
  humanize,
} from './model/labels'
import { type RuleBook, ruleText } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

type SendVoyageFormProps = {
  index: CosmosIndex
  rules: RuleBook
  defaultWorldId: number | undefined
}

export function SendVoyageForm({
  index,
  rules,
  defaultWorldId,
}: SendVoyageFormProps) {
  const origins = index.worlds.filter(
    (item) => item.world.discovery !== 'forgotten'
  )
  const [originChoice, setOrigin] = useState<string>('')
  const origin = Number(
    originChoice || defaultWorldId || origins[0]?.world.id || 0
  )
  const [traveller, setTraveller] = useState('')
  const [routeChoice, setRoute] = useState('')
  const [intent, setIntent] = useState<JourneyIntent>('exploration')
  const [percent, setPercent] = useState(() => {
    const known = rules.get('voyagePercent')
    return known === undefined ? '' : String(known)
  })
  const travelling = useMemo(
    () =>
      new Set(
        index.data.journeys
          .filter(isUnderway)
          .map((journey) => journey.traveller_entity_id)
      ),
    [index]
  )
  const travellers = index
    .communitiesOf(origin)
    .filter((item) => !travelling.has(item.id))
    .sort(
      (a, b) => b.power_level - a.power_level || a.name.localeCompare(b.name)
    )
  const routes = index
    .routesOf(origin)
    .filter((route) => route.known && routeState(route).open)
  const selectedRoute = routeChoice || (routes[0] ? String(routes[0].id) : '')
  const maxPercent = rules.get('voyageMaxPercent')
  const parsedPercent = percent.trim() === '' ? undefined : Number(percent)
  const percentInvalid =
    parsedPercent !== undefined &&
    (!Number.isInteger(parsedPercent) ||
      parsedPercent < 1 ||
      (maxPercent !== undefined && parsedPercent > maxPercent))
  const send = useCosmicAction({
    run: () =>
      unwrap(
        api.POST('/api/entities/{entity_id}/expedition', {
          params: { path: { entity_id: Number(traveller) } },
          body: {
            route_id: Number(selectedRoute),
            intent,
            ...(parsedPercent === undefined ? {} : { percent: parsedPercent }),
          },
        })
      ),
    success: 'Voyage set out',
    onDone: () => {
      setTraveller('')
      setPercent('')
    },
  })
  const blocked =
    routes.length === 0
      ? 'No open, known route leaves this world.'
      : traveller === ''
        ? 'Choose a traveller first.'
        : percentInvalid
          ? `Enter a whole percent from 1 to ${ruleText(maxPercent)}.`
          : undefined
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <FormRow label='From'>
        {(id) => (
          <Select
            value={String(origin)}
            onValueChange={(value) => {
              setOrigin(value)
              setTraveller('')
              setRoute('')
            }}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue placeholder='Choose a world' />
            </SelectTrigger>
            <SelectContent>
              {origins.map((item) => (
                <SelectItem key={item.world.id} value={String(item.world.id)}>
                  {item.world.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='Traveller'>
        {(id) => (
          <Select value={traveller} onValueChange={setTraveller}>
            <SelectTrigger id={id} className='w-full'>
              <SelectValue
                placeholder={
                  travellers.length
                    ? 'Choose a community'
                    : 'No free community here'
                }
              />
            </SelectTrigger>
            <SelectContent>
              {travellers.map((item) => (
                <SelectItem key={item.id} value={String(item.id)}>
                  {`${item.name} · ${humanize(item.entity_type)}`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='Route'>
        {(id) => (
          <Select value={selectedRoute} onValueChange={setRoute}>
            <SelectTrigger id={id} className='w-full'>
              <SelectValue placeholder='No open route' />
            </SelectTrigger>
            <SelectContent>
              {routes.map((route) => (
                <SelectItem key={route.id} value={String(route.id)}>
                  {`${index.worldName(otherEnd(route, origin))} · ${TRAVEL_METHOD_LABEL[route.method]} · ${plural(route.duration_epochs, 'epoch', 'epochs')} · danger ${route.danger}`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='Intent'>
        {(id) => (
          <Select
            value={intent}
            onValueChange={(value) => setIntent(value as JourneyIntent)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {JOURNEY_INTENTS.map((item) => (
                <SelectItem key={item} value={item}>
                  {JOURNEY_INTENT_LABEL[item]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow
        label='Share of the population'
        description={`Percent, 1 to ${ruleText(maxPercent)}; blank uses ${ruleText(rules.get('voyagePercent'))}.`}
      >
        {(id) => (
          <Input
            id={id}
            type='number'
            min={1}
            max={maxPercent}
            inputMode='numeric'
            placeholder={ruleText(rules.get('voyagePercent'))}
            value={percent}
            aria-invalid={percentInvalid || undefined}
            onChange={(event) => setPercent(event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <CosmicActionButton
          actionId='expedition'
          label='Set out'
          icon={Send}
          variant='default'
          pending={send.isPending}
          blockedReason={blocked}
          onRun={() => send.mutate()}
        />
      </div>
      <Muted variant='caption'>
        The travellers leave their home with their share of the population. A
        voyage the god commands ignores vessel and knowledge requirements.
      </Muted>
    </div>
  )
}
