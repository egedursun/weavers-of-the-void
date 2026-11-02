export type Violation = {
  rule: string
  detail: string
}

export type CheckOptions = {
  tolerancePx: number
}

export function collectViolations(options: CheckOptions): Violation[] {
  const tolerance = options.tolerancePx
  const violations: Violation[] = []
  const viewportWidth = document.documentElement.clientWidth

  type Box = { left: number; top: number; right: number; bottom: number }

  const describe = (element: Element): string => {
    const id = element.id ? `#${element.id}` : ''
    const slot = element.getAttribute('data-slot')
    const text = (element.textContent ?? '').trim().replace(/\s+/g, ' ').slice(0, 40)
    const classes = (element.getAttribute('class') ?? '').slice(0, 60)
    return `${element.tagName.toLowerCase()}${id}${slot ? `[${slot}]` : ''} .${classes} "${text}"`
  }

  const isShown = (element: Element): boolean =>
    element.checkVisibility({ opacityProperty: true, visibilityProperty: true })

  const clipsOverflow = (style: CSSStyleDeclaration): boolean =>
    style.overflowX !== 'visible' || style.overflowY !== 'visible'

  const intersect = (a: Box, b: Box): Box | null => {
    const box = {
      left: Math.max(a.left, b.left),
      top: Math.max(a.top, b.top),
      right: Math.min(a.right, b.right),
      bottom: Math.min(a.bottom, b.bottom),
    }
    return box.right > box.left && box.bottom > box.top ? box : null
  }

  const clipped = (start: Element | null, box: Box): Box | null => {
    let current: Box | null = box
    let ancestor = start
    while (current && ancestor && ancestor !== document.documentElement) {
      const style = getComputedStyle(ancestor)
      if (clipsOverflow(style)) {
        const rect = ancestor.getBoundingClientRect()
        current = intersect(current, rect)
      }
      ancestor = ancestor.parentElement
    }
    return current
  }

  const resolvePx = (expression: string): number => {
    const probe = document.createElement('div')
    probe.style.position = 'absolute'
    probe.style.visibility = 'hidden'
    probe.style.height = expression
    document.body.appendChild(probe)
    const value = probe.getBoundingClientRect().height
    probe.remove()
    return value
  }

  const modal = Array.from(
    document.querySelectorAll('[role="dialog"][data-state="open"],[role="alertdialog"][data-state="open"],[role="menu"][data-state="open"]')
  )
  const inScope = (element: Element): boolean =>
    modal.length === 0 || modal.some((dialog) => dialog.contains(element))

  const expectedHeight: Record<string, number> = {
    sm: resolvePx('var(--control-height-sm)'),
    default: resolvePx('var(--control-height-md)'),
    lg: resolvePx('var(--control-height-lg)'),
  }
  const expectedBadge: Record<string, number> = {
    sm: resolvePx('var(--spacing-badge-sm)'),
    default: resolvePx('var(--spacing-badge-md)'),
  }
  const controlFont = resolvePx('var(--control-font-size)')

  for (const control of Array.from(document.querySelectorAll('[data-control-size]'))) {
    if (!isShown(control) || !inScope(control)) continue
    const size = control.getAttribute('data-control-size') ?? 'default'
    const rect = control.getBoundingClientRect()
    if (rect.width === 0 || rect.height === 0) continue
    const style = getComputedStyle(control)
    if (Math.abs(rect.height - expectedHeight[size]) > 0.5) {
      violations.push({
        rule: 'control-height',
        detail: `${describe(control)} size=${size} height=${rect.height} expected=${expectedHeight[size]}`,
      })
    }
    if (Math.abs(parseFloat(style.fontSize) - controlFont) > 0.1) {
      violations.push({
        rule: 'control-font-size',
        detail: `${describe(control)} size=${size} font=${style.fontSize} expected=${controlFont}px`,
      })
    }
  }

  for (const badge of Array.from(document.querySelectorAll('[data-badge-size]'))) {
    if (!isShown(badge) || !inScope(badge)) continue
    const size = badge.getAttribute('data-badge-size') ?? 'default'
    const rect = badge.getBoundingClientRect()
    if (rect.height === 0) continue
    if (Math.abs(rect.height - expectedBadge[size]) > 0.5) {
      violations.push({
        rule: 'badge-height',
        detail: `${describe(badge)} size=${size} height=${rect.height} expected=${expectedBadge[size]}`,
      })
    }
  }

  const roleSize: Record<string, number> = {
    'page-title': resolvePx('var(--display-font-size)'),
    'section-title': resolvePx('var(--text-title)'),
    body: resolvePx('var(--text-body)'),
    prose: resolvePx('var(--text-prose)'),
    caption: resolvePx('var(--text-caption)'),
    label: resolvePx('var(--text-caption)'),
    overline: resolvePx('var(--text-overline)'),
    'stat-kpi': resolvePx('var(--text-kpi)'),
  }

  for (const element of Array.from(document.querySelectorAll('[data-typography]'))) {
    if (!isShown(element) || !inScope(element)) continue
    const role = element.getAttribute('data-typography') ?? ''
    const expected = roleSize[role]
    if (expected === undefined) continue
    const actual = parseFloat(getComputedStyle(element).fontSize)
    if (Math.abs(actual - expected) > 0.1) {
      violations.push({
        rule: 'typography-size',
        detail: `${describe(element)} role=${role} font=${actual}px expected=${expected}px`,
      })
    }
  }

  type Piece = { owner: Element; kind: 'text' | 'icon'; box: Box; label: string }
  const pieces: Piece[] = []

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const content = node.textContent ?? ''
    if (!content.trim()) continue
    const owner = node.parentElement
    if (!owner || !isShown(owner) || !inScope(owner)) continue
    if (owner.closest('svg,script,style,noscript,[aria-hidden="true"][data-radix-select-viewport]')) continue
    const range = document.createRange()
    range.selectNodeContents(node)
    for (const rect of Array.from(range.getClientRects())) {
      if (rect.width <= 1 || rect.height <= 1) continue
      const box = clipped(owner, rect)
      if (!box || box.right - box.left <= 1 || box.bottom - box.top <= 1) continue
      pieces.push({ owner, kind: 'text', box, label: content.trim().slice(0, 30) })
    }
  }

  for (const icon of Array.from(document.querySelectorAll('svg'))) {
    if (icon.parentElement?.closest('svg')) continue
    if (!isShown(icon) || !inScope(icon)) continue
    const rect = icon.getBoundingClientRect()
    if (rect.width <= 1 || rect.height <= 1) continue
    const box = clipped(icon.parentElement, rect)
    if (!box) continue
    pieces.push({ owner: icon, kind: 'icon', box, label: `svg.${icon.getAttribute('class') ?? ''}`.slice(0, 40) })
  }

  for (let i = 0; i < pieces.length; i += 1) {
    for (let j = i + 1; j < pieces.length; j += 1) {
      const a = pieces[i]
      const b = pieces[j]
      if (a.owner === b.owner && a.kind === 'text' && b.kind === 'text') continue
      if (a.kind === 'icon' && b.kind === 'icon') continue
      const overlap = intersect(a.box, b.box)
      if (!overlap) continue
      if (overlap.right - overlap.left <= tolerance || overlap.bottom - overlap.top <= tolerance) continue
      violations.push({
        rule: a.kind === 'icon' || b.kind === 'icon' ? 'icon-text-overlap' : 'text-overlap',
        detail: `"${a.label}" overlaps "${b.label}"`,
      })
    }
  }

  if (document.documentElement.scrollWidth > viewportWidth + tolerance) {
    violations.push({
      rule: 'page-horizontal-overflow',
      detail: `scrollWidth=${document.documentElement.scrollWidth} viewport=${viewportWidth}`,
    })
  }

  const spillsVisibly = (element: Element, rect: DOMRect): boolean =>
    Array.from(element.querySelectorAll('*')).some((child) => {
      if (!isShown(child)) return false
      const own = child.getBoundingClientRect()
      if (own.width === 0 || own.height === 0) return false
      const box = clipped(child.parentElement, own)
      if (!box) return false
      return box.right > rect.right + tolerance || box.left < rect.left - tolerance
    })

  for (const element of Array.from(document.body.querySelectorAll('*'))) {
    if (!(element instanceof HTMLElement) || !isShown(element) || !inScope(element)) continue
    const style = getComputedStyle(element)
    if (style.position === 'fixed') continue
    const rect = element.getBoundingClientRect()
    if (rect.width === 0 || rect.height === 0) continue
    const box = clipped(element.parentElement, rect)
    if (!box) continue
    if (box.right > viewportWidth + tolerance || box.left < -tolerance) {
      violations.push({
        rule: 'element-outside-viewport',
        detail: `${describe(element)} left=${Math.round(box.left)} right=${Math.round(box.right)} viewport=${viewportWidth}`,
      })
      continue
    }
    if (
      style.display !== 'inline' &&
      style.overflowX === 'visible' &&
      element.scrollWidth > element.clientWidth + tolerance &&
      element.clientWidth > 0 &&
      spillsVisibly(element, rect)
    ) {
      violations.push({
        rule: 'content-overflows-box',
        detail: `${describe(element)} scrollWidth=${element.scrollWidth} clientWidth=${element.clientWidth}`,
      })
    }
  }

  return violations
}
