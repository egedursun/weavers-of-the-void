import { Fragment, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNames } from '@/features/entity/api/queries'
import { fetchWorldState, overviewKeys } from '@/features/overview/api'
import { EntityLink } from './EntityLink'
import {
  type MentionIndex,
  type MentionName,
  type MentionThread,
  hasMentions,
  parseLore,
} from './mentionTokens'
import { type LinkTarget, stripMarkers } from './nameLinks'

export type { LinkTarget } from './nameLinks'

const NO_TARGETS: LinkTarget[] = []

function useMentionIndex(enabled: boolean): MentionIndex {
  const names = useNames(enabled)
  const state = useQuery({
    queryKey: overviewKeys.state,
    queryFn: fetchWorldState,
    enabled,
  })
  return useMemo(() => {
    const byId = new Map<number, MentionName>()
    const threads = new Map<number, MentionThread>()
    if (!enabled) return { names: byId, threads }
    for (const entry of names.data ?? []) byId.set(entry.id, entry)
    for (const thread of state.data?.threads ?? [])
      threads.set(thread.id, thread)
    return { names: byId, threads }
  }, [enabled, names.data, state.data?.threads])
}

type MentionTextProps = {
  text: string
  targets?: LinkTarget[]
  selfId?: number
}

export function MentionText({
  text,
  targets = NO_TARGETS,
  selfId,
}: MentionTextProps) {
  const tokens = hasMentions(stripMarkers(text))
  const index = useMentionIndex(tokens)
  const pieces = useMemo(
    () => parseLore(text, index, targets, selfId),
    [text, index, targets, selfId]
  )
  return (
    <>
      {pieces.map((piece, position) => {
        if (piece.type === 'link')
          return (
            <EntityLink
              key={position}
              kind={piece.kind}
              id={piece.kind === 'creator' ? undefined : String(piece.id)}
            >
              {piece.text}
            </EntityLink>
          )
        if (piece.type === 'thread')
          return (
            <abbr key={position} title={piece.title} className='no-underline'>
              {piece.text}
            </abbr>
          )
        return <Fragment key={position}>{piece.text}</Fragment>
      })}
    </>
  )
}
