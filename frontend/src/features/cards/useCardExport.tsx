import { useCallback, useEffect, useRef, useState } from 'react'
import { toPng } from 'html-to-image'
import { createPortal } from 'react-dom'
import { toast } from 'sonner'
import { CardFace } from './LoreCard'
import { type CharacterCard } from './api'
import { type CardSide, cardFileName } from './cardModel'

const EXPORT_ART_WIDTH = 1280
const EXPORT_PIXEL_RATIO = 2

type ExportJob = {
  card: CharacterCard
  side: CardSide
}

async function settled(node: HTMLElement): Promise<void> {
  await document.fonts.ready
  await Promise.all(
    Array.from(node.querySelectorAll('img'), (image) =>
      image.decode().catch(() => undefined)
    )
  )
}

function save(url: string, fileName: string) {
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.rel = 'noopener'
  link.click()
}

export function useCardExport() {
  const [job, setJob] = useState<ExportJob | null>(null)
  const target = useRef<HTMLDivElement>(null)
  const running = useRef<ExportJob | null>(null)

  useEffect(() => {
    if (!job || running.current === job) return
    running.current = job
    const run = async () => {
      const node = target.current
      if (!node) throw new Error('The card could not be laid out.')
      await settled(node)
      const url = await toPng(node, { pixelRatio: EXPORT_PIXEL_RATIO })
      save(url, cardFileName(job.card, job.side))
    }
    run()
      .then(() =>
        toast.success(
          `${job.side === 'front' ? 'Front' : 'Back'} of ${job.card.name} saved`
        )
      )
      .catch((error: unknown) =>
        toast.error(
          error instanceof Error
            ? `The card could not be saved: ${error.message}`
            : 'The card could not be saved.'
        )
      )
      .finally(() => {
        running.current = null
        setJob(null)
      })
  }, [job])

  const download = useCallback((card: CharacterCard, side: CardSide) => {
    setJob((current) => current ?? { card, side })
  }, [])

  const layer = job
    ? createPortal(
        <div className='lore-card-export' aria-hidden='true'>
          <div ref={target}>
            <CardFace
              card={job.card}
              side={job.side}
              artWidth={EXPORT_ART_WIDTH}
            />
          </div>
        </div>,
        document.body
      )
    : null

  return {
    layer,
    download,
    busyReason: job ? `Saving the card of ${job.card.name}.` : null,
  }
}
