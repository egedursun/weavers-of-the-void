import { describe, it } from 'node:test'
import { RuleTester } from 'eslint'
import tseslint from 'typescript-eslint'
import { aeronaPlugin } from './aeronaPlugin.js'

RuleTester.describe = describe
RuleTester.it = it

const tester = new RuleTester({
  languageOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    parserOptions: { ecmaFeatures: { jsx: true } },
  },
})

const rules = aeronaPlugin.rules

tester.run('class-policy', rules['class-policy'], {
  valid: [
    "<div className='flex min-w-0 flex-col gap-4' />",
    "<Button size='sm' variant='outline' className='w-full'>Go</Button>",
    "<div className={cn('grid gap-2', active && 'bg-accent')} />",
    "<div className='ms-auto md:grid-cols-label-track' />",
    "<svg className='size-icon-md text-muted-foreground' />",
    "<div className='p-4 md:p-6' />",
    "<TabsList className='w-full'>x</TabsList>",
  ],
  invalid: [
    { code: "<div className='w-[13px]' />", errors: [{ messageId: 'arbitrary' }] },
    { code: "<div className='[&_svg]:size-4' />", errors: [{ messageId: 'arbitrary' }] },
    { code: "<p className='text-sm' />", errors: [{ messageId: 'textSize' }] },
    { code: "<p className='md:text-2xl' />", errors: [{ messageId: 'textSize' }] },
    { code: "<p className='text-body' />", errors: [{ messageId: 'textSize' }] },
    { code: "<p className='font-bold leading-tight' />", errors: [{ messageId: 'typeTuning' }, { messageId: 'typeTuning' }] },
    { code: "<div className='mt-4' />", errors: [{ messageId: 'margin' }] },
    { code: "<div className='-mx-2 space-y-2' />", errors: [{ messageId: 'margin' }, { messageId: 'margin' }] },
    { code: "<div className='z-50' />", errors: [{ messageId: 'zIndex' }] },
    { code: "<Button className='h-8' />", errors: [{ messageId: 'controlBox' }] },
    { code: "<SelectTrigger className='px-2 py-1' />", errors: [{ messageId: 'controlBox' }, { messageId: 'controlBox' }] },
    { code: "<Input className='rounded-full' />", errors: [{ messageId: 'controlBox' }] },
    { code: "<svg className='size-4' />", errors: [{ messageId: 'numericSize' }] },
    { code: "<div className={cn('flex', open && 'text-lg')} />", errors: [{ messageId: 'textSize' }] },
    { code: "<div className={`gap-2 ${open ? 'mt-2' : ''}`} />", errors: [{ messageId: 'margin' }] },
    { code: "const styles = cn('text-xs')", errors: [{ messageId: 'textSize' }] },
    { code: "<TabsList className='w-full flex-wrap'>x</TabsList>", errors: [{ messageId: 'tabsWrap' }] },
    { code: "<TabsList className='md:grid'>x</TabsList>", errors: [{ messageId: 'tabsWrap' }] },
  ],
})

tester.run('no-inline-style', rules['no-inline-style'], {
  valid: ["<div className='flex' />"],
  invalid: [{ code: '<div style={{ width: 10 }} />', errors: [{ messageId: 'inlineStyle' }] }],
})

tester.run('no-raw-color', rules['no-raw-color'], {
  valid: ["const tone = 'text-primary'", "const anchor = '#content'"],
  invalid: [
    { code: "const gold = '#e8ad48'", errors: [{ messageId: 'rawColor' }] },
    { code: "const ink = 'rgba(0, 0, 0, 0.5)'", errors: [{ messageId: 'rawColor' }] },
    { code: 'const sky = `oklch(0.7 0.1 250)`', errors: [{ messageId: 'rawColor' }] },
  ],
})

tester.run('no-raw-elements', rules['no-raw-elements'], {
  valid: ['<Button>Go</Button>', '<main />', '<section />', "<Picture src='a.webp' />"],
  invalid: [
    { code: '<button>Go</button>', errors: [{ messageId: 'rawElement' }] },
    { code: '<input />', errors: [{ messageId: 'rawElement' }] },
    { code: '<h2>Title</h2>', errors: [{ messageId: 'rawElement' }] },
    { code: "<img src='a.webp' alt='' />", errors: [{ messageId: 'rawElement' }] },
  ],
})

tester.run('no-raw-surface', rules['no-raw-surface'], {
  valid: [
    "<div className='rounded-md border border-gild/70 bg-card surface-framed p-4' />",
    "<div className='rounded-md p-3 sealed-well' />",
    "<div className='border-t pt-2' />",
    "<span className='rounded-full border px-2 py-0.5' />",
  ],
  invalid: [
    { code: "<div className='rounded-xl border bg-card p-4' />", errors: [{ messageId: 'rawSurface' }] },
    { code: "<div className='rounded-lg border bg-muted/30 p-3' />", errors: [{ messageId: 'rawSurface' }] },
    { code: "<div className='rounded-lg border border-dashed p-3' />", errors: [{ messageId: 'rawSurface' }] },
    {
      code: "<li className={cn('rounded-xl border p-4', idle && 'bg-background')} />",
      errors: [{ messageId: 'rawSurface' }],
    },
    { code: "<div className='rounded-md border surface-brackets p-4' />", errors: [{ messageId: 'rawSurface' }] },
    { code: "<div className='rounded-lg border p-3' />", errors: [{ messageId: 'rawSurface' }] },
    { code: "<div className='rounded-xl border border-primary/30 bg-primary/5 p-3' />", errors: [{ messageId: 'rawSurface' }] },
  ],
})

