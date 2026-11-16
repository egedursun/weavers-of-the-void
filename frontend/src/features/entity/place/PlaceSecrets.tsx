import { useState } from 'react'
import { EyeOff, KeyRound, Lock, Plus, Trash2, Unlock } from 'lucide-react'
import {
  knowledgeBranchValues,
  magicSchoolValues,
  materialKindValues,
  secretKindValues,
} from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EntityLink, Medallion, Paged } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useSons } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { plain } from '../environment/labels'
import { busyOf, PERCENT } from '../lore/model'
import { MindPicker } from '../mind/parts'
import { AdjustPanel, Card, NumberField } from '../wilds/parts'
import { type PlaceProfile, type PlaceSecret, usePlaceAction } from './api'
import { MODE, ORIGIN, choices, secretOf } from './labels'

type SecretKindValue = PlaceSecret['kind']
const NONE = 'none'

function humanize(key: string): string {
  return plain({}, key)
}

function detail(secret: PlaceSecret): string | null {
  const value = secret.material ?? secret.school ?? secret.branch
  return value ? humanize(value) : null
}

function SecretTile({
  secret,
  placeId,
}: {
  secret: PlaceSecret
  placeId: number
}) {
  const { reason } = useGodGate()
  const sonRows = useSons()
  const sons = Object.fromEntries(
    (sonRows.data ?? []).map((view) => [String(view.son.id), view.son.name])
  )
  const reveal = usePlaceAction('place:reveal')
  const edit = usePlaceAction('place:secret_edit')
  const erase = usePlaceAction('place:secret_delete')
  const busy = busyOf(
    reason(),
    reveal.isPending,
    edit.isPending,
    erase.isPending
  )
  const spec = secretOf(secret.kind)
  const known =
    secret.revealed_epoch !== null && secret.revealed_epoch !== undefined
  const extra = detail(secret)
  return (
    <div
      className='@container/secret flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'
      data-secret={secret.id}
    >
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion
          icon={known ? spec.icon : EyeOff}
          tone={known ? (spec.tone ?? 'gold') : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='medium' truncate>
            {known ? spec.label : `Hidden: ${spec.label.toLowerCase()}`}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {known
              ? `Found in age ${secret.revealed_epoch} by ${secret.revealed_by_name ?? MODE[secret.revealed_by ?? ''] ?? 'someone'}`
              : `${ORIGIN[secret.origin] ?? 'Hidden'}${secret.hidden_by_son_id !== null ? ` by ${sons[String(secret.hidden_by_son_id)] ?? 'a son'}` : ''}; strength ${secret.strength}${extra ? `; ${extra}` : ''}`}
          </Muted>
        </div>
        {secret.sealed && (
          <Badge size='sm' variant='destructive'>
            Sealed
          </Badge>
        )}
        {secret.held && <Badge size='sm'>Held hidden</Badge>}
      </div>
      {secret.result_entity_id && secret.result_name && (
        <EntityLink kind='entity' id={String(secret.result_entity_id)} showIcon>
          {secret.result_name}
        </EntityLink>
      )}
      <div className='flex min-w-0 flex-wrap gap-2'>
        {!known && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() =>
              reveal.mutate({ secret_id: secret.id, release: false })
            }
          >
            <KeyRound />
            Reveal
          </Button>
        )}
        {secret.sealed && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() =>
              reveal.mutate({ secret_id: secret.id, release: true })
            }
          >
            <Unlock />
            Break the seal
          </Button>
        )}
        {!known && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() =>
              edit.mutate({ secret_id: secret.id, held: !secret.held })
            }
          >
            <Lock />
            {secret.held ? 'Let the land give it up' : 'Keep it hidden'}
          </Button>
        )}
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          aria-label={`Erase the secret of place ${placeId}`}
          onClick={() => erase.mutate({ secret_id: secret.id })}
        >
          <Trash2 />
          Erase
        </Button>
      </div>
      {!known && <ReshapeSecret secret={secret} />}
    </div>
  )
}

