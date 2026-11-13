import { type components } from '@/api/generated/schema'
import { type VehicleFamily, type VehicleFrame } from './labels'

type BuildingForm = components['schemas']['BuildingForm']

export const CANVAS = { width: 560, height: 280 } as const

export type Mark = {
  d: string
  line?: number
  neutral?: boolean
  solid?: boolean
}

export type Feature = {
  keys: readonly string[]
  marks: readonly Mark[]
  at: readonly [number, number]
  label: readonly [number, number]
  back?: boolean
  shape?: boolean
}

export type Hold = { x: number; y: number; w: number; h: number }

export type Setting = 'water' | 'ground' | 'space' | 'air' | 'deep'

export type Blueprint = {
  body: string
  bodyKeys: readonly string[]
  hold: Hold
  features: readonly Feature[]
  setting: Setting
  decor?: readonly Mark[]
  fill?: 'evenodd' | 'nonzero'
}

function circle(cx: number, cy: number, r: number): string {
  return `M ${cx - r} ${cy} a ${r} ${r} 0 1 0 ${r * 2} 0 a ${r} ${r} 0 1 0 ${-r * 2} 0 Z`
}

function rect(x: number, y: number, w: number, h: number): string {
  return `M ${x} ${y} H ${x + w} V ${y + h} H ${x} Z`
}

function ring(cx: number, cy: number, rx: number, ry: number): string {
  return `M ${cx - rx} ${cy} a ${rx} ${ry} 0 1 0 ${rx * 2} 0 a ${rx} ${ry} 0 1 0 ${-rx * 2} 0 Z`
}

function wheel(cx: number, cy: number, r: number): Mark[] {
  return [
    { d: circle(cx, cy, r) },
    { d: circle(cx, cy, r * 0.3), neutral: true },
    {
      d: `M ${cx - r * 0.8} ${cy} H ${cx + r * 0.8} M ${cx} ${cy - r * 0.8} V ${cy + r * 0.8} M ${cx - r * 0.56} ${cy - r * 0.56} L ${cx + r * 0.56} ${cy + r * 0.56} M ${cx - r * 0.56} ${cy + r * 0.56} L ${cx + r * 0.56} ${cy - r * 0.56}`,
      line: 1.2,
      neutral: true,
    },
  ]
}

function wheels(radius: number, y: number, ...xs: number[]): Mark[] {
  return xs.flatMap((x) => wheel(x, y, radius))
}

function shaped(item: Feature): Feature {
  return { ...item, shape: true }
}

function feature(
  keys: readonly string[],
  at: readonly [number, number],
  label: readonly [number, number],
  marks: readonly Mark[],
  back?: boolean
): Feature {
  return { keys, at, label, marks, back }
}

function leg(x: number, hock: boolean): string {
  return hock
    ? `M ${x} 54 L ${x + 11} 54 L ${x + 12} 76 L ${x + 8} 90 L ${x + 9} 108 L ${x + 1} 108 L ${x + 1} 90 L ${x + 3} 76 Z`
    : `M ${x} 54 L ${x + 10} 54 L ${x + 9} 88 L ${x + 10} 108 L ${x + 1} 108 L ${x + 1} 88 Z`
}

const QUADRUPED = [
  'M 32 42 C 32 28 46 24 62 25 L 90 25 C 108 25 118 32 118 45 C 118 58 108 64 92 64 L 54 64 C 40 64 32 56 32 42 Z',
  'M 40 54 C 28 46 20 36 14 29 L 7 31 C 2 31 0 27 2 23 C 5 16 13 9 19 7 L 24 1 L 26 9 C 32 16 40 24 46 32 Z',
  leg(36, false),
  leg(49, false),
  leg(94, true),
  leg(106, true),
].join(' ')

const QUADRUPED_TAIL = 'M 117 40 C 126 50 126 66 120 82'

type Pose = {
  x: number
  ground: number
  sx: number
  sy: number
  right?: boolean
}

function tenth(value: number): number {
  return Math.round(value * 10) / 10
}

function spot(pose: Pose, lx: number, ly: number): readonly [number, number] {
  const x = pose.right ? pose.x + (120 - lx) * pose.sx : pose.x + lx * pose.sx
  return [tenth(x), tenth(pose.ground - (108 - ly) * pose.sy)]
}

function place(path: string, pose: Pose): string {
  let index = 0
  return path.replace(/-?\d+(?:\.\d+)?/g, (token) => {
    const value = Number(token)
    const [x, y] = spot(pose, value, value)
    return String(index++ % 2 === 0 ? x : y)
  })
}

function draft(x: number, ground: number, scale = 1.15): Pose {
  return { x, ground, sx: scale, sy: scale }
}

function team(...poses: Pose[]): Mark[] {
  return poses.flatMap((pose) => [
    { d: place(QUADRUPED_TAIL, pose), line: 3 * pose.sx },
    { d: place(QUADRUPED, pose), solid: true },
  ])
}

function traces(pose: Pose, toX: number, toY: number): Mark {
  const [cx, cy] = spot(pose, 27, 44)
  const [bx, by] = spot(pose, 30, 56)
  return {
    d: `M ${cx} ${cy} L ${toX} ${toY} M ${bx} ${by} L ${toX} ${toY + 14}`,
    line: 3,
  }
}

function drafted(pose: Pose, toX: number, toY: number): Feature[] {
  return [
    feature(
      ['draft_team'],
      spot(pose, 66, 50),
      spot(pose, 66, -14),
      team(pose)
    ),
    feature(['harness'], spot(pose, 40, 48), spot(pose, 96, -14), [
      traces(pose, toX, toY),
      { d: place('M 22 38 Q 30 30 34 24', pose), line: 4 },
    ]),
  ]
}

const RIDER: Pose = { x: 150, ground: 258, sx: 2.15, sy: 2.1, right: true }
const BEARER: Pose = { x: 146, ground: 258, sx: 2.25, sy: 2, right: true }
const HAULER: Pose = { x: 104, ground: 258, sx: 2.9, sy: 1.8, right: true }

function torso(pose: Pose): Hold {
  const [left, top] = spot(pose, 108, 30)
  const [right, bottom] = spot(pose, 42, 60)
  const x = Math.min(left, right)
  return { x, y: top, w: Math.abs(right - left), h: bottom - top }
}

function bridle(pose: Pose): Feature {
  return feature(['harness'], spot(pose, 10, 22), spot(pose, -6, 4), [
    { d: place('M 3 25 Q 10 19 18 14 M 12 31 L 26 44', pose), line: 2.4 },
  ])
}

function barding(pose: Pose): Feature {
  return feature(['barding'], spot(pose, 66, 68), spot(pose, 66, 84), [
    {
      d: place(
        'M 34 44 L 34 60 Q 46 70 58 64 Q 70 72 82 66 Q 94 72 110 60 L 114 44',
        pose
      ),
      line: 2.6,
    },
  ])
}

function beast(pose: Pose, features: readonly Feature[]): Blueprint {
  return {
    setting: 'ground',
    body: place(QUADRUPED, pose),
    fill: 'nonzero',
    bodyKeys: ['mount_body'],
    hold: torso(pose),
    features,
    decor: [{ d: place(QUADRUPED_TAIL, pose), line: 3 * pose.sx }],
  }
}

const RIDING = beast(RIDER, [
  barding(RIDER),
  feature(['saddle'], spot(RIDER, 72, 24), spot(RIDER, 72, 6), [
    {
      d: place(
        'M 58 27 C 60 19 70 19 74 21 L 86 23 C 92 24 92 28 92 30 L 92 35 L 58 35 Z',
        RIDER
      ),
    },
    { d: place('M 74 35 L 74 62', RIDER), line: 2, neutral: true },
  ]),
  bridle(RIDER),
])

const PACK = beast(BEARER, [
  barding(BEARER),
  feature(['saddle'], spot(BEARER, 72, 20), spot(BEARER, 72, 2), [
    { d: place('M 56 27 Q 58 13 72 13 Q 88 13 90 27 Z', BEARER) },
    {
      d: place(
        'M 48 34 Q 48 29 54 29 L 66 29 L 66 54 Q 66 58 61 58 L 53 58 Q 48 58 48 53 Z',
        BEARER
      ),
    },
    {
      d: place(
        'M 78 29 L 90 29 Q 96 29 96 34 L 96 53 Q 96 58 91 58 L 83 58 Q 78 58 78 54 Z',
        BEARER
      ),
    },
    { d: place('M 50 26 Q 72 4 94 26', BEARER), line: 1.6, neutral: true },
  ]),
  bridle(BEARER),
])

const CARRIER = beast(HAULER, [
  barding(HAULER),
  feature(['saddle'], spot(HAULER, 72, 14), spot(HAULER, 72, -12), [
    { d: place('M 42 30 L 102 30 L 102 24 L 42 24 Z', HAULER) },
    { d: place('M 50 24 L 52 8 L 92 8 L 94 24 Z', HAULER) },
    { d: place('M 46 8 L 72 -6 L 98 8 Z', HAULER) },
    {
      d: place('M 60 10 L 60 22 M 72 10 L 72 22 M 84 10 L 84 22', HAULER),
      line: 2,
      neutral: true,
    },
  ]),
  bridle(HAULER),
])

const TRAVOIS_TEAM = draft(24, 252)
const TRAVOIS: Blueprint = {
  setting: 'ground',
  body: 'M 296 196 Q 300 180 330 182 L 440 196 Q 468 200 466 222 L 462 244 L 300 222 Z',
  bodyKeys: ['chassis', 'frame'],
  hold: { x: 304, y: 194, w: 156, h: 34 },
  features: [
    ...drafted(TRAVOIS_TEAM, 96, 172),
    feature(
      ['wheels', 'axle'],
      [500, 246],
      [500, 266],
      [{ d: 'M 70 168 L 524 250 M 62 178 L 516 260', line: 4 }]
    ),
  ],
}

const SLEDGE_TEAM = draft(24, 244)
const SLEDGE: Blueprint = {
  setting: 'ground',
  body: rect(200, 150, 260, 60),
  bodyKeys: ['chassis', 'frame'],
  hold: { x: 206, y: 156, w: 248, h: 48 },
  features: [
    ...drafted(SLEDGE_TEAM, 200, 168),
    feature(
      ['wheels', 'axle'],
      [330, 238],
      [330, 262],
      [
        { d: 'M 182 222 Q 196 238 220 238 H 470 Q 490 238 494 212', line: 6 },
        {
          d: 'M 230 210 V 238 M 330 210 V 238 M 430 210 V 238',
          line: 3,
          neutral: true,
        },
      ]
    ),
  ],
}

const HANDCART: Blueprint = {
  setting: 'ground',
  body: 'M 220 140 L 420 140 L 404 206 L 236 206 Z',
  bodyKeys: ['chassis', 'frame'],
  hold: { x: 236, y: 146, w: 170, h: 54 },
  features: [
    feature(
      ['draft_team'],
      [92, 186],
      [70, 166],
      [{ d: 'M 86 178 L 86 196 M 80 186 L 92 186', line: 6 }]
    ),
    feature(
      ['harness'],
      [150, 170],
      [130, 150],
      [{ d: 'M 230 160 L 96 186 M 86 186 H 110', line: 5 }]
    ),
    feature(['wheels', 'axle'], [320, 220], [320, 266], wheel(320, 220, 34)),
  ],
}

const CART_TEAM = draft(24, 256)
const CART: Blueprint = {
  setting: 'ground',
  body: 'M 200 124 L 452 124 L 452 196 L 210 196 Z',
  bodyKeys: ['chassis', 'frame'],
  hold: { x: 214, y: 130, w: 232, h: 60 },
  features: [
    ...drafted(CART_TEAM, 206, 168),
    feature(['wheels', 'axle'], [330, 214], [330, 266], wheel(330, 214, 42)),
  ],
}

const MINECART_TEAM = draft(24, 240)
const MINECART: Blueprint = {
  setting: 'ground',
  body: 'M 190 128 L 460 128 L 436 206 L 214 206 Z',
  bodyKeys: ['chassis', 'frame'],
  hold: { x: 214, y: 134, w: 222, h: 64 },
  features: [
    ...drafted(MINECART_TEAM, 200, 170),
    feature(
      ['wheels', 'axle'],
      [260, 222],
      [330, 266],
      wheels(16, 222, 250, 400)
    ),
  ],
  decor: [{ d: 'M 20 240 H 540 M 20 248 H 540', line: 2 }],
}

const WAGON_TEAM = draft(24, 254)

function wagon(
  body: string,
  hold: Hold,
  extra: readonly Feature[],
  ws: readonly number[],
  radius = 30
): Blueprint {
  return {
    setting: 'ground',
    body,
    bodyKeys: ['chassis', 'frame', 'hull'],
    hold,
    features: [
      ...drafted(WAGON_TEAM, ws[0] - radius - 10, 186),
      ...extra,
      feature(
        ['axle'],
        [320, 224],
        [320, 214],
        [{ d: `M ${ws[0]} 224 H ${ws[ws.length - 1]}`, line: 5 }]
      ),
      feature(
        ['wheels'],
        [ws[0], 224],
        [ws[0], 268],
        wheels(radius, 224, ...ws)
      ),
    ],
  }
}

const WAGON = wagon(
  rect(176, 128, 300, 72),
  { x: 184, y: 134, w: 284, h: 60 },
  [],
  [220, 432]
)

const COVERED = wagon(
  rect(176, 150, 300, 52),
  { x: 184, y: 154, w: 284, h: 42 },
  [
    feature(
      ['cargo_bay'],
      [326, 110],
      [326, 60],
      [
        { d: 'M 182 150 Q 182 70 240 70 H 412 Q 470 70 470 150 Z' },
        {
          d: 'M 230 76 V 150 M 280 70 V 150 M 330 70 V 150 M 380 70 V 150 M 426 76 V 150',
          line: 1.4,
          neutral: true,
        },
      ]
    ),
  ],
  [220, 432]
)

const CARRIAGE = wagon(
  'M 196 186 L 196 108 Q 198 82 230 80 L 422 80 Q 454 82 456 108 L 456 186 Z',
  { x: 204, y: 120, w: 244, h: 60 },
  [
    feature(
      ['cargo_bay'],
      [326, 96],
      [326, 62],
      [{ d: rect(220, 92, 80, 34) }, { d: rect(352, 92, 80, 34) }]
    ),
  ],
  [230, 430],
  34
)

const WAR_WAGON = wagon(
  'M 176 200 L 176 104 L 200 88 L 452 88 L 476 104 L 476 200 Z',
  { x: 184, y: 108, w: 284, h: 86 },
  [],
  [220, 432]
)

const CHARIOT_NEAR = draft(52, 270, 1.12)
const CHARIOT_FAR = draft(20, 262, 1.04)

const CHARIOT: Blueprint = {
  setting: 'ground',
  body: 'M 240 120 L 380 120 L 380 200 L 228 200 Q 222 160 240 120 Z',
  bodyKeys: ['chassis', 'frame', 'hull'],
  hold: { x: 244, y: 128, w: 128, h: 64 },
  features: [
    feature(
      ['draft_team'],
      spot(CHARIOT_NEAR, 66, 50),
      spot(CHARIOT_NEAR, 66, -14),
      team(CHARIOT_FAR, CHARIOT_NEAR)
    ),
    feature(
      ['harness'],
      spot(CHARIOT_NEAR, 40, 48),
      spot(CHARIOT_NEAR, 100, -14),
      [traces(CHARIOT_NEAR, 232, 170)]
    ),
    feature(
      ['platform'],
      [306, 196],
      [420, 214],
      [{ d: rect(226, 192, 158, 9) }]
    ),
    feature(
      ['axle'],
      [320, 230],
      [390, 236],
      [{ d: 'M 300 230 H 340', line: 5 }]
    ),
    feature(['wheels'], [320, 230], [320, 272], wheel(320, 230, 40)),
  ],
}

function motor(
  body: string,
  hold: Hold,
  extra: readonly Feature[],
  ws: readonly number[],
  radius = 28
): Blueprint {
  return {
    setting: 'ground',
    body,
    bodyKeys: ['chassis', 'frame', 'hull'],
    hold,
    features: [
      ...extra,
      feature(
        ['wheels', 'tracks'],
        [ws[0], 214],
        [ws[0], 264],
        wheels(radius, 214, ...ws)
      ),
    ],
  }
}

const CAR = motor(
  'M 70 206 L 70 164 Q 74 146 112 142 L 186 138 Q 220 102 296 100 L 384 100 Q 424 106 446 138 L 494 144 Q 514 150 514 178 L 514 206 Z',
  { x: 74, y: 142, w: 436, h: 60 },
  [
    feature(
      ['steering'],
      [226, 134],
      [226, 108],
      [{ d: ring(226, 134, 8, 8), line: 3 }]
    ),
    feature(
      ['cockpit'],
      [300, 122],
      [300, 86],
      [
        { d: 'M 206 138 Q 232 112 296 110 L 334 110 L 334 138 Z' },
        { d: 'M 344 110 L 380 110 Q 410 114 428 138 L 344 138 Z' },
      ]
    ),
    feature(
      ['hardpoint'],
      [300, 86],
      [400, 76],
      [{ d: rect(280, 88, 40, 12) }, { d: rect(318, 92, 50, 4) }]
    ),
  ],
  [150, 436]
)

