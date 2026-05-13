import re
import json

with open('index-v9.html', 'r', encoding='utf-8') as f:
    content = f.read()

pattern = r'const POINTS = \[(.*?)\];'
match = re.search(pattern, content, re.DOTALL)
if not match:
    print('ERROR: POINTS not found')
    exit(1)

points_content = match.group(1)
points_content = points_content.replace('},,', '}|SEP|')
raw = points_content.split('|SEP|')

points = []
for p in raw:
    p = p.strip()
    if not p or "code:" not in p:
        continue
    code_m = re.search(r"code: '([^']+)'", p)
    name_m = re.search(r"name: '([^']+)'", p)
    meridian_m = re.search(r"meridian: '([^']+)'", p)
    location_m = re.search(r"location: '([^']+)'", p)
    loc_detail_m = re.search(r"locationDetail: '([^']+)'", p)
    indications_m = re.search(r'indications: \[([^\]]+)\]', p)
    technique_m = re.search(r"technique: '([^']+)'", p)
    notes_m = re.search(r"notes: '([^']+)'", p)
    
    if not all([code_m, name_m, meridian_m, location_m]):
        continue
    
    code = code_m.group(1)
    name = name_m.group(1)
    meridian = meridian_m.group(1)
    location = location_m.group(1)
    loc_detail = loc_detail_m.group(1) if loc_detail_m else ''
    technique = technique_m.group(1) if technique_m else ''
    notes = notes_m.group(1) if notes_m else ''
    
    indications = []
    if indications_m:
        indications = re.findall(r"'([^']+)'", indications_m.group(1))
    
    points.append({
        'code': code,
        'name': name,
        'meridian': meridian,
        'location': location,
        'location_detail': loc_detail,
        'indications': indications,
        'technique': technique,
        'notes': notes
    })

print(f'Extracted {len(points)} points')

# Image mapping from ATLAS_IMAGES in index-v9.html
IMAGE_MAP = {
    'Governing Vessel': 'atlas_images_small/p310_img0.jpeg',
    'Extra Point': 'atlas_images_small/p314_img0.jpeg',
    'Large Intestine': 'atlas_images_small/p113_img0.jpeg',
    'Pericardium': 'atlas_images_small/p211_img1.jpeg',
    'Heart': 'atlas_images_small/p213_img0.jpeg',
    'Conception Vessel': 'atlas_images_small/p100_img1.jpeg',
    'Stomach': 'atlas_images_small/p104_img0.jpeg',
    'Spleen': 'atlas_images_small/p206_img0.jpeg',
    'Gallbladder': 'atlas_images_small/p117_img0.jpeg',
    'Liver': 'atlas_images_small/p217_img0.jpeg',
    'Kidney': 'atlas_images_small/p210_img0.jpeg',
    'Bladder': 'atlas_images_small/p308_img0.jpeg',
    'San Jiao': 'atlas_images_small/p111_img0.jpeg',
    'Lung': 'atlas_images_small/p211_img0.jpeg',
    'Small Intestine': 'atlas_images_small/p113_img1.jpeg',
}