function ReshapeSecret({ secret }: { secret: PlaceSecret }) {
  const { reason } = useGodGate()
  const edit = usePlaceAction('place:secret_edit')
  const [kind, setKind] = useState<SecretKindValue>(secret.kind)
  const [strength, setStrength] = useState(String(secret.strength))
  const busy = busyOf(reason(), edit.isPending)
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 @md/secret:grid-cols-3'>
      <MindPicker
        label='Kind'
        value={kind}
        table={choices(secretKindValues, (key) => secretOf(key).label)}
        blocked={busy}
        onPick={(value) => setKind(value as SecretKindValue)}
      />
      <NumberField
        label='Strength'
        value={strength}
        min={0}
        max={PERCENT}
        disabled={busy !== null}
        onChange={setStrength}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() =>
          edit.mutate({
            secret_id: secret.id,
            kind,
            strength: Number(strength),
          })
        }
      >
        Reshape
      </Button>
    </div>
  )
}

function HideSecret({ placeId }: { placeId: number }) {
  const { reason } = useGodGate()
  const hide = usePlaceAction('place:secret', 'A secret now lies hidden')
  const [kind, setKind] = useState<SecretKindValue>('buried_relic')
  const [strength, setStrength] = useState('50')
  const [material, setMaterial] = useState(NONE)
  const [school, setSchool] = useState(NONE)
  const [branch, setBranch] = useState(NONE)
  const busy = busyOf(reason(), hide.isPending)
  const optional = (values: readonly string[]) => ({
    [NONE]: 'Let the land choose',
    ...choices(values, humanize),
  })
  const pick = <T,>(value: string): T | null =>
    value === NONE ? null : (value as T)
  return (
    <AdjustPanel
      title='Hide a secret'
      note='Bury a relic, seal a spirit, hide a seam, lose a rite or open a way below. Searchers, seers and deep miners may find it.'
      label='Hide'
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/place:grid-cols-2 @3xl/place:grid-cols-3'>
        <MindPicker
          label='What lies hidden'
          value={kind}
          table={choices(secretKindValues, (key) => secretOf(key).label)}
          blocked={busy}
          onPick={(value) => setKind(value as SecretKindValue)}
        />
        <NumberField
          label='Strength'
          value={strength}
          min={0}
          max={PERCENT}
          disabled={busy !== null}
          onChange={setStrength}
        />
        {kind === 'hidden_resource' && (
          <MindPicker
            label='Material'
            value={material}
            table={optional(materialKindValues)}
            blocked={busy}
            onPick={setMaterial}
          />
        )}
        {kind === 'lost_rite' && (
          <MindPicker
            label='School'
            value={school}
            table={optional(magicSchoolValues)}
            blocked={busy}
            onPick={setSchool}
          />
        )}
        {kind === 'lost_knowledge' && (
          <MindPicker
            label='Branch'
            value={branch}
            table={optional(knowledgeBranchValues)}
            blocked={busy}
            onPick={setBranch}
          />
        )}
      </div>
      <Muted variant='caption'>{secretOf(kind).hint}</Muted>
      <div>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() =>
            hide.mutate({
              place_id: placeId,
              kind,
              strength: Number(strength),
              material: kind === 'hidden_resource' ? pick(material) : null,
              school: kind === 'lost_rite' ? pick(school) : null,
              branch: kind === 'lost_knowledge' ? pick(branch) : null,
            })
          }
        >
          <Plus />
          Hide it
        </Button>
      </div>
    </AdjustPanel>
  )
}

export function PlaceSecrets({ profile }: { profile: PlaceProfile }) {
  const hidden = profile.secrets.filter(
    (secret) =>
      secret.revealed_epoch === null || secret.revealed_epoch === undefined
  ).length
  return (
    <Card
      title='Secrets'
      icon={KeyRound}
      tone={hidden > 0 ? 'warning' : 'muted'}
      hint={`${profile.secrets.length - hidden} found, ${hidden} still hidden`}
    >
      {profile.secrets.length === 0 ? (
        <Muted>Nothing lies hidden here, that anyone knows.</Muted>
      ) : (
        <div className='grid min-w-0 grid-cols-1 gap-2 @3xl/card:grid-cols-2'>
          <Paged items={profile.secrets}>
            {(secret) => (
              <SecretTile
                key={secret.id}
                secret={secret}
                placeId={profile.place_id}
              />
            )}
          </Paged>
        </div>
      )}
      <HideSecret placeId={profile.place_id} />
    </Card>
  )
}