tester.run('paged-lists', rules['paged-lists'], {
  valid: [
    '<Paged items={laws}>{(law) => <li key={law.id}>{law.name}</li>}</Paged>',
    '<ul>{page.visible.map((law) => <li key={law.id}>{law.name}</li>)}</ul>',
    '<ul>{STAGES.map((stage) => <li key={stage}>{stage}</li>)}</ul>',
    "<ul>{['a', 'b'].map((key) => <li key={key}>{key}</li>)}</ul>",
    '<div>{laws.map((law) => <span key={law.id}>{law.name}</span>)}</div>',
    '<ul>{words.slice(0, shown).map((word) => <li key={word}>{word}</li>)}</ul>',
    '<ul>{greatFieldValues.map((key) => <li key={key}>{key}</li>)}</ul>',
    '<ul>{Object.keys(SCALES).map((key) => <li key={key}>{key}</li>)}</ul>',
    '<ul>{page.map((item) => <Tile key={item.id} item={item} />)}</ul>',
  ],
  invalid: [
    { code: '<ul>{laws.map((law) => <li key={law.id}>{law.name}</li>)}</ul>', errors: [{ messageId: 'unpaged' }] },
    { code: '<ul>{query.data?.rows.map((row) => <li key={row.id}>{row.name}</li>)}</ul>', errors: [{ messageId: 'unpaged' }] },
    { code: '<ul>{steps.map((step) => <StepRow key={step.id} step={step} />)}</ul>', errors: [{ messageId: 'unpaged' }] },
  ],
})

tester.run('disabled-needs-reason', rules['disabled-needs-reason'], {
  valid: [
    '<Button>Go</Button>',
    '<Button disabled={false}>Go</Button>',
    "<Button disabled disabledReason='No essence'>Go</Button>",
  ],
  invalid: [
    { code: '<Button disabled>Go</Button>', errors: [{ messageId: 'missingReason' }] },
    { code: '<Button disabled={busy}>Go</Button>', errors: [{ messageId: 'missingReason' }] },
  ],
})

tester.run('scene-tap', rules['scene-tap'], {
  valid: [
    '<mesh onClick={onTap(() => pick(1))} />',
    '<points onClick={picking ? onTap(choose) : undefined} />',
    '<Button onClick={() => go()}>Go</Button>',
    '<div onClick={() => go()} />',
  ],
  invalid: [
    { code: '<mesh onClick={() => pick(1)} />', errors: [{ messageId: 'dragClick' }] },
    { code: '<points onClick={picking ? choose : undefined} />', errors: [{ messageId: 'dragClick' }] },
    { code: '<group onDoubleClick={open} />', errors: [{ messageId: 'dragClick' }] },
  ],
})

tester.run('glsl-safe-pow', rules['glsl-safe-pow'], {
  valid: [
    'const glsl = `float a = pow(max(x, 0.0), 2.0);`',
    'const glsl = `float a = pow(clamp(1.0 - up, 0.0, 1.0), 2.6) + pow(abs(q.x), 3.0);`',
    'const glsl = `float a = exp(-d*d); float b = pow(2.0, x);`',
    'const glsl = `float a = 1.0 - smoothstep(0.97, 1.0, s) + smoothstep(-0.2, 0.6, n);`',
    'const text = `power(x, 2)`',
  ],
  invalid: [
    { code: 'const glsl = `float a = pow(1.0 - d, 2.0);`', errors: [{ messageId: 'negativeBase' }] },
    { code: 'const glsl = `float a = exp(-pow((d - 0.7)*7.0, 2.0));`', errors: [{ messageId: 'negativeBase' }] },
    { code: 'const glsl = `float a = pow(max(x, 0.0), 2.0) + pow(0.5 + 0.5*sin(t), 3.0);`', errors: [{ messageId: 'negativeBase' }] },
    { code: 'const glsl = `float a = smoothstep(1.0, 0.97, s);`', errors: [{ messageId: 'reversedEdges' }] },
    { code: 'const glsl = `float a = smoothstep(0.5, 0.5, s);`', errors: [{ messageId: 'reversedEdges' }] },
  ],
})

const typedTester = new RuleTester({
  languageOptions: { ecmaVersion: 'latest', sourceType: 'module', parser: tseslint.parser },
})

typedTester.run('typed-request-body', rules['typed-request-body'], {
  valid: [
    "postAction('impact:call', { world_id: 1 })",
    "api.POST('/api/images', { body: file as never, bodySerializer: (body) => body as never })",
    "api.POST('/api/x', { body })",
  ],
  invalid: [
    { code: "api.POST('/api/actions/x', { body: body as never })", errors: [{ messageId: 'untypedBody' }] },
    { code: "api.PATCH('/api/x', { params: {}, body: input as never })", errors: [{ messageId: 'untypedBody' }] },
  ],
})
