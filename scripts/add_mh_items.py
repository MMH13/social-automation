import json
from pathlib import Path

content_file = Path(r"..\Automation\scheduled_mh\content.json")
queue = json.loads(content_file.read_text(encoding="utf-8"))

existing_ids = {item["id"] for item in queue}
next_id = max(existing_ids, default=0) + 1

new_posts = [
    {
        "id": next_id,
        "format": "A",
        "hook": "জরুরি প্রেজেন্টেশন বানাতে হবে?\n*১০ মিনিটে স্লাইড* রেডি করার ৩টি AI টুল 👇",
        "theme": "black",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• Gamma.app - টপিক লিখে দিলে সম্পূর্ণ প্রেজেন্টেশন, ডিজাইন ও চার্ট অটো বানিয়ে দেয়।\n• Canva Magic Design - টেক্সট পেস্ট করলেই রেডিমেড প্রফেশনাল স্লাইড সাজিয়ে দেয়।\n• Beautiful.ai - করপোরেট স্ট্যান্ডার্ড স্লাইড তৈরির জন্য বেস্ট টুল।\n• টিপস: প্রেজেন্টেশন শেষে PowerPoint বা PDF এ সরাসরি এক্সপোর্ট করতে পারবেন।"
    },
    {
        "id": next_id + 1,
        "format": "A",
        "hook": "PDF এডিট করতে গিয়ে *টাকা চাচ্ছে*?\nসম্পূর্ণ ফ্রি ৪টি কাজের ওয়েবসাইট 👇",
        "theme": "crimson",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• PDF24 Tools (tools.pdf24.org) - সম্পূর্ণ আনলিমিটেড এবং ফ্রি, কোনো ফাইল সাইজ লিমিট বা ওয়াটারমার্ক নেই।\n• Sejda PDF Editor (sejda.com) - সরাসরি টেক্সট এডিট ও সাইন করার জন্য সহজ।\n• ILovePDF (ilovepdf.com) - PDF কম্প্রেস, কনভার্ট ও পেজ মার্চ করার জন্য জনপ্রিয়।\n• TinyWow (tinywow.com) - PDF ছাড়াও সব ধরনের ফাইল কনভার্শনের ১০০+ ফ্রি টুল।"
    },
    {
        "id": next_id + 2,
        "format": "A",
        "hook": "বই বা রিসার্চ পেপার পড়ার সময় নেই?\n*Google NotebookLM* দিয়ে পডকাস্ট বানান 👇",
        "theme": "black",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• notebooklm.google.com এ যান এবং গুগল একাউন্ট দিয়ে লগইন করুন।\n• আপনার যেকোনো বড় PDF বা রিসার্চ পেপার আপলোড করুন।\n• 'Audio Overview' তে ক্লিক করলে দুইজনে মিলে পুরো পেপারের মূল বিষয় আলোচনা করে পডকাস্ট বানিয়ে দেবে।\n• আপনি যেকোনো প্রশ্ন করলে সরাসরি পেপারের রেফারেন্স দিয়ে উত্তর বলে দেবে।"
    },
    {
        "id": next_id + 3,
        "format": "hot",
        "caption": "AI আপনার চাকরি খাবে না, কিন্তু যে মানুষটা AI ঠিকমতো ব্যবহার করতে পারে — সে হয়তো আপনার চেয়ে অনেক দ্রুত এগিয়ে যাবে।\n\nপ্রতিদিন শুধু ১০ মিনিট সময় দিন নতুন এআই টুল আর প্রম্পটিং প্র্যাকটিসে। দিনশেষে স্কিলই আপনার সবচেয়ে বড় নিরাপত্তা।",
        "first_comment": "আপনি প্রতিদিন কোন AI টুলটি সবচেয়ে বেশি ব্যবহার করেন? কমেন্টে জানান।"
    },
    {
        "id": next_id + 4,
        "format": "A",
        "hook": "ফ্রিল্যান্সিংয়ে কাজ পাচ্ছেন না?\n*বাইরের ক্লায়েন্ট খোঁজার* ৪টি বিকল্প মাধ্যম 👇",
        "theme": "crimson",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• LinkedIn Search - 'hiring remote [your skill]' ফিল্টার দিয়ে সরাসরি ফাউন্ডার বা রিক্রুটারকে রিচ করুন।\n• Wellfound (AngelList) - স্টার্টআপ কোম্পানিতে রিমোট পার্ট-টাইম বা ফুল-টাইম কাজের সেরা প্ল্যাটফর্ম।\n• We Work Remotely (weworkremotely.com) - গ্লোবাল রিমোট কাজের সবচেয়ে বড় বোর্ড।\n• X (Twitter) Search - বিভিন্ন টেক ও ক্রিয়েটিভ প্রজেক্টের ওপেনিং দ্রুত খুঁজে পাওয়া যায়।"
    },
    {
        "id": next_id + 5,
        "format": "A",
        "hook": "কোল্ড ইমেইল পাঠালে *রিপ্লাই পান না*?\nক্লড বা ChatGPT-র ১টি কার্যকর প্রম্পট 👇",
        "theme": "black",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• প্রম্পট কপি করে নিন: 'আমি [আপনার সার্ভিস] অফার করি। ক্লায়েন্টের কোম্পানি [কোম্পানির নাম/লিংক]। তাদের প্রধান সমস্যা কীভাবে দূর করব তা উল্লেখ করে ১০০ শব্দের একটি পার্সোনালাইজড কোল্ড ইমেইল লিখে দিন। কোনো চটকদার কথা নয়, সরাসরি ভ্যালু ফোকাসড হবে।'\n• টিপস: প্রথম লাইনেই তাদের সাম্প্রতিক কোনো কাজের প্রশংসা করুন।"
    },
    {
        "id": next_id + 6,
        "format": "A",
        "hook": "দামি সফটওয়্যার কেনার *দরকার নেই*!\nটপ ৩টি সফটওয়্যারের সেরা ফ্রি বিকল্প 👇",
        "theme": "crimson",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• Photoshop এর বদলে: Photopea (photopea.com) - ব্রাউজারেই হুবহু ফটোশপের সব ফিচার ফ্রি।\n• MS Office এর বদলে: LibreOffice অথবা Google Docs/Sheets।\n• Premiere Pro এর বদলে: DaVinci Resolve - হলিউড গ্রেডের ভিডিও এডিটিং সম্পূর্ণ ফ্রিতে শেখা যায়।"
    },
    {
        "id": next_id + 7,
        "format": "A",
        "hook": "ফেসবুক পেজ সুরক্ষিত রাখতে চান?\n*হ্যাকিং থেকে বাঁচার* ৩টি জরুরি সেটিংস 👇",
        "theme": "crimson",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• Two-Factor Authentication (2FA) চালু রাখুন Authenticator App দিয়ে, SMS দিয়ে নয়।\n• বিজনেস ম্যানেজারে অন্য কাউকে ফুল কন্ট্রোল (Admin) না দিয়ে শুধু Task Access দিন।\n• ইনবক্সে কোনো 'Copyright Infringement' বা অস্বাভাবিক ফাইল লিংকে কখনোই ক্লিক করবেন না।"
    },
    {
        "id": next_id + 8,
        "format": "A",
        "hook": "১ ঘণ্টার ইউটিউব ভিডিও দেখার *ধৈর্য নেই*?\nAI দিয়ে ৫ মিনিটে সামারি বের করুন 👇",
        "theme": "black",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• Glasp YouTube Summary (Chrome Extension) - এক ক্লিকে পুরো ভিডিওর ট্রান্সক্রিপ্ট ও সামারি তৈরি করে।\n• NoteGPT (notegpt.io) - ভিডিওর মূল পয়েন্ট ও টাইমস্ট্যাম্পসহ নোট বানিয়ে দেয়।\n• Eightify AI - যেকোনো দীর্ঘ লেকচার বা পডকাস্টের কি-টেকঅ্যাওয়ে বের করার জন্য সেরা।"
    },
    {
        "id": next_id + 9,
        "format": "A",
        "hook": "ছবি ঘোলা বা ব্যাকগ্রাউন্ড খারাপ?\n*১ ক্লিকে ফিক্স করার* ৩টি ফ্রি AI টুল 👇",
        "theme": "black",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• Upscayl (upscayl.org) - সম্পূর্ণ ফ্রি ওপেন সোর্স টুল, ঘোলা ছবিকে ৪ গুণ ক্রিস্টাল ক্লিয়ার করে।\n• Adobe Podcast Enhance (podcast.adobe.com) - যেকোনো নয়েজযুক্ত খারাপ ভয়েসকে স্টুডিও কোয়ালিটি বানায়।\n• Clipdrop (clipdrop.co) - ছবির অপ্রয়োজনীয় অবজেক্ট বা ওয়াটারমার্ক মুহূর্তেই মুছে ফেলার বেস্ট টুল।"
    },
    {
        "id": next_id + 10,
        "format": "A",
        "hook": "স্পোকেন ইংলিশ প্র্যাকটিস করতে চান?\n*ChatGPT Voice* দিয়ে ফ্রি স্পিকিং পার্টনার 👇",
        "theme": "black",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• ফোনের ChatGPT অ্যাপ ওপেন করে হেডফোন আইকনে চাপ দিন।\n• বলুন: 'Act as an IELTS speaking examiner and take a mock interview on everyday topics. Point out my grammar mistakes politely.'\n• প্রতিদিন ১০ মিনিট কথা বলুন — লজ্জা ছাড়াই ফ্লুয়েন্সি বাড়বে।"
    },
    {
        "id": next_id + 11,
        "format": "hot",
        "caption": "ইন্টারনেটে হাজার হাজার প্রম্পটের বান্ডেল কিনে আসলে কোনো লাভ হয় না।\n\nপ্রম্পটিং মুখস্থ করার জিনিস না, এটা হলো নিজের ভাবনাকে পরিষ্কার ভাষায় AI-কে বোঝানোর একটা আর্ট। ৩টা জিনিস মাথায় রাখুন: রোল (Role), কনটেক্সট (Context), এবং আউটপুট ফরম্যাট (Format)।",
        "first_comment": "আপনার পছন্দের প্রম্পট ফ্রেমওয়ার্ক কোনটি? নিচে শেয়ার করুন।"
    },
    {
        "id": next_id + 12,
        "format": "A",
        "hook": "ওয়েবসাইটে এরর আসছে কিন্তু কোডিং পারেন না?\n*AI দিয়ে সমাধান* করার সহজ টেকনিক 👇",
        "theme": "crimson",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• ব্রাউজারের Inspect > Console থেকে লাল রঙের এরর কোডটি হুবহু কপি করুন।\n• Claude বা ChatGPT-তে পেস্ট করে লিখুন: 'Explain this error in simple Bengali and give me the exact step-by-step fix for WordPress/HTML.'\n• কোডের ব্যাকআপ রেখে তারপর ফিক্স অ্যাপ্লাই করুন।"
    },
    {
        "id": next_id + 13,
        "format": "A",
        "hook": "চাকরির ইন্টারভিউ নিয়ে নার্ভাস?\n*৫টি প্রম্পট দিয়ে* বাসায় মক টেস্ট দিন 👇",
        "theme": "black",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• 'আমি [পদের নাম] এর জন্য আবেদন করেছি। এই পদের সবচেয়ে কঠিন ৫টি প্রশ্ন করুন।'\n• 'আমার উত্তর বিশ্লেষণ করে বলুন কোন দিকটা আরও স্ট্রং হতে পারত।'\n• 'এই কোম্পানির সম্পর্কে ইন্টারভিউয়ারকে জিজ্ঞাসা করার মতো ৩টি স্মার্ট প্রশ্ন তৈরি করে দিন।'"
    },
    {
        "id": next_id + 14,
        "format": "A",
        "hook": "কম্পিউটার দিন দিন স্লো হয়ে যাচ্ছে?\n*কোনো সফটওয়্যার ছাড়াই* গতি বাড়ান 👇",
        "theme": "crimson",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• Win + R চেপে লিখুন 'temp' এবং সব ফাইল ডিলিট করুন।\n• আবার Win + R চেপে '%temp%' লিখে ফাইল ক্লিয়ার করুন।\n• Task Manager ওপেন করে Startup Apps থেকে অপ্রয়োজনীয় অ্যাপস Disable করে রাখুন।"
    },
    {
        "id": next_id + 15,
        "format": "A",
        "hook": "AI থেকে দুর্বল উত্তর পাচ্ছেন?\n*CLEAR ফ্রেমওয়ার্ক* ব্যবহার করে দেখুন 👇",
        "theme": "black",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• C - Context (প্রেক্ষাপট দিন)\n• L - Limitations (কোন বিষয়গুলো বাদ দিতে হবে বলুন)\n• E - Examples (একটি ভালো উদাহরণ দিন)\n• A - Audience (কার জন্য কনটেন্ট লিখছেন)\n• R - Role (এআই-কে একজন এক্সপার্টের চরিত্র দিন)"
    },
    {
        "id": next_id + 16,
        "format": "A",
        "hook": "Excel বা Google Sheets-এ সময় নষ্ট?\n*AI ফর্মুলা জেনারেটর* দিয়ে কাজ করুন 👇",
        "theme": "black",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• Formula Bot (formulabot.com) - বাংলায় লিখুন কী হিসাব চান, এটি সঠিক এক্সেল ফর্মুলা তৈরি করে দেবে।\n• ChatGPT-তে আপনার কলামের নামগুলো দিয়ে বলুন: 'Write an Excel formula to calculate total commission based on sales in column B.'\n• সময় বাঁচবে অন্তত ৮০%।"
    },
    {
        "id": next_id + 17,
        "format": "A",
        "hook": "পাসপোর্ট সাইজ ছবি লাগবে আর্জেন্ট?\n*ঘরে বসে ফোনে* পাসপোর্ট ছবি বানান 👇",
        "theme": "black",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• Cutout.pro (Passport Photo Maker) তে যান।\n• যেকোনো সাধারণ ব্যাকগ্রাউন্ডের ছবি আপলোড করুন।\n• এআই স্বয়ংক্রিয়ভাবে সাদা ব্যাকগ্রাউন্ড ও অফিশিয়াল স্যুট/শার্ট পরিয়ে পাসপোর্ট সাইজ প্রিন্ট কপি তৈরি করে দেবে।"
    },
    {
        "id": next_id + 18,
        "format": "A",
        "hook": "AI কি মনগড়া তথ্য দিচ্ছে?\n*Hallucination বন্ধ করার* ২টি জাদুকরী প্রম্পট 👇",
        "theme": "crimson",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• প্রম্পটের শেষে সবসময় যোগ করুন: 'If you are unsure or do not have verified facts, explicitly state \"I do not know\" rather than guessing.'\n• কোনো তথ্যের ক্ষেত্রে লিখুন: 'Provide reputable sources or official URLs for every statistic mentioned.'\n• জটিল তথ্যের জন্য Perplexity AI ব্যবহার করুন।"
    },
    {
        "id": next_id + 19,
        "format": "A",
        "hook": "আপওয়ার্কে বিড করে কাজ পাচ্ছেন না?\n*প্রস্তাব লেখার সেরা* ৩টি টেকনিক 👇",
        "theme": "crimson",
        "cta": "\n\n👉 এমন আরও AI টিপস পেতে ফলো করুন Mamun Hossain",
        "first_comment": "• 'Dear Sir/Mam' বা নিজের গুণগান দিয়ে শুরু করবেন না। প্রথম দুই লাইনেই ক্লায়েন্টের জব পোস্টের সমস্যা তুলে ধরুন।\n• তাদের প্রজেক্টে আপনি কীভাবে হেল্প করবেন তার একটি কুইক একশন প্ল্যান দিন।\n• অতীতে এই ধরনের কাজের একটি লাইভ স্যাম্পল লিংক বা স্ক্রিনশট যুক্ত করুন।"
    }
]

queue.extend(new_posts)
content_file.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Successfully added {len(new_posts)} items! Total items now: {len(queue)}")
