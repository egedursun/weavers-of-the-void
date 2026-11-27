import { existsSync, mkdirSync, readdirSync, statSync, copyFileSync } from 'node:fs'
import { dirname, join, extname } from 'node:path'
import { fileURLToPath } from 'node:url'
import sharp from 'sharp'

const here = dirname(fileURLToPath(import.meta.url))
const root = join(here, '..', '..')
const site = join(here, '..')
const art = join(root, 'common', 'assets', 'images')
const fronts = join(art, 'dlc')
const backs = join(fronts, 'cover-back')
const publicDir = join(site, 'public')
const screensIn = join(site, 'screens')

const COVER_WIDTH = 480
const BACK_WIDTH = 960
const SCREEN_WIDTH = 1600
const QUALITY = 80
const CARD_WIDTH = 1200
const CARD_HEIGHT = 630
const CARD_COVER_HEIGHT = 560
const CARD_GAP = 28
const CARD_RULE = 6
const CARD_QUALITY = 84

function numbered(folder, pattern) {
  const found = new Map()
  for (const name of readdirSync(folder)) {
    const match = pattern.exec(name)
    if (match) found.set(Number(match[1]), join(folder, name))
  }
  return found
}

async function webp(source, target, width) {
  if (existsSync(target) && statSync(target).mtimeMs >= statSync(source).mtimeMs) return
  mkdirSync(dirname(target), { recursive: true })
  await sharp(source).resize({ width, withoutEnlargement: true }).webp({ quality: QUALITY }).toFile(target)
}

const frontFiles = numbered(fronts, /^dlc-(\d+)-/)
const backFiles = numbered(backs, /^dlc-(\d+)-cover-back/)
async function cover(source, target) {
  if (existsSync(target) && statSync(target).mtimeMs >= statSync(source).mtimeMs) return
  mkdirSync(dirname(target), { recursive: true })
  const width = COVER_WIDTH
  const height = Math.round((COVER_WIDTH * 3) / 2)
  await sharp(source).resize(width, height, { fit: 'fill' }).webp({ quality: QUALITY }).toFile(target)
}

async function shareCard(front, back, target) {
  const newest = Math.max(statSync(front).mtimeMs, statSync(back).mtimeMs)
  if (existsSync(target) && statSync(target).mtimeMs >= newest) return
  mkdirSync(dirname(target), { recursive: true })
  const coverWidth = Math.round((CARD_COVER_HEIGHT * 1696) / 2528)
  const top = Math.round((CARD_HEIGHT - CARD_RULE - CARD_COVER_HEIGHT) / 2)
  const left = Math.round((CARD_WIDTH - coverWidth * 2 - CARD_GAP) / 2)
  const backdrop = await sharp(front)
    .resize(CARD_WIDTH, CARD_HEIGHT, { fit: 'cover' })
    .blur(36)
    .modulate({ brightness: 0.42, saturation: 1.15 })
    .toBuffer()
  const face = (source) => sharp(source).resize(coverWidth, CARD_COVER_HEIGHT, { fit: 'fill' }).toBuffer()
  const shade = Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${CARD_WIDTH}" height="${CARD_HEIGHT}">` +
      `<defs><filter id="s" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="18"/></filter>` +
      `<linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#a5741f"/><stop offset="0.5" stop-color="#fbeaa8"/><stop offset="1" stop-color="#a5741f"/></linearGradient></defs>` +
      `<rect x="${left - 6}" y="${top + 14}" width="${coverWidth * 2 + CARD_GAP + 12}" height="${CARD_COVER_HEIGHT}" fill="#05020c" opacity="0.85" filter="url(#s)"/>` +
      `<rect x="0" y="${CARD_HEIGHT - CARD_RULE}" width="${CARD_WIDTH}" height="${CARD_RULE}" fill="url(#g)"/></svg>`,
  )
  await sharp(backdrop)
    .composite([
      { input: shade, left: 0, top: 0 },
      { input: await face(front), left, top },
      { input: await face(back), left: left + coverWidth + CARD_GAP, top },
    ])
    .jpeg({ quality: CARD_QUALITY, mozjpeg: true })
    .toFile(target)
}

