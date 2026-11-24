const INVALID_NESTING =
  /cannot be a descendant of|cannot contain a nested|cannot be a child of/

let found: string[] = []

type Sink = { error: (...args: unknown[]) => void }

export function installNestingGuard() {
  const sink = Reflect.get(globalThis, 'console') as Sink
  const original = sink.error.bind(sink)
  sink.error = (...args: unknown[]) => {
    const text = args.map((part) => String(part)).join(' ')
    if (INVALID_NESTING.test(text)) found.push(text.slice(0, 400))
    original(...args)
  }
}

export function takeNestingViolations(): string[] {
  const taken = found
  found = []
  return taken
}
