import type { Locale } from './index'

const en = {
  hero: {
    eyebrow: 'The Worldbuilding Studio',
    title: 'Your universe, built by',
    titleAccent: 'the people who made the engine.',
    lead: 'Bring one idea. We set its laws, live it through 2,500 years of history, check it by hand and deliver a finished universe, ready for your novel, game, series or campaign.',
    primary: 'Commission a world',
    secondary: 'Compare the packages',
    proof: ['Reviewed by people', 'Yours to keep, royalty free', 'Delivered in three formats'],
    charter: {
      title: 'Your commission',
      seed: 'World seed',
      seedValue: 'Your idea',
      epochs: 'Epochs lived',
      years: 'Years of history',
      records: 'Typed records',
      rules: 'Rules tuned to you',
      depth: 'Hand-review depth',
      depthValue: 'up to 96%',
      relics: 'Arrives as',
      status: 'Ready to begin',
    },
  },
  promise: {
    eyebrow: 'Open source, studio crafted',
    title: 'The software is free.',
    titleAccent: 'The craft is ours.',
    lead: 'Weavers of the Void stays free for everyone, with every feature included. When you would rather hold a finished world than run one yourself, our studio takes the wheel.',
    free: {
      title: 'Free forever',
      price: '$0',
      items: [
        'The full simulator and all 99 expansions',
        'Personal and commercial use',
        'Self-hosting for teams of any size',
        'Your worlds and lore stay yours',
      ],
      cta: 'Get it on GitHub',
    },
    studio: {
      title: 'Done for you',
      price: 'From $79 / hour',
      items: [
        'A complete universe, built and reviewed for you',
        'New mechanics engineered for your world',
        'Your canon cared for over the years',
        'A private server, run on your behalf',
      ],
      cta: 'Explore the services',
    },
  },
  journey: {
    eyebrow: 'Your commission, stage by stage',
    title: 'From a single brief to a living canon',
    lead: 'Four stages, one team, and you approve every turn of the road.',
    stage: 'Stage',
    reward: 'You receive',
    steps: [
      {
        title: 'The brief',
        text: 'You share your vision: the tone, the peoples, the history and the questions your story needs answered. We shape the starting world, its physics, cosmology and societies around it.',
        reward: 'A configured universe, approved by you',
      },
      {
        title: 'The simulation',
        text: 'Fifty epochs are lived season by season. Lore is deepened, pictures are painted, the network of the world is drawn and every thin area is strengthened.',
        reward: '2,500 years of history, every cause kept',
      },
      {
        title: 'The review',
        text: 'Our reviewers check your critical canon first: your main gods, civilisations and turning points. Then they sample every kind of record across every age.',
        reward: 'A canon you can build on',
      },
      {
        title: 'The delivery',
        text: 'You receive the finished universe in three formats, with your revision rounds included to make it exactly yours.',
        reward: 'Universe Book, Codex and World Package',
      },
    ],
  },
  packages: {
    title: 'Choose how deeply we read your world',
  },
  compare: {
    eyebrow: 'Side by side',
    title: 'Compare the packages',
    lead: 'Every package lives the same 50 epochs and 2,500 years. What grows is how much of your world our reviewers read and refine by hand.',
    pick: 'Choose a package to compare',
    feature: 'What you get',
    depth: 'Hand-review depth',
    depthLevels: [8, 32, 96],
    rows: {
      price: 'Price',
      epochs: 'Simulation',
      history: 'History',
      records: 'Typed records (planned)',
      review: 'Expert review',
      sampled: 'Records read by hand',
      delivery: 'Delivery',
      revisions: 'Revision rounds included',
      extra: 'Extra revisions',
      payment: 'Payment',
    },
    values: {
      epochs: '50 epochs',
      history: '2,500 years',
      records: '30,000',
      reviewHours: ['40 hours', '160 hours', '480 hours'],
      sampled: ['about 2,400', 'about 9,600', 'about 28,800'],
      revisions: ['1 round', '2 rounds', '3 rounds'],
      extra: '$79 per hour',
      payment: '50% to start, 50% on delivery',
    },
    cta: 'Request',
  },
  included: {
    eyebrow: 'In every package',
    title: 'Everything your world needs',
    titleAccent: 'to leave the studio',
    items: [
      { title: 'Your universe, configured', text: 'The starting world, its physics, cosmology and societies, with more than 16,500 existing rules set to your vision.' },
      { title: 'Fifty lived epochs', text: 'Two and a half thousand years of births, reigns, faiths, markets and wars, each change kept with its cause.' },
      { title: 'Deepened lore', text: 'Thin regions, peoples and histories are strengthened until the whole world holds together.' },
      { title: 'Pictures throughout', text: 'Portraits, places and scenes painted across your world, in the visual style you choose.' },
      { title: 'The network of the world', text: 'Every bond between people, peoples, faiths and places, drawn as one graph and corrected by hand.' },
      { title: 'Three formats', text: 'The Universe Book in HTML and PDF, the Codex in Markdown and ZIP, and the portable World Package.' },
    ],
    note: 'Tuning the existing rules is always included. Brand-new mechanics are built as Universe Engineering.',
  },
  canon: {
    eyebrow: 'Canon you can trust',
    title: 'How our reviewers read your world',
    lead: 'Thirty thousand records are never read at random. Our review follows the parts of your world that matter most to you.',
    pillars: [
      { title: 'Critical canon first', text: 'Your main gods, civilisations and defining events are checked before anything else.' },
      { title: 'Follow the connections', text: 'The records with the most bonds carry the most weight, so they are read most often.' },
      { title: 'Every kind, every age', text: 'Each type of record and each epoch is represented, so no corner of your world goes unread.' },
      { title: 'Dig where it matters', text: 'Where reviewers find a cluster of issues, the sample widens until it is resolved.' },
    ],
    note: 'Want more of your canon read by hand than your package covers? We agree the extra scope with you before any work begins.',
  },
  more: {
    eyebrow: 'Beyond a single world',
    title: 'Specialists, servers and support',
    lead: 'Engineering, canon care, training and infrastructure, on their own or together, whether we built your world or you did.',
  },
  details: {
    cloud: [
      'Every feature, unlimited worlds and epochs',
      'Setup, updates, backups and monitoring handled',
      'Infrastructure support included',
      'Bring your own AI account',
      'Need more room? We size a larger server',
    ],
    enterprise: [
      'On-premise or private cloud',
      'Single sign-on and security hardening',
      'Local AI models and picture generation',
      'Backups and performance tuning',
    ],
    hourly: {
      engineering: [
        'Your own magic, physics, biology, economy, cosmology or politics',
        'Designed, coded, tested and documented',
        'By the hour, or a fixed quote for a defined project',
      ],
      canon: [
        'Simulation follow-up and canon checks',
        'Lore improvements and creative changes on request',
        'No monthly commitment, only approved hours',
      ],
      consulting: [
        'Simulation design and rule configuration',
        'Professional worldbuilding practice',
        'For you or your whole team',
      ],
    },
  },
  terms: {
    eyebrow: 'Clear terms',
    title: 'No surprises on the invoice',
    billingTitle: 'How each service is billed',
    billing: [
      { key: 'worldbuilding', name: 'Custom Worldbuilding', terms: '50% to start, 50% on delivery' },
      { key: 'hourly', name: 'Universe Engineering and Canon Management', terms: 'Billed weekly' },
      { key: 'consulting', name: 'Consulting & Training', terms: 'Paid in advance' },
      { key: 'cloud', name: 'Managed Cloud', terms: 'Monthly, in advance' },
      { key: 'deployment', name: 'Enterprise Deployment', terms: 'As agreed in your contract' },
    ],
    promisesTitle: 'What we promise',
    promises: [
      'All prices in US dollars, excluding VAT where it applies.',
      'You connect your own AI account securely and pay its usage directly, so that cost stays visible and in your hands.',
      'Extra revisions are billed at $79 per hour, and only after you approve them.',
      'Delivery windows count our working time. Time spent waiting for feedback is not included.',
      'Everything we create for you is yours, with no royalties and no licence fees.',
    ],
  },
  faq: {
    eyebrow: 'Before you commission',
    title: 'Questions studios ask us',
    more: 'Show more questions',
    items: [
      {
        q: 'How do I choose between Standard, Professional and Enterprise?',
        a: 'Every package lives the same 50 epochs and 2,500 years, so the world itself is just as rich. What changes is how much of it our reviewers read and refine by hand. Standard suits a novel or a campaign of your own. Professional suits a series or a studio that will build on its canon for years. Enterprise is for franchises and licensed worlds where nearly every record has to be checked.',
      },
      {
        q: 'What do I need to bring to the brief?',
        a: 'As much or as little as you have. One paragraph is enough to begin. The more you share about the tone, the peoples, the history you want, the facts that must not change and what the world is for, the closer the first configuration lands. We follow up with questions before anything is simulated.',
      },
      {
        q: 'Can you build on a world or canon I already have?',
        a: 'Yes. Your existing facts, maps, characters and timelines are set in the world as locked canon before the simulation starts, so the new history grows around them instead of overwriting them.',
      },
      {
        q: 'Do I need to know how to use the software?',
        a: 'Not at all. We run every step. You share your vision, answer our questions and review the result.',
      },
      {
        q: 'How involved am I along the way?',
        a: 'As involved as you like. You approve the configured universe before the simulation begins, you can follow its progress, and your revision rounds let you steer the finished canon until it is exactly yours.',
      },
      {
        q: 'Why do I bring my own AI account?',
        a: 'Your world is generated through an AI account you control, for both text and pictures. You pay its usage directly to your provider, with no markup from us, and you decide which provider your ideas go to. A model running on your own hardware works too.',
      },
      {
        q: 'How much will the AI usage cost me?',
        a: 'It depends on the provider and the models you choose. Before we start, we help you pick a setup that fits your budget, and you can watch every bit of usage in your own provider account as the work goes on.',
      },
      {
        q: 'Is my world kept confidential?',
        a: 'Yes. Everyone who works on your world is bound by confidentiality, and we never show it publicly, not even as an example, without your permission.',
      },
      {
        q: 'Who owns the world you build for me?',
        a: 'You do. The universe, its lore, its pictures and its books are yours to publish, adapt and sell, for a novel, a game, a show or anything else, with no royalties and no licence fees.',
      },
      {
        q: 'What if my world needs a mechanic that does not exist yet?',
        a: 'Tuning the more than 16,500 existing rules is part of every package. A brand-new system, such as your own magic, physics or economy, is built as Universe Engineering, by the hour or for a fixed quote.',
      },
      {
        q: 'What if I want changes after delivery?',
        a: 'Your package includes one, two or three revision rounds. Beyond those, extra revisions are billed at $79 per hour, always agreed with you first. For a world that keeps growing, Canon Management looks after it for as long as you need.',
      },
      {
        q: 'Can I keep the world running after delivery?',
        a: 'Yes. The World Package opens in any copy of Weavers of the Void, on your machine, your servers or our Managed Cloud. Keep playing it yourself as its god, or let Canon Management carry it into new ages.',
      },
    ],
  },
  final: {
    title: 'Your world is one brief away.',
    lead: 'Tell us what you imagine. A worldbuilder reads every request and writes back personally.',
    cta: 'Start your commission',
    free: 'Or build it yourself, free',
  },
}

