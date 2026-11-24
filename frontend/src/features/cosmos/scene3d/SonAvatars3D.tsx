import { useCallback } from 'react'
import { rarityValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Portrait } from '@/components/domain'
import { useEntryStack } from '@/components/layout/entry/useEntryStack'
import { wordOf } from '@/features/entity/affairs/labels'
import { mediaUrl } from '@/features/pantheon/media'
import { type SonPublic } from '../api'
import { type CosmosIndex } from '../model/cosmosModel'
import { labelKey } from './labelKeys'

const MAX_AVATARS = 7
const AVATAR_COVER_WIDTH = 160

type SonAvatars3DProps = {
  index: CosmosIndex
  sons: SonPublic[]
  labels: Map<string, HTMLElement>
}

export function SonAvatars3D({ index, sons, labels }: SonAvatars3DProps) {
  const entryStack = useEntryStack()
  const byId = new Map(sons.map((son) => [son.son.id, son]))
  const register = useCallback(
    (key: string) => (element: HTMLElement | null) => {
      if (element) labels.set(key, element)
      else labels.delete(key)
    },
    [labels]
  )
  return (
    <div className='pointer-events-none absolute inset-0 overflow-hidden'>
      {index.worlds
        .filter((item) => item.sons.length > 0)
        .map((item) => {
          const shown = item.sons.slice(0, MAX_AVATARS)
          const extra = item.sons.length - shown.length
          return (
            <div
              key={item.world.id}
              ref={register(labelKey('avatars', item.world.id))}
              className='absolute top-0 left-0 flex items-center gap-0.5'
              style={{
                opacity: 0,
                visibility: 'hidden',
                pointerEvents: 'none',
              }}
            >
              {shown.map((ref) => {
                const son = byId.get(ref.id)
                const rarity = son?.son.rarity
                return (
                  <Button
                    key={ref.id}
                    variant='ghost'
                    size='icon-sm'
                    aria-label={`${ref.name}${rarity ? `, ${wordOf(rarityValues, rarity)} son` : ''} on ${item.world.name}`}
                    title={`${ref.name}${rarity ? ` · ${wordOf(rarityValues, rarity)} son` : ''} · on ${item.world.name}`}
                    onClick={() =>
                      void entryStack.open({ kind: 'son', id: String(ref.id) })
                    }
                  >
                    <Portrait
                      name={ref.name}
                      src={mediaUrl(son?.cover, AVATAR_COVER_WIDTH)}
                      size='xs'
                      rarity={rarity}
                    />
                  </Button>
                )
              })}
              {extra > 0 && (
                <Badge
                  size='sm'
                  variant='secondary'
                  title={`${extra} more sons on ${item.world.name}; all are on the world card`}
                >
                  {`+${extra}`}
                </Badge>
              )}
            </div>
          )
        })}
    </div>
  )
}
