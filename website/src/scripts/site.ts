const STAR_DENSITY = 9000
const LANGUAGE_KEY = 'wov-language'

function reducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function startStars(): void {
  const canvas = document.querySelector<HTMLCanvasElement>('[data-stars]')
  const context = canvas?.getContext('2d')
  if (!canvas || !context) return
  type Star = { x: number; y: number; radius: number; phase: number; speed: number; warm: boolean }
  let stars: Star[] = []
  let width = 0
  let height = 0
  const ratio = Math.min(window.devicePixelRatio || 1, 2)

  const seed = () => {
    width = window.innerWidth
    height = window.innerHeight
    canvas.width = width * ratio
    canvas.height = height * ratio
    context.setTransform(ratio, 0, 0, ratio, 0, 0)
    const count = Math.round((width * height) / STAR_DENSITY)
    stars = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: Math.random() * 1.15 + 0.2,
      phase: Math.random() * Math.PI * 2,
      speed: Math.random() * 0.9 + 0.3,
      warm: Math.random() < 0.18,
    }))
  }

  const draw = (time: number) => {
    context.clearRect(0, 0, width, height)
    for (const star of stars) {
      const glow = reducedMotion() ? 0.7 : 0.45 + 0.55 * Math.abs(Math.sin(star.phase + (time / 1000) * star.speed))
      context.beginPath()
      context.arc(star.x, star.y, star.radius, 0, Math.PI * 2)
      context.fillStyle = star.warm ? `rgba(255, 222, 150, ${glow})` : `rgba(220, 210, 255, ${glow * 0.85})`
      context.fill()
    }
  }

  let frame = 0
  const loop = (time: number) => {
    draw(time)
    frame = window.requestAnimationFrame(loop)
  }

  seed()
  if (reducedMotion()) draw(0)
  else frame = window.requestAnimationFrame(loop)
  window.addEventListener('resize', () => {
    seed()
    if (reducedMotion()) draw(0)
  })
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) window.cancelAnimationFrame(frame)
    else if (!reducedMotion()) frame = window.requestAnimationFrame(loop)
  })
}

function startReveal(): void {
  const items = document.querySelectorAll<HTMLElement>('.reveal')
  if (!('IntersectionObserver' in window) || reducedMotion()) {
    items.forEach((item) => item.classList.add('is-shown'))
    return
  }
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-shown')
          observer.unobserve(entry.target)
        }
      }
    },
    { rootMargin: '0px 0px -8% 0px', threshold: 0.12 },
  )
  items.forEach((item) => observer.observe(item))
}

function startMasthead(): void {
  const masthead = document.querySelector<HTMLElement>('[data-masthead]')
  const toggle = document.querySelector<HTMLButtonElement>('[data-menu-toggle]')
  const menu = document.querySelector<HTMLElement>('[data-mobile-menu]')
  const label = document.querySelector<HTMLElement>('[data-menu-label]')
  if (!masthead) return
  const onScroll = () => masthead.classList.toggle('is-scrolled', window.scrollY > 12)
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
  if (!toggle || !menu) return
  let resting = 0
  const setOpen = (open: boolean) => {
    const wasOpen = toggle.getAttribute('aria-expanded') === 'true'
    if (open && !wasOpen) resting = window.scrollY
    toggle.setAttribute('aria-expanded', String(open))
    menu.hidden = !open
    masthead.classList.toggle('is-open', open)
    document.documentElement.classList.toggle('menu-open', open)
    if (!open && wasOpen) window.scrollTo({ top: resting, behavior: 'instant' })
    if (label) label.textContent = (open ? label.dataset.close : label.dataset.open) ?? ''
  }
  toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'))
  menu.addEventListener('click', (event) => {
    if ((event.target as HTMLElement).closest('a')) setOpen(false)
  })
  document.addEventListener(
    'click',
    (event) => {
      if (toggle.getAttribute('aria-expanded') !== 'true') return
      if (masthead.contains(event.target as Node)) return
      event.preventDefault()
      event.stopPropagation()
      setOpen(false)
    },
    { capture: true },
  )
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setOpen(false)
      toggle.focus()
    }
  })
  window.matchMedia('(min-width: 1200px)').addEventListener('change', (query) => {
    if (query.matches) setOpen(false)
  })
}

function rememberLanguage(): void {
  document.querySelectorAll<HTMLAnchorElement>('[data-lang-link]').forEach((link) => {
    link.addEventListener('click', () => {
      try {
        window.localStorage.setItem(LANGUAGE_KEY, link.dataset.langLink ?? '')
      } catch {
        return
      }
    })
  })
}

function startTilt(): void {
  if (reducedMotion() || !window.matchMedia('(hover: hover)').matches) return
  document.querySelectorAll<HTMLElement>('[data-tilt]').forEach((element) => {
    element.addEventListener('pointermove', (event) => {
      const box = element.getBoundingClientRect()
      const x = (event.clientX - box.left) / box.width - 0.5
      const y = (event.clientY - box.top) / box.height - 0.5
      element.style.setProperty('--tilt-x', `${(-y * 10).toFixed(2)}deg`)
      element.style.setProperty('--tilt-y', `${(x * 12).toFixed(2)}deg`)
      element.style.setProperty('--shine-x', `${((x + 0.5) * 100).toFixed(1)}%`)
      element.style.setProperty('--shine-y', `${((y + 0.5) * 100).toFixed(1)}%`)
    })
    element.addEventListener('pointerleave', () => {
      element.style.setProperty('--tilt-x', '0deg')
      element.style.setProperty('--tilt-y', '0deg')
    })
  })
}

export function startSite(): void {
  startStars()
  startReveal()
  startMasthead()
  rememberLanguage()
  startTilt()
}

export { LANGUAGE_KEY }