const TRUCK = motor(
  'M 60 206 L 60 150 Q 62 128 88 126 L 150 126 L 150 96 L 520 96 L 520 206 Z',
  { x: 156, y: 104, w: 356, h: 96 },
  [
    feature(
      ['steering'],
      [128, 154],
      [128, 128],
      [{ d: ring(128, 154, 8, 8), line: 3 }]
    ),
    feature(
      ['cockpit'],
      [104, 140],
      [96, 108],
      [{ d: 'M 74 160 L 74 144 Q 76 134 92 134 L 140 134 L 140 160 Z' }]
    ),
    feature(['engine'], [70, 182], [40, 230], [{ d: rect(60, 168, 44, 30) }]),
  ],
  [110, 370, 450]
)

const MOTORCYCLE: Blueprint = {
  setting: 'ground',
  body: 'M 200 176 Q 220 136 280 132 L 360 132 Q 386 134 392 158 L 360 182 L 232 186 Z',
  bodyKeys: ['chassis', 'frame', 'hull'],
  hold: { x: 236, y: 138, w: 130, h: 40 },
  features: [
    feature(
      ['cockpit'],
      [306, 128],
      [306, 104],
      [{ d: 'M 270 134 Q 300 118 342 126 L 342 134 Z' }]
    ),
    feature(
      ['steering'],
      [396, 112],
      [440, 96],
      [{ d: 'M 372 140 L 396 104 L 420 100', line: 5 }]
    ),
    feature(
      ['engine'],
      [300, 196],
      [300, 230],
      [{ d: rect(270, 180, 60, 26) }]
    ),
    feature(['wheels'], [170, 214], [170, 264], wheels(40, 214, 170, 430)),
  ],
}

const STEAM_CAR = motor(
  'M 110 200 L 110 140 L 300 140 L 300 104 L 450 104 L 450 200 Z',
  { x: 116, y: 146, w: 328, h: 50 },
  [
    feature(
      ['boiler', 'engine'],
      [180, 100],
      [180, 70],
      [{ d: rect(150, 96, 60, 44) }, { d: 'M 170 96 V 66 H 190 V 96', line: 3 }]
    ),
    feature(
      ['steering'],
      [332, 130],
      [332, 104],
      [{ d: ring(332, 130, 8, 8), line: 3 }]
    ),
    feature(
      ['cockpit'],
      [376, 120],
      [376, 86],
      [{ d: rect(316, 112, 120, 22) }]
    ),
  ],
  [170, 400],
  36
)

const ARMOURED = motor(
  'M 70 200 L 92 140 L 180 126 L 420 126 L 500 140 L 510 200 Z',
  { x: 96, y: 136, w: 404, h: 60 },
  [
    feature(
      ['turret', 'hardpoint'],
      [300, 102],
      [300, 76],
      [
        { d: 'M 252 126 L 262 100 L 338 100 L 348 126 Z' },
        { d: rect(338, 106, 80, 8) },
      ]
    ),
    feature(
      ['steering'],
      [162, 146],
      [162, 120],
      [{ d: ring(162, 146, 8, 8), line: 3 }]
    ),
    feature(
      ['cockpit'],
      [150, 140],
      [150, 112],
      [{ d: 'M 120 150 H 180', line: 5 }]
    ),
  ],
  [150, 300, 440],
  26
)

const HOVERCRAFT: Blueprint = {
  setting: 'water',
  body: 'M 70 176 Q 70 132 120 130 L 440 130 Q 490 132 494 176 Z',
  bodyKeys: ['chassis', 'frame', 'hull'],
  hold: { x: 100, y: 136, w: 360, h: 36 },
  features: [
    feature(
      ['wheels', 'tracks'],
      [280, 196],
      [280, 252],
      [{ d: 'M 60 176 H 504 Q 512 214 470 216 H 94 Q 52 214 60 176 Z' }]
    ),
    feature(
      ['engine', 'drive'],
      [450, 96],
      [500, 70],
      [
        { d: ring(440, 100, 26, 30) },
        { d: 'M 440 70 V 130 M 414 100 H 466', line: 1.4, neutral: true },
      ]
    ),
    feature(
      ['steering'],
      [222, 124],
      [222, 98],
      [{ d: ring(222, 124, 8, 8), line: 3 }]
    ),
    feature(
      ['cockpit'],
      [180, 118],
      [180, 96],
      [{ d: 'M 140 130 L 152 108 H 230 L 240 130 Z' }]
    ),
  ],
}

function tracked(
  body: string,
  hold: Hold,
  extra: readonly Feature[],
  hover = false
): Blueprint {
  return {
    setting: 'ground',
    body,
    bodyKeys: ['chassis', 'frame', 'hull'],
    hold,
    features: [
      ...extra,
      hover
        ? feature(
            ['tracks', 'wheels'],
            [290, 222],
            [290, 262],
            [
              {
                d: 'M 110 206 H 470 Q 480 222 470 230 H 110 Q 100 222 110 206 Z',
              },
              { d: ring(290, 244, 170, 6), neutral: true },
            ]
          )
        : feature(
            ['tracks', 'wheels'],
            [290, 214],
            [290, 262],
            [
              {
                d: 'M 92 192 H 488 Q 514 192 514 214 Q 514 238 488 238 H 92 Q 66 238 66 214 Q 66 192 92 192 Z',
              },
              ...[110, 170, 230, 290, 350, 410, 470].map((x) => ({
                d: circle(x, 215, 13),
                neutral: true,
              })),
            ]
          ),
    ],
  }
}

const TANK = tracked(
  'M 76 166 L 108 134 L 470 134 L 502 166 L 482 194 L 98 194 Z',
  { x: 100, y: 140, w: 382, h: 50 },
  [
    feature(
      ['cockpit'],
      [140, 140],
      [130, 116],
      [{ d: 'M 118 134 L 128 124 H 160 L 166 134 Z' }]
    ),
    feature(
      ['turret'],
      [300, 104],
      [300, 88],
      [
        { d: 'M 228 134 L 244 102 L 360 102 L 378 134 Z' },
        { d: rect(360, 110, 128, 10) },
      ]
    ),
    feature(
      ['hardpoint'],
      [262, 92],
      [190, 92],
      [{ d: rect(250, 92, 26, 10) }]
    ),
  ]
)

const CRAWLER = tracked(
  rect(90, 70, 400, 124),
  { x: 98, y: 78, w: 384, h: 108 },
  [
    feature(
      ['turret'],
      [340, 58],
      [340, 36],
      [{ d: 'M 296 70 L 306 50 H 374 L 384 70 Z' }, { d: rect(380, 56, 90, 8) }]
    ),
    feature(['cockpit'], [140, 60], [140, 36], [{ d: rect(104, 50, 90, 20) }]),
  ]
)

const AMPHIBIAN = tracked(
  'M 60 160 Q 70 128 120 126 L 470 126 L 506 150 L 488 196 L 92 196 Z',
  { x: 96, y: 132, w: 392, h: 60 },
  [
    feature(
      ['cockpit'],
      [150, 120],
      [140, 96],
      [{ d: 'M 128 126 L 138 116 H 170 L 176 126 Z' }]
    ),
    feature(
      ['turret', 'hardpoint'],
      [300, 110],
      [300, 92],
      [{ d: 'M 260 126 L 270 106 H 330 L 340 126 Z' }]
    ),
  ]
)

const HOVER_TANK = tracked(
  'M 76 170 L 108 130 L 470 130 L 502 170 L 482 200 L 98 200 Z',
  { x: 100, y: 136, w: 382, h: 58 },
  [
    feature(
      ['cockpit'],
      [140, 126],
      [130, 102],
      [{ d: 'M 118 130 L 128 120 H 160 L 166 130 Z' }]
    ),
    feature(
      ['turret'],
      [300, 100],
      [300, 84],
      [
        { d: 'M 230 130 L 250 98 L 356 98 L 376 130 Z' },
        { d: rect(356, 106, 140, 8) },
      ]
    ),
  ],
  true
)

const LOCOMOTIVE: Blueprint = {
  setting: 'ground',
  body: 'M 84 140 Q 84 124 102 124 L 372 124 L 372 92 L 486 92 L 486 196 L 84 196 Z',
  bodyKeys: ['chassis', 'frame', 'hull'],
  hold: { x: 92, y: 132, w: 388, h: 58 },
  features: [
    feature(
      ['boiler'],
      [150, 96],
      [150, 66],
      [{ d: 'M 136 124 L 140 84 L 168 84 L 172 124 Z' }]
    ),
    feature(
      ['cockpit'],
      [428, 112],
      [428, 76],
      [{ d: rect(396, 102, 70, 26) }]
    ),
    feature(
      ['wheels'],
      [200, 216],
      [200, 264],
      wheels(22, 216, 140, 220, 330, 440)
    ),
  ],
  decor: [{ d: 'M 30 240 H 540', line: 3 }],
}

const RAIL_CAR: Blueprint = {
  setting: 'ground',
  body: rect(90, 96, 400, 104),
  bodyKeys: ['chassis', 'frame', 'hull'],
  hold: { x: 168, y: 104, w: 314, h: 88 },
  features: [
    feature(
      ['cockpit'],
      [130, 110],
      [130, 80],
      [{ d: rect(100, 110, 60, 34) }]
    ),
    feature(['engine'], [290, 86], [290, 66], [{ d: rect(240, 82, 100, 14) }]),
    feature(
      ['wheels'],
      [160, 218],
      [160, 264],
      wheels(18, 218, 130, 180, 400, 450)
    ),
  ],
  decor: [{ d: 'M 30 240 H 540', line: 3 }],
}

const MINE_TRAIN: Blueprint = {
  setting: 'ground',
  body: 'M 60 196 L 60 120 L 180 120 L 180 196 Z M 200 140 L 360 140 L 344 196 L 216 196 Z M 380 140 L 540 140 L 524 196 L 396 196 Z',
  bodyKeys: ['chassis', 'frame', 'hull'],
  hold: { x: 66, y: 146, w: 470, h: 44 },
  features: [
    feature(
      ['boiler'],
      [110, 96],
      [110, 70],
      [{ d: 'M 96 120 L 100 90 H 124 L 128 120 Z' }]
    ),
    feature(
      ['wheels'],
      [100, 214],
      [100, 262],
      wheels(14, 214, 90, 150, 240, 320, 420, 500)
    ),
  ],
  decor: [{ d: 'M 30 236 H 540', line: 3 }],
}

function stilt(x: number, top: number, bottom: number, lean: number): Mark[] {
  const knee = top + (bottom - top) * 0.48
  const kneeX = x + lean
  return [
    {
      d: `M ${x - 11} ${top} L ${x + 11} ${top} L ${kneeX + 9} ${knee} L ${kneeX - 9} ${knee} Z`,
    },
    {
      d: `M ${kneeX - 9} ${knee} L ${kneeX + 9} ${knee} L ${x + 8} ${bottom - 6} L ${x - 8} ${bottom - 6} Z`,
    },
    {
      d: `M ${x - 18} ${bottom - 6} L ${x + 18} ${bottom - 6} L ${x + 22} ${bottom} L ${x - 22} ${bottom} Z`,
    },
    { d: circle(kneeX, knee, 7), neutral: true },
  ]
}

function walker(
  armKeys: readonly string[] | null,
  extra: readonly Feature[]
): Blueprint {
  return {
    setting: 'ground',
    body: 'M 206 52 L 354 52 Q 384 54 386 88 L 386 150 Q 384 176 354 178 L 206 178 Q 176 176 174 150 L 174 88 Q 176 54 206 52 Z',
    bodyKeys: ['frame', 'chassis', 'hull', 'core'],
    hold: { x: 182, y: 70, w: 196, h: 100 },
    features: [
      feature(
        ['cockpit'],
        [280, 52],
        [280, 30],
        [{ d: 'M 234 52 Q 280 26 326 52 Z' }]
      ),
      feature(
        ['hardpoint'],
        [400, 70],
        [450, 52],
        [{ d: rect(386, 62, 30, 18) }, { d: rect(414, 67, 46, 6) }]
      ),
      ...(armKeys
        ? [
            feature(
              armKeys,
              [150, 120],
              [120, 92],
              [
                {
                  d: 'M 176 88 L 150 96 L 136 132 L 146 136 L 160 104 L 176 100 Z',
                },
                { d: 'M 136 132 L 130 160 L 142 166 L 146 136 Z' },
                {
                  d: 'M 384 88 L 410 96 L 424 132 L 414 136 L 400 104 L 384 100 Z',
                },
                { d: 'M 424 132 L 430 160 L 418 166 L 414 136 Z' },
              ]
            ),
          ]
        : []),
      feature(
        ['platform'],
        [280, 46],
        [380, 36],
        [{ d: rect(192, 44, 176, 8) }]
      ),
      ...extra,
      feature(
        ['legs'],
        [226, 220],
        [170, 250],
        [...stilt(226, 176, 258, -14), ...stilt(334, 176, 258, 14)]
      ),
    ],
  }
}

const WALKER = walker(null, [])
const CONSTRUCT = walker(['arm'], [])
const FLYING_CONSTRUCT: Blueprint = {
  ...walker(
    ['arm'],
    [
      shaped(
        feature(
          ['wings'],
          [120, 60],
          [80, 40],
          [...wing(178, 96, -1, 130, 70), ...wing(382, 96, 1, 130, 70)],
          true
        )
      ),
    ]
  ),
  setting: 'air',
}
const DELVING_CONSTRUCT: Blueprint = {
  ...walker(null, [
    feature(
      ['arm', 'ram_head'],
      [120, 130],
      [90, 100],
      [
        { d: 'M 174 110 L 120 130 L 60 120 L 120 150 L 174 140 Z' },
        { d: 'M 386 110 L 440 130 L 500 120 L 440 150 L 386 140 Z' },
      ]
    ),
  ]),
  setting: 'deep',
}
const CARRIER_CONSTRUCT: Blueprint = {
  setting: 'ground',
  body: rect(120, 90, 320, 100),
  bodyKeys: ['frame', 'chassis', 'core'],
  hold: { x: 128, y: 98, w: 304, h: 84 },
  features: [
    feature(['platform'], [280, 86], [280, 66], [{ d: rect(140, 82, 280, 8) }]),
    feature(
      ['cockpit'],
      [150, 80],
      [150, 60],
      [{ d: 'M 120 90 Q 150 64 184 90 Z' }]
    ),
    feature(
      ['arm'],
      [470, 120],
      [500, 96],
      [{ d: 'M 440 110 L 480 130 L 470 170', line: 10 }]
    ),
    feature(
      ['legs'],
      [150, 222],
      [100, 236],
      [
        ...stilt(150, 190, 258, -10),
        ...stilt(220, 190, 258, -10),
        ...stilt(340, 190, 258, 10),
        ...stilt(410, 190, 258, 10),
      ]
    ),
  ],
}

const RAM: Blueprint = {
  setting: 'ground',
  body: 'M 150 122 L 316 72 L 482 122 L 482 196 L 150 196 Z',
  bodyKeys: ['frame', 'chassis', 'hull'],
  hold: { x: 160, y: 124, w: 314, h: 66 },
  features: [
    feature(
      ['ram_head'],
      [56, 152],
      [70, 128],
      [
        { d: rect(48, 146, 108, 14) },
        { d: 'M 20 136 L 52 136 L 58 170 L 20 170 Q 10 153 20 136 Z' },
      ]
    ),
    feature(
      ['armour_plating'],
      [316, 96],
      [316, 80],
      [{ d: 'M 150 122 L 316 72 L 482 122', line: 7 }]
    ),
    feature(['wheels'], [210, 218], [210, 264], wheels(24, 218, 210, 420)),
  ],
}

const MANTLET: Blueprint = {
  setting: 'ground',
  body: 'M 230 60 L 300 50 L 300 210 L 230 210 Z',
  bodyKeys: ['frame', 'chassis', 'armour_plating'],
  hold: { x: 236, y: 70, w: 58, h: 132 },
  features: [
    feature(
      ['ram_head', 'platform'],
      [360, 180],
      [400, 160],
      [{ d: 'M 300 170 L 420 190 L 420 200 L 300 186 Z' }]
    ),
    feature(['wheels'], [266, 222], [266, 266], wheels(18, 222, 250, 400)),
  ],
}

