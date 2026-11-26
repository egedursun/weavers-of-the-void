import { expect, test } from '@playwright/test'
import { captureWrites, replyWith, writesTo } from './capture'
import { mockApi } from './mockApi'

test.describe('atlas', () => {
  test('search narrows the tree and lands in the address', async ({ page }) => {
    await mockApi(page)
    await page.goto('/atlas')
    await expect(page.getByText('11 records match')).toBeVisible()
    await page.getByRole('searchbox', { name: 'Search the atlas' }).fill('glass')
    await expect(page).toHaveURL(/q=glass/)
    await expect(page.getByText(/records? match/)).not.toHaveText('11 records match')
    await expect(page.getByRole('tree', { name: 'Atlas tree' }).getByText('Velmora-under-the-Glass')).toBeVisible()
  })

  test('the kind filter deep link narrows the list and can be cleared', async ({ page }) => {
    await mockApi(page)
    await page.goto('/atlas?view=list&type=language')
    await expect(page.getByText('Old Brine Tongue').first()).toBeVisible()
    await expect(page.getByText('2 records match')).toBeVisible()
    await expect(page.getByText('Velmora-under-the-Glass')).toHaveCount(0)
    await page.getByRole('combobox', { name: 'Kind' }).click()
    await page.getByRole('option', { name: 'Every kind' }).click()
    await expect(page).not.toHaveURL(/type=/)
  })

  test('the favourites filter keeps only favourite records', async ({ page }) => {
    await mockApi(page)
    await page.goto('/atlas?view=list')
    await page.getByRole('button', { name: 'Favourites only' }).click()
    await expect(page).toHaveURL(/favorites=true|favourites=true|fav/)
    await expect(page.getByText('1 record matches').or(page.getByText('1 records match'))).toBeVisible()
  })

  test('the tree opens and closes branches and remembers them after a reload', async ({ page }) => {
    await mockApi(page)
    await page.goto('/atlas')
    const tree = page.getByRole('tree', { name: 'Atlas tree' })
    await page.getByRole('button', { name: 'Close Pantheon' }).click()
    await expect(tree.getByText('Aeron')).toHaveCount(0)
    await page.reload()
    await expect(tree.getByText('Aeron')).toHaveCount(0)
    await page.getByRole('button', { name: 'Open Pantheon' }).click()
    await expect(tree.getByText('Aeron')).toBeVisible()
  })

  test('open all and close all expand and collapse every branch', async ({ page }) => {
    await mockApi(page)
    await page.goto('/atlas')
    await page.getByRole('button', { name: 'Close all' }).click()
    const items = page.getByRole('treeitem')
    const closed = await items.count()
    await page.getByRole('button', { name: 'Open all' }).click()
    expect(await items.count()).toBeGreaterThan(closed)
  })

  test('the keyboard moves through the tree, expands and collapses, and opens the record', async ({ page }) => {
    await mockApi(page)
    await page.goto('/atlas')
    const tree = page.getByRole('tree', { name: 'Atlas tree' })
    const first = tree.getByRole('treeitem').first()
    await first.focus()
    await page.keyboard.press('ArrowLeft')
    await expect(first).toHaveAttribute('aria-expanded', 'false')
    await page.keyboard.press('ArrowRight')
    await expect(first).toHaveAttribute('aria-expanded', 'true')
    await page.keyboard.press('ArrowDown')
    const second = tree.getByRole('treeitem').nth(1)
    await expect(second).toBeFocused()
    await page.keyboard.press('ArrowUp')
    await expect(first).toBeFocused()
    await page.keyboard.press('ArrowDown')
    await page.keyboard.press(' ')
    await expect(page).toHaveURL(/select=/)
  })

  test('selecting a record shows its full page, and nothing selected shows the empty state', async ({ page }) => {
    await mockApi(page)
    await page.goto('/atlas')
    await expect(page.getByText('Choose a record')).toBeVisible()
    await page.goto('/atlas?select=entity:43')
    await expect(page.getByRole('heading', { name: 'Velmora-under-the-Glass' }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Hand of God', exact: true }).first()).toBeVisible()
    await page.goto('/atlas?select=entity:9999')
    await expect(page.getByText(/no longer|Nothing here|not found|does not exist/i).first()).toBeVisible()
  })

  test('a god record in the tree is read from the cosmos data', async ({ page }) => {
    await mockApi(page)
    await page.goto('/atlas?select=foreign-god:31')
    await expect(page.getByRole('button', { name: 'Open the page' })).toBeVisible()
  })
})

test.describe('chronicle', () => {
  test('lists every closed epoch with counts, a jump strip and the ongoing epoch', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle')
    await expect(page.getByText('Ongoing', { exact: true })).toBeVisible()
    for (const epoch of ['E7', 'E6', 'E5', 'E1']) {
      await expect(page.getByRole('button', { name: epoch, exact: true })).toBeVisible()
    }
    await expect(page.getByText(/records shown · \d+ of 7 epochs read/)).toBeVisible()
    await expect(page.getByText('The Age of Brine and Whispering Crystal').first()).toBeVisible()
  })

  test('the jump strip scrolls to an epoch', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle')
    await page.getByRole('button', { name: 'E1', exact: true }).click()
    await expect(page.locator('[id^="epoch-"]').last()).toBeInViewport()
  })

  test('the header offers the codex download and the book', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle')
    const codex = page.getByRole('link', { name: 'Codex (Markdown)' })
    await expect(codex).toHaveAttribute('download', '')
    await expect(codex).toHaveAttribute('href', /\/api\//)
    await expect(page.getByRole('link', { name: 'The book' })).toHaveAttribute('target', '_blank')
  })

  test('opening every epoch loads its entries with kind labels and linked names', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle')
    await page.getByRole('button', { name: 'Open every epoch' }).click()
    await expect(page).toHaveURL(/all=true/)
    await expect(page.getByText(/Ithren raised/)).toBeVisible()
    await expect(page.getByRole('link', { name: 'Velmora-under-the-Glass' }).first()).toBeVisible()
    await expect(page.getByText('Birth', { exact: true }).first()).toBeVisible()
  })

  test('the raw engine log is hidden until its kind is chosen', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle?all=true')
    await expect(page.getByText('tick 7: prosperity +2')).toHaveCount(0)
    await page.getByRole('button', { name: 'Kinds' }).click()
    await page.getByRole('checkbox', { name: /Engine/i }).click()
    await expect(page).toHaveURL(/kinds=/)
    await expect(page.getByText('tick 7: prosperity +2')).toBeVisible()
  })

  test('the world filter keeps only the lines of one world and can be cleared', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle?all=true')
    await expect(page.getByText(/Ash Choir sang a note/).first()).toBeVisible()
    await page.getByRole('combobox', { name: 'World', exact: true }).click()
    await page.getByRole('option', { name: 'Saltreach' }).click()
    await expect(page).toHaveURL(/world=3/)
    await expect(page.getByText('On the Hollow Moon of Ashes the Ash Choir sang a note nobody could hear.')).toHaveCount(0)
    await page.getByRole('button', { name: 'Clear', exact: true }).click()
    await expect(page).not.toHaveURL(/world=/)
  })

  test('the search finds lines across epochs grouped by epoch with a way to go there', async ({ page }) => {
    await mockApi(page)
    await replyWith(page, 'GET', /\/api\/search/, [
      { category: 'chronicle', id: 1, title: 'Creation', subtitle: null, snippet: 'Ithren raised Velmora from the glass', epoch: 1 },
    ])
    await page.goto('/chronicle')
    await page.getByRole('searchbox', { name: 'Search the chronicle' }).fill('glass')
    await expect(page).toHaveURL(/q=glass/)
    await expect(page.getByRole('button', { name: /Go to epoch/ }).first()).toBeVisible()
  })

  test('the cosmic chronicle grid shows events per world and quiet worlds', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle')
    const grid = page.getByRole('table').first()
    await expect(page.getByText('The cosmic chronicle')).toBeVisible()
    await expect(page.getByText('quiet').first()).toBeVisible()
    await expect(page.getByText('3 events')).toBeVisible()
    await expect(grid).toBeVisible()
  })

  test('an epoch article shows the chronicler and a people retelling in narrator tabs', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle')
    await expect(page.getByRole('tab', { name: 'The chronicler' }).first()).toBeVisible()
    await expect(page.getByText('Maelis of the Lantern').first()).toBeVisible()
    await page.getByRole('tab', { name: 'The Brine-Singers of the Ninth Shore' }).first().click()
    await expect(page.getByText(/It was we who held the wells/)).toBeVisible()
  })

  test('comparing two epochs shows each metric with its difference', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle')
    const table = page.getByRole('table').filter({ hasText: 'Measure' })
    await expect(table.getByRole('row', { name: /Population\s+3,240\s+3,580\s+\+340/ })).toBeVisible()
    await expect(table.getByRole('row', { name: /Wars\s+0\s+1\s+\+1/ })).toBeVisible()
    await expect(table.getByRole('row', { name: /Languages\s+4\s+4\s+±0/ })).toBeVisible()
    await page.getByRole('button', { name: 'Swap the epochs' }).click()
    await expect(table.getByRole('row', { name: /Population\s+3,580\s+3,240\s+-340/ })).toBeVisible()
  })

  test('stories are split into open and closed threads', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle')
    await expect(page.getByText(/Open stories/).or(page.getByRole('button', { name: /Open a story/ })).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /Closed stories · 1/ })).toBeVisible()
  })

  test('the traces of the epochs chart population, disciples, words and records', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle')
    await expect(page.getByText('Traces of the epochs')).toBeVisible()
    for (const title of ['Population', 'Disciples', 'Words in the lexicons', 'Records in canon']) {
      await expect(page.getByText(title, { exact: true }).first()).toBeVisible()
    }
  })

  test('a deep link to one line highlights nothing but still opens its epoch', async ({ page }) => {
    await mockApi(page)
    await page.goto('/chronicle?epoch=5&all=true')
    await expect(page.getByText(/War of the Glass Wells began/).first()).toBeVisible()
  })
})

