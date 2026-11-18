import { useState } from 'react'
import { Plus } from 'lucide-react'
import { placeKindValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Section, FieldTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { busyOf, PERCENT } from '../lore/model'
import { MindPicker } from '../mind/parts'
import { AdjustPanel, NumberField, SwitchField, Tile } from '../wilds/parts'
import { type ActionBody, usePlaceAction } from './api'
import { PLACE_ICON, choices, kindOf } from './labels'

type Kind = ActionBody<'place:create'>['kind']

export function CreatePlace({ regionId }: { regionId: number }) {
  const { reason } = useGodGate()
  const create = usePlaceAction('place:create')
  const [name, setName] = useState('')
  const [kind, setKind] = useState<Kind>('grove')
  const [mystery, setMystery] = useState('50')
  const [danger, setDanger] = useState('30')
  const [fertility, setFertility] = useState('50')
  const [holy, setHoly] = useState(false)
  const [sacredness, setSacredness] = useState('60')
  const busy =
    busyOf(reason({ world: true }), create.isPending) ??
    (name.trim() ? null : 'Name the place first')
  const spec = kindOf(kind)
  return (
    <Section
      id='section-create-place'
      title='Bring forth a place'
      description='Raise a new place of a chosen kind in this region: its ground, cover, water, sanctity and secrets follow its kind.'
      icon={PLACE_ICON}
    >
      <div className='@container/place flex min-w-0 flex-col gap-3'>
        <Tile spec={spec} caption={spec.hint} />
        <AdjustPanel
          title='A new place'
          note='Every new place is written into the ledger and can be undone.'
          label='Create'
        >
          <div className='grid min-w-0 grid-cols-1 gap-3 @md/place:grid-cols-2 @3xl/place:grid-cols-3'>
            <FieldTile id={`place-name-${regionId}`} label='Name'>
              <Input
                id={`place-name-${regionId}`}
                value={name}
                maxLength={60}
                onChange={(event) => setName(event.target.value)}
              />
            </FieldTile>
            <MindPicker
              label='Kind'
              value={kind}
              table={choices(placeKindValues, (key) => kindOf(key).label)}
              blocked={null}
              onPick={(value) => setKind(value as Kind)}
            />
            <NumberField
              label='Mystery'
              value={mystery}
              min={0}
              max={PERCENT}
              onChange={setMystery}
            />
            <NumberField
              label='Danger'
              value={danger}
              min={0}
              max={PERCENT}
              onChange={setDanger}
            />
            <NumberField
              label='Fertility'
              value={fertility}
              min={0}
              max={PERCENT}
              onChange={setFertility}
            />
            <SwitchField
              label='Holy from the start'
              checked={holy}
              onChange={setHoly}
            />
            {holy && (
              <NumberField
                label='Sacredness'
                value={sacredness}
                min={0}
                max={PERCENT}
                onChange={setSacredness}
              />
            )}
          </div>
          <Muted variant='caption'>
            A held sacredness keeps the place as holy as you set it until you
            release it.
          </Muted>
          <div>
            <Button
              size='sm'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() =>
                create.mutate(
                  {
                    region_id: regionId,
                    name: name.trim(),
                    kind,
                    mystery: Number(mystery),
                    danger: Number(danger),
                    fertility: Number(fertility),
                    sacredness: holy ? Number(sacredness) : null,
                  },
                  { onSuccess: () => setName('') }
                )
              }
            >
              <Plus />
              Bring it forth
            </Button>
          </div>
        </AdjustPanel>
      </div>
    </Section>
  )
}