# Build HTML
html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Acupuncture Atlas</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0f172a; color: #e2e8f0; font-family: system-ui, sans-serif; min-height: 100vh; }
.header { background: #1e293b; padding: 16px 20px; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; }
.header h1 { color: #fbbf24; font-size: 1.3rem; }
.header .count { color: #64748b; font-size: 0.85rem; }
.search-bar { padding: 12px 20px; background: #1e293b/50; border-bottom: 1px solid #334155; }
.search-bar input { width: 100%; background: #1e293b; border: 1px solid #475569; border-radius: 8px; padding: 10px 14px; color: #e2e8f0; font-size: 0.95rem; }
.search-bar input:focus { outline: none; border-color: #fbbf24; }
.tabs { display: flex; background: #1e293b/50; border-bottom: 1px solid #334155; }
.tab { flex: 1; padding: 12px; text-align: center; cursor: pointer; font-size: 0.9rem; color: #94a3b8; border-bottom: 2px solid transparent; transition: all 0.2s; }
.tab.active { color: #fbbf24; border-bottom-color: #fbbf24; }
.tab:hover { color: #e2e8f0; }
.content { max-width: 900px; margin: 0 auto; padding: 16px; }
.point-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; margin-bottom: 12px; overflow: hidden; transition: border-color 0.2s; }
.point-card:hover { border-color: #fbbf24/50; }
.point-header { padding: 16px; cursor: pointer; display: flex; align-items: center; gap: 12px; }
.point-code { background: #fbbf24; color: #0f172a; font-weight: 800; padding: 6px 10px; border-radius: 6px; font-size: 0.9rem; min-width: 60px; text-align: center; }
.point-name { flex: 1; font-weight: 600; font-size: 1rem; }
.point-meridian { color: #64748b; font-size: 0.8rem; background: #334155; padding: 3px 10px; border-radius: 12px; }
.point-detail { display: none; padding: 0 16px 16px; }
.point-card.open .point-detail { display: block; }
.point-card.open .point-header { border-bottom: 1px solid #334155; }
.detail-section { margin-bottom: 14px; }
.detail-label { color: #fbbf24; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; margin-bottom: 6px; }
.detail-text { color: #cbd5e1; font-size: 0.9rem; line-height: 1.5; }
.indications { display: flex; flex-wrap: wrap; gap: 6px; }
.indication-tag { background: #334155; color: #94a3b8; font-size: 0.78rem; padding: 4px 10px; border-radius: 14px; }
.point-image { width: 100%; max-height: 300px; object-fit: contain; border-radius: 8px; margin-bottom: 12px; background: #0f172a; }
.chevron { color: #64748b; transition: transform 0.2s; font-size: 1.2rem; }
.point-card.open .chevron { transform: rotate(180deg); }
.symptom-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 10px; cursor: pointer; }
.symptom-card:hover { border-color: #fbbf24/50; }
.symptom-name { font-weight: 600; color: #e2e8f0; margin-bottom: 4px; }
.symptom-desc { color: #64748b; font-size: 0.85rem; }
.pattern-detail { display: none; margin-top: 12px; padding-top: 12px; border-top: 1px solid #334155; }
.symptom-card.open .pattern-detail { display: block; }
.pattern-name { color: #fbbf24; font-weight: 600; font-size: 0.9rem; margin-bottom: 8px; }
.pattern-point { background: #0f172a; border-radius: 8px; padding: 12px; margin-bottom: 8px; }
.pattern-point-code { color: #fbbf24; font-weight: 700; }
.pattern-point-why { color: #94a3b8; font-size: 0.85rem; margin-top: 4px; }
.diagnostic { color: #64748b; font-size: 0.8rem; font-style: italic; margin-top: 8px; }
.chat-container { display: flex; flex-direction: column; height: calc(100vh - 180px); }
.chat-messages { flex: 1; overflow-y: auto; padding: 12px 0; }
.chat-msg { margin-bottom: 12px; max-width: 85%; padding: 12px 16px; border-radius: 16px; font-size: 0.9rem; line-height: 1.5; }
.chat-msg.user { background: #fbbf24/20; color: #fef3c7; margin-left: auto; border-bottom-right-radius: 4px; }
.chat-msg.assistant { background: #1e293b; color: #e2e8f0; margin-right: auto; border-bottom-left-radius: 4px; }
.chat-input-area { display: flex; gap: 8px; padding: 12px 0; border-top: 1px solid #334155; }
.chat-input { flex: 1; background: #1e293b; border: 1px solid #475569; border-radius: 10px; padding: 12px; color: #e2e8f0; font-size: 0.9rem; }
.chat-input:focus { outline: none; border-color: #fbbf24; }
.chat-send { background: #fbbf24; color: #0f172a; border: none; border-radius: 10px; padding: 12px 18px; font-weight: 600; cursor: pointer; }
.chat-send:disabled { opacity: 0.4; }
.settings-panel { display: none; background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
.settings-panel.open { display: block; }
.setting-row { margin-bottom: 12px; }
.setting-label { color: #94a3b8; font-size: 0.85rem; margin-bottom: 4px; }
.setting-input { width: 100%; background: #0f172a; border: 1px solid #475569; border-radius: 8px; padding: 10px; color: #e2e8f0; }
.settings-toggle { background: none; border: none; color: #64748b; cursor: pointer; font-size: 1.2rem; padding: 4px; }
.empty-chat { text-align: center; padding: 40px 20px; color: #64748b; }
.quick-btn { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px 14px; color: #94a3b8; font-size: 0.85rem; cursor: pointer; margin: 6px 0; width: 100%; text-align: left; }
.quick-btn:hover { border-color: #fbbf24/50; color: #e2e8f0; }
.typing { color: #64748b; font-size: 0.9rem; padding: 12px; }
</style>
</head>
<body>
<div class="header">
    <h1>Acupuncture Atlas</h1>
    <div style="display:flex;align-items:center;gap:12px;">
        <span class="count" id="pointCount"></span>
        <button class="settings-toggle" id="settingsToggle">&#9881;</button>
    </div>
</div>
<div class="search-bar" id="searchBar">
    <input type="text" id="searchInput" placeholder="Search points, symptoms...">
</div>
<div class="tabs">
    <div class="tab active" data-tab="atlas">Atlas</div>
    <div class="tab" data-tab="symptoms">Symptoms</div>
    <div class="tab" data-tab="chat">AI Chat</div>
</div>
<div class="content" id="content"></div>

<script>
const IMAGE_MAP = ''' + json.dumps(IMAGE_MAP) + ''';

const POINTS = ''' + json.dumps(points, ensure_ascii=False) + ''';

const SYMPTOMS = {
  "Head & Face": [
    { name: "Headache", desc: "General headache, tension headache",
      patterns: [
        { name: "Liver Yang Rising", points: [{code:"LV3",name:"Taichong",why:"Source point of Liver. Drains ascending Liver Yang."},{code:"GV20",name:"Baihui",why:"Subdues rising Yang, calms the head."},{code:"GB20",name:"Fengchi",why:"Descends Yang, relieves occipital tension."},{code:"KI3",name:"Taixi",why:"Nourishes Kidney Yin to anchor Yang."}], diag: "Tongue: red sides. Pulse: wiry. Irritability, red face, tinnitus, worse with stress." },
        { name: "Qi Stagnation", points: [{code:"LI4",name:"Hegu",why:"Moves Qi and Blood. Face and mouth: seek Hegu."},{code:"LV3",name:"Taichong",why:"Spreads stagnant Liver Qi."},{code:"SJ5",name:"Waiguan",why:"Opens Shaoyang channel, moves Qi in temples."},{code:"GB8",name:"Shuaigu",why:"Local point for temporal headache."}], diag: "Tongue: normal or slightly dark. Pulse: wiry. Distending pain, worse with stress." },
        { name: "Blood Deficiency", points: [{code:"GV20",name:"Baihui",why:"Raises clear Yang to the head."},{code:"ST36",name:"Zusanli",why:"Tonifies Qi and Blood."},{code:"SP6",name:"Sanyinjiao",why:"Nourishes Blood."},{code:"LI4",name:"Hegu",why:"Gentle pain relief without draining."}], diag: "Tongue: pale. Pulse: thin. Dull headache, dizziness, worse with exertion." }
      ]
    },
    { name: "Nasal congestion / Sinusitis", desc: "Stuffy nose, sinus pressure",
      patterns: [
        { name: "Wind-Cold", points: [{code:"LI20",name:"Yingxiang",why:"Opens nasal passages."},{code:"LI4",name:"Hegu",why:"Releases exterior, opens nose."},{code:"GV14",name:"Dazhui",why:"Releases exterior, expels cold."},{code:"GB20",name:"Fengchi",why:"Expels wind from head."}], diag: "Tongue: thin white coat. Pulse: floating tight. Clear discharge, aversion to cold." },
        { name: "Wind-Heat", points: [{code:"LI20",name:"Yingxiang",why:"Opens nose, clears heat."},{code:"LI11",name:"Quchi",why:"Clears heat, reduces fever."},{code:"LI4",name:"Hegu",why:"Releases exterior heat."},{code:"SJ5",name:"Waiguan",why:"Clears heat from Shaoyang."}], diag: "Tongue: red tip, thin yellow coat. Thick yellow discharge, fever." },
        { name: "Damp-Heat", points: [{code:"LI20",name:"Yingxiang",why:"Local point for nose."},{code:"ST40",name:"Fenglong",why:"Resolves phlegm-damp."},{code:"SP6",name:"Sanyinjiao",why:"Transforms dampness."},{code:"LI11",name:"Quchi",why:"Clears heat."}], diag: "Tongue: thick yellow greasy coat. Thick sticky discharge, facial pressure." }
      ]
    },
    { name: "Toothache", desc: "Tooth pain, dental pain",
      patterns: [
        { name: "Stomach Fire", points: [{code:"LI4",name:"Hegu",why:"Master analgesic. LI goes through teeth."},{code:"ST6",name:"Jiache",why:"Local point for lower jaw."},{code:"ST36",name:"Zusanli",why:"Clears Stomach heat."},{code:"ST44",name:"Neiting",why:"Ying-Spring point, clears Stomach fire."}], diag: "Tongue: red, yellow coat. Severe burning pain, swollen gums, thirst." },
        { name: "Kidney Yin Deficiency", points: [{code:"KI3",name:"Taixi",why:"Nourishes Kidney Yin."},{code:"LI4",name:"Hegu",why:"Pain relief."},{code:"ST6",name:"Jiache",why:"Local point."},{code:"SP6",name:"Sanyinjiao",why:"Nourishes Yin."}], diag: "Tongue: red, little coat. Dull ache, loose teeth, night sweating." }
      ]
    }
  ],
  "Digestive": [
    { name: "Nausea / Vomiting", desc: "Morning sickness, motion sickness, chemo",
      patterns: [
        { name: "Stomach Cold", points: [{code:"PC6",name:"Neiguan",why:"THE anti-nausea point."},{code:"CV12",name:"Zhongwan",why:"Warms the middle jiao."},{code:"ST36",name:"Zusanli",why:"Harmonizes Stomach."},{code:"CV6",name:"Qihai",why:"Warms with moxa."}], diag: "Tongue: pale, white coat. Cold sensation, relief with warmth." },
        { name: "Stomach Heat", points: [{code:"PC6",name:"Neiguan",why:"Anti-nausea."},{code:"CV12",name:"Zhongwan",why:"Clears Stomach heat."},{code:"ST44",name:"Neiting",why:"Clears Stomach fire."},{code:"LI11",name:"Quchi",why:"Clears heat."}], diag: "Tongue: red, yellow coat. Burning sensation, bitter taste." },
        { name: "Liver Qi Invading Stomach", points: [{code:"PC6",name:"Neiguan",why:"Stops nausea."},{code:"LV3",name:"Taichong",why:"Soothes Liver Qi."},{code:"CV12",name:"Zhongwan",why:"Harmonizes Stomach."},{code:"GB34",name:"Yanglingquan",why:"Regulates Liver Qi."}], diag: "Tongue: red sides. Nausea triggered by stress, belching." }
      ]
    },
    { name: "Stomach pain / Bloating", desc: "Epigastric pain, fullness after eating",
      patterns: [
        { name: "Cold in Stomach", points: [{code:"CV12",name:"Zhongwan",why:"Front-Mu of Stomach."},{code:"ST36",name:"Zusanli",why:"Warms middle jiao."},{code:"CV6",name:"Qihai",why:"Warms with moxa."},{code:"SP6",name:"Sanyinjiao",why:"Transforms cold-damp."}], diag: "Tongue: pale, white coat. Pain relieved by warmth." },
        { name: "Damp-Heat in Stomach", points: [{code:"CV12",name:"Zhongwan",why:"Regulates Stomach."},{code:"ST36",name:"Zusanli",why:"Transforms damp."},{code:"SP9",name:"Yinlingquan",why:"Clears damp-heat."},{code:"ST44",name:"Neiting",why:"Clears heat."}], diag: "Tongue: yellow greasy coat. Burning pain, thirst." },
        { name: "Food Stagnation", points: [{code:"CV12",name:"Zhongwan",why:"Promotes digestion."},{code:"ST36",name:"Zusanli",why:"Harmonizes Stomach."},{code:"ST25",name:"Tianshu",why:"Moves stagnation."},{code:"ST44",name:"Neiting",why:"Clears heat from stagnation."}], diag: "Tongue: thick greasy coat. Bloating after eating, belching." }
      ]
    },
    { name: "Diarrhea", desc: "Loose stools, chronic diarrhea",
      patterns: [
        { name: "Spleen Qi Deficiency", points: [{code:"ST25",name:"Tianshu",why:"Regulates Large Intestine."},{code:"ST36",name:"Zusanli",why:"Tonifies Spleen Qi."},{code:"SP6",name:"Sanyinjiao",why:"Strengthens Spleen."},{code:"CV6",name:"Qihai",why:"Warms with moxa."}], diag: "Tongue: pale, teeth marks. Chronic, fatigue, poor appetite." },
        { name: "Damp-Heat in Intestines", points: [{code:"ST25",name:"Tianshu",why:"Regulates intestines."},{code:"ST36",name:"Zusanli",why:"Transforms damp."},{code:"ST44",name:"Neiting",why:"Clears damp-heat."},{code:"BL25",name:"Dachangshu",why:"Back-Shu of Large Intestine."}], diag: "Tongue: red, yellow greasy coat. Urgent, burning, foul odor." }
      ]
    },
    { name: "Constipation", desc: "Difficulty passing stool",
      patterns: [
        { name: "Heat in Intestines", points: [{code:"ST25",name:"Tianshu",why:"Regulates Large Intestine."},{code:"ST36",name:"Zusanli",why:"Promotes peristalsis."},{code:"ST44",name:"Neiting",why:"Clears heat, moistens."},{code:"BL25",name:"Dachangshu",why:"Back-Shu of Large Intestine."}], diag: "Tongue: red, yellow dry coat. Dry hard stool, burning anus." },
        { name: "Blood Deficiency", points: [{code:"ST25",name:"Tianshu",why:"Regulates intestines."},{code:"ST36",name:"Zusanli",why:"Generates Blood."},{code:"SP6",name:"Sanyinjiao",why:"Nourishes Blood, moistens."},{code:"KI6",name:"Zhaohai",why:"Moistens intestines."}], diag: "Tongue: pale. Dry stool, dizziness, common in elderly." },
        { name: "Qi Stagnation", points: [{code:"ST25",name:"Tianshu",why:"Moves Qi in intestines."},{code:"LV3",name:"Taichong",why:"Moves Liver Qi."},{code:"ST36",name:"Zusanli",why:"Promotes descent."},{code:"CV6",name:"Qihai",why:"Moves Qi."}], diag: "Tongue: normal or slightly dark. Bloating, worse with stress." }
      ]
    }
  ],
  "Mental-Emotional": [
    { name: "Insomnia", desc: "Difficulty falling asleep, staying asleep",
      patterns: [
        { name: "Heart Blood Deficiency", points: [{code:"HT7",name:"Shenmen",why:"Calms Shen. Primary point for sleep."},{code:"SP6",name:"Sanyinjiao",why:"Nourishes Blood."},{code:"ST36",name:"Zusanli",why:"Generates Blood."},{code:"Yintang",name:"Yintang",why:"Calms mind."}], diag: "Tongue: pale. Difficulty staying asleep, palpitations." },
        { name: "Liver Fire", points: [{code:"HT7",name:"Shenmen",why:"Calms Shen."},{code:"LV3",name:"Taichong",why:"Drains Liver fire."},{code:"GV20",name:"Baihui",why:"Calms spirit."},{code:"PC6",name:"Neiguan",why:"Calms heart."}], diag: "Tongue: red sides. Wakes at 1-3am, irritability, vivid dreams." },
        { name: "Kidney Yin Deficiency", points: [{code:"HT7",name:"Shenmen",why:"Calms Shen."},{code:"KI3",name:"Taixi",why:"Nourishes Kidney Yin."},{code:"SP6",name:"Sanyinjiao",why:"Nourishes Yin."},{code:"Yintang",name:"Yintang",why:"Calms mind."}], diag: "Tongue: red, little coat. Night sweating, tinnitus, five-palm heat." }
      ]
    },
    { name: "Anxiety / Stress", desc: "Nervousness, worry, feeling overwhelmed",
      patterns: [
        { name: "Heart Qi Deficiency", points: [{code:"HT7",name:"Shenmen",why:"Calms Shen."},{code:"PC6",name:"Neiguan",why:"Calms heart."},{code:"CV17",name:"Danzhong",why:"Opens chest."},{code:"ST36",name:"Zusanli",why:"Tonifies Qi."}], diag: "Tongue: pale. Palpitations, shortness of breath, fatigue." },
        { name: "Liver Qi Stagnation", points: [{code:"LV3",name:"Taichong",why:"Moves stagnant Qi."},{code:"HT7",name:"Shenmen",why:"Calms Shen."},{code:"CV17",name:"Danzhong",why:"Opens chest."},{code:"GB34",name:"Yanglingquan",why:"Soothes Liver."}], diag: "Tongue: normal or red sides. Tension, chest tightness, sighing." }
      ]
    },
    { name: "Depression", desc: "Low mood, lack of motivation",
      patterns: [
        { name: "Liver Qi Stagnation", points: [{code:"GV20",name:"Baihui",why:"Raises Yang, lifts mood."},{code:"LV3",name:"Taichong",why:"Moves Qi."},{code:"CV17",name:"Danzhong",why:"Opens chest."},{code:"PC6",name:"Neiguan",why:"Calms heart."}], diag: "Tongue: normal. Emotional constraint, chest distension." },
        { name: "Spleen Qi Deficiency with Phlegm", points: [{code:"ST36",name:"Zusanli",why:"Tonifies Qi."},{code:"SP6",name:"Sanyinjiao",why:"Transforms phlegm."},{code:"ST40",name:"Fenglong",why:"Resolves phlegm."},{code:"GV20",name:"Baihui",why:"Raises clear Yang."}], diag: "Tongue: pale, swollen, teeth marks. Heaviness, foggy mind, overthinking." }
      ]
    }
  ],
  "Pain": [
    { name: "Lower back pain", desc: "Lumbar pain, sciatica, back strain",
      patterns: [
        { name: "Kidney Deficiency", points: [{code:"BL23",name:"Shenshu",why:"Back-Shu of Kidneys."},{code:"KI3",name:"Taixi",why:"Source point of Kidneys."},{code:"GV4",name:"Mingmen",why:"Tonifies Yang."},{code:"BL40",name:"Weizhong",why:"Command point for back."}], diag: "Tongue: pale or red. Chronic, worse with exertion, soreness." },
        { name: "Cold-Damp Bi", points: [{code:"BL23",name:"Shenshu",why:"Back-Shu of Kidneys."},{code:"BL40",name:"Weizhong",why:"Opens channel."},{code:"GV4",name:"Mingmen",why:"Warms with moxa."},{code:"GB30",name:"Huantiao",why:"Opens hip channel."}], diag: "Tongue: pale, white greasy coat. Heavy sensation, worse in cold/damp." },
        { name: "Blood Stagnation", points: [{code:"BL40",name:"Weizhong",why:"Command point. Bleed for acute pain."},{code:"BL23",name:"Shenshu",why:"Back-Shu."},{code:"GV1",name:"Changqiang",why:"Opens channel."},{code:"SP10",name:"Xuehai",why:"Moves Blood."}], diag: "Tongue: dark spots. Stabbing pain, fixed location, worse at night." }
      ]
    }
  ],
  "Women's Health": [
    { name: "Menstrual pain", desc: "Painful periods, cramps",
      patterns: [
        { name: "Cold in Uterus", points: [{code:"SP6",name:"Sanyinjiao",why:"Primary gynecology point."},{code:"CV4",name:"Guanyuan",why:"Warms uterus."},{code:"CV6",name:"Qihai",why:"Warms with moxa."},{code:"ST29",name:"Guilai",why:"Local point."}], diag: "Tongue: pale, white coat. Cramping relieved by warmth, dark clots." },
        { name: "Qi and Blood Stagnation", points: [{code:"SP6",name:"Sanyinjiao",why:"Moves Blood."},{code:"LI4",name:"Hegu",why:"Moves Qi and Blood."},{code:"LV3",name:"Taichong",why:"Moves Liver Qi."},{code:"SP8",name:"Diji",why:"Xi-cleft, stops pain."}], diag: "Tongue: dark, purple spots. Sharp pain, clots, relief after passing." }
      ]
    }
  ]
};

let currentTab = 'atlas';
let searchQuery = '';
let ollamaUrl = localStorage.getItem('ollamaUrl') || 'http://localhost:11434';
let modelName = localStorage.getItem('modelName') || 'qwen2.5:7b';
let chatMessages = [];
let isTyping = false;

document.getElementById('pointCount').textContent = POINTS.length + ' points';

// Tabs
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentTab = tab.dataset.tab;
        document.getElementById('searchBar').style.display = currentTab === 'chat' ? 'none' : 'block';
        render();
    });
});

// Search
document.getElementById('searchInput').addEventListener('input', (e) => {
    searchQuery = e.target.value.toLowerCase();
    render();
});

// Settings toggle
document.getElementById('settingsToggle').addEventListener('click', () => {
    const panel = document.getElementById('settingsPanel');
    panel.classList.toggle('open');
});

// Chat send
function sendChat() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text || isTyping) return;
    chatMessages.push({ role: 'user', content: text });
    input.value = '';
    isTyping = true;
    render();
    scrollToBottom();

    fetch(ollamaUrl + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: modelName,
            messages: [
                { role: 'system', content: 'You are an expert acupuncturist. For each query: 1) List ALL possible TCM patterns (excess/deficiency, heat/cold, qi stagnation, blood stasis, yin/yang imbalance). 2) For each pattern, give a clear recipe with point codes, locations, and rationale. 3) Label each recipe clearly: "Pattern: X". 4) Include diagnostic questions (tongue, pulse, associated symptoms) to help choose between patterns. 5) Be practical and reference specific points with location instructions.' },
                ...chatMessages.slice(-8).map(m => ({ role: m.role, content: m.content }))
            ],
            stream: true,
        }),
    }).then(res => {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        chatMessages.push({ role: 'assistant', content: '' });
        isTyping = true;
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let content = '';
        function read() {
            return reader.read().then(({ done, value }) => {
                if (done) { isTyping = false; render(); return; }
                const chunk = decoder.decode(value);
                const lines = chunk.split('\\n').filter(Boolean);
                for (const line of lines) {
                    try {
                        const data = JSON.parse(line);
                        if (data.message && data.message.content) {
                            content += data.message.content;
                            chatMessages[chatMessages.length - 1].content = content;
                            render();
                            scrollToBottom();
                        }
                    } catch (e) {}
                }
                return read();
            });
        }
        return read();
    }).catch(err => {
        chatMessages.push({ role: 'assistant', content: 'Connection error: ' + err.message + '. Check settings -> Ollama URL.' });
        isTyping = false;
        render();
    });
}

function scrollToBottom() {
    setTimeout(() => {
        const el = document.querySelector('.chat-messages');
        if (el) el.scrollTop = el.scrollHeight;
    }, 50);
}

function findPoint(code) {
    return POINTS.find(p => p.code === code);
}

function getImageUrl(point) {
    return IMAGE_MAP[point.meridian] || '';
}

function renderAtlas() {
    const filtered = POINTS.filter(p => {
        if (!searchQuery) return true;
        return p.code.toLowerCase().includes(searchQuery) || 
               p.name.toLowerCase().includes(searchQuery) || 
               p.meridian.toLowerCase().includes(searchQuery) ||
               p.location.toLowerCase().includes(searchQuery);
    });

    let html = '';
    filtered.forEach(p => {
        const img = getImageUrl(p);
        html += '<div class="point-card" id="point-' + p.code + '">';
        html += '<div class="point-header" onclick="togglePoint(\\'' + p.code + '\\')">';
        html += '<div class="point-code">' + p.code + '</div>';
        html += '<div class="point-name">' + p.name + '</div>';
        html += '<div class="point-meridian">' + p.meridian + '</div>';
        html += '<div class="chevron">&#9660;</div>';
        html += '</div>';
        html += '<div class="point-detail">';
        if (img) {
            html += '<img class="point-image" src="' + img + '" alt="' + p.meridian + '" loading="lazy" onerror="this.style.display=\\'none\\'">';
        }
        html += '<div class="detail-section"><div class="detail-label">Location</div><div class="detail-text">' + p.location + '</div></div>';
        if (p.location_detail) {
            html += '<div class="detail-section"><div class="detail-label">Step by step</div><div class="detail-text">' + p.location_detail + '</div></div>';
        }
        if (p.technique) {
            html += '<div class="detail-section"><div class="detail-label">Needling technique</div><div class="detail-text">' + p.technique + '</div></div>';
        }
        if (p.notes) {
            html += '<div class="detail-section"><div class="detail-label">Notes</div><div class="detail-text">' + p.notes + '</div></div>';
        }
        html += '<div class="detail-section"><div class="detail-label">Indications</div><div class="indications">';
        p.indications.forEach(ind => {
            html += '<span class="indication-tag">' + ind + '</span>';
        });
        html += '</div></div></div></div>';
    });
    return html;
}

function renderSymptoms() {
    let html = '';
    for (const [category, symptoms] of Object.entries(SYMPTOMS)) {
        const filtered = symptoms.filter(s => !searchQuery || s.name.toLowerCase().includes(searchQuery));
        if (filtered.length === 0) continue;
        html += '<h3 style="color:#fbbf24;margin:20px 0 10px;font-size:1.1rem;">' + category + '</h3>';
        filtered.forEach((s, si) => {
            html += '<div class="symptom-card" id="symptom-' + category + '-' + si + '" onclick="toggleSymptom(\\'' + category + '-' + si + '\\')">';
            html += '<div class="symptom-name">' + s.name + '</div>';
            html += '<div class="symptom-desc">' + s.desc + '</div>';
            html += '<div style="color:#64748b;font-size:0.75rem;margin-top:4px;">' + s.patterns.map(p => p.name).join(' &#8226; ') + '</div>';
            html += '<div class="pattern-detail">';
            s.patterns.forEach((pat, pi) => {
                html += '<div class="pattern-name">Pattern: ' + pat.name + '</div>';
                pat.points.forEach(pt => {
                    const full = findPoint(pt.code);
                    html += '<div class="pattern-point">';
                    html += '<div class="pattern-point-code">' + pt.code + ' ' + (full ? full.name : pt.name) + '</div>';
                    html += '<div class="pattern-point-why">' + pt.why + '</div>';
                    if (full) {
                        html += '<div style="color:#64748b;font-size:0.8rem;margin-top:4px;">Find: ' + full.location + '</div>';
                    }
                    html += '</div>';
                });
                html += '<div class="diagnostic">' + pat.diag + '</div>';
            });
            html += '</div></div>';
        });
    }
    return html;
}

function renderChat() {
    let html = '<div class="settings-panel" id="settingsPanel">';
    html += '<div class="setting-row"><div class="setting-label">Ollama URL</div><input class="setting-input" id="ollamaUrlInput" value="' + ollamaUrl + '" placeholder="http://localhost:11434"></div>';
    html += '<div class="setting-row"><div class="setting-label">Model</div><input class="setting-input" id="modelNameInput" value="' + modelName + '" placeholder="qwen2.5:7b"></div>';
    html += '<button class="quick-btn" onclick="saveSettings()">Save Settings</button>';
    html += '</div>';

    html += '<div class="chat-container">';
    html += '<div class="chat-messages">';

    if (chatMessages.length === 0) {
        html += '<div class="empty-chat">';
        html += '<p style="font-size:1.1rem;margin-bottom:20px;">Ask about acupuncture points, symptoms, or treatments</p>';
        html += '<button class="quick-btn" onclick="document.getElementById(\\'chatInput\\').value=\\'Points for headache\\';sendChat();">Points for headache?</button>';
        html += '<button class="quick-btn" onclick="document.getElementById(\\'chatInput\\').value=\\'Tell me about ST36 Zusanli\\';sendChat();">Tell me about ST36 Zusanli</button>';
        html += '<button class="quick-btn" onclick="document.getElementById(\\'chatInput\\').value=\\'Recipe for stress and anxiety\\';sendChat();">Recipe for stress and anxiety</button>';
        html += '<button class="quick-btn" onclick="document.getElementById(\\'chatInput\\').value=\\'Points for lower back pain with patterns\\';sendChat();">Points for lower back pain</button>';
        html += '</div>';
    } else {
        chatMessages.forEach(msg => {
            html += '<div class="chat-msg ' + msg.role + '">' + msg.content.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>').replace(/\\n/g, '<br>') + '</div>';
        });
        if (isTyping) {
            html += '<div class="typing">Thinking...</div>';
        }
    }

    html += '</div>';
    html += '<div class="chat-input-area">';
    html += '<input class="chat-input" id="chatInput" placeholder="Ask about acupuncture..." onkeydown="if(event.key===\\'Enter\\')sendChat()">';
    html += '<button class="chat-send" onclick="sendChat()" id="sendBtn" ' + (isTyping ? 'disabled' : '') + '>Send</button>';
    html += '</div></div>';
    return html;
}

function render() {
    const content = document.getElementById('content');
    if (currentTab === 'atlas') {
        content.innerHTML = renderAtlas();
    } else if (currentTab === 'symptoms') {
        content.innerHTML = renderSymptoms();
    } else {
        content.innerHTML = renderChat();
        scrollToBottom();
    }
}

function togglePoint(code) {
    const el = document.getElementById('point-' + code);
    el.classList.toggle('open');
}

function toggleSymptom(id) {
    const el = document.getElementById('symptom-' + id);
    el.classList.toggle('open');
}

function saveSettings() {
    ollamaUrl = document.getElementById('ollamaUrlInput').value;
    modelName = document.getElementById('modelNameInput').value;
    localStorage.setItem('ollamaUrl', ollamaUrl);
    localStorage.setItem('modelName', modelName);
    document.getElementById('settingsPanel').classList.remove('open');
}

render();
</script>
</body>
</html>'''

with open('/root/acupuncture/static_enhanced_final.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('SUCCESS: Generated static_enhanced_final.html')
print('File size:', len(html), 'bytes')