test.describe('languages', () => {
  test('the dictionary lists languages with word counts, speakers and the lexicon', async ({ page }) => {
    await mockApi(page)
    await page.goto('/languages')
    await expect(page.getByText('2 languages')).toBeVisible()
    await expect(page.getByText('The tongue of the first tide, thick with words for salt and grief.')).toBeVisible()
    await expect(page.getByText('Script: Notch')).toBeVisible()
    await expect(page.getByText('Spoken by')).toBeVisible()
    await expect(page.getByRole('cell', { name: 'velm', exact: true })).toBeVisible()
    await expect(page.getByText('Names born in it')).toBeVisible()
  })

  test('choosing another language switches the lexicon and the address', async ({ page }) => {
    await mockApi(page)
    await page.goto('/languages')
    await page.getByRole('navigation', { name: 'Languages' }).getByRole('button', { name: /Low Vel/ }).click()
    await expect(page).toHaveURL(/language=47/)
    await expect(page.getByText('A harbour dialect.')).toBeVisible()
  })

  test('the word search runs across every language', async ({ page }) => {
    await mockApi(page)
    await page.goto('/languages')
    await page.getByRole('searchbox', { name: 'Search the lexicons' }).fill('glass')
    await expect(page).toHaveURL(/q=glass/)
    await expect(page.getByText('glass that remembers').first()).toBeVisible()
  })

  test('the language tree selection shows a language with its cognates', async ({ page }) => {
    await mockApi(page)
    await page.goto('/languages?view=tree')
    await expect(page.getByRole('tab', { name: 'Language tree' })).toHaveAttribute('data-state', 'active')
    await page.getByRole('button', { name: /Low Vel/ }).first().click()
    await expect(page).toHaveURL(/language=47/)
    await expect(page.getByText('velm')).toBeVisible()
    await expect(page.getByText(/velm \(glass that remembers/)).toBeVisible()
    await page.getByRole('button', { name: 'Open its dictionary' }).click()
    await expect(page.getByRole('tab', { name: 'Dictionary' })).toHaveAttribute('data-state', 'active')
  })

  test('the knowledge tree shows level, branch, knowers and the inventor', async ({ page }) => {
    await mockApi(page)
    await page.goto('/languages?view=knowledge')
    await expect(page.getByText('Salt Reading').first()).toBeVisible()
    await expect(page.getByText(/Writing/i).first()).toBeVisible()
    await expect(page.getByText(/Level 2|level 2/).first()).toBeVisible()
    await expect(page.getByText('Velmora-under-the-Glass').first()).toBeVisible()
  })

  test('translation needs text, posts it and shows the result with the new words', async ({ page }) => {
    await mockApi(page)
    await replyWith(page, 'POST', /\/api\/languages\/46\/translate/, {
      translation: 'velm ora sang',
      pronunciation: 'VELM or-a',
      word_by_word: [{ word: 'velm', meaning: 'glass' }],
      new_words: [{ word: 'ora', meaning: 'song', kind: 'noun', origin: 'the first song' }],
      note: null,
    })
    const writes = await captureWrites(page)
    await page.goto('/languages')
    const translate = page.getByRole('button', { name: 'Translate' })
    await expect(translate).toHaveAttribute('aria-disabled', 'true')
    await page.getByLabel(/Text to translate into/).fill('The glass remembers.')
    await translate.click()
    await expect(page.getByText('Translated into Old Brine Tongue')).toBeVisible()
    await expect(page.getByText('velm ora sang').first()).toBeVisible()
    expect(writesTo(writes, 'POST', /\/translate$/)[0]?.body).toEqual({ text: 'The glass remembers.' })
  })

  test('the world filter limits the languages to those of one world', async ({ page }) => {
    await mockApi(page)
    await page.goto('/languages')
    await page.getByRole('combobox', { name: 'World', exact: true }).click()
    await page.getByRole('option').nth(1).click()
    await expect(page.getByText(/languages?$/).first()).toBeVisible()
  })
})

test.describe('gallery and images', () => {
  test('the gallery wall shows images newest first with kind chips and a lightbox', async ({ page }) => {
    await mockApi(page)
    await page.goto('/gallery')
    await expect(page.getByRole('radio', { name: /All · 2/ })).toBeVisible()
    await expect(page.getByRole('radio', { name: /Entity · 2/ })).toBeVisible()
    await page.getByRole('link', { name: /Crystal Ossuary of Vel/ }).first().click()
    await expect(page.getByRole('dialog').last()).toBeVisible()
  })

  test('the missing images list shows importance, a prompt copy and an upload drop zone', async ({ page }) => {
    await mockApi(page)
    await page.goto('/gallery')
    await expect(page.getByText('Important records without an image')).toBeVisible()
    await expect(page.getByText('Importance 5').first()).toBeVisible()
    await expect(page.getByText('Drop images here, paste them, or choose files. PNG, JPEG or WEBP.').first()).toBeVisible()
    await expect(page.getByLabel('Upload for Velmora-under-the-Glass')).toBeAttached()
  })

  test('generating is off with the reason while no image model is set', async ({ page }) => {
    await mockApi(page)
    await page.goto('/gallery')
    const button = page.getByRole('button', { name: 'Generate image' }).first()
    await expect(button).toHaveAttribute('aria-disabled', 'true')
    await expect(page.getByText('No image model')).toBeVisible()
    await expect(page.getByText('Image generation is off: no image model is set. Add one under Team and workspace, Models.').first()).toBeVisible()
  })

  test('uploading a file posts it to the record', async ({ page }) => {
    await mockApi(page)
    const writes = await captureWrites(page)
    await page.goto('/gallery')
    await page.getByLabel('Upload for Velmora-under-the-Glass').setInputFiles({
      name: 'salt.png',
      mimeType: 'image/png',
      buffer: Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        'base64'
      ),
    })
    await expect.poll(() => writes.filter((write) => /\/api\/(entities\/43\/)?images/.test(write.path)).length).toBeGreaterThan(0)
  })

  test('the bulk image panel shows the counts, worker log and stays off without a worker', async ({ page }) => {
    await mockApi(page)
    await page.goto('/gallery')
    await expect(page.getByText('Missing images', { exact: true })).toBeVisible()
    await expect(page.getByText('Without a prompt')).toBeVisible()
    await expect(page.getByText('Waiting in queue')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Generate 7 missing images' })).toHaveAttribute('aria-disabled', 'true')
    await expect(page.getByText('The worker is not configured; set IMAGE_WORKER_URL to paint.')).toBeVisible()
  })

  test('the upload for the god or a world button opens the creator images', async ({ page }) => {
    await mockApi(page)
    await page.goto('/gallery')
    await page.getByRole('button', { name: 'Upload for the god or a world' }).click()
    await expect(page).toHaveURL(/entry=creator/)
  })

  test('the record gallery marks the cover and the lightbox manages the image', async ({ page }) => {
    await mockApi(page)
    const writes = await captureWrites(page)
    await page.goto('/chronicle?entry=entity:42')
    const entryWindow = page.getByRole('dialog').last()
    await expect(entryWindow.getByText('Cover').first()).toBeVisible()
    await entryWindow.getByRole('link', { name: /singing ossuary/ }).first().click()
    const lightbox = page.getByRole('dialog').last()
    await expect(lightbox.getByLabel('Caption')).toHaveValue('The singing ossuary at the hour of the white tide')
    await lightbox.getByRole('button', { name: 'Next image' }).dispatchEvent('click')
    await lightbox.getByRole('button', { name: /Make cover/ }).dispatchEvent('click')
    await expect.poll(() => writes.filter((write) => /\/api\/images\/2/.test(write.path)).length).toBeGreaterThan(0)
    await lightbox.getByRole('button', { name: /Delete/ }).dispatchEvent('click')
    await page.getByRole('alertdialog').getByRole('button', { name: 'Delete', exact: true }).click()
    await expect.poll(() => writesTo(writes, 'DELETE', /\/api\/images\/2$/).length).toBe(1)
  })

  test('the prompt box shows the prompt, copies it and saves an edit', async ({ page }) => {
    await mockApi(page)
    const writes = await captureWrites(page)
    await page.goto('/chronicle?entry=entity:42')
    const entryWindow = page.getByRole('dialog').last()
    await expect(entryWindow.getByRole('button', { name: 'Copy' })).toBeVisible()
    await entryWindow.getByRole('button', { name: 'Edit', exact: true }).last().click()
    await entryWindow.getByRole('textbox').last().fill('A hall of brine-glass under a white tide.')
    await entryWindow.getByRole('button', { name: /Save/ }).last().click()
    await expect.poll(() => writes.filter((write) => write.method === 'PUT' || write.method === 'PATCH').length).toBeGreaterThan(0)
  })
})
