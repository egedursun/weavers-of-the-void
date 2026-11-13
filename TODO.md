**IMPROVEMENTS**

1.   [ ] ASK-RAG: Ask the lore a question. Direct RAG question to the full book + the full relationship graph. (after complete integration)

2.   [ ] VOICE: Ses dosyaları; dillerin kelimelerinin seslendirilmesi, marşlar, karakter sloganları, tanrısal seslendirmeler, meclis, ortam sesleri ve benzeri. Başka ne generate edilebiliyorsa tespit edilip incelensin sonra bir çözüm düşünelim.  (after complete integration)

3.   [ ] FE/GAMIFICATION: Front end düzeltmeleri ve gamification'ı yapılmalı.  (after complete integration)

4.   [ ] LIBRARY: Support for multiple worlds, world picker / library.  (after complete integration)

5.   [ ] COMMUNITY: LoreHub for people to upload their complete lores.  (after complete integration)

---

**GENERAL**

X.   [ ] Check the flexibility of the simulation engine to create cosmos, worlds, characters, mortals, gods, places, events, wars, and every entity present in the game; and identify what you "cannot" do with the currently existing mechanics; for example, is the number of different types of stars enough, or is the number of different types of worlds that can be created enough? The former sentence is ONLY AN EXAMPLE; it is purely given as a sample for a few entities in the simulation. But in the simulation, there are many entities, and you must check each and every entity; identify the missing flexibility features; and implement EACH AND EVERY one of them; for EACH AND EVERY ONE OF entities to make the simulation as deep as possible in terms of specs, attributes, mechanics, dynamics, narrative, behavior, and everything you can potentially ask from a fully flexible lore generator. After that, you must apply the same logic for the main onboarding world generation screen that appears when you start the app for the first time; and you must give the same critical look and ask; if it is customizable enough, if it gives enough sample examples for worlds that the user can pick; is it properly visually represented; can there be more? Then after determining what can be deepened, improved etc you must do it the same way for each and every entity you did. --- önce her entity için önerilen esnetme geliştirme genişletme düzeltme sağlamlaştırma mükemmelleştirme büyütme derinleştirmeleri içeren bir yeni spec dosyası oluşturacaksın. entegrasyonun kendisinden önce; cömert bir dosya olacak dediğim gibi. iyice araştırman gerekiyor. hayvan gibi on milyon tane ajan salma; uygulama devasa değil tek tek inceleyebilirsin veya batchler halinde. 

---

**NOVEL FEATURES**

1.   [ ] Türkçe dil desteği entegre edilmeli. (Quota yiyen bir faaliyet olacak). Tüm frontendin türkçeye uygun bir şekilde ayarlanması sağlanmalı. Default arayüz dili hala ingilizce kalabilir; ama türkçeye support vermemiz şart.

2.   [ ] Codex desteği. Uygulamaya oauth için gerekli kurulum sihirbazının ayrı olarak ayarlanması gerekecek. Yani burada sadece codex gibi düşünmeyelim ama insanların en sık kullandığı paid LLM subscription firmalarını düşünelim ve onlar için entegre edelim. Yani Gemini de mesela sıkça kullanılan bir örnek dolayısıyla onu da entegre etmemiz gerekecek. Bunları bir belirleyelim onun üzerinden eksiksiz bir şekilde entegre edeceğiz.

3.   [ ] API desteği. Bifrost tarzı bir çoklu sağlayıcı entegre edilmesi uygun olur. Local LLM'ler de desteklenmeli. Şu anda sadece OAuth entegrasyonu ile çalışıyoruz fakat commercial kullanımlar için bu legal bir seçenek olmayabilir birçok sağlayıcı açısından (ör. Anthropic). O yüzden API key kullanarak da kullanılabilmesi lazım. Tabii tüm kodu kendimiz her provider için tek tek yazmamız çok verimsiz bir faaliyet o yüzden en iyi çoklu provider entegrasyon sağlayıcısını bulmalı ve onunla çalışmalı; tam ve eksiksiz bir entegrasyon yapmalıyız.

4.   [ ] Farklı modeller ile image generation desteği getirilmeli. Şu anda sadece lokal model ile generation yapılabiliyor. Ama uygun bir çoklu provider sağlayıcısı ile biz çok fazla kod yazmadan bu sorunu çözebiliriz.

5.   [ ] Versiyonlama sistemi güzel bir şekilde oturtulmalı. Burada commit ağacındaki versiyonlamadan bahsetmiyorum. Sahip olmamız gereken ve tek yerden kontrol edilebilen. v0.1.0-beta tarzı bir uygulama versiyonlama biçiminden bahsediyorum. Bunu her seferinde 10 yerden değiştirmem amelelelik işi olur; o sebeple bu tek bir yerden kolayca değiştirilebilir olmalı ve kolayca yönetilebilmeli.

---

**NEXT STAGES**

1.   [ ] Kod kalitesi analiz, audit, performans, hız, kalite ve tutarlılık turları gerçekleştirilmelidir. Kapsamlı bir raporlama çoklu ajanlar ile gerçekleştirilmeli ve bulunan tüm açıklar eksiksiz bir biçimde kapatılmalı; uygulama sağlam, tutarlı, kullanılabilir ve kaliteli bir hale getirilmelidir.

---