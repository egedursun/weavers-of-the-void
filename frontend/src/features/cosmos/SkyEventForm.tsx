import { useState } from 'react'
import { CloudLightning } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FormRow } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { CosmicActionButton } from './CosmicActionButton'
import { type SkyEventKind } from './api'
import { type CosmosIndex, routeState } from './model/cosmosModel'
import {
  SKY_EVENTS,
  SKY_EVENT_DESCRIPTION,
  SKY_EVENT_LABEL,
  TRAVEL_METHOD_LABEL,
} from './model/labels'
import { type RuleBook, ruleText } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

const NO_STAR = 'none'

type SkyBody = components['schemas']['PostCosmicSkyEventBody']

type SkyEventFormProps = {
  index: CosmosIndex
  rules: RuleBook
  worldId: number | undefined
}

export function SkyEventForm({ index, rules, worldId }: SkyEventFormProps) {
  const [kind, setKind] = useState<SkyEventKind>('eclipse')
  const [worldChoice, setWorld] = useState('')
  const [star, setStar] = useState(NO_STAR)
  const [routeChoice, setRoute] = useState('')
  const [epochs, setEpochs] = useState(() => {
    const known = rules.get('stormEpochs')
    return known === undefined ? '' : String(known)
  })
  const openRoutes = index.data.routes.filter((route) => routeState(route).open)
  const storm = kind === 'void_storm'
  const world =
    worldChoice || String(worldId ?? index.worlds[0]?.world.id ?? '')
  const route = routeChoice || String(openRoutes[0]?.id ?? '')
  const parsedEpochs = epochs.trim() === '' ? undefined : Number(epochs)
  const order = useCosmicAction({
    run: () => {
      const body: SkyBody = { kind }
      if (storm) {
        body.route_id = Number(route)
        if (parsedEpochs !== undefined) body.duration = parsedEpochs
      } else if (star !== NO_STAR) body.star_id = Number(star)
      else body.world_id = Number(world)
      return unwrap(api.POST('/api/cosmic/sky-event', { body }))
    },
    success: 'Something happened in the sky',
  })
  const blocked = storm
    ? openRoutes.length === 0
      ? 'A void storm needs an open route.'
      : parsedEpochs !== undefined &&
          (!Number.isInteger(parsedEpochs) || parsedEpochs < 1)
        ? 'Enter a whole number of epochs, at least 1.'
        : undefined
    : !world && star === NO_STAR
      ? 'Choose a world or a star.'
      : undefined
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <FormRow label='Event'>
        {(id) => (
          <Select
            value={kind}
            onValueChange={(value) => setKind(value as SkyEventKind)}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SKY_EVENTS.map((value) => (
                <SelectItem
                  key={value}
                  value={value}
                  disabled={value === 'void_storm' && openRoutes.length === 0}
                >
                  {value === 'void_storm' && openRoutes.length === 0
                    ? `${SKY_EVENT_LABEL[value]} · no open route`
                    : SKY_EVENT_LABEL[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <Muted variant='caption'>{SKY_EVENT_DESCRIPTION[kind]}</Muted>
      {storm ? (
        <>
          <FormRow label='Which route breaks'>
            {(id) => (
              <Select value={route} onValueChange={setRoute}>
                <SelectTrigger id={id} className='w-full'>
                  <SelectValue placeholder='No open route' />
                </SelectTrigger>
                <SelectContent>
                  {openRoutes.map((item) => (
                    <SelectItem key={item.id} value={String(item.id)}>
                      {`${index.worldName(item.world_a_id)} ↔ ${index.worldName(item.world_b_id)} · ${TRAVEL_METHOD_LABEL[item.method]}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </FormRow>
          <FormRow
            label='For how many epochs'
            description={`Blank uses ${ruleText(rules.get('stormEpochs'))}.`}
          >
            {(id) => (
              <Input
                id={id}
                type='number'
                min={1}
                inputMode='numeric'
                placeholder={ruleText(rules.get('stormEpochs'))}
                value={epochs}
                onChange={(event) => setEpochs(event.target.value)}
              />
            )}
          </FormRow>
        </>
      ) : (
        <>
          <FormRow label="Which world's sky">
            {(id) => (
              <Select
                value={world}
                onValueChange={setWorld}
                disabled={star !== NO_STAR}
              >
                <SelectTrigger id={id} className='w-full'>
                  <SelectValue placeholder='Choose a world' />
                </SelectTrigger>
                <SelectContent>
                  {index.worlds.map((item) => (
                    <SelectItem
                      key={item.world.id}
                      value={String(item.world.id)}
                    >
                      {item.world.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </FormRow>
          <FormRow
            label='Or a star'
            description='Choosing a star makes the event happen in its whole system.'
          >
            {(id) => (
              <Select value={star} onValueChange={setStar}>
                <SelectTrigger id={id} className='w-full'>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NO_STAR}>
                    No star, the world above
                  </SelectItem>
                  {index.data.stars.map((item) => (
                    <SelectItem key={item.id} value={String(item.id)}>
                      {item.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </FormRow>
        </>
      )}
      <div className='flex min-w-0 flex-wrap gap-2'>
        <CosmicActionButton
          actionId='cosmic:sky_event'
          label='Command the sky'
          icon={CloudLightning}
          variant='default'
          cost={rules.get('skyEvent')}
          pending={order.isPending}
          blockedReason={blocked}
          onRun={() => order.mutate()}
        />
      </div>
      <SkyHistory index={index} />
    </div>
  )
}

const HISTORY_LENGTH = 6

function SkyHistory({ index }: { index: CosmosIndex }) {
  const events = index.data.sky_events.slice(0, HISTORY_LENGTH)
  if (events.length === 0)
    return <Muted variant='caption'>The sky has been quiet so far.</Muted>
  return (
    <ul className='flex min-w-0 flex-col gap-1.5'>
      {events.map((event) => (
        <li key={event.id} className='flex min-w-0 flex-col gap-0.5'>
          <Text variant='caption' weight='medium'>
            {`Epoch ${event.epoch} · ${SKY_EVENT_LABEL[event.kind]}${event.until_epoch ? ` until epoch ${event.until_epoch}` : ''}${event.world_id ? ` · ${index.worldName(event.world_id)}` : ''}${event.star_id ? ` · ${index.star(event.star_id)?.name ?? 'a star'}` : ''}`}
          </Text>
          {event.text && (
            <Muted variant='caption' truncate={2}>
              {event.text}
            </Muted>
          )}
        </li>
      ))}
    </ul>
  )
}
