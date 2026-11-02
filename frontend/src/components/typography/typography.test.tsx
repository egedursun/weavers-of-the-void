import '@/styles/index.css'
import { describe, expect, it } from 'vitest'
import { render } from 'vitest-browser-react'
import { Label, Muted, PageTitle, SectionTitle, Stat, Text } from '.'

function fontSizeOf(selector: string) {
  const element = document.querySelector(selector)
  if (!element) throw new Error(`Missing ${selector}`)
  return parseFloat(getComputedStyle(element).fontSize)
}

describe('typography roles', () => {
  it('renders each role with its own tag and one size', async () => {
    await render(
      <>
        <PageTitle>Orvael</PageTitle>
        <SectionTitle level={3}>Sons</SectionTitle>
        <Text>Body</Text>
        <Text variant='caption'>Caption</Text>
        <Muted>Muted</Muted>
        <Label>Label</Label>
        <Stat value={1284000} size='kpi' />
      </>
    )
    expect(document.querySelector('h1')?.textContent).toBe('Orvael')
    expect(document.querySelector('h3')?.textContent).toBe('Sons')
    const display = fontSizeOf('[data-typography="page-title"]')
    const title = fontSizeOf('[data-typography="section-title"]')
    const body = fontSizeOf('[data-typography="body"]')
    const caption = fontSizeOf('[data-typography="caption"]')
    expect(display).toBeGreaterThan(title)
    expect(title).toBeGreaterThan(body)
    expect(body).toBeGreaterThan(caption)
    expect(fontSizeOf('[data-typography="label"]')).toBe(caption)
    const muted = document.querySelectorAll('[data-typography="body"]')[1]
    expect(getComputedStyle(muted).fontSize).toBe(`${body}px`)
  })

  it('keeps the role size when a color is passed', async () => {
    await render(
      <Text tone='destructive' className='text-foreground'>
        Danger
      </Text>
    )
    expect(
      document.querySelector('[data-typography="body"]')?.className
    ).toContain('text-body')
  })

  it('formats stats with tabular numbers', async () => {
    const screen = await render(
      <Stat value={0.42} format='percent' unit='done' />
    )
    await expect.element(screen.getByText('42%')).toBeInTheDocument()
    const stat = document.querySelector(
      '[data-typography="stat"]'
    ) as HTMLElement
    expect(getComputedStyle(stat).fontVariantNumeric).toContain('tabular-nums')
  })

  it('truncates long names to one line', async () => {
    await render(
      <div className='w-40'>
        <Text truncate>
          {'Vaelorithanqueduskmarrowenthalisorvaelunthrexiamorduskavethin'}
        </Text>
      </div>
    )
    const text = document.querySelector('[data-truncate="1"]') as HTMLElement
    expect(text.scrollWidth).toBeGreaterThan(text.clientWidth)
    expect(getComputedStyle(text).textOverflow).toBe('ellipsis')
  })
})