const SIEGE_TOWER: Blueprint = {
  setting: 'ground',
  body: rect(214, 46, 140, 156),
  bodyKeys: ['frame', 'tower', 'chassis'],
  hold: { x: 220, y: 52, w: 128, h: 144 },
  features: [
    feature(
      ['platform'],
      [284, 30],
      [284, 16],
      [
        {
          d: 'M 206 46 V 30 H 220 V 38 H 236 V 30 H 252 V 38 H 268 V 30 H 284 V 38 H 300 V 30 H 316 V 38 H 332 V 30 H 348 V 38 H 362 V 46 Z',
        },
      ]
    ),
    feature(['wheels'], [240, 220], [240, 266], wheels(20, 220, 238, 330)),
  ],
}

const TREBUCHET: Blueprint = {
  setting: 'ground',
  body: 'M 160 200 L 230 92 L 300 92 L 370 200 Z',
  bodyKeys: ['frame', 'chassis'],
  hold: { x: 200, y: 140, w: 140, h: 56 },
  features: [
    feature(
      ['arm'],
      [176, 50],
      [140, 36],
      [
        { d: 'M 380 140 L 150 40', line: 9 },
        { d: 'M 150 40 Q 120 60 130 96', line: 1.4, neutral: true },
      ]
    ),
    feature(
      ['counterweight'],
      [392, 160],
      [440, 186],
      [{ d: rect(366, 140, 50, 44) }]
    ),
    feature(['wheels'], [190, 218], [190, 264], wheels(20, 218, 190, 340)),
  ],
}

const CATAPULT: Blueprint = {
  setting: 'ground',
  body: rect(150, 160, 280, 40),
  bodyKeys: ['frame', 'chassis'],
  hold: { x: 156, y: 164, w: 268, h: 32 },
  features: [
    feature(
      ['arm'],
      [220, 70],
      [180, 50],
      [
        { d: 'M 330 166 L 210 70', line: 10 },
        { d: 'M 190 56 Q 210 50 226 66 Q 210 84 190 76 Z' },
      ]
    ),
    feature(
      ['counterweight'],
      [340, 150],
      [400, 130],
      [{ d: rect(310, 136, 60, 24) }]
    ),
    feature(['wheels'], [190, 218], [190, 264], wheels(20, 218, 190, 390)),
  ],
}

const BALLISTA: Blueprint = {
  setting: 'ground',
  body: 'M 200 150 L 420 150 L 400 200 L 220 200 Z',
  bodyKeys: ['frame', 'chassis'],
  hold: { x: 224, y: 156, w: 172, h: 38 },
  features: [
    feature(
      ['arm'],
      [180, 120],
      [160, 76],
      [
        { d: 'M 160 150 L 470 120', line: 6 },
        { d: 'M 230 70 Q 270 130 230 190', line: 5 },
        { d: 'M 230 70 L 420 128 L 230 190', line: 1.2, neutral: true },
      ]
    ),
    feature(
      ['counterweight'],
      [440, 130],
      [480, 160],
      [{ d: rect(420, 120, 40, 20) }]
    ),
    feature(['wheels'], [240, 218], [240, 264], wheels(18, 218, 240, 380)),
  ],
}

function gun(
  barrel: string,
  label: readonly [number, number],
  extra: readonly Feature[] = []
): Blueprint {
  return {
    setting: 'ground',
    body: 'M 150 176 L 380 150 L 402 196 L 166 204 Z',
    bodyKeys: ['chassis', 'frame'],
    hold: { x: 170, y: 160, w: 220, h: 38 },
    features: [
      feature(['hardpoint'], label, label, [
        { d: barrel },
        { d: circle(300, 150, 16), neutral: true },
      ]),
      ...extra,
      feature(['wheels'], [300, 210], [300, 262], wheel(300, 210, 38)),
    ],
  }
}

const FIELD_GUN = gun('M 300 138 L 518 102 L 524 124 L 306 160 Z', [470, 92])
const BOMBARD = gun('M 260 120 L 470 96 L 482 156 L 272 172 Z', [420, 86])
const MORTAR = gun('M 270 156 L 340 50 L 380 66 L 318 166 Z', [390, 52])
const ROCKET_BATTERY = gun(
  'M 240 150 L 470 70 L 486 104 L 256 180 Z',
  [440, 66],
  [
    feature(
      ['magazine'],
      [360, 120],
      [400, 150],
      [
        {
          d: 'M 260 152 L 470 80 M 262 162 L 474 90 M 264 172 L 478 100',
          line: 2,
          neutral: true,
        },
      ]
    ),
  ]
)

function ship(
  extra: readonly Feature[],
  masts: readonly number[] = [],
  hull: 'sail' | 'steam' = 'sail'
): Blueprint {
  const mastFeatures: Feature[] = masts.length
    ? [
        feature(
          ['mast'],
          [masts[0], 150],
          [masts[0], 16],
          [
            {
              d: masts
                .map((x, index) => `M ${x} 152 V ${30 + index * 10}`)
                .join(' '),
              line: 5,
            },
          ],
          true
        ),
        feature(
          ['sails'],
          [masts[0] + 40, 90],
          [masts[masts.length - 1] + 70, 60],
          masts.flatMap((x, index) => [
            {
              d: `M ${x - 44} ${44 + index * 10} L ${x + 44} ${44 + index * 10} L ${x + 50} ${92 + index * 6} L ${x - 50} ${92 + index * 6} Z`,
            },
            {
              d: `M ${x - 48} ${98 + index * 6} L ${x + 48} ${98 + index * 6} L ${x + 54} 142 L ${x - 54} 142 Z`,
            },
          ]),
          true
        ),
        feature(
          ['rigging'],
          [130, 90],
          [96, 82],
          [
            {
              d: `M 36 140 L ${masts[0]} 28 ${masts.map((x, index) => `L ${x} ${28 + index * 10}`).join(' ')} L 516 110`,
              line: 1.3,
            },
          ],
          true
        ),
      ]
    : []
  const keel = feature(
    ['keel'],
    [300, 246],
    [300, 264],
    [{ d: 'M 128 240 Q 300 254 476 236', line: 7 }]
  )
  const rudder = feature(
    ['rudder', 'steering'],
    [520, 196],
    [540, 232],
    [{ d: 'M 510 168 L 534 172 L 530 224 L 506 214 Z' }]
  )
  if (hull === 'steam')
    return {
      setting: 'water',
      body: 'M 24 146 H 526 L 520 206 Q 516 232 488 236 H 100 Q 76 234 66 212 Z',
      bodyKeys: ['hull'],
      hold: { x: 80, y: 156, w: 434, h: 56 },
      features: [
        feature(
          ['deck'],
          [300, 146],
          [120, 128],
          [{ d: rect(36, 142, 482, 7) }]
        ),
        ...extra,
        feature(
          ['rudder', 'steering'],
          [512, 240],
          [540, 254],
          [{ d: 'M 496 228 L 520 230 L 518 256 L 498 252 Z' }]
        ),
        feature(
          ['keel'],
          [300, 240],
          [300, 262],
          [{ d: 'M 104 238 H 486', line: 7 }]
        ),
      ],
    }
  return {
    setting: 'water',
    body: 'M 32 140 Q 72 150 112 152 L 498 152 L 520 138 L 508 200 Q 478 238 300 242 Q 140 244 96 218 Q 56 192 32 140 Z',
    bodyKeys: ['hull'],
    hold: { x: 112, y: 178, w: 392, h: 50 },
    features: [
      feature(
        ['oars'],
        [200, 236],
        [150, 270],
        [70, 120, 170, 220, 270, 320, 370, 420].map((x) => ({
          d: `M ${x + 40} 200 L ${x + 18} 266`,
          line: 3,
        })),
        true
      ),
      ...mastFeatures,
      feature(
        ['bow'],
        [86, 130],
        [62, 112],
        [
          {
            d: 'M 34 141 Q 62 120 116 116 L 150 116 L 150 152 L 112 152 Q 72 150 34 141 Z',
          },
        ]
      ),
      feature(
        ['stern'],
        [474, 108],
        [480, 92],
        [{ d: 'M 430 152 L 430 112 L 514 106 L 520 138 L 498 152 Z' }]
      ),
      feature(
        ['deck'],
        [300, 150],
        [300, 136],
        [{ d: rect(150, 146, 280, 7) }]
      ),
      feature(
        ['gun_deck'],
        [300, 164],
        [220, 136],
        [
          { d: 'M 96 158 H 506 V 172 H 104 Z' },
          {
            d: [140, 180, 220, 260, 300, 340, 380, 420, 460]
              .map((x) => rect(x, 161, 10, 8))
              .join(' '),
            neutral: true,
          },
        ]
      ),
      ...extra,
      rudder,
      keel,
    ],
  }
}

const RAFT: Blueprint = {
  setting: 'water',
  body: 'M 110 186 H 450 L 458 222 H 102 Z',
  bodyKeys: ['hull', 'frame'],
  hold: { x: 116, y: 190, w: 334, h: 28 },
  features: [
    feature(
      ['mast'],
      [280, 186],
      [280, 70],
      [{ d: 'M 280 186 V 80', line: 4 }],
      true
    ),
    feature(
      ['sails'],
      [300, 130],
      [360, 100],
      [{ d: 'M 284 86 L 360 120 L 284 176 Z' }],
      true
    ),
    feature(
      ['oars'],
      [96, 230],
      [60, 252],
      [{ d: 'M 120 196 L 70 256', line: 3 }]
    ),
    feature(
      ['rudder', 'steering'],
      [470, 226],
      [500, 252],
      [{ d: 'M 450 200 L 490 252', line: 4 }]
    ),
  ],
}

const CANOE: Blueprint = {
  setting: 'water',
  body: 'M 60 180 Q 120 206 280 208 Q 440 206 500 180 Q 470 230 280 232 Q 90 230 60 180 Z',
  bodyKeys: ['hull', 'frame'],
  hold: { x: 120, y: 202, w: 320, h: 26 },
  features: [
    feature(
      ['oars'],
      [220, 200],
      [220, 160],
      [{ d: 'M 220 150 L 260 250 M 340 150 L 300 250', line: 3 }]
    ),
    feature(
      ['rudder', 'steering'],
      [492, 196],
      [520, 170],
      [{ d: 'M 486 190 L 510 214', line: 4 }]
    ),
    feature(['hold'], [280, 204], [280, 186], [{ d: rect(250, 198, 60, 10) }]),
  ],
}

const ROWBOAT: Blueprint = {
  setting: 'water',
  body: 'M 90 176 L 470 176 Q 450 234 280 238 Q 110 234 90 176 Z',
  bodyKeys: ['hull', 'frame'],
  hold: { x: 120, y: 182, w: 320, h: 46 },
  features: [
    feature(
      ['oars'],
      [200, 220],
      [160, 270],
      [{ d: 'M 200 180 L 150 262 M 360 180 L 410 262', line: 3 }],
      true
    ),
    feature(
      ['mast'],
      [280, 176],
      [280, 50],
      [{ d: 'M 280 176 V 60', line: 4 }],
      true
    ),
    feature(
      ['sails'],
      [300, 116],
      [370, 90],
      [{ d: 'M 284 64 L 380 150 L 284 160 Z' }],
      true
    ),
    feature(
      ['rudder', 'steering'],
      [478, 200],
      [510, 186],
      [{ d: 'M 466 186 L 490 190 L 486 226 L 462 220 Z' }]
    ),
    feature(
      ['keel'],
      [280, 240],
      [280, 262],
      [{ d: 'M 150 232 Q 280 246 410 232', line: 5 }]
    ),
  ],
}

const BARGE: Blueprint = {
  setting: 'water',
  body: 'M 50 170 L 510 170 L 500 216 L 60 216 Z',
  bodyKeys: ['hull', 'frame'],
  hold: { x: 64, y: 176, w: 432, h: 34 },
  features: [
    feature(
      ['cargo_bay', 'hold'],
      [280, 150],
      [280, 126],
      [{ d: rect(120, 140, 320, 30) }]
    ),
    feature(
      ['bridge', 'steering'],
      [470, 140],
      [480, 116],
      [{ d: rect(450, 130, 44, 40) }]
    ),
    feature(
      ['oars', 'drive'],
      [40, 200],
      [30, 248],
      [{ d: 'M 46 160 L 22 252', line: 4 }]
    ),
    feature(
      ['rudder'],
      [516, 210],
      [540, 196],
      [{ d: 'M 504 200 L 528 204 L 524 238 L 500 232 Z' }]
    ),
  ],
}

const CATAMARAN: Blueprint = {
  setting: 'water',
  body: 'M 70 196 Q 70 176 100 176 L 460 176 Q 490 176 490 196 Q 490 216 460 216 L 100 216 Q 70 216 70 196 Z',
  bodyKeys: ['hull', 'frame'],
  hold: { x: 104, y: 180, w: 352, h: 32 },
  decor: [
    { d: 'M 280 164 V 40', line: 4 },
    { d: 'M 286 46 L 420 156 L 286 156 Z', line: 1.4 },
    { d: 'M 274 60 L 186 156 L 274 156 Z', line: 1.4 },
    { d: rect(110, 158, 340, 10), line: 1.4 },
    { d: 'M 90 222 Q 280 236 470 222', line: 5 },
  ],
  features: [
    feature(
      ['oars'],
      [180, 236],
      [140, 262],
      [{ d: 'M 200 200 L 160 256 M 360 200 L 400 256', line: 3 }],
      true
    ),
    feature(
      ['rudder', 'steering'],
      [494, 214],
      [522, 238],
      [{ d: 'M 488 204 L 508 232', line: 4 }]
    ),
  ],
}

const LANDING_CRAFT: Blueprint = {
  setting: 'water',
  body: 'M 120 150 L 500 150 L 500 216 L 140 216 Z',
  bodyKeys: ['hull', 'frame'],
  hold: { x: 146, y: 158, w: 346, h: 52 },
  features: [
    shaped(
      feature(
        ['bow', 'ram_head'],
        [90, 190],
        [70, 150],
        [{ d: 'M 120 150 L 60 206 L 140 216 Z' }]
      )
    ),
    feature(
      ['bridge', 'steering'],
      [460, 120],
      [470, 96],
      [{ d: rect(430, 110, 60, 40) }]
    ),
    feature(
      ['oars', 'engine', 'drive'],
      [516, 228],
      [540, 252],
      [{ d: 'M 500 222 L 528 246', line: 4 }, { d: ring(530, 248, 8, 12) }]
    ),
    feature(
      ['rudder'],
      [510, 206],
      [540, 196],
      [{ d: 'M 500 198 L 524 202 L 520 236 L 500 230 Z' }]
    ),
  ],
}

const AMPHIBIOUS_RAFT: Blueprint = {
  ...RAFT,
  features: [
    ...RAFT.features,
    feature(
      ['wheels', 'axle'],
      [200, 230],
      [200, 262],
      wheels(16, 228, 170, 390)
    ),
  ],
}

const SAILBOAT: Blueprint = {
  setting: 'water',
  body: 'M 80 176 L 470 176 Q 452 236 280 240 Q 112 236 80 176 Z',
  bodyKeys: ['hull', 'frame'],
  hold: { x: 120, y: 182, w: 320, h: 46 },
  decor: [
    { d: 'M 260 176 V 40', line: 4 },
    { d: 'M 266 46 L 400 168 L 266 168 Z', line: 1.4 },
    { d: 'M 254 60 L 150 168 L 254 168 Z', line: 1.4 },
  ],
  features: [
    feature(
      ['oars'],
      [200, 230],
      [160, 270],
      [{ d: 'M 200 186 L 150 262 M 360 186 L 410 262', line: 3 }],
      true
    ),
    feature(
      ['mast'],
      [260, 176],
      [300, 34],
      [{ d: 'M 260 176 V 40', line: 5 }],
      true
    ),
    feature(
      ['sails'],
      [330, 120],
      [420, 90],
      [
        { d: 'M 266 46 L 400 168 L 266 168 Z' },
        { d: 'M 254 60 L 150 168 L 254 168 Z' },
      ],
      true
    ),
    feature(
      ['rudder', 'steering'],
      [478, 200],
      [510, 186],
      [{ d: 'M 466 186 L 490 190 L 486 226 L 462 220 Z' }]
    ),
    feature(
      ['keel'],
      [280, 240],
      [280, 262],
      [{ d: 'M 150 234 Q 280 250 410 234', line: 5 }]
    ),
  ],
}

const LONGSHIP = ship(
  [
    feature(
      ['bow'],
      [60, 100],
      [60, 80],
      [{ d: 'M 34 141 Q 30 100 52 76 Q 70 70 70 92 Q 60 110 80 150 Z' }]
    ),
  ],
  [280]
)

const TRIREME = ship(
  [
    feature(
      ['ram_head'],
      [20, 190],
      [30, 220],
      [{ d: 'M 60 182 L 10 190 L 60 198 Z' }]
    ),
  ],
  [280]
)

