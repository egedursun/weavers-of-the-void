import { describe, it } from 'node:test'
import { RuleTester } from 'eslint'
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
  valid: ['<Button>Go</Button>', '<main />', '<section />'],
  invalid: [
    { code: '<button>Go</button>', errors: [{ messageId: 'rawElement' }] },
    { code: '<input />', errors: [{ messageId: 'rawElement' }] },
    { code: '<h2>Title</h2>', errors: [{ messageId: 'rawElement' }] },
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