for (let number = 0; number <= 99; number += 1) {
  if (!frontFiles.has(number) || !backFiles.has(number)) throw new Error(`expansion ${number} has no front or back cover`)
  await cover(frontFiles.get(number), join(publicDir, 'covers', `${number}.webp`))
  await webp(backFiles.get(number), join(publicDir, 'backs', `${number}.webp`), BACK_WIDTH)
  await shareCard(frontFiles.get(number), backFiles.get(number), join(publicDir, 'social', 'expansions', `${number}.jpg`))
}

const cards = join(site, 'art', 'social')
mkdirSync(join(publicDir, 'social'), { recursive: true })
for (const name of readdirSync(cards)) {
  if (extname(name) === '.jpg') copyFileSync(join(cards, name), join(publicDir, 'social', name))
}

await webp(join(art, 'collectors-edition.jpg'), join(publicDir, 'art', 'collectors-edition.webp'), 1200)

const minds = join(site, 'art')
mkdirSync(join(publicDir, 'art', 'minds'), { recursive: true })
for (const name of readdirSync(minds)) {
  if ((name.startsWith('minds-') || name.startsWith('audience-')) && extname(name) === '.jpg') await webp(join(minds, name), join(publicDir, 'art', 'minds', name.replace('.jpg', '.webp')), 900)
}

const steps = join(site, 'art', 'steps')
for (const name of readdirSync(steps)) {
  if (extname(name) === '.jpg') await webp(join(steps, name), join(publicDir, 'art', 'steps', name.replace('.jpg', '.webp')), 900)
}

const brand = join(root, 'frontend', 'public', 'brand')
mkdirSync(join(publicDir, 'brand'), { recursive: true })
for (const name of ['logo-512.webp', 'logo-256.webp', 'logo-1024.webp', 'logo-192.png', 'logo-512.png', 'apple-touch-icon.png', 'favicon.ico']) {
  copyFileSync(join(brand, name), join(publicDir, 'brand', name))
}

const ornate = join(root, 'frontend', 'src', 'assets', 'ornate')
const ornateOut = join(site, 'src', 'assets', 'ornate')
mkdirSync(ornateOut, { recursive: true })
for (const name of readdirSync(ornate)) {
  if (extname(name) === '.webp') copyFileSync(join(ornate, name), join(ornateOut, name))
}

const starOut = join(ornateOut, 'star.webp')
if (!existsSync(starOut)) {
  const STAR_SIZE = 240
  const trimmed = await sharp(join(ornate, 'divider.webp'))
    .extract({ left: 418, top: 0, width: 114, height: 114 })
    .resize(STAR_SIZE, STAR_SIZE, { fit: 'fill', kernel: 'lanczos3' })
    .png()
    .toBuffer()
  const half = STAR_SIZE / 2
  const upperLeft = await sharp(trimmed).extract({ left: 0, top: 0, width: half, height: half }).png().toBuffer()
  const upperRight = await sharp(trimmed).extract({ left: half, top: 0, width: half, height: half }).png().toBuffer()
  const lowerRight = await sharp(upperLeft).rotate(180).png().toBuffer()
  const lowerLeft = await sharp(upperRight).rotate(180).png().toBuffer()
  await sharp({ create: { width: STAR_SIZE, height: STAR_SIZE, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([
      { input: upperLeft, left: 0, top: 0 },
      { input: upperRight, left: half, top: 0 },
      { input: lowerLeft, left: 0, top: half },
      { input: lowerRight, left: half, top: half },
    ])
    .webp({ quality: 92 })
    .toFile(starOut)
}

if (existsSync(screensIn)) {
  for (const name of readdirSync(screensIn)) {
    if (['.png', '.jpg', '.jpeg', '.webp'].includes(extname(name).toLowerCase())) {
      await webp(join(screensIn, name), join(publicDir, 'screens', `${name.replace(/\.[^.]+$/, '')}.webp`), SCREEN_WIDTH)
    }
  }
}

console.log('images: 100 covers, 100 backs, 100 share cards, the collector box, the logo, ornaments and screens ready')