const STEAMSHIP = ship(
  [
    feature(
      ['bridge'],
      [380, 120],
      [380, 102],
      [
        { d: 'M 350 152 L 354 118 L 420 118 L 426 152 Z' },
        { d: rect(362, 124, 50, 8), neutral: true },
      ]
    ),
    feature(
      ['boiler', 'engine'],
      [270, 100],
      [270, 70],
      [
        { d: 'M 252 152 L 256 92 L 286 92 L 290 152 Z' },
        { d: 'M 296 152 L 300 100 L 326 100 L 330 152 Z' },
      ]
    ),
    feature(
      ['turret'],
      [180, 136],
      [180, 120],
      [
        { d: 'M 160 152 L 166 134 L 204 134 L 210 152 Z' },
        { d: rect(110, 138, 52, 5) },
      ]
    ),
  ],
  [],
  'steam'
)

const BATTLESHIP = ship(
  [
    feature(
      ['bridge'],
      [330, 92],
      [330, 70],
      [
        {
          d: 'M 296 152 L 300 110 L 314 110 L 318 84 L 352 84 L 356 110 L 370 110 L 374 152 Z',
        },
      ]
    ),
    feature(
      ['boiler', 'engine'],
      [400, 110],
      [430, 86],
      [{ d: 'M 386 152 L 392 104 L 416 104 L 422 152 Z' }]
    ),
    feature(
      ['turret'],
      [200, 136],
      [200, 120],
      [
        { d: 'M 170 152 L 178 132 L 228 132 L 236 152 Z' },
        { d: rect(110, 136, 64, 6) },
        { d: 'M 440 152 L 448 132 L 490 132 L 498 152 Z' },
      ]
    ),
  ],
  [],
  'steam'
)

const CARRIER_SHIP = ship(
  [
    feature(
      ['deck', 'platform'],
      [280, 140],
      [200, 126],
      [{ d: 'M 20 132 H 540 V 146 H 30 Z' }]
    ),
    feature(['bridge'], [440, 112], [450, 90], [{ d: rect(420, 100, 40, 32) }]),
  ],
  [],
  'steam'
)

const SUBMARINE: Blueprint = {
  setting: 'deep',
  body: 'M 60 176 Q 62 140 122 138 L 466 138 Q 522 142 526 176 Q 522 210 466 214 L 122 214 Q 62 212 60 176 Z',
  bodyKeys: ['hull'],
  hold: { x: 92, y: 146, w: 410, h: 60 },
  features: [
    feature(
      ['bridge'],
      [296, 104],
      [296, 88],
      [{ d: 'M 252 140 L 264 100 L 330 100 L 342 140 Z' }]
    ),
    feature(
      ['sensors'],
      [300, 80],
      [340, 62],
      [{ d: 'M 296 100 V 62 H 310', line: 3 }]
    ),
    feature(
      ['hardpoint'],
      [78, 176],
      [60, 236],
      [{ d: circle(78, 166, 6) }, { d: circle(78, 186, 6) }]
    ),
    feature(
      ['rudder', 'steering', 'tail'],
      [530, 176],
      [530, 236],
      [{ d: 'M 520 176 L 548 146 L 552 206 Z' }]
    ),
    feature(
      ['drive'],
      [554, 176],
      [548, 120],
      [{ d: 'M 548 160 Q 562 176 548 192 Q 536 176 548 160 Z' }]
    ),
  ],
}

const BATHYSCAPHE: Blueprint = {
  setting: 'deep',
  body: 'M 120 120 Q 120 80 180 80 L 400 80 Q 460 80 460 120 L 460 150 Q 460 170 440 170 L 140 170 Q 120 170 120 150 Z',
  bodyKeys: ['hull'],
  hold: { x: 140, y: 90, w: 300, h: 70 },
  features: [
    feature(
      ['life_support', 'bridge', 'cockpit'],
      [290, 210],
      [290, 256],
      [{ d: circle(290, 206, 32) }, { d: circle(290, 206, 12), neutral: true }]
    ),
    feature(
      ['sensors'],
      [470, 200],
      [500, 230],
      [{ d: 'M 330 220 L 470 240', line: 3 }]
    ),
    feature(
      ['ballast'],
      [160, 176],
      [120, 210],
      [{ d: rect(150, 170, 40, 16) }, { d: rect(390, 170, 40, 16) }]
    ),
  ],
}

const DIVING_BELL: Blueprint = {
  setting: 'deep',
  body: 'M 200 230 Q 196 120 240 90 Q 280 70 320 90 Q 364 120 360 230 Z',
  bodyKeys: ['hull', 'frame'],
  hold: { x: 214, y: 120, w: 132, h: 100 },
  features: [
    feature(
      ['airlock', 'life_support'],
      [280, 236],
      [280, 262],
      [{ d: rect(206, 228, 148, 10) }]
    ),
    feature(
      ['sensors', 'harness'],
      [280, 40],
      [330, 30],
      [{ d: 'M 280 0 V 76', line: 3 }]
    ),
  ],
}

const LIVING_SHIP: Blueprint = {
  setting: 'water',
  body: 'M 30 170 Q 60 110 180 104 Q 330 98 450 120 Q 520 136 540 110 Q 534 150 540 196 Q 510 170 450 190 Q 320 236 180 230 Q 60 226 30 170 Z',
  bodyKeys: ['hull', 'core'],
  hold: { x: 110, y: 132, w: 340, h: 76 },
  features: [
    feature(
      ['drive'],
      [530, 150],
      [540, 90],
      [{ d: 'M 520 120 Q 556 150 520 196 Q 530 156 520 120 Z' }]
    ),
    feature(['sensors'], [60, 150], [40, 120], [{ d: circle(66, 154, 7) }]),
    feature(
      ['bow'],
      [60, 180],
      [30, 220],
      [{ d: 'M 30 170 Q 50 200 90 214 Q 60 196 30 170 Z' }]
    ),
  ],
}

function envelope(
  body: string,
  hold: Hold,
  extra: readonly Feature[]
): Blueprint {
  return {
    setting: 'air',
    body,
    bodyKeys: ['envelope'],
    hold,
    features: [
      feature(
        ['frame'],
        [280, 110],
        [280, 24],
        [
          {
            d: 'M 70 110 H 494 M 120 62 Q 280 100 440 62 M 120 158 Q 280 120 440 158',
            line: 1.2,
          },
        ],
        true
      ),
      ...extra,
    ],
  }
}

const BALLOON = envelope(
  'M 280 18 Q 386 18 388 106 Q 388 156 312 190 L 248 190 Q 172 156 172 106 Q 174 18 280 18 Z',
  { x: 196, y: 46, w: 168, h: 116 },
  [
    feature(
      ['gondola'],
      [280, 232],
      [280, 268],
      [
        { d: rect(244, 216, 72, 34) },
        {
          d: 'M 252 190 L 248 216 M 308 190 L 312 216',
          line: 1.4,
          neutral: true,
        },
      ]
    ),
    feature(
      ['ballast'],
      [232, 240],
      [180, 252],
      [
        {
          d: 'M 226 222 Q 220 222 220 230 L 220 240 Q 220 246 228 246 L 236 246 Q 244 246 244 240 L 244 230 Q 244 222 238 222 Z',
        },
        {
          d: 'M 316 222 Q 322 222 322 230 L 322 240 Q 322 246 330 246 L 338 246 Q 346 246 346 240 L 346 230 Q 346 222 340 222 Z',
        },
      ]
    ),
    feature(
      ['engine', 'drive'],
      [280, 202],
      [350, 204],
      [{ d: 'M 266 194 L 280 210 L 294 194 Z' }]
    ),
  ]
)

const AIRSHIP = envelope(
  'M 54 110 Q 58 40 280 38 Q 498 40 510 110 Q 498 180 280 182 Q 58 180 54 110 Z',
  { x: 110, y: 64, w: 340, h: 92 },
  [
    feature(
      ['gondola'],
      [280, 222],
      [280, 262],
      [
        { d: 'M 200 206 H 360 Q 366 236 340 242 H 220 Q 194 236 200 206 Z' },
        {
          d: 'M 220 180 L 214 206 M 280 182 V 206 M 340 180 L 346 206',
          line: 1.4,
          neutral: true,
        },
      ]
    ),
    feature(
      ['rudder', 'steering', 'tail'],
      [520, 110],
      [530, 62],
      [{ d: 'M 498 110 L 540 60 L 548 110 L 540 160 Z' }]
    ),
    feature(
      ['engine', 'drive'],
      [172, 220],
      [130, 238],
      [{ d: rect(150, 210, 34, 16) }, { d: 'M 150 206 V 230', line: 2 }]
    ),
    feature(
      ['hardpoint'],
      [380, 214],
      [420, 238],
      [{ d: rect(368, 206, 30, 12) }]
    ),
  ]
)

const SKYSHIP: Blueprint = {
  setting: 'air',
  body: 'M 70 170 L 490 170 Q 470 228 280 232 Q 100 228 70 170 Z',
  bodyKeys: ['hull', 'gondola'],
  hold: { x: 110, y: 176, w: 340, h: 48 },
  features: [
    feature(
      ['envelope'],
      [280, 70],
      [280, 24],
      [
        {
          d: 'M 90 80 Q 94 30 280 28 Q 470 30 474 80 Q 470 130 280 132 Q 94 130 90 80 Z',
        },
      ],
      true
    ),
    feature(
      ['frame'],
      [214, 150],
      [180, 150],
      [
        {
          d: 'M 150 128 L 140 170 M 280 132 L 280 170 M 410 128 L 420 170',
          line: 2,
        },
      ]
    ),
    feature(
      ['sails'],
      [40, 150],
      [500, 140],
      [
        { d: 'M 70 150 L 30 120 L 30 180 Z' },
        { d: 'M 490 150 L 530 120 L 530 180 Z' },
      ]
    ),
    feature(
      ['rudder', 'steering', 'tail'],
      [500, 196],
      [520, 240],
      [{ d: 'M 488 176 L 512 180 L 508 222 L 484 214 Z' }]
    ),
    feature(
      ['engine', 'drive'],
      [84, 196],
      [56, 238],
      [{ d: ring(84, 196, 12, 16) }]
    ),
    feature(
      ['hardpoint'],
      [300, 238],
      [360, 258],
      [{ d: rect(270, 230, 40, 10) }, { d: rect(306, 233, 30, 4) }]
    ),
  ],
}

const FLYING_CARRIAGE: Blueprint = {
  setting: 'air',
  body: 'M 196 200 L 196 122 Q 198 96 230 94 L 422 94 Q 454 96 456 122 L 456 200 Z',
  bodyKeys: ['hull', 'gondola', 'chassis'],
  hold: { x: 204, y: 140, w: 244, h: 54 },
  features: [
    shaped(
      feature(
        ['wings'],
        [120, 70],
        [96, 22],
        [...wing(200, 116, -1, 128, 80), ...wing(452, 116, 1, 96, 80)],
        true
      )
    ),
    feature(['envelope'], [326, 40], [326, 12], [{ d: ring(326, 42, 96, 22) }]),
    feature(
      ['frame'],
      [430, 104],
      [470, 76],
      [{ d: 'M 270 62 L 262 94 M 326 64 L 326 94 M 382 62 L 390 94', line: 2 }]
    ),
    feature(
      ['steering'],
      [240, 128],
      [240, 102],
      [{ d: ring(240, 128, 8, 8), line: 3 }]
    ),
    feature(
      ['cockpit'],
      [326, 110],
      [326, 80],
      [{ d: rect(228, 102, 80, 28) }, { d: rect(344, 102, 80, 28) }]
    ),
    feature(
      ['rudder', 'tail'],
      [470, 170],
      [500, 200],
      [{ d: 'M 456 150 L 486 140 L 492 196 L 456 196 Z' }]
    ),
    feature(
      ['engine', 'drive'],
      [180, 170],
      [150, 200],
      [{ d: ring(180, 168, 14, 20) }]
    ),
    feature(
      ['hardpoint'],
      [326, 210],
      [400, 226],
      [{ d: rect(300, 200, 52, 10) }]
    ),
  ],
}

const HARVESTER = envelope(
  'M 60 120 Q 64 30 280 26 Q 496 30 500 120 Q 496 210 280 214 Q 64 210 60 120 Z',
  { x: 110, y: 60, w: 340, h: 120 },
  [
    feature(
      ['gondola'],
      [280, 236],
      [280, 266],
      [{ d: 'M 200 214 L 220 252 H 340 L 360 214 Z' }]
    ),
    feature(
      ['rudder', 'steering', 'tail'],
      [520, 120],
      [540, 70],
      [{ d: 'M 496 120 L 540 76 L 548 120 L 540 164 Z' }]
    ),
    feature(
      ['engine', 'drive'],
      [40, 120],
      [36, 80],
      [{ d: 'M 60 104 L 20 96 L 20 144 L 60 136 Z' }]
    ),
    feature(
      ['hardpoint', 'sensors'],
      [280, 18],
      [360, 14],
      [{ d: rect(256, 12, 48, 14) }]
    ),
  ]
)

function wing(
  rootX: number,
  rootY: number,
  side: 1 | -1,
  span: number,
  lift: number
): Mark[] {
  const at = (along: number, up: number) =>
    `${rootX + side * span * along} ${rootY - lift * up}`
  const scallop = (from: [number, number], to: [number, number]) =>
    `Q ${rootX + side * span * ((from[0] + to[0]) / 2 - 0.06)} ${rootY - lift * ((from[1] + to[1]) / 2 - 0.14)} ${at(to[0], to[1])}`
  const trail: [number, number][] = [
    [1, 1],
    [0.9, 0.6],
    [0.7, 0.36],
    [0.46, 0.16],
    [0.12, -0.08],
  ]
  return [
    {
      d: `M ${at(0, 0)} C ${at(0.2, 0.7)} ${at(0.6, 1.06)} ${at(1, 1)} ${trail
        .slice(1)
        .map((point, index) => scallop(trail[index], point))
        .join(' ')} Z`,
    },
    {
      d: trail
        .slice(0, 4)
        .map(
          (point) =>
            `M ${at(0.04, 0)} L ${at(point[0] * 0.94, point[1] * 0.94)}`
        )
        .join(' '),
      line: 1.1,
      neutral: true,
    },
  ]
}

function aircraft(
  extra: readonly Feature[],
  wings: readonly Mark[],
  rotor = false,
  wingLabel: readonly [number, number] = [380, 214]
): Blueprint {
  return {
    setting: 'air',
    body: 'M 36 140 Q 56 116 116 114 L 432 114 L 520 98 L 526 128 L 442 164 L 116 166 Q 56 164 36 140 Z',
    bodyKeys: ['frame', 'hull', 'chassis'],
    hold: { x: 148, y: 120, w: 290, h: 40 },
    features: [
      feature(['wings'], [300, 170], wingLabel, wings, true),
      feature(
        ['tail'],
        [482, 76],
        [500, 40],
        [{ d: 'M 448 114 L 480 54 L 512 54 L 500 114 Z' }]
      ),
      feature(
        ['cockpit'],
        [96, 122],
        [86, 96],
        [{ d: 'M 66 128 Q 86 108 130 110 L 140 126 Z' }]
      ),
      ...(rotor
        ? [
            feature(
              ['rotor'],
              [280, 92],
              [400, 82],
              [
                { d: 'M 120 96 H 440', line: 4 },
                { d: 'M 280 96 V 114', line: 6 },
              ]
            ),
          ]
        : []),
      ...extra,
    ],
  }
}

const GLIDER = aircraft(
  [],
  [{ d: 'M 196 148 L 352 148 L 446 176 L 300 176 Z' }]
)

const ORNITHOPTER = aircraft(
  [
    feature(
      ['engine', 'drive'],
      [280, 140],
      [330, 196],
      [{ d: circle(280, 140, 10) }]
    ),
  ],
  [...wing(250, 118, -1, 100, 92), ...wing(292, 118, 1, 112, 96)],
  false,
  [420, 30]
)

const AEROPLANE = aircraft(
  [
    feature(
      ['engine', 'drive'],
      [40, 140],
      [30, 100],
      [{ d: 'M 36 120 V 160', line: 4 }]
    ),
    feature(
      ['hardpoint'],
      [220, 172],
      [170, 196],
      [{ d: rect(196, 166, 46, 8) }]
    ),
  ],
  [{ d: 'M 214 150 L 330 150 L 384 192 L 296 192 Z' }]
)

const JET = aircraft(
  [
    feature(
      ['engine', 'drive'],
      [470, 140],
      [530, 180],
      [{ d: 'M 430 132 L 540 132 L 540 152 L 430 152 Z' }]
    ),
    feature(
      ['hardpoint'],
      [300, 186],
      [240, 210],
      [{ d: rect(272, 180, 56, 7) }]
    ),
  ],
  [{ d: 'M 220 152 L 330 152 L 414 200 L 352 200 Z' }]
)

