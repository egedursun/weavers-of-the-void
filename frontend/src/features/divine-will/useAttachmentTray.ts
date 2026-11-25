import { useCallback, useEffect, useRef, useState } from 'react'
import { formatBytes, plural } from '@/lib/units'
import { uploadAttachment } from './api'
import { type WillAttachment, type WillCapabilities } from './types'

const MEBIBYTE = 1024 * 1024

export type TrayStatus = 'uploading' | 'done' | 'failed' | 'rejected'

export type TrayFile = {
  key: string
  file: File
  progress: number
  status: TrayStatus
  attachment: WillAttachment | null
  error: string
  preview: string | null
}

export type Limits = Pick<
  WillCapabilities,
  'upload_max_files' | 'upload_max_mb'
>

let nextKey = 0

function keyOf(): string {
  nextKey += 1
  return `file-${String(nextKey)}`
}

function rejection(file: File, limits: Limits, count: number): string {
  if (count >= limits.upload_max_files)
    return `Only ${plural(limits.upload_max_files, 'file')} fit in one message.`
  if (file.size > limits.upload_max_mb * MEBIBYTE)
    return `${formatBytes(file.size)} is over the ${String(limits.upload_max_mb)} MB limit.`
  if (file.size === 0) return 'The file is empty.'
  return ''
}

export function useAttachmentTray(limits: Limits | null) {
  const [files, setFiles] = useState<TrayFile[]>([])
  const controllers = useRef(new Map<string, AbortController>())
  const latest = useRef(files)
  useEffect(() => {
    latest.current = files
  })

  const patch = useCallback((key: string, change: Partial<TrayFile>) => {
    setFiles((current) =>
      current.map((item) => (item.key === key ? { ...item, ...change } : item))
    )
  }, [])

  const add = useCallback(
    (incoming: File[]) => {
      if (!limits) return
      let accepted = latest.current.filter(
        (item) => item.status !== 'rejected' && item.status !== 'failed'
      ).length
      const added: TrayFile[] = incoming.map((file) => {
        const reason = rejection(file, limits, accepted)
        if (!reason) accepted += 1
        return {
          key: keyOf(),
          file,
          progress: 0,
          status: reason ? 'rejected' : 'uploading',
          attachment: null,
          error: reason,
          preview: file.type.startsWith('image/')
            ? URL.createObjectURL(file)
            : null,
        }
      })
      setFiles((current) => [...current, ...added])
      for (const item of added) {
        if (item.status !== 'uploading') continue
        const controller = new AbortController()
        controllers.current.set(item.key, controller)
        uploadAttachment(
          item.file,
          (progress) => patch(item.key, { progress }),
          controller.signal
        )
          .then((attachment) =>
            patch(item.key, { status: 'done', progress: 1, attachment })
          )
          .catch((error: unknown) => {
            if (controller.signal.aborted) return
            patch(item.key, {
              status: 'failed',
              error: error instanceof Error ? error.message : String(error),
            })
          })
          .finally(() => controllers.current.delete(item.key))
      }
    },
    [limits, patch]
  )

  const remove = useCallback((key: string) => {
    controllers.current.get(key)?.abort()
    controllers.current.delete(key)
    setFiles((current) => {
      const gone = current.find((item) => item.key === key)
      if (gone?.preview) URL.revokeObjectURL(gone.preview)
      return current.filter((item) => item.key !== key)
    })
  }, [])

  const clear = useCallback(() => {
    for (const controller of controllers.current.values()) controller.abort()
    controllers.current.clear()
    setFiles((current) => {
      for (const item of current)
        if (item.preview) URL.revokeObjectURL(item.preview)
      return []
    })
  }, [])

  const ids = files.flatMap((item) =>
    item.status === 'done' && item.attachment ? [item.attachment.id] : []
  )
  const uploading = files.some((item) => item.status === 'uploading')
  const accepted = files.filter(
    (item) => item.status === 'uploading' || item.status === 'done'
  ).length
  return { files, add, remove, clear, ids, uploading, accepted }
}

export type AttachmentTray = ReturnType<typeof useAttachmentTray>
