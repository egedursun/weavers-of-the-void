import '@/styles/index.css'
import { describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { page } from 'vitest/browser'
import { OrnateFrame } from '@/components/ui/ornate'
import { PanelGrid } from './PanelGrid'
import { Section } from './Section'

const ORNAMENTS =
  ':scope > .ornate-corner, :scope > .ornate-stud, :scope > .ornate-gem, :scope > .ornate-crest, :scope > .ornate-nameplate'

const SLACK = 0.5

type Box = Pick<DOMRect, 'left' | 'right' | 'top' | 'bottom'>

function inside(inner: Box, outer: Box) {
  return (
    inner.left >= outer.left - SLACK &&
    inner.right <= outer.right + SLACK &&
    inner.top >= outer.top - SLACK &&
    inner.bottom <= outer.bottom + SLACK
  )
}

function overlaps(a: Box, b: Box) {
  return (
    a.left < b.right - SLACK &&
    b.left < a.right - SLACK &&
    a.top < b.bottom - SLACK &&
    b.top < a.bottom - SLACK
  )
}

async function settled() {
  await Promise.all(
    [...document.images].map((image) =>
      image.complete ? Promise.resolve() : image.decode().catch(() => null)
    )
  )
}

function audit() {
  const bays = [...document.querySelectorAll('[data-slot=ornate-bay]')]
  const escaping: string[] = []
  const clashing: string[] = []
  for (const bay of bays) {
    const frame = bay.firstElementChild as Element
    const ornaments = [...frame.querySelectorAll(ORNAMENTS)]
    for (const ornament of ornaments)
      if (
        !inside(ornament.getBoundingClientRect(), bay.getBoundingClientRect())
      )
        escaping.push(ornament.className)
    const plate = frame.querySelector(':scope > .ornate-nameplate')
    if (plate)
      for (const corner of frame.querySelectorAll(':scope > .ornate-corner'))
        if (
          overlaps(
            plate.getBoundingClientRect(),
            corner.getBoundingClientRect()
          )
        )
          clashing.push(corner.getAttribute('data-corner') ?? '')
  }
  const touching: string[] = []
  bays.forEach((a, index) =>
    bays.slice(index + 1).forEach((b) => {
      if (a.contains(b) || b.contains(a)) return
      if (overlaps(a.getBoundingClientRect(), b.getBoundingClientRect()))
        touching.push(`${a.textContent} / ${b.textContent}`)
    })
  )
  return { bays: bays.length, escaping, clashing, touching }
}

function Panel({ title }: { title: string }) {
  return (
    <Section title={title} surface='card'>
      <p>{title}</p>
    </Section>
  )
}

describe('ornate frames own their ornaments', () => {
  it('never reach a neighbour, even with no gap between them', async () => {
    await page.viewport(1280, 900)
    await render(
      <div className='flex w-full flex-col'>
        <Panel title='First panel' />
        <Panel title='Second panel' />
        <div className='grid grid-cols-2'>
          <Panel title='Left panel' />
          <Panel title='Right panel' />
        </div>
        <div className='grid grid-cols-4'>
          {['One', 'Two', 'Three', 'Four'].map((name) => (
            <OrnateFrame key={name} frame='tile' crest className='p-4'>
              {name}
            </OrnateFrame>
          ))}
        </div>
        <OrnateFrame footCrest className='p-6'>
          Plain frame
        </OrnateFrame>
        <OrnateFrame crest footCrest className='p-6'>
          Crested frame
        </OrnateFrame>
        <OrnateFrame frame='card' crest className='p-4'>
          Card frame
        </OrnateFrame>
      </div>
    )
    await settled()
    const result = audit()
    expect(result.bays).toBe(11)
    expect(result.escaping).toEqual([])
    expect(result.touching).toEqual([])
  })

  it('keeps a long nameplate clear of the corners at every width', async () => {
    const title =
      'A nameplate that carries a very long title that has to be cut short'
    for (const width of [360, 640, 900, 1280]) {
      await page.viewport(width, 900)
      const screen = await render(
        <div className='w-full'>
          <Panel title={title} />
        </div>
      )
      await settled()
      const result = audit()
      expect(result.escaping, `width ${width}`).toEqual([])
      expect(result.clashing, `width ${width}`).toEqual([])
      await screen.unmount()
    }
  })

  it('shows a section title of a few words in full on a phone', async () => {
    await page.viewport(390, 900)
    const screen = await render(
      <div className='w-full px-4'>
        <Panel title='Who reaches Probe World' />
      </div>
    )
    await settled()
    const heading = document.querySelector(
      '.ornate-nameplate > [data-typography]'
    )
    expect(heading).not.toBeNull()
    expect(heading?.scrollHeight ?? 0).toBeLessThanOrEqual(
      (heading?.clientHeight ?? 0) + 1
    )
    expect(heading?.scrollWidth ?? 0).toBeLessThanOrEqual(
      (heading?.clientWidth ?? 0) + 1
    )
    expect(audit().escaping).toEqual([])
    await screen.unmount()
  })

  it('lines up the panels of one row in a panel grid', async () => {
    await page.viewport(1280, 900)
    await render(
      <PanelGrid>
        <Section title='Short' surface='card'>
          <p>One line.</p>
        </Section>
        <Section title='Tall' surface='card'>
          <p>One line.</p>
          <p>Two lines.</p>
          <p>Three lines.</p>
          <p>Four lines.</p>
        </Section>
        <Section title='Alone' surface='card'>
          <p>The last panel takes the whole row.</p>
        </Section>
      </PanelGrid>
    )
    await settled()
    const frames = [
      ...document.querySelectorAll('[data-slot=ornate-frame]'),
    ].map((frame) => frame.getBoundingClientRect())
    expect(frames).toHaveLength(3)
    expect(Math.abs(frames[0].top - frames[1].top)).toBeLessThan(1)
    expect(Math.abs(frames[0].bottom - frames[1].bottom)).toBeLessThan(1)
    expect(frames[2].width).toBeGreaterThan(frames[0].width * 1.8)
  })
})