const BOMBER = aircraft(
  [
    feature(
      ['engine', 'drive'],
      [300, 176],
      [230, 214],
      [
        { d: 'M 276 168 H 320 Q 328 175 320 182 H 276 Z' },
        { d: 'M 318 188 H 362 Q 370 195 362 202 H 318 Z' },
      ]
    ),
    feature(
      ['magazine', 'hardpoint'],
      [240, 168],
      [160, 196],
      [{ d: rect(200, 162, 80, 9) }]
    ),
  ],
  [{ d: 'M 180 152 L 340 152 L 430 210 L 320 210 Z' }]
)

const DRONE: Blueprint = {
  setting: 'air',
  body: 'M 180 140 Q 200 120 260 118 L 360 118 Q 400 120 410 140 Q 400 160 360 162 L 260 162 Q 200 160 180 140 Z',
  bodyKeys: ['frame', 'hull', 'chassis'],
  hold: { x: 236, y: 124, w: 150, h: 32 },
  features: [
    feature(
      ['tail'],
      [390, 110],
      [404, 84],
      [{ d: 'M 370 122 L 386 96 L 404 96 L 398 122 Z' }]
    ),
    feature(
      ['cockpit'],
      [240, 168],
      [216, 196],
      [{ d: 'M 224 160 Q 240 180 256 160 Z' }]
    ),
    feature(
      ['wings'],
      [320, 170],
      [380, 200],
      [{ d: 'M 250 150 L 350 150 L 386 182 L 292 182 Z' }],
      true
    ),
    feature(['sensors'], [190, 160], [150, 190], [{ d: circle(196, 156, 10) }]),
    feature(
      ['engine', 'drive'],
      [420, 140],
      [470, 120],
      [{ d: 'M 408 126 L 440 120 L 440 160 L 408 154 Z' }]
    ),
    feature(
      ['hardpoint'],
      [300, 176],
      [380, 186],
      [{ d: rect(280, 168, 40, 8) }]
    ),
  ],
}
const ROTORCRAFT: Blueprint = {
  setting: 'air',
  body: 'M 100 150 Q 104 112 170 108 L 320 108 Q 360 112 364 146 L 520 132 L 524 150 L 360 172 Q 330 190 170 188 Q 104 186 100 150 Z',
  bodyKeys: ['frame', 'hull', 'chassis'],
  hold: { x: 250, y: 118, w: 104, h: 62 },
  features: [
    feature(
      ['rotor'],
      [240, 80],
      [400, 72],
      [
        { d: 'M 40 84 H 440', line: 4 },
        { d: 'M 240 84 V 108', line: 6 },
      ]
    ),
    feature(
      ['tail'],
      [520, 124],
      [530, 96],
      [{ d: ring(522, 126, 6, 22), line: 3 }]
    ),
    feature(
      ['cockpit'],
      [120, 140],
      [96, 112],
      [{ d: 'M 104 150 Q 108 120 160 116 L 170 150 Z' }]
    ),
    feature(
      ['troop_bay'],
      [206, 150],
      [206, 204],
      [
        { d: rect(178, 124, 58, 50) },
        { d: 'M 207 124 V 174', line: 1.2, neutral: true },
      ]
    ),
    feature(
      ['legs', 'wheels'],
      [240, 214],
      [240, 254],
      [{ d: 'M 140 210 H 340 M 180 188 V 210 M 300 188 V 210', line: 4 }]
    ),
    feature(
      ['hardpoint'],
      [200, 200],
      [150, 230],
      [{ d: rect(176, 192, 50, 8) }]
    ),
  ],
}

function leftmost(path: string): number {
  const numbers = path.match(/-?\d+(?:\.\d+)?/g) ?? []
  return Math.min(...numbers.filter((_, index) => index % 2 === 0).map(Number))
}

function starship(
  body: string,
  hold: Hold,
  extra: readonly Feature[]
): Blueprint {
  const has = (key: string) => extra.some((item) => item.keys.includes(key))
  const tx = hold.x + hold.w * 0.62
  const ty = hold.y - 6
  const bx = hold.x + hold.w * 0.4
  const by = hold.y + hold.h + 6
  const nx = leftmost(body)
  return {
    setting: 'space',
    body,
    bodyKeys: ['hull', 'frame'],
    hold,
    features: [
      ...extra,
      ...(has('turret')
        ? []
        : [
            feature(
              ['turret'],
              [tx, ty - 4],
              [tx, ty - 22],
              [
                {
                  d: `M ${tx - 16} ${ty + 6} L ${tx - 10} ${ty - 8} H ${tx + 10} L ${tx + 16} ${ty + 6} Z`,
                },
                { d: rect(tx + 10, ty - 6, 28, 4) },
              ]
            ),
          ]),
      ...(has('airlock')
        ? []
        : [
            feature(
              ['airlock'],
              [bx, by + 2],
              [bx, by + 22],
              [
                { d: rect(bx - 13, by - 6, 26, 14) },
                {
                  d: `M ${bx} ${by - 4} V ${by + 6}`,
                  line: 1.4,
                  neutral: true,
                },
              ]
            ),
          ]),
      ...(has('sensors')
        ? []
        : [
            feature(
              ['sensors'],
              [nx - 8, 150],
              [nx + 10, 122],
              [
                { d: `M ${nx + 2} 150 H ${nx - 14}`, line: 2 },
                { d: circle(nx - 18, 150, 5) },
              ]
            ),
          ]),
    ],
  }
}

function engines(x: number, ys: readonly number[], w = 26, h = 16): Mark[] {
  return ys.flatMap((y) => [{ d: rect(x, y - h / 2, w, h) }])
}

const WARSHIP_SPACE = starship(
  'M 26 150 L 116 112 L 378 100 L 468 112 L 526 122 L 526 178 L 468 188 L 378 200 L 116 188 Z',
  { x: 120, y: 114, w: 398, h: 72 },
  [
    shaped(
      feature(
        ['wings'],
        [380, 60],
        [420, 26],
        [
          { d: 'M 290 104 L 384 34 L 436 34 L 404 106 Z' },
          { d: 'M 290 196 L 384 266 L 436 266 L 404 194 Z' },
        ],
        true
      )
    ),
    feature(
      ['drive', 'engine'],
      [540, 150],
      [540, 216],
      engines(522, [136, 164])
    ),
    feature(
      ['bridge', 'cockpit'],
      [150, 102],
      [132, 84],
      [{ d: 'M 106 116 Q 150 82 206 104 L 206 112 Z' }]
    ),
    feature(
      ['sensors'],
      [14, 150],
      [30, 120],
      [{ d: 'M 26 150 H 4 M 10 140 L 26 150 L 10 160', line: 2 }]
    ),
    feature(
      ['turret'],
      [300, 92],
      [300, 74],
      [
        { d: 'M 280 102 L 286 90 L 314 90 L 320 102 Z' },
        { d: rect(312, 92, 30, 4) },
        { d: 'M 280 198 L 286 210 L 314 210 L 320 198 Z' },
      ]
    ),
  ]
)

const DREADNOUGHT = starship(
  'M 10 150 L 70 120 L 200 104 L 470 96 L 540 110 L 540 190 L 470 204 L 200 196 L 70 180 Z',
  { x: 76, y: 110, w: 456, h: 80 },
  [
    feature(
      ['drive', 'engine'],
      [548, 150],
      [540, 222],
      engines(536, [124, 150, 176], 18, 18)
    ),
    feature(
      ['bridge', 'cockpit'],
      [360, 80],
      [360, 60],
      [{ d: 'M 320 98 L 330 70 L 390 70 L 400 98 Z' }]
    ),
    feature(
      ['turret'],
      [200, 92],
      [200, 70],
      [
        { d: 'M 160 104 L 168 88 L 204 88 L 212 104 Z' },
        { d: 'M 240 100 L 248 84 L 284 84 L 292 100 Z' },
        { d: 'M 160 196 L 168 212 L 204 212 L 212 196 Z' },
        { d: 'M 240 200 L 248 216 L 284 216 L 292 200 Z' },
      ]
    ),
    feature(
      ['sensors'],
      [6, 150],
      [30, 116],
      [{ d: 'M 10 150 H -6', line: 3 }]
    ),
  ]
)

const FIGHTER = starship(
  'M 60 150 L 220 112 L 440 112 L 480 128 L 480 172 L 440 188 L 220 188 Z',
  { x: 226, y: 120, w: 248, h: 60 },
  [
    shaped(
      feature(
        ['wings'],
        [380, 60],
        [420, 28],
        [
          { d: 'M 300 114 L 400 40 L 440 40 L 420 114 Z' },
          { d: 'M 300 186 L 400 260 L 440 260 L 420 186 Z' },
        ],
        true
      )
    ),
    feature(
      ['bridge', 'cockpit'],
      [170, 136],
      [150, 108],
      [{ d: 'M 112 146 Q 168 118 222 124 L 222 146 Z' }]
    ),
    feature(
      ['drive', 'engine'],
      [494, 150],
      [520, 196],
      engines(480, [138, 162], 26, 18)
    ),
    feature(
      ['hardpoint'],
      [300, 106],
      [270, 92],
      [{ d: rect(240, 104, 130, 5) }, { d: rect(240, 191, 130, 5) }]
    ),
  ]
)

const SHUTTLE = starship(
  'M 60 160 Q 70 124 140 120 L 440 118 L 500 132 L 500 176 L 440 186 L 140 188 Q 70 190 60 160 Z',
  { x: 120, y: 126, w: 370, h: 56 },
  [
    shaped(
      feature(
        ['wings'],
        [330, 210],
        [330, 256],
        [{ d: 'M 240 184 L 450 184 L 470 250 L 380 250 Z' }],
        true
      )
    ),
    shaped(
      feature(
        ['tail'],
        [470, 96],
        [490, 66],
        [{ d: 'M 430 118 L 470 70 L 494 70 L 486 120 Z' }]
      )
    ),
    feature(
      ['cockpit', 'bridge'],
      [104, 130],
      [90, 104],
      [{ d: 'M 72 146 Q 90 124 140 124 L 146 142 Z' }]
    ),
    feature(
      ['drive', 'engine'],
      [512, 154],
      [530, 200],
      engines(498, [144, 166], 22, 16)
    ),
    feature(
      ['cargo_bay'],
      [300, 116],
      [300, 98],
      [{ d: rect(200, 112, 200, 10) }]
    ),
  ]
)

const LANDER = starship(
  'M 150 196 L 186 84 Q 280 50 374 84 L 410 196 Z',
  { x: 196, y: 98, w: 168, h: 92 },
  [
    shaped(
      feature(
        ['legs', 'wheels'],
        [280, 232],
        [460, 250],
        [
          {
            d: 'M 172 196 L 128 252 H 106 M 388 196 L 432 252 H 454 M 248 196 L 238 252 M 312 196 L 322 252',
            line: 4,
          },
        ]
      )
    ),
    feature(
      ['drive', 'engine'],
      [280, 210],
      [280, 266],
      [{ d: 'M 250 196 L 258 222 H 302 L 310 196 Z' }]
    ),
    feature(
      ['bridge', 'cockpit'],
      [280, 72],
      [280, 50],
      [{ d: 'M 238 80 Q 280 58 322 80 Z' }]
    ),
  ]
)

const FREIGHTER = starship(
  'M 60 150 L 110 120 H 470 L 500 136 V 164 L 470 180 H 110 Z',
  { x: 112, y: 126, w: 356, h: 48 },
  [
    feature(
      ['cargo_bay', 'hold'],
      [280, 96],
      [280, 72],
      [
        { d: rect(140, 86, 70, 34) },
        { d: rect(220, 86, 70, 34) },
        { d: rect(300, 86, 70, 34) },
        { d: rect(140, 180, 70, 34) },
        { d: rect(220, 180, 70, 34) },
        { d: rect(300, 180, 70, 34) },
      ]
    ),
    feature(
      ['bridge', 'cockpit'],
      [86, 140],
      [60, 110],
      [{ d: 'M 60 150 L 110 120 V 150 Z' }]
    ),
    feature(
      ['drive', 'engine'],
      [512, 150],
      [530, 200],
      engines(498, [142, 158], 26, 14)
    ),
  ]
)

const MINING = starship(
  'M 120 150 L 160 116 H 470 L 500 132 V 168 L 470 184 H 160 Z',
  { x: 162, y: 122, w: 306, h: 56 },
  [
    shaped(
      feature(
        ['arm', 'hardpoint'],
        [80, 150],
        [60, 100],
        [
          {
            d: 'M 120 136 L 60 110 L 30 126 M 120 164 L 60 190 L 30 174',
            line: 7,
          },
        ]
      )
    ),
    feature(
      ['hold', 'cargo_bay'],
      [320, 220],
      [320, 254],
      [{ d: rect(220, 184, 200, 30) }]
    ),
    feature(
      ['drive', 'engine'],
      [512, 150],
      [530, 200],
      engines(498, [140, 160])
    ),
  ]
)

const CORVETTE = starship(
  'M 40 150 L 150 112 L 420 106 L 506 124 L 506 176 L 420 194 L 150 188 Z',
  { x: 156, y: 118, w: 340, h: 64 },
  [
    shaped(
      feature(
        ['wings'],
        [370, 74],
        [420, 50],
        [
          { d: 'M 320 108 L 390 64 L 430 64 L 414 110 Z' },
          { d: 'M 320 192 L 390 236 L 430 236 L 414 190 Z' },
        ],
        true
      )
    ),
    feature(
      ['bridge', 'cockpit'],
      [110, 132],
      [96, 104],
      [{ d: 'M 84 136 Q 120 112 160 116 L 160 136 Z' }]
    ),
    feature(
      ['drive', 'engine'],
      [520, 150],
      [536, 200],
      engines(506, [136, 164], 22, 16)
    ),
  ]
)

const ARK = starship(
  'M 40 150 Q 40 96 100 96 L 460 96 Q 520 96 520 150 Q 520 204 460 204 L 100 204 Q 40 204 40 150 Z',
  { x: 150, y: 110, w: 340, h: 80 },
  [
    feature(
      ['life_support', 'core'],
      [110, 150],
      [110, 84],
      [{ d: `${ring(110, 150, 30, 58)} ${ring(110, 150, 18, 40)}` }]
    ),
    feature(
      ['drive', 'engine'],
      [534, 150],
      [540, 220],
      [{ d: 'M 520 120 L 552 106 V 194 L 520 180 Z' }]
    ),
    feature(
      ['bridge', 'cockpit'],
      [40, 150],
      [40, 110],
      [{ d: circle(46, 150, 18) }]
    ),
    shaped(
      feature(
        ['sails', 'collectors'],
        [280, 250],
        [420, 256],
        [{ d: rect(160, 216, 240, 18) }, { d: rect(160, 66, 240, 18) }]
      )
    ),
  ]
)

const SOLAR_SAILER = starship(
  'M 140 150 L 190 116 H 390 L 430 150 L 390 184 H 190 Z',
  { x: 194, y: 122, w: 192, h: 56 },
  [
    shaped(
      feature(
        ['sails', 'envelope', 'mast'],
        [290, 50],
        [470, 30],
        [
          { d: 'M 290 116 L 110 22 L 470 22 Z' },
          { d: 'M 290 184 L 110 278 L 470 278 Z' },
          { d: 'M 290 22 L 290 278', line: 1.4, neutral: true },
        ],
        true
      )
    ),
    feature(
      ['drive', 'engine'],
      [444, 150],
      [476, 172],
      engines(428, [150], 22, 16)
    ),
    feature(
      ['bridge', 'cockpit'],
      [150, 150],
      [120, 120],
      [{ d: circle(156, 150, 14) }]
    ),
  ]
)

const SKIMMER = starship(
  'M 50 160 Q 120 112 300 110 Q 470 112 520 150 Q 470 184 300 186 Q 120 186 50 160 Z',
  { x: 120, y: 122, w: 350, h: 54 },
  [
    feature(
      ['drive', 'engine'],
      [520, 150],
      [540, 196],
      engines(512, [140, 160], 20, 14)
    ),
    feature(
      ['bridge', 'cockpit'],
      [100, 140],
      [80, 112],
      [{ d: 'M 70 150 Q 100 128 150 128 L 150 146 Z' }]
    ),
    feature(
      ['hold', 'cargo_bay'],
      [300, 208],
      [300, 248],
      [{ d: 'M 220 186 L 240 222 H 360 L 380 186 Z' }]
    ),
  ]
)

const PLANAR = starship(
  'M 40 150 L 140 90 L 300 70 L 460 90 L 530 150 L 460 210 L 300 230 L 140 210 Z',
  { x: 120, y: 110, w: 360, h: 80 },
  [
    shaped(
      feature(
        ['core'],
        [300, 80],
        [300, 52],
        [
          {
            d: 'M 300 52 L 316 72 L 300 92 L 284 72 Z',
          },
        ]
      )
    ),
    feature(
      ['drive', 'engine'],
      [540, 150],
      [540, 200],
      [{ d: 'M 530 150 L 556 132 L 556 168 Z' }]
    ),
    feature(
      ['bridge', 'cockpit'],
      [80, 150],
      [60, 116],
      [{ d: 'M 40 150 L 100 120 V 180 Z' }]
    ),
  ]
)