export type StudioCopy = typeof en

const tr: StudioCopy = {
  hero: {
    eyebrow: 'Dünya Kurma Stüdyosu',
    title: 'Evrenin, motoru yapan',
    titleAccent: 'ellerde hayat bulsun.',
    lead: 'Tek bir fikir getir. Yasalarını kuralım, 2.500 yıllık tarihini yaşatalım, elle inceleyelim ve romanın, oyunun, dizin ya da kampanyan için hazır, eksiksiz bir evren teslim edelim.',
    primary: 'Evrenini sipariş et',
    secondary: 'Paketleri karşılaştır',
    proof: ['İnsanlar tarafından incelenir', 'Telifsiz, tamamen senin', 'Üç formatta teslim'],
    charter: {
      title: 'Siparişin',
      seed: 'Dünya tohumu',
      seedValue: 'Senin fikrin',
      epochs: 'Yaşanan devir',
      years: 'Yıllık tarih',
      records: 'Tipli kayıt',
      rules: 'Sana göre ayarlanan kural',
      depth: 'Elle inceleme derinliği',
      depthValue: '%96’ya kadar',
      relics: 'Teslim biçimi',
      status: 'Başlamaya hazır',
    },
  },
  promise: {
    eyebrow: 'Açık kaynak, stüdyo işçiliği',
    title: 'Yazılım ücretsiz.',
    titleAccent: 'Ustalık bizden.',
    lead: 'Weavers of the Void herkes için, bütün özellikleriyle ücretsiz kalır. Bir dünyayı kendin yürütmek yerine bitmiş hâlini elinde tutmak istediğinde dümeni stüdyomuz alır.',
    free: {
      title: 'Sonsuza dek ücretsiz',
      price: '$0',
      items: [
        'Simülatörün tamamı ve 99 genişlemenin hepsi',
        'Kişisel ve ticari kullanım',
        'Her büyüklükte ekip için kendi sunucunda kurulum',
        'Dünyaların ve lore’un sende kalır',
      ],
      cta: 'GitHub’dan edin',
    },
    studio: {
      title: 'Senin için yapılır',
      price: 'Saatlik $79’dan',
      items: [
        'Senin için kurulmuş ve incelenmiş eksiksiz bir evren',
        'Dünyana özel geliştirilen yeni mekanikler',
        'Yıllar boyunca özenle korunan kanon',
        'Senin adına yönetilen özel bir sunucu',
      ],
      cta: 'Hizmetleri keşfet',
    },
  },
  journey: {
    eyebrow: 'Siparişin, aşama aşama',
    title: 'Tek bir brief’ten yaşayan bir kanona',
    lead: 'Dört aşama, tek ekip ve yolun her dönemecinde son onay senin.',
    stage: 'Aşama',
    reward: 'Elde ettiğin',
    steps: [
      {
        title: 'Brief',
        text: 'Vizyonunu paylaşırsın: tonu, halkları, tarihi ve hikâyenin cevap bekleyen sorularını. Başlangıç dünyasını, fiziğini, kozmolojisini ve toplumlarını bunun etrafında şekillendiririz.',
        reward: 'Senin onayladığın, yapılandırılmış bir evren',
      },
      {
        title: 'Simülasyon',
        text: 'Elli devir mevsim mevsim yaşanır. Lore derinleşir, görseller çizilir, dünyanın ağı çıkarılır ve zayıf kalan her alan güçlendirilir.',
        reward: 'Her nedeni saklanmış 2.500 yıllık tarih',
      },
      {
        title: 'İnceleme',
        text: 'İnceleyicilerimiz önce kritik kanonunu kontrol eder: ana tanrılarını, medeniyetlerini ve dönüm noktalarını. Ardından her çağdan her türden kaydı örnekler.',
        reward: 'Üzerine güvenle inşa edebileceğin bir kanon',
      },
      {
        title: 'Teslimat',
        text: 'Bitmiş evreni üç formatta teslim alırsın; onu tam olarak senin yapacak revizyon turları da dahildir.',
        reward: 'Evren Kitabı, Codex ve World Package',
      },
    ],
  },
  packages: {
    title: 'Dünyanın ne kadar derin okunacağını seç',
  },
  compare: {
    eyebrow: 'Yan yana',
    title: 'Paketleri karşılaştır',
    lead: 'Her paket aynı 50 devri ve 2.500 yılı yaşar. Büyüyen şey, dünyanın ne kadarının inceleyicilerimiz tarafından elle okunup iyileştirildiğidir.',
    pick: 'Karşılaştırmak için bir paket seç',
    feature: 'Neler dahil',
    depth: 'Elle inceleme derinliği',
    depthLevels: [8, 32, 96],
    rows: {
      price: 'Fiyat',
      epochs: 'Simülasyon',
      history: 'Tarih',
      records: 'Tipli kayıt (plan)',
      review: 'Uzman incelemesi',
      sampled: 'Elle okunan kayıt',
      delivery: 'Teslimat',
      revisions: 'Dahil revizyon turu',
      extra: 'Ek revizyon',
      payment: 'Ödeme',
    },
    values: {
      epochs: '50 devir',
      history: '2.500 yıl',
      records: '30.000',
      reviewHours: ['40 saat', '160 saat', '480 saat'],
      sampled: ['yaklaşık 2.400', 'yaklaşık 9.600', 'yaklaşık 28.800'],
      revisions: ['1 tur', '2 tur', '3 tur'],
      extra: 'saatlik $79',
      payment: '%50 başlangıçta, %50 teslimatta',
    },
    cta: 'Talep et',
  },
  included: {
    eyebrow: 'Her pakette',
    title: 'Dünyanın stüdyodan çıkmak için',
    titleAccent: 'ihtiyaç duyduğu her şey',
    items: [
      { title: 'Yapılandırılmış evren', text: 'Başlangıç dünyası, fiziği, kozmolojisi ve toplumları; mevcut 16.500’ü aşkın kural vizyonuna göre ayarlanır.' },
      { title: 'Yaşanmış elli devir', text: 'Doğumlar, hükümdarlıklar, inançlar, pazarlar ve savaşlarla dolu iki bin beş yüz yıl; her değişiklik nedeniyle birlikte saklanır.' },
      { title: 'Derinleştirilmiş lore', text: 'Zayıf kalan bölgeler, halklar ve tarihler, bütün dünya birbirini tutana dek güçlendirilir.' },
      { title: 'Baştan sona görseller', text: 'Dünyanın dört bir yanından portreler, mekânlar ve sahneler, seçtiğin görsel üslupta.' },
      { title: 'Dünyanın ağı', text: 'İnsanlar, halklar, inançlar ve yerler arasındaki her bağ tek bir grafikte çizilir ve elle düzeltilir.' },
      { title: 'Üç format', text: 'HTML ve PDF olarak Evren Kitabı, Markdown ve ZIP olarak Codex ve taşınabilir World Package.' },
    ],
    note: 'Mevcut kuralların ayarlanması her zaman dahildir. Bütünüyle yeni mekanikler Evren Mühendisliği olarak geliştirilir.',
  },
  canon: {
    eyebrow: 'Güvenilir kanon',
    title: 'İnceleyicilerimiz dünyanı nasıl okur',
    lead: 'Otuz bin kayıt asla rastgele okunmaz. İncelememiz dünyanın senin için en önemli kısımlarını izler.',
    pillars: [
      { title: 'Önce kritik kanon', text: 'Ana tanrıların, medeniyetlerin ve belirleyici olayların her şeyden önce kontrol edilir.' },
      { title: 'Bağlantıları izle', text: 'En çok bağı olan kayıtlar en çok ağırlığı taşır, bu yüzden en sık onlar okunur.' },
      { title: 'Her tür, her çağ', text: 'Her kayıt türü ve her devir temsil edilir; dünyanın hiçbir köşesi okunmadan kalmaz.' },
      { title: 'Gereken yeri derinleştir', text: 'İnceleyiciler bir sorun kümesi bulduğunda örneklem, sorun çözülene dek genişler.' },
    ],
    note: 'Kanonunun paketinin kapsadığından fazlasının elle okunmasını mı istiyorsun? Ek kapsamı, iş başlamadan önce seninle birlikte belirleriz.',
  },
  more: {
    eyebrow: 'Tek bir dünyanın ötesinde',
    title: 'Uzmanlar, sunucular ve destek',
    lead: 'Mühendislik, kanon bakımı, eğitim ve altyapı; tek tek ya da bir arada. Dünyanı ister biz kuralım ister sen.',
  },
  details: {
    cloud: [
      'Bütün özellikler, sınırsız dünya ve devir',
      'Kurulum, güncelleme, yedekleme ve izleme bizden',
      'Altyapı desteği dahil',
      'Kendi yapay zekâ hesabını kullan',
      'Daha fazla alan mı lazım? Daha büyük bir sunucu hazırlarız',
    ],
    enterprise: [
      'Kendi sunucuların ya da özel bulut',
      'Tek oturum açma ve güvenlik sıkılaştırması',
      'Yerel yapay zekâ modelleri ve görsel üretimi',
      'Yedekleme ve performans ayarı',
    ],
    hourly: {
      engineering: [
        'Kendi büyün, fiziğin, biyolojin, ekonomin, kozmolojin ya da siyasetin',
        'Tasarlanır, kodlanır, test edilir ve belgelenir',
        'Saatlik ya da tanımlı bir proje için sabit teklif',
      ],
      canon: [
        'Simülasyon takibi ve kanon kontrolleri',
        'Talebine göre lore iyileştirmeleri ve yaratıcı müdahaleler',
        'Aylık taahhüt yok, yalnızca onaylanan saatler',
      ],
      consulting: [
        'Simülasyon tasarımı ve kural yapılandırması',
        'Profesyonel dünya kurma pratiği',
        'Kendin ya da bütün ekibin için',
      ],
    },
  },
  terms: {
    eyebrow: 'Açık koşullar',
    title: 'Faturada sürpriz yok',
    billingTitle: 'Her hizmet nasıl faturalanır',
    billing: [
      { key: 'worldbuilding', name: 'Özel Evren Kurulumu', terms: '%50 başlangıçta, %50 teslimatta' },
      { key: 'hourly', name: 'Evren Mühendisliği ve Kanon Yönetimi', terms: 'Haftalık faturalandırma' },
      { key: 'consulting', name: 'Danışmanlık ve Eğitim', terms: 'Peşin ödeme' },
      { key: 'cloud', name: 'Yönetilen Bulut', terms: 'Aylık, peşin' },
      { key: 'deployment', name: 'Kurumsal Kurulum', terms: 'Sözleşmende belirlendiği gibi' },
    ],
    promisesTitle: 'Sözümüz',
    promises: [
      'Bütün fiyatlar ABD doları cinsindendir; uygulandığı yerde KDV hariçtir.',
      'Kendi yapay zekâ hesabını güvenle bağlar, kullanım bedelini doğrudan ödersin; bu maliyet her zaman görünür ve senin kontrolünde kalır.',
      'Ek revizyonlar saatlik $79 üzerinden ve yalnızca senin onayınla faturalanır.',
      'Teslimat süreleri bizim çalışma süremizi kapsar; geri bildirim beklenen süre buna dahil değildir.',
      'Senin için ürettiğimiz her şey senindir; telif ya da lisans ücreti yoktur.',
    ],
  },
  faq: {
    eyebrow: 'Sipariş vermeden önce',
    title: 'Stüdyoların bize sorduğu sorular',
    more: 'Daha fazla soru göster',
    items: [
      {
        q: 'Standard, Professional ve Enterprise arasında nasıl seçim yaparım?',
        a: 'Her paket aynı 50 devri ve 2.500 yılı yaşar; dünyanın kendisi hepsinde aynı zenginliktedir. Değişen, inceleyicilerimizin onun ne kadarını elle okuyup iyileştirdiğidir. Standard kendi romanın ya da kampanyan için uygundur. Professional, kanonu üzerine yıllarca inşa edecek bir seri ya da stüdyo içindir. Enterprise ise neredeyse her kaydın kontrol edilmesi gereken markalar ve lisanslı dünyalar içindir.',
      },
      {
        q: 'Brief için ne getirmem gerekiyor?',
        a: 'Elinde ne varsa. Başlamak için tek bir paragraf yeterli. Ton, halklar, istediğin tarih, değişmemesi gereken gerçekler ve dünyanın ne için kullanılacağı hakkında ne kadar çok şey paylaşırsan ilk yapılandırma o kadar isabetli olur. Simülasyon başlamadan önce sorularımızla geri döneriz.',
      },
      {
        q: 'Elimdeki bir dünyanın ya da kanonun üzerine inşa edebilir misiniz?',
        a: 'Evet. Var olan gerçeklerin, haritaların, karakterlerin ve zaman çizelgelerin simülasyon başlamadan önce dünyaya kilitli kanon olarak yerleştirilir; yeni tarih onların üzerine yazılmaz, etraflarında büyür.',
      },
      {
        q: 'Yazılımı kullanmayı bilmem gerekiyor mu?',
        a: 'Hiç gerekmiyor. Her adımı biz yürütürüz. Sen vizyonunu paylaşır, sorularımızı yanıtlar ve sonucu incelersin.',
      },
      {
        q: 'Süreçte ne kadar yer alırım?',
        a: 'İstediğin kadar. Simülasyon başlamadan önce yapılandırılmış evreni sen onaylarsın, ilerleyişini takip edebilirsin ve revizyon turlarınla bitmiş kanonu tam olarak senin olana dek yönlendirirsin.',
      },
      {
        q: 'Neden kendi yapay zekâ hesabımı getiriyorum?',
        a: 'Dünyan, metinleri ve görselleriyle birlikte, kontrolü sende olan bir yapay zekâ hesabıyla üretilir. Kullanım bedelini, bizim hiçbir ek ücretimiz olmadan doğrudan sağlayıcına ödersin ve fikirlerinin hangi sağlayıcıya gideceğine sen karar verirsin. Kendi donanımında çalışan bir model de olur.',
      },
      {
        q: 'Yapay zekâ kullanımı bana kaça mal olur?',
        a: 'Seçtiğin sağlayıcıya ve modellere bağlıdır. Başlamadan önce bütçene uyan bir kurulum seçmene yardım ederiz; iş ilerlerken her kullanımı kendi sağlayıcı hesabından izleyebilirsin.',
      },
      {
        q: 'Dünyam gizli tutulur mu?',
        a: 'Evet. Dünyan üzerinde çalışan herkes gizlilik yükümlülüğü altındadır ve onu iznin olmadan, örnek olarak bile, asla herkese açık göstermeyiz.',
      },
      {
        q: 'Benim için kurduğunuz dünya kimin?',
        a: 'Senin. Evren, lore’u, görselleri ve kitapları bir roman, oyun, dizi ya da başka her şey için yayımlaman, uyarlaman ve satman için senindir; telif ya da lisans ücreti yoktur.',
      },
      {
        q: 'Dünyamın henüz var olmayan bir mekaniğe ihtiyacı varsa?',
        a: 'Mevcut 16.500’ü aşkın kuralın ayarlanması her paketin parçasıdır. Kendi büyün, fiziğin ya da ekonomin gibi bütünüyle yeni bir sistem, saatlik ya da sabit teklifle Evren Mühendisliği olarak geliştirilir.',
      },
      {
        q: 'Teslimattan sonra değişiklik istersem ne olur?',
        a: 'Paketin bir, iki ya da üç revizyon turu içerir. Bunların ötesindeki ek revizyonlar, her zaman önce seninle kararlaştırılarak saatlik $79 üzerinden faturalanır. Büyümeye devam eden bir dünya için Kanon Yönetimi ona ihtiyacın olduğu sürece bakar.',
      },
      {
        q: 'Teslimattan sonra dünyayı yaşatmaya devam edebilir miyim?',
        a: 'Evet. World Package, Weavers of the Void’un her kopyasında açılır: kendi bilgisayarında, kendi sunucularında ya da Yönetilen Bulut’umuzda. Onu tanrısı olarak kendin oynamaya devam edebilir ya da Kanon Yönetimi ile yeni çağlara taşıyabilirsin.',
      },
    ],
  },
  final: {
    title: 'Dünyan bir brief uzağında.',
    lead: 'Hayal ettiğini anlat. Her talebi bir dünya kurucu okur ve sana bizzat yazar.',
    cta: 'Siparişini başlat',
    free: 'Ya da kendin kur, ücretsiz',
  },
}

const STUDIO: Record<Locale, StudioCopy> = { en, tr }

export function studioCopy(locale: Locale): StudioCopy {
  return STUDIO[locale]
}
