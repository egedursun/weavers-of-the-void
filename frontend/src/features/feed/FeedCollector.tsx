import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { type ServerEvent, useAnyEvent } from '@/realtime'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { queryKeys } from '@/api/queryKeys'
import { FEED_STREAM_THROTTLE_MS } from '@/constants/ui'
import { useEpochRun } from '@/features/epoch/runStore'
import { useImageGenEvents } from '@/features/images/imageGenState'
import { type FeedLine, toFeedLine } from './feedModel'
import { playTone, startDrone, stopDrone } from './feedSound'
import { useFeed, useFeedPreferences } from './feedStore'
import { THROTTLED_STREAM_KINDS } from './feedStream'
import { closesStreams, feedToast } from './feedToasts'
import { leavesWorld } from './feedWorld'

const ACTIVITY_LOG_KEY = [...queryKeys.epochs.all, 'activity-log'] as const

function useActivityRestore() {
  const restore = useFeed((state) => state.restore)
  const restored = useFeed((state) => state.restored)
  const apply = useEpochRun((state) => state.apply)
  const log = useQuery({
    queryKey: ACTIVITY_LOG_KEY,
    queryFn: () => unwrap(api.GET('/api/activity-log')),
    enabled: !restored,
    staleTime: Infinity,
  })
  const applied = useRef(false)
  useEffect(() => {
    if (!log.data || applied.current) return
    applied.current = true
    const events = log.data as ServerEvent[]
    for (const event of events) apply(event)
    restore(events.map(toFeedLine).filter((line) => line !== null))
  }, [apply, log.data, restore])
}

function useAmbientDrone() {
  const ambient = useFeedPreferences((state) => state.ambient)
  useEffect(() => {
    if (!ambient) {
      stopDrone()
      return
    }
    const begin = () => startDrone()
    window.addEventListener('pointerdown', begin, { once: true })
    return () => window.removeEventListener('pointerdown', begin)
  }, [ambient])
}

function useThrottledAdd() {
  const add = useFeed((state) => state.add)
  const pending = useRef<FeedLine[]>([])
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const flush = useCallback(() => {
    if (timer.current !== null) clearTimeout(timer.current)
    timer.current = null
    if (pending.current.length === 0) return
    const batch = pending.current
    pending.current = []
    add(batch)
  }, [add])
  useEffect(() => flush, [flush])
  return useCallback(
    (line: FeedLine, throttled: boolean) => {
      pending.current.push(line)
      if (!throttled) {
        flush()
        return
      }
      if (timer.current === null)
        timer.current = setTimeout(flush, FEED_STREAM_THROTTLE_MS)
    },
    [flush]
  )
}

export function FeedCollector() {
  const push = useThrottledAdd()
  const apply = useEpochRun((state) => state.apply)
  const closeOpen = useFeed((state) => state.closeOpen)
  const [since] = useState(() => Date.now())
  useActivityRestore()
  useAmbientDrone()
  useImageGenEvents()
  useAnyEvent((event) => {
    if (leavesWorld(event)) useFeed.getState().clear()
    apply(event)
    if (closesStreams(event)) closeOpen()
    feedToast(event, since)
    const line = toFeedLine(event)
    if (!line) return
    push(line, THROTTLED_STREAM_KINDS.has(event.kind))
    const { sounds, muted } = useFeedPreferences.getState()
    if (sounds && line.category && !muted.includes(line.category))
      playTone(line.category)
  })
  return null
}