const BURROWER: Blueprint = {
  setting: 'deep',
  body: 'M 140 112 L 470 112 Q 508 112 508 150 L 508 172 Q 508 200 470 200 L 140 200 Z',
  bodyKeys: ['hull', 'frame'],
  hold: { x: 148, y: 120, w: 352, h: 74 },
  features: [
    feature(
      ['ram_head'],
      [70, 156],
      [70, 104],
      [
        { d: 'M 140 108 L 30 156 L 140 204 Z' },
        {
          d: 'M 112 120 L 112 192 M 84 133 L 84 179 M 56 146 L 56 166',
          line: 1.6,
          neutral: true,
        },
      ]
    ),
    feature(
      ['tracks'],
      [320, 222],
      [320, 262],
      [
        {
          d: 'M 150 206 H 494 Q 512 206 512 222 Q 512 238 494 238 H 150 Q 132 238 132 222 Q 132 206 150 206 Z',
        },
      ]
    ),
    feature(
      ['cockpit'],
      [440, 104],
      [440, 84],
      [{ d: 'M 410 112 Q 440 90 470 112 Z' }]
    ),
  ],
}

type Roof = 'gable' | 'flat' | 'dome' | 'wings' | 'none'

type Mass = { x: number; y: number; w: number; h: number }

const GROUND = 232

function roofHeight(roof: Roof, mass: Mass): number {
  if (roof === 'gable') return Math.min(76, mass.w * 0.32)
  if (roof === 'dome') return Math.min(80, mass.w * 0.3)
  if (roof === 'none') return 10
  return 12
}

function roofMark(roof: Roof, mass: Mass): string {
  const middle = mass.x + mass.w / 2
  const rise = roofHeight(roof, mass)
  if (roof === 'gable')
    return `M ${mass.x - 14} ${mass.y} L ${middle} ${mass.y - rise} L ${mass.x + mass.w + 14} ${mass.y} Z`
  if (roof === 'dome')
    return `M ${mass.x + 8} ${mass.y} A ${mass.w / 2 - 8} ${rise} 0 0 1 ${mass.x + mass.w - 8} ${mass.y} Z`
  if (roof === 'wings')
    return `${rect(mass.x - 6, mass.y - 12, 122, 12)} ${rect(mass.x + mass.w - 116, mass.y - 12, 122, 12)}`
  if (roof === 'none') return rect(middle - 16, mass.y - 10, 32, 10)
  return rect(mass.x - 8, mass.y - 12, mass.w + 16, 12)
}

function crenels(left: number, right: number, y: number): string {
  const teeth = Array.from(
    { length: Math.max(1, Math.floor((right - left) / 24)) },
    (_, index) => rect(left + 4 + index * 24, y - 12, 12, 8)
  )
  return [rect(left, y - 4, right - left, 4), ...teeth].join(' ')
}

function above(y: number): number {
  return Math.max(12, y)
}

function building(
  body: string,
  mass: Mass,
  roof: Roof,
  hold: Hold,
  options: {
    setting?: Setting
    footing?: string
    crown?: number
    spireAt?: number
    extra?: readonly Feature[]
  } = {}
): Blueprint {
  const middle = mass.x + mass.w / 2
  const bottom = mass.y + mass.h
  const top = mass.y - roofHeight(roof, mass)
  const towerWidth = Math.min(32, Math.max(16, mass.w * 0.18))
  const towerTop =
    mass.h > 150 ? mass.y + mass.h * 0.3 : Math.max(24, mass.y - 30)
  const crowned =
    roof === 'gable'
      ? roofHeight(roof, mass) * 0.55
      : roof === 'none'
        ? 0
        : roofHeight(roof, mass)
  const domeWidth =
    roof === 'gable'
      ? Math.min(mass.w * 0.36, 110)
      : Math.min(mass.w * 0.62, 180)
  const domeRise = Math.min(domeWidth * 0.5, 70)
  const spireAt = options.spireAt ?? mass.x + mass.w * 0.82
  const crown = options.crown ?? mass.y - crowned
  return {
    setting: options.setting ?? 'ground',
    body,
    bodyKeys: ['outer_wall', 'main_hall', 'span'],
    hold,
    features: [
      feature(
        ['keep'],
        [middle, mass.y - 24],
        [middle, above(mass.y - 66)],
        [{ d: rect(middle - mass.w * 0.2, mass.y - 54, mass.w * 0.4, 58) }],
        true
      ),
      feature(
        ['roof'],
        [middle, mass.y - 8],
        [mass.x + mass.w * 0.22, above(mass.y - 22)],
        [{ d: roofMark(roof, mass) }]
      ),
      feature(
        ['dome'],
        [middle, crown - domeRise / 2],
        [middle, above(crown - domeRise - 14)],
        [
          {
            d: `M ${middle - domeWidth / 2} ${crown} A ${domeWidth / 2} ${domeRise} 0 0 1 ${middle + domeWidth / 2} ${crown} Z`,
          },
        ]
      ),
      feature(
        ['spire'],
        [spireAt, crown - 40],
        [spireAt, above(crown - 108)],
        [
          {
            d: `M ${spireAt - 16} ${crown} L ${spireAt} ${crown - 96} L ${spireAt + 16} ${crown} Z`,
          },
        ]
      ),
      feature(
        ['battlements'],
        [middle, mass.y - 6],
        [mass.x + mass.w * 0.7, above(mass.y - 24)],
        [{ d: crenels(mass.x, mass.x + mass.w, mass.y) }]
      ),
      feature(
        ['towers'],
        [mass.x - 18, (towerTop + bottom) / 2],
        [mass.x - 18, above(towerTop - 14)],
        [
          {
            d: rect(
              mass.x - towerWidth - 4,
              towerTop,
              towerWidth,
              bottom - towerTop
            ),
          },
          {
            d: rect(
              mass.x + mass.w + 4,
              towerTop,
              towerWidth,
              bottom - towerTop
            ),
          },
        ]
      ),
      feature(
        ['gate', 'gatehouse'],
        [middle, bottom - 18],
        [middle, bottom - 54],
        [
          {
            d: `M ${middle - 20} ${bottom} L ${middle - 20} ${bottom - 26} Q ${middle} ${bottom - 50} ${middle + 20} ${bottom - 26} L ${middle + 20} ${bottom} Z`,
          },
        ]
      ),
      feature(
        ['docks', 'slipway'],
        [mass.x + mass.w + 40, GROUND],
        [mass.x + mass.w + 40, GROUND + 26],
        [
          { d: rect(mass.x + mass.w, GROUND - 6, 70, 8) },
          {
            d: `M ${mass.x + mass.w + 20} ${GROUND + 2} V ${GROUND + 20} M ${mass.x + mass.w + 52} ${GROUND + 2} V ${GROUND + 20}`,
            line: 3,
            neutral: true,
          },
        ]
      ),
      feature(
        ['wheel'],
        [mass.x - 34, bottom - 32],
        [mass.x - 34, bottom - 72],
        wheel(mass.x - 34, bottom - 32, 28)
      ),
      feature(
        ['beacon', 'collectors'],
        [middle, top - 16],
        [middle + 44, above(top - 16)],
        [{ d: circle(middle, above(top - 16), 9) }]
      ),
      feature(
        ['piers', 'shafts', 'conduits'],
        [mass.x + mass.w * 0.25, (bottom + 248) / 2],
        [mass.x + mass.w * 0.25 - 40, 262],
        [
          {
            d: [0.2, 0.4, 0.6, 0.8]
              .map(
                (share) =>
                  `M ${mass.x + mass.w * share} ${bottom} L ${mass.x + mass.w * share} 248`
              )
              .join(' '),
            line: 7,
          },
        ]
      ),
      feature(
        ['foundation', 'earthwork'],
        [middle, GROUND + 8],
        [middle, GROUND + 28],
        [{ d: options.footing ?? rect(mass.x - 14, GROUND, mass.w + 28, 14) }]
      ),
      ...(options.extra ?? []),
    ],
  }
}

function plain(x: number, w: number, top: number, roof: Roof): Blueprint {
  return building(
    rect(x, top, w, GROUND - top),
    { x, y: top, w, h: GROUND - top },
    roof,
    { x: x + 6, y: top + 6, w: w - 12, h: GROUND - top - 12 }
  )
}

const ARCADE_BODY = [
  rect(90, 120, 380, 112),
  ...[0, 1, 2, 3, 4, 5].map(
    (index) =>
      `M ${106 + index * 60} 232 L ${106 + index * 60} 210 Q ${128 + index * 60} 188 ${150 + index * 60} 210 L ${150 + index * 60} 232 Z`
  ),
].join(' ')

const RING: Blueprint = {
  setting: 'space',
  body: `${ring(280, 140, 130, 102)} ${ring(280, 140, 96, 74)}`,
  bodyKeys: ['ring_segments', 'habitat_decks'],
  hold: { x: 236, y: 112, w: 88, h: 56 },
  features: [
    feature(
      ['spine'],
      [280, 140],
      [210, 140],
      [{ d: 'M 150 140 H 410 M 280 38 V 242', line: 5 }],
      true
    ),
    feature(
      ['control_core', 'core'],
      [280, 140],
      [280, 112],
      [{ d: circle(280, 140, 26) }]
    ),
    feature(
      ['docking_ring'],
      [96, 140],
      [96, 104],
      [{ d: `${ring(96, 140, 20, 20)} ${ring(96, 140, 10, 10)}` }]
    ),
    feature(
      ['collectors'],
      [468, 70],
      [500, 34],
      [
        { d: 'M 430 60 L 520 30 L 532 70 L 442 100 Z' },
        { d: 'M 430 220 L 520 250 L 532 210 L 442 180 Z' },
      ]
    ),
    feature(
      ['thrusters'],
      [440, 140],
      [500, 140],
      [{ d: 'M 410 128 L 446 116 L 446 164 L 410 152 Z' }]
    ),
    feature(
      ['shielding'],
      [280, 30],
      [160, 26],
      [{ d: ring(280, 140, 154, 124), line: 1.6 }],
      true
    ),
  ],
}

function walkerFigure(x: number, ground: number, lean = 0): Mark[] {
  const hip = ground - 54
  return [
    { d: circle(x + lean, ground - 104, 11) },
    { d: `M ${x + lean} ${ground - 92} L ${x} ${hip}`, line: 6 },
    {
      d: `M ${x} ${hip} L ${x - 14} ${ground} M ${x} ${hip} L ${x + 16} ${ground}`,
      line: 6,
    },
  ]
}

function windows(
  x: number,
  y: number,
  count: number,
  step: number,
  w: number,
  h: number
): string {
  return Array.from({ length: count }, (_, index) =>
    rect(x + index * step, y, w, h)
  ).join(' ')
}

const BICYCLE: Blueprint = {
  setting: 'ground',
  body: 'M 206 196 L 262 126 L 372 126 L 336 196 Z',
  bodyKeys: ['chassis', 'frame'],
  hold: { x: 262, y: 134, w: 80, h: 52 },
  features: [
    feature(
      ['draft_team'],
      [300, 40],
      [240, 30],
      [
        { d: circle(318, 30, 11) },
        { d: 'M 314 42 L 286 112', line: 6 },
        { d: 'M 304 64 L 372 106', line: 5 },
        { d: 'M 286 112 L 320 196', line: 6 },
      ]
    ),
    feature(
      ['harness'],
      [384, 104],
      [440, 86],
      [
        { d: 'M 370 126 L 382 98 L 404 94', line: 5 },
        { d: circle(300, 196, 15) },
      ]
    ),
    feature(
      ['cargo_bay'],
      [186, 116],
      [150, 96],
      [{ d: rect(150, 112, 74, 10) }]
    ),
    feature(
      ['wheels'],
      [170, 198],
      [100, 262],
      [...wheel(170, 198, 54), ...wheel(410, 198, 54)]
    ),
  ],
}

const RICKSHAW: Blueprint = {
  setting: 'ground',
  body: 'M 260 200 L 260 124 Q 262 98 304 94 L 388 94 L 410 124 L 410 200 Z',
  bodyKeys: ['chassis', 'frame'],
  hold: { x: 270, y: 126, w: 130, h: 68 },
  features: [
    feature(
      ['cargo_bay'],
      [330, 62],
      [330, 40],
      [{ d: 'M 252 102 Q 320 30 420 84 L 408 100 Q 320 58 266 112 Z' }]
    ),
    feature(
      ['harness'],
      [180, 178],
      [180, 150],
      [{ d: 'M 262 172 L 102 178 M 262 186 L 102 192', line: 5 }]
    ),
    feature(
      ['draft_team'],
      [96, 140],
      [60, 110],
      [...walkerFigure(96, 240, -4), { d: 'M 96 130 L 106 180', line: 5 }]
    ),
    feature(['wheels', 'axle'], [350, 214], [350, 266], wheel(350, 214, 42)),
  ],
}

const PALANQUIN: Blueprint = {
  setting: 'ground',
  body: rect(214, 96, 152, 82),
  bodyKeys: ['chassis', 'frame'],
  hold: { x: 224, y: 104, w: 132, h: 66 },
  features: [
    feature(
      ['cargo_bay'],
      [290, 72],
      [290, 44],
      [{ d: 'M 202 98 L 290 54 L 378 98 Z' }]
    ),
    feature(
      ['harness'],
      [140, 150],
      [140, 124],
      [{ d: 'M 60 150 H 520', line: 6 }]
    ),
    feature(
      ['draft_team'],
      [110, 170],
      [70, 120],
      [...walkerFigure(110, 250), ...walkerFigure(470, 250)]
    ),
  ],
}

const TRAM: Blueprint = {
  setting: 'ground',
  body: 'M 80 200 L 80 122 Q 84 98 112 96 L 468 96 Q 496 98 500 122 L 500 200 Z',
  bodyKeys: ['chassis', 'frame', 'hull'],
  hold: { x: 160, y: 104, w: 330, h: 88 },
  features: [
    feature(
      ['engine'],
      [300, 72],
      [400, 40],
      [
        { d: 'M 268 96 L 290 64 L 330 64 L 310 96', line: 3 },
        { d: 'M 256 60 H 360', line: 3 },
      ]
    ),
    feature(['cockpit'], [120, 128], [110, 80], [{ d: rect(92, 108, 58, 42) }]),
    feature(
      ['cargo_bay'],
      [300, 128],
      [300, 150],
      [{ d: windows(170, 110, 5, 64, 48, 32), neutral: true }]
    ),
    feature(
      ['wheels'],
      [160, 218],
      [160, 264],
      wheels(18, 218, 140, 190, 390, 440)
    ),
  ],
  decor: [
    { d: 'M 30 240 H 540', line: 3 },
    { d: 'M 30 56 H 540', line: 1.4, neutral: true },
  ],
}

const MAGLEV: Blueprint = {
  setting: 'ground',
  body: 'M 40 186 Q 46 122 150 106 L 510 100 L 524 112 L 524 186 Z',
  bodyKeys: ['chassis', 'frame', 'hull'],
  hold: { x: 170, y: 112, w: 340, h: 68 },
  features: [
    feature(
      ['cockpit'],
      [100, 136],
      [90, 100],
      [{ d: 'M 70 152 Q 96 118 156 112 L 160 142 Z' }]
    ),
    feature(
      ['cargo_bay'],
      [340, 128],
      [340, 150],
      [{ d: windows(190, 118, 6, 54, 38, 22), neutral: true }]
    ),
    feature(
      ['engine'],
      [330, 192],
      [330, 172],
      [{ d: rect(130, 186, 394, 10) }]
    ),
    feature(
      ['wheels'],
      [200, 206],
      [200, 262],
      [{ d: 'M 110 206 H 530', line: 6 }]
    ),
  ],
  decor: [
    { d: 'M 30 222 H 540', line: 9 },
    { d: 'M 120 226 V 266 M 300 226 V 266 M 480 226 V 266', line: 6 },
  ],
}

const BUS = motor(
  'M 60 206 L 60 116 Q 62 92 92 90 L 500 90 Q 518 92 520 112 L 520 206 Z',
  { x: 120, y: 98, w: 390, h: 100 },
  [
    feature(
      ['cockpit'],
      [86, 122],
      [80, 70],
      [{ d: 'M 66 150 L 66 106 Q 68 98 86 98 L 112 98 L 112 150 Z' }]
    ),
    feature(
      ['steering'],
      [100, 160],
      [70, 176],
      [{ d: ring(100, 160, 8, 8), line: 3 }]
    ),
    feature(
      ['cargo_bay'],
      [300, 122],
      [300, 150],
      [{ d: windows(130, 104, 6, 62, 50, 36), neutral: true }]
    ),
    feature(
      ['engine'],
      [490, 184],
      [530, 230],
      [{ d: rect(470, 168, 42, 30) }]
    ),
  ],
  [130, 430]
)

const TRACTOR: Blueprint = {
  setting: 'ground',
  body: 'M 120 196 L 120 150 L 300 150 L 300 96 L 404 96 L 412 196 Z',
  bodyKeys: ['chassis', 'frame', 'hull'],
  hold: { x: 130, y: 158, w: 160, h: 32 },
  features: [
    feature(
      ['cockpit'],
      [350, 112],
      [350, 72],
      [{ d: rect(312, 104, 82, 44) }]
    ),
    feature(
      ['engine'],
      [190, 170],
      [190, 120],
      [{ d: rect(132, 156, 130, 34) }, { d: 'M 232 150 V 108', line: 6 }]
    ),
    feature(
      ['steering'],
      [300, 140],
      [280, 120],
      [{ d: ring(300, 142, 8, 8), line: 3 }]
    ),
    feature(
      ['cargo_bay'],
      [440, 182],
      [480, 160],
      [{ d: rect(412, 176, 56, 10) }]
    ),
    feature(
      ['wheels', 'tracks'],
      [370, 200],
      [370, 266],
      [...wheel(370, 200, 58), ...wheel(166, 222, 34)]
    ),
  ],
}

const APC = tracked(
  'M 70 172 L 104 120 L 462 120 L 502 152 L 502 194 L 80 194 Z',
  { x: 104, y: 128, w: 388, h: 60 },
  [
    feature(
      ['cockpit'],
      [130, 116],
      [120, 96],
      [{ d: 'M 106 120 L 118 108 H 152 L 158 120 Z' }]
    ),
    feature(
      ['turret'],
      [334, 102],
      [334, 82],
      [
        { d: 'M 302 120 L 312 100 L 360 100 L 370 120 Z' },
        { d: rect(360, 104, 74, 6) },
      ]
    ),
    feature(
      ['armour_plating'],
      [280, 150],
      [280, 168],
      [{ d: rect(116, 144, 330, 8) }]
    ),
    feature(
      ['engine'],
      [430, 132],
      [470, 104],
      [{ d: rect(404, 126, 54, 14) }]
    ),
  ]
)

const SELF_PROPELLED_GUN = tracked(
  'M 76 172 L 100 142 L 480 142 L 504 172 L 486 194 L 96 194 Z',
  { x: 102, y: 148, w: 378, h: 42 },
  [
    feature(
      ['turret'],
      [360, 96],
      [200, 84],
      [
        { d: 'M 300 142 L 312 88 L 462 88 L 472 142 Z' },
        { d: rect(64, 102, 252, 12) },
      ]
    ),
    feature(
      ['cockpit'],
      [130, 138],
      [120, 116],
      [{ d: 'M 108 142 L 120 130 H 150 L 156 142 Z' }]
    ),
    feature(
      ['magazine'],
      [440, 112],
      [500, 84],
      [{ d: rect(420, 100, 36, 30) }]
    ),
  ]
)

const MISSILE_CARRIER = motor(
  'M 60 206 L 60 150 Q 62 128 88 126 L 150 126 L 150 162 L 520 162 L 520 206 Z',
  { x: 160, y: 166, w: 352, h: 34 },
  [
    feature(
      ['cockpit'],
      [104, 140],
      [96, 108],
      [{ d: 'M 74 160 L 74 144 Q 76 134 92 134 L 140 134 L 140 160 Z' }]
    ),
    feature(
      ['steering'],
      [128, 170],
      [128, 186],
      [{ d: ring(128, 170, 7, 7), line: 3 }]
    ),
    feature(
      ['cargo_bay'],
      [340, 110],
      [420, 60],
      [
        { d: 'M 198 158 L 468 72 L 482 92 L 214 170 Z' },
        { d: 'M 214 150 L 476 62 L 486 76 L 226 160 Z' },
      ]
    ),
    feature(['engine'], [70, 182], [40, 230], [{ d: rect(60, 168, 44, 30) }]),
  ],
  [110, 330, 400, 470]
)

const MOTORBOAT: Blueprint = {
  setting: 'water',
  body: 'M 70 168 L 476 160 L 508 150 L 494 200 Q 460 228 300 230 Q 130 228 70 168 Z',
  bodyKeys: ['hull', 'frame'],
  hold: { x: 110, y: 172, w: 340, h: 44 },
  features: [
    feature(
      ['rudder', 'steering'],
      [340, 140],
      [340, 110],
      [
        { d: 'M 300 162 L 330 128 L 384 128 L 384 160 Z' },
        { d: ring(360, 150, 7, 7), line: 2.4, neutral: true },
      ]
    ),
    feature(
      ['oars', 'engine'],
      [512, 200],
      [540, 250],
      [{ d: 'M 498 160 L 522 160 L 528 236 L 510 236 Z' }]
    ),
  ],
  decor: [{ d: 'M 20 214 H 540', line: 1.2, neutral: true }],
}

const HYDROFOIL: Blueprint = {
  setting: 'water',
  body: 'M 60 140 Q 80 110 160 106 L 484 104 L 506 120 L 494 152 L 94 158 Q 66 156 60 140 Z',
  bodyKeys: ['hull', 'frame'],
  hold: { x: 120, y: 114, w: 360, h: 38 },
  features: [
    feature(
      ['hold'],
      [300, 124],
      [300, 90],
      [{ d: windows(150, 116, 7, 46, 30, 14), neutral: true }]
    ),
    feature(
      ['oars', 'engine'],
      [150, 206],
      [110, 250],
      [
        { d: 'M 150 156 V 206 M 420 154 V 206', line: 6 },
        { d: 'M 116 208 H 184 M 386 208 H 454', line: 5 },
      ]
    ),
    feature(
      ['rudder', 'steering'],
      [500, 160],
      [530, 190],
      [{ d: 'M 488 150 L 508 152 L 504 186 L 486 180 Z' }]
    ),
  ],
  decor: [{ d: 'M 20 200 H 540', line: 1.2, neutral: true }],
}

const CONTAINER_SHIP = ship(
  [
    feature(
      ['bridge'],
      [474, 106],
      [474, 76],
      [{ d: 'M 442 146 L 446 92 L 504 92 L 508 146 Z' }]
    ),
    feature(
      ['boiler', 'engine'],
      [424, 114],
      [410, 84],
      [{ d: 'M 414 146 L 418 108 L 432 108 L 436 146 Z' }]
    ),
    feature(
      ['hold'],
      [230, 112],
      [230, 64],
      [
        { d: windows(60, 120, 10, 35, 32, 24) },
        { d: windows(94, 94, 8, 35, 32, 24) },
      ]
    ),
  ],
  [],
  'steam'
)

const TANKER = ship(
  [
    feature(
      ['bridge'],
      [470, 110],
      [470, 80],
      [{ d: 'M 440 146 L 444 96 L 500 96 L 504 146 Z' }]
    ),
    feature(
      ['boiler', 'engine'],
      [420, 118],
      [400, 88],
      [{ d: 'M 410 146 L 414 112 L 428 112 L 432 146 Z' }]
    ),
    feature(
      ['hold'],
      [230, 130],
      [230, 96],
      [
        ...[90, 170, 250, 330].map((x) => ({
          d: `M ${x} 146 A 34 18 0 0 1 ${x + 68} 146 Z`,
        })),
        { d: 'M 70 134 H 410', line: 3, neutral: true },
      ]
    ),
  ],
  [],
  'steam'
)

const DESTROYER = ship(
  [
    feature(
      ['bridge'],
      [230, 108],
      [230, 60],
      [
        { d: 'M 204 146 L 208 112 L 254 112 L 258 146 Z' },
        { d: 'M 230 112 V 70 M 216 82 H 244', line: 3 },
      ]
    ),
    feature(
      ['boiler', 'engine'],
      [320, 116],
      [320, 86],
      [
        { d: 'M 296 146 L 300 108 L 320 108 L 324 146 Z' },
        { d: 'M 334 146 L 338 112 L 356 112 L 360 146 Z' },
      ]
    ),
    feature(
      ['turret'],
      [130, 134],
      [100, 116],
      [
        { d: 'M 114 146 L 120 130 L 150 130 L 156 146 Z' },
        { d: rect(70, 134, 46, 4) },
        { d: 'M 428 146 L 434 130 L 464 130 L 470 146 Z' },
      ]
    ),
  ],
  [],
  'steam'
)

const CRUISER = ship(
  [
    feature(
      ['bridge'],
      [290, 90],
      [290, 52],
      [
        {
          d: 'M 260 146 L 264 108 L 276 108 L 280 72 L 304 72 L 308 108 L 320 108 L 324 146 Z',
        },
      ]
    ),
    feature(
      ['boiler', 'engine'],
      [370, 108],
      [400, 80],
      [
        { d: 'M 350 146 L 356 100 L 378 100 L 384 146 Z' },
        { d: 'M 390 146 L 396 104 L 416 104 L 422 146 Z' },
      ]
    ),
    feature(
      ['turret'],
      [170, 132],
      [150, 112],
      [
        { d: 'M 140 146 L 148 128 L 196 128 L 204 146 Z' },
        { d: rect(84, 132, 60, 6) },
        { d: 'M 210 146 L 216 132 L 248 132 L 254 146 Z' },
        { d: 'M 452 146 L 460 128 L 500 128 L 508 146 Z' },
      ]
    ),
  ],
  [],
  'steam'
)

const ICEBREAKER = ship(
  [
    feature(
      ['armour_plating'],
      [60, 196],
      [40, 254],
      [{ d: 'M 26 150 L 92 150 L 110 228 L 72 232 Z' }]
    ),
    feature(
      ['bridge'],
      [190, 100],
      [190, 66],
      [{ d: 'M 150 146 L 156 86 L 226 86 L 232 146 Z' }]
    ),
    feature(
      ['boiler', 'engine'],
      [330, 112],
      [330, 82],
      [{ d: 'M 312 146 L 316 102 L 344 102 L 348 146 Z' }]
    ),
    feature(['hold'], [430, 134], [470, 112], [{ d: rect(392, 124, 90, 22) }]),
  ],
  [],
  'steam'
)

const VTOL = aircraft(
  [
    feature(
      ['engine', 'drive'],
      [300, 70],
      [400, 40],
      [{ d: rect(288, 60, 26, 56) }, { d: 'M 236 56 H 366', line: 3 }]
    ),
    feature(
      ['hardpoint'],
      [200, 174],
      [150, 200],
      [{ d: rect(178, 166, 46, 8) }]
    ),
  ],
  [{ d: 'M 244 152 L 344 152 L 364 178 L 264 178 Z' }]
)

const SPACEPLANE = starship(
  'M 40 158 Q 60 132 140 128 L 470 124 L 510 136 L 510 170 L 470 178 L 140 184 Q 60 184 40 158 Z',
  { x: 130, y: 132, w: 370, h: 44 },
  [
    shaped(
      feature(
        ['wings'],
        [380, 214],
        [380, 258],
        [{ d: 'M 200 180 L 462 176 L 494 240 L 360 242 Z' }],
        true
      )
    ),
    shaped(
      feature(
        ['tail'],
        [474, 100],
        [494, 70],
        [{ d: 'M 440 124 L 474 76 L 496 76 L 490 126 Z' }]
      )
    ),
    feature(
      ['cockpit', 'bridge'],
      [84, 142],
      [70, 112],
      [{ d: 'M 54 154 Q 74 134 126 134 L 130 150 Z' }]
    ),
    feature(
      ['drive', 'engine'],
      [516, 154],
      [534, 204],
      engines(506, [146, 162], 20, 12)
    ),
  ]
)

const ESCAPE_POD = starship(
  'M 184 204 L 222 94 Q 280 56 338 94 L 376 204 Z',
  { x: 220, y: 112, w: 120, h: 84 },
  [
    feature(
      ['drive', 'engine'],
      [280, 216],
      [280, 250],
      [{ d: 'M 228 204 L 218 228 H 342 L 332 204 Z' }]
    ),
    feature(
      ['life_support'],
      [376, 150],
      [430, 120],
      [{ d: rect(370, 136, 30, 28) }, { d: 'M 360 150 H 370', line: 3 }]
    ),
    feature(
      ['cockpit', 'bridge'],
      [280, 88],
      [280, 50],
      [{ d: circle(280, 86, 10) }]
    ),
  ]
)

const SPACE_TUG = starship(
  'M 180 196 L 180 116 Q 182 102 198 100 L 384 100 Q 400 102 402 116 L 402 196 Z',
  { x: 196, y: 112, w: 192, h: 78 },
  [
    feature(
      ['cargo_bay'],
      [120, 150],
      [100, 96],
      [
        { d: 'M 182 116 L 100 104 L 92 118 L 182 134 Z' },
        { d: 'M 182 180 L 100 192 L 92 178 L 182 162 Z' },
      ]
    ),
    feature(
      ['cockpit', 'bridge'],
      [214, 116],
      [214, 82],
      [{ d: rect(194, 106, 40, 18) }]
    ),
    feature(
      ['drive', 'engine'],
      [414, 148],
      [450, 200],
      engines(400, [126, 148, 170], 26, 16)
    ),
  ]
)

const MOTHERSHIP = starship(
  'M 30 150 Q 120 92 280 88 Q 440 92 530 150 Q 440 208 280 212 Q 120 208 30 150 Z',
  { x: 130, y: 120, w: 300, h: 60 },
  [
    feature(
      ['bridge', 'cockpit'],
      [280, 80],
      [280, 50],
      [{ d: 'M 240 92 A 40 22 0 0 1 320 92 Z' }]
    ),
    feature(
      ['cargo_bay'],
      [280, 196],
      [280, 240],
      [{ d: rect(214, 186, 132, 16) }]
    ),
    feature(
      ['crew_quarters'],
      [180, 148],
      [120, 236],
      [{ d: windows(140, 104, 8, 36, 20, 7), neutral: true }]
    ),
    feature(
      ['drive', 'engine'],
      [520, 150],
      [540, 196],
      engines(510, [138, 162], 18, 12)
    ),
  ]
)

const BATTLE_MECH: Blueprint = {
  ...walker(null, [
    feature(
      ['armour_plating'],
      [280, 112],
      [140, 60],
      [{ d: 'M 196 80 L 364 80 L 352 150 L 208 150 Z' }]
    ),
    feature(
      ['power_core'],
      [280, 114],
      [280, 190],
      [{ d: circle(280, 114, 14) }]
    ),
  ]),
  body: 'M 196 40 L 364 40 L 404 70 L 412 160 Q 400 184 360 186 L 200 186 Q 160 184 148 160 L 156 70 Z',
}

const BIOSHIP: Blueprint = {
  setting: 'space',
  body: 'M 30 150 Q 80 96 200 100 Q 340 104 470 120 Q 530 128 548 150 Q 530 172 470 180 Q 340 196 200 200 Q 80 204 30 150 Z',
  bodyKeys: ['hull', 'core'],
  hold: { x: 120, y: 124, w: 320, h: 52 },
  features: [
    feature(['core'], [280, 150], [280, 90], [{ d: circle(280, 150, 22) }]),
    feature(
      ['drive'],
      [540, 150],
      [540, 100],
      [{ d: 'M 540 138 Q 562 118 548 96 M 540 162 Q 562 182 548 204', line: 3 }]
    ),
    feature(['sensors'], [64, 150], [40, 116], [{ d: circle(70, 150, 8) }]),
    feature(
      ['ward'],
      [200, 210],
      [200, 254],
      [{ d: ring(280, 150, 220, 70), line: 1.6, neutral: true }]
    ),
  ],
  decor: [
    {
      d: 'M 160 108 Q 170 150 160 192 M 230 102 Q 242 150 230 198 M 380 112 Q 392 150 380 188',
      line: 1.4,
      neutral: true,
    },
  ],
}

const HIGH_RISE: Blueprint = {
  ...building(
    'M 186 232 V 80 H 212 V 52 H 238 V 26 H 322 V 52 H 348 V 80 H 374 V 232 Z',
    { x: 186, y: 80, w: 188, h: 152 },
    'none',
    { x: 196, y: 90, w: 168, h: 136 }
  ),
  decor: [{ d: windows(246, 32, 4, 18, 8, 16), line: 1, neutral: true }],
}

const ARCOLOGY = building(
  'M 60 232 L 112 172 L 156 172 L 196 112 L 236 112 L 266 56 L 294 56 L 324 112 L 364 112 L 404 172 L 448 172 L 500 232 Z',
  { x: 156, y: 112, w: 248, h: 120 },
  'none',
  { x: 170, y: 124, w: 220, h: 100 }
)

const BUNKER: Blueprint = {
  ...building(
    'M 112 232 Q 132 168 280 160 Q 428 168 448 232 Z',
    { x: 150, y: 172, w: 260, h: 60 },
    'none',
    { x: 170, y: 184, w: 220, h: 42 }
  ),
  decor: [{ d: rect(236, 186, 88, 6) }],
}

const FLOATING = building(
  rect(130, 116, 300, 84),
  { x: 130, y: 116, w: 300, h: 84 },
  'flat',
  { x: 140, y: 124, w: 280, h: 68 },
  {
    setting: 'water',
    footing: `${rect(120, 200, 80, 30)} ${rect(240, 200, 80, 30)} ${rect(360, 200, 80, 30)}`,
  }
)

const GEODESIC: Blueprint = {
  ...building(
    'M 140 232 A 140 120 0 0 1 420 232 Z',
    { x: 160, y: 140, w: 240, h: 92 },
    'none',
    { x: 190, y: 160, w: 180, h: 66 }
  ),
  decor: [
    {
      d: 'M 280 112 L 200 172 L 160 232 M 280 112 L 360 172 L 400 232 M 200 172 H 360 M 200 172 L 280 232 L 360 172 M 240 142 H 320',
      line: 1.2,
      neutral: true,
    },
  ],
}

const MODULAR = building(
  'M 140 232 V 160 H 250 V 108 H 198 V 60 H 310 V 106 H 378 V 148 H 464 V 232 Z',
  { x: 140, y: 106, w: 324, h: 126 },
  'none',
  { x: 196, y: 118, w: 230, h: 106 }
)

const GROWN = building(
  'M 150 232 Q 118 160 168 108 Q 220 48 292 58 Q 382 70 402 140 Q 422 200 412 232 Z',
  { x: 170, y: 110, w: 222, h: 122 },
  'none',
  { x: 190, y: 128, w: 186, h: 96 }
)

const CARVED: Blueprint = {
  ...building(
    'M 40 232 L 62 122 L 120 72 L 262 42 L 402 58 L 500 112 L 522 232 Z',
    { x: 150, y: 120, w: 260, h: 112 },
    'none',
    { x: 170, y: 134, w: 220, h: 92 },
    { setting: 'deep' }
  ),
  decor: [
    {
      d: 'M 256 232 V 182 Q 280 160 304 182 V 232 M 196 150 H 224 V 176 H 196 Z M 336 150 H 364 V 176 H 336 Z',
      line: 2,
      neutral: true,
    },
  ],
}

export const BLUEPRINTS = {
  riding: RIDING,
  pack: PACK,
  carrier: CARRIER,
  travois: TRAVOIS,
  sledge: SLEDGE,
  handcart: HANDCART,
  cart: CART,
  minecart: MINECART,
  wagon: WAGON,
  covered: COVERED,
  carriage: CARRIAGE,
  war_wagon: WAR_WAGON,
  chariot: CHARIOT,
  car: CAR,
  truck: TRUCK,
  motorcycle: MOTORCYCLE,
  steam_car: STEAM_CAR,
  armoured: ARMOURED,
  hovercraft: HOVERCRAFT,
  tank: TANK,
  crawler: CRAWLER,
  amphibian: AMPHIBIAN,
  hover_tank: HOVER_TANK,
  locomotive: LOCOMOTIVE,
  rail_car: RAIL_CAR,
  mine_train: MINE_TRAIN,
  walker: WALKER,
  construct: CONSTRUCT,
  flying_construct: FLYING_CONSTRUCT,
  delving_construct: DELVING_CONSTRUCT,
  carrier_construct: CARRIER_CONSTRUCT,
  ram: RAM,
  mantlet: MANTLET,
  siege_tower: SIEGE_TOWER,
  trebuchet: TREBUCHET,
  catapult: CATAPULT,
  ballista: BALLISTA,
  field_gun: FIELD_GUN,
  bombard: BOMBARD,
  mortar: MORTAR,
  rocket_battery: ROCKET_BATTERY,
  raft: RAFT,
  canoe: CANOE,
  rowboat: ROWBOAT,
  barge: BARGE,
  catamaran: CATAMARAN,
  landing_craft: LANDING_CRAFT,
  amphibious_raft: AMPHIBIOUS_RAFT,
  sailboat: SAILBOAT,
  galley: ship([], [250]),
  longship: LONGSHIP,
  trireme: TRIREME,
  cog: ship([], [280]),
  two_master: ship([], [220, 342]),
  three_master: ship([], [190, 290, 390]),
  steamship: STEAMSHIP,
  battleship: BATTLESHIP,
  carrier_ship: CARRIER_SHIP,
  submarine: SUBMARINE,
  bathyscaphe: BATHYSCAPHE,
  diving_bell: DIVING_BELL,
  living_ship: LIVING_SHIP,
  balloon: BALLOON,
  airship: AIRSHIP,
  skyship: SKYSHIP,
  flying_carriage: FLYING_CARRIAGE,
  harvester: HARVESTER,
  glider: GLIDER,
  ornithopter: ORNITHOPTER,
  aeroplane: AEROPLANE,
  jet: JET,
  bomber: BOMBER,
  drone: DRONE,
  rotorcraft: ROTORCRAFT,
  warship_space: WARSHIP_SPACE,
  dreadnought: DREADNOUGHT,
  fighter: FIGHTER,
  shuttle: SHUTTLE,
  lander: LANDER,
  freighter: FREIGHTER,
  mining: MINING,
  corvette: CORVETTE,
  ark: ARK,
  solar_sailer: SOLAR_SAILER,
  skimmer: SKIMMER,
  planar: PLANAR,
  burrower: BURROWER,
  hall: plain(118, 324, 108, 'gable'),
  longhouse: plain(70, 420, 140, 'gable'),
  flat: plain(118, 324, 108, 'flat'),
  keep: plain(170, 220, 70, 'flat'),
  tower: plain(236, 88, 40, 'flat'),
  dome: plain(130, 300, 130, 'flat'),
  wall: plain(40, 480, 140, 'flat'),
  courtyard: building(
    'M 80 232 V 120 H 190 V 170 H 370 V 120 H 480 V 232 Z',
    { x: 80, y: 120, w: 400, h: 112 },
    'wings',
    { x: 86, y: 176, w: 388, h: 50 },
    { crown: 170, spireAt: 280 }
  ),
  arcade: building(ARCADE_BODY, { x: 90, y: 120, w: 380, h: 112 }, 'flat', {
    x: 96,
    y: 126,
    w: 368,
    h: 58,
  }),
  terrace: building(
    'M 60 232 V 196 H 170 V 160 H 280 V 124 H 500 V 232 Z',
    { x: 280, y: 124, w: 220, h: 108 },
    'none',
    { x: 286, y: 130, w: 208, h: 96 }
  ),
  platform: building(
    rect(80, 150, 400, 46),
    { x: 80, y: 150, w: 400, h: 46 },
    'flat',
    { x: 86, y: 154, w: 388, h: 38 }
  ),
  spire: building(
    'M 236 232 L 252 96 L 308 96 L 324 232 Z',
    { x: 252, y: 96, w: 56, h: 136 },
    'none',
    { x: 254, y: 120, w: 52, h: 106 },
    { spireAt: 280 }
  ),
  stepped: building(
    'M 100 232 V 196 H 140 V 160 H 180 V 124 H 220 V 92 H 340 V 124 H 380 V 160 H 420 V 196 H 460 V 232 Z',
    { x: 220, y: 92, w: 120, h: 140 },
    'none',
    { x: 146, y: 166, w: 268, h: 60 }
  ),
  pyramid: building(
    'M 90 232 L 280 46 L 470 232 Z',
    { x: 250, y: 76, w: 60, h: 156 },
    'none',
    { x: 196, y: 160, w: 168, h: 66 }
  ),
  tent: building(
    'M 100 232 L 128 150 Q 200 110 280 60 Q 360 110 432 150 L 460 232 Z',
    { x: 128, y: 150, w: 304, h: 82 },
    'none',
    { x: 140, y: 150, w: 280, h: 76 }
  ),
  mound: building(
    'M 100 232 Q 110 120 280 110 Q 450 120 460 232 Z',
    { x: 150, y: 120, w: 260, h: 112 },
    'none',
    { x: 150, y: 140, w: 260, h: 86 }
  ),
  amphitheatre: building(
    'M 70 232 L 96 120 Q 280 92 464 120 L 490 232 Z',
    { x: 96, y: 112, w: 368, h: 120 },
    'none',
    { x: 110, y: 160, w: 340, h: 66 },
    {
      extra: [
        feature(
          ['seating'],
          [280, 132],
          [400, 100],
          [
            { d: 'M 104 130 Q 280 104 456 130 L 450 154 Q 280 130 110 154 Z' },
            { d: 'M 108 142 Q 280 117 452 142', line: 1.2, neutral: true },
          ]
        ),
        feature(
          ['stage'],
          [280, 222],
          [280, 252],
          [{ d: 'M 220 232 L 230 214 H 330 L 340 232 Z' }]
        ),
      ],
    }
  ),
  bridge: building(
    'M 30 120 H 530 V 150 H 30 Z',
    { x: 30, y: 120, w: 500, h: 30 },
    'flat',
    { x: 36, y: 123, w: 488, h: 24 },
    {
      setting: 'water',
      footing: `${rect(10, 120, 40, 128)} ${rect(510, 120, 40, 128)}`,
    }
  ),
  tunnel: building(
    'M 160 232 V 170 Q 280 90 400 170 V 232 Z',
    { x: 160, y: 130, w: 240, h: 102 },
    'none',
    { x: 200, y: 150, w: 160, h: 76 },
    { setting: 'deep' }
  ),
  ring: RING,
  bicycle: BICYCLE,
  rickshaw: RICKSHAW,
  palanquin: PALANQUIN,
  tram: TRAM,
  maglev: MAGLEV,
  bus: BUS,
  tractor: TRACTOR,
  apc: APC,
  self_propelled_gun: SELF_PROPELLED_GUN,
  missile_carrier: MISSILE_CARRIER,
  motorboat: MOTORBOAT,
  hydrofoil: HYDROFOIL,
  container_ship: CONTAINER_SHIP,
  tanker: TANKER,
  destroyer: DESTROYER,
  cruiser: CRUISER,
  icebreaker: ICEBREAKER,
  vtol: VTOL,
  spaceplane: SPACEPLANE,
  escape_pod: ESCAPE_POD,
  space_tug: SPACE_TUG,
  mothership: MOTHERSHIP,
  battle_mech: BATTLE_MECH,
  bioship: BIOSHIP,
  high_rise: HIGH_RISE,
  arcology: ARCOLOGY,
  bunker: BUNKER,
  floating: FLOATING,
  geodesic: GEODESIC,
  modular: MODULAR,
  grown: GROWN,
  carved: CARVED,
} as const satisfies Record<string, Blueprint>

export type Silhouette = keyof typeof BLUEPRINTS

const FRAME_SHAPES: Record<VehicleFrame, Silhouette> = {
  riding_mount: 'riding',
  pack_mount: 'pack',
  beast_carrier: 'carrier',
  travois: 'travois',
  sledge: 'sledge',
  handcart: 'handcart',
  cart: 'cart',
  tunnel_cart: 'minecart',
  wagon: 'wagon',
  covered_wagon: 'covered',
  carriage: 'carriage',
  war_wagon: 'war_wagon',
  chariot: 'chariot',
  rail_car: 'rail_car',
  locomotive: 'locomotive',
  mine_train: 'mine_train',
  steam_carriage: 'steam_car',
  motor_car: 'car',
  motor_truck: 'truck',
  motorcycle: 'motorcycle',
  armoured_car: 'armoured',
  hovercraft: 'hovercraft',
  tank: 'tank',
  crawler: 'crawler',
  amphibious_carrier: 'amphibian',
  deep_crawler: 'crawler',
  hover_tank: 'hover_tank',
  walker: 'walker',
  construct_walker: 'construct',
  construct_carrier: 'carrier_construct',
  flying_construct: 'flying_construct',
  delving_construct: 'delving_construct',
  battering_ram: 'ram',
  mantlet: 'mantlet',
  siege_tower: 'siege_tower',
  catapult: 'catapult',
  trebuchet: 'trebuchet',
  ballista: 'ballista',
  bombard: 'bombard',
  field_gun: 'field_gun',
  mortar: 'mortar',
  rocket_battery: 'rocket_battery',
  raft: 'raft',
  canoe: 'canoe',
  rowboat: 'rowboat',
  boat: 'rowboat',
  river_barge: 'barge',
  sailboat: 'sailboat',
  fire_ship: 'sailboat',
  landing_craft: 'landing_craft',
  amphibious_raft: 'amphibious_raft',
  catamaran: 'catamaran',
  galley: 'galley',
  longship: 'longship',
  trireme: 'trireme',
  cog: 'cog',
  coastal_trader: 'two_master',
  carrack: 'two_master',
  galleon: 'three_master',
  frigate: 'three_master',
  warship: 'three_master',
  ship_of_the_line: 'three_master',
  steamship: 'steamship',
  ironclad: 'steamship',
  battleship: 'battleship',
  fleet_carrier: 'carrier_ship',
  submarine: 'submarine',
  attack_submarine: 'submarine',
  deep_submersible: 'bathyscaphe',
  diving_bell: 'diving_bell',
  living_ship: 'living_ship',
  balloon: 'balloon',
  airship: 'airship',
  sky_sailer: 'skyship',
  skyship: 'skyship',
  flying_carriage: 'flying_carriage',
  aerostat: 'airship',
  gas_harvester: 'harvester',
  glider: 'glider',
  ornithopter: 'ornithopter',
  aeroplane: 'aeroplane',
  flying_car: 'car',
  jet_fighter: 'jet',
  bomber: 'bomber',
  drone: 'drone',
  rotorcraft: 'rotorcraft',
  orbital_lander: 'lander',
  shuttle: 'shuttle',
  solar_sailer: 'solar_sailer',
  starship: 'warship_space',
  generation_ship: 'ark',
  void_ark: 'ark',
  cloud_skimmer: 'skimmer',
  planar_vessel: 'planar',
  deep_diver: 'skimmer',
  rift_skiff: 'fighter',
  planar_ark: 'ark',
  divine_vessel: 'planar',
  space_fighter: 'fighter',
  freighter: 'freighter',
  mining_barge: 'mining',
  corvette: 'corvette',
  dreadnought: 'dreadnought',
  burrower: 'burrower',
  bicycle: 'bicycle',
  rickshaw: 'rickshaw',
  palanquin: 'palanquin',
  tram: 'tram',
  maglev: 'maglev',
  bus: 'bus',
  tractor: 'tractor',
  apc: 'apc',
  self_propelled_gun: 'self_propelled_gun',
  missile_carrier: 'missile_carrier',
  motorboat: 'motorboat',
  hydrofoil: 'hydrofoil',
  container_ship: 'container_ship',
  tanker: 'tanker',
  destroyer: 'destroyer',
  cruiser: 'cruiser',
  icebreaker: 'icebreaker',
  vtol: 'vtol',
  spaceplane: 'spaceplane',
  escape_pod: 'escape_pod',
  space_tug: 'space_tug',
  mothership: 'mothership',
  battle_mech: 'battle_mech',
  bioship: 'bioship',
}

const FAMILY_SHAPES: Record<VehicleFamily, Silhouette> = {
  mount: 'riding',
  cart: 'cart',
  wagon: 'wagon',
  chariot: 'chariot',
  rail: 'locomotive',
  motor: 'car',
  tracked: 'tank',
  walker: 'walker',
  construct: 'construct',
  ram: 'ram',
  tower: 'siege_tower',
  thrower: 'trebuchet',
  gun: 'field_gun',
  boat: 'rowboat',
  galley: 'galley',
  sailing_ship: 'two_master',
  steam_ship: 'steamship',
  submarine: 'submarine',
  living: 'living_ship',
  balloon: 'balloon',
  airship: 'airship',
  aircraft: 'aeroplane',
  rotorcraft: 'rotorcraft',
  spacecraft: 'warship_space',
  burrower: 'burrower',
}

const FORM_SHAPES: Record<BuildingForm, Silhouette> = {
  hall: 'hall',
  longhouse: 'longhouse',
  tower: 'tower',
  keep: 'keep',
  dome: 'dome',
  spire: 'spire',
  stepped: 'stepped',
  pyramid: 'pyramid',
  courtyard: 'courtyard',
  ring: 'amphitheatre',
  tent: 'tent',
  mound: 'mound',
  arcade: 'arcade',
  terrace: 'terrace',
  platform: 'platform',
  bridge_form: 'bridge',
  wall_line: 'wall',
  tunnel_form: 'tunnel',
  orbital: 'ring',
  high_rise: 'high_rise',
  arcology: 'arcology',
  bunker: 'bunker',
  floating: 'floating',
  geodesic: 'geodesic',
  modular: 'modular',
  grown: 'grown',
  carved: 'carved',
}

export function vehicleShape(
  frame: VehicleFrame | null | undefined,
  family: VehicleFamily | null | undefined
): Silhouette {
  if (frame) return FRAME_SHAPES[frame]
  return family ? FAMILY_SHAPES[family] : 'cart'
}

export function buildingShape(
  form: BuildingForm | null | undefined
): Silhouette {
  return form ? FORM_SHAPES[form] : 'flat'
}
