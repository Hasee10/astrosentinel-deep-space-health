"""Rebuild README animations: python docs/readme/generate_assets.py (Pillow)."""
from pathlib import Path
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FONT = Path('C:/Windows/Fonts/arial.ttf')
if not FONT.exists():
    FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
def font(size):
    return ImageFont.truetype(str(FONT), size)

W, H = 1200, 420
base = ImageOps.fit(Image.open(ROOT/'frontend/public/images/astronaut-earth.webp').convert('RGB'), (W,H), centering=(.75,.5)).convert('RGBA')
veil = Image.new('RGBA',(W,H))
p = veil.load()
for x in range(W):
    for y in range(H):
        p[x,y] = (3,14,23, int(244*(1-x/W)**.55))
base = Image.alpha_composite(base,veil)
d = ImageDraw.Draw(base)
d.text((54,40),'HUMAN PERFORMANCE / DEEP SPACE',font=font(14),fill='#a2d9d0')
d.text((50,93),'ASTROSENTINEL',font=font(64),fill='#f0f6f7')
d.text((54,184),'Beyond Earth. Ahead of risk.',font=font(29),fill='#b5e7dc')
d.text((54,238),'Independent evidence. Clearer decisions.',font=font(18),fill='#d7e5eb')
d.text((54,267),'A synthetic crew-health research platform.',font=font(18),fill='#a6bbc6')
d.line((54,321,1146,321),fill='#36555c',width=1)
d.text((54,345),'300 PROFILES    /    30 DAYS    /    2 OUTCOMES',font=font(16),fill='#d2e8e7')
frames=[]
rng=random.Random(2026)
stars=[(rng.randrange(730,1180),rng.randrange(20,300),rng.random()*math.tau) for _ in range(22)]
for i in range(36):
    im=base.copy();d=ImageDraw.Draw(im)
    for x,y,phase in stars:
        c=int(130+100*math.sin(i/36*math.tau+phase));d.ellipse((x,y,x+1,y+1),fill=(c,c,min(255,c+20)))
    pulse=(math.sin(i/36*math.tau)+1)/2
    radius=4+int(pulse*3)
    d.ellipse((1081-radius,353-radius,1081+radius,353+radius),fill=(70,int(155+pulse*80),190))
    d.text((1096,345),'SIM',font=font(15),fill='#c4eee6')
    frames.append(im.convert('RGB'))
banner_palette=base.convert('RGB').quantize(colors=160)
frames=[im.quantize(palette=banner_palette) for im in frames]
frames[0].save(OUT/'mission-banner.gif',save_all=True,append_images=frames[1:],duration=85,loop=0,optimize=True,disposal=1)

shots=[
 ('01-landing.jpg','01 / THE MISSION','The next frontier is human.'),
 ('02-cohort.jpg','02 / MISSION CONTROL','Explore 300 synthetic astronaut profiles.'),
 ('03-assessments.jpg','03 / ENGINEERING EXAMPLE','Independent SANS and venous assessments.'),
 ('04-timeline.jpg','04 / TIME-ORDERED EVIDENCE','Follow ultrasound observations across the mission.'),
 ('05-earth.jpg','05 / EARTH LINK','Distinguish onboard evidence from received snapshots.'),
 ('06-consultation.jpg','06 / SIMULATED CONSULTATION','Trace the request, ground response and audit trail.'),
 ('07-comparison.jpg','07 / ENGINEERING COMPARISON','Inspect scan burden and scheduling trade-offs.'),
]
cards=[]
for name,kicker,title in shots:
    im=Image.new('RGB',(960,612),'#081720');d=ImageDraw.Draw(im)
    d.text((22,12),kicker,font=font(12),fill='#94d6c8')
    d.text((22,33),title,font=font(18),fill='#eef5f6')
    screen=ImageOps.fit(Image.open(OUT/'screens'/name).convert('RGB'),(960,540))
    im.paste(screen,(0,72));cards.append(im)
palette_source=Image.new('RGB',(960,612*len(cards)))
for i,im in enumerate(cards):palette_source.paste(im,(0,612*i))
palette=palette_source.quantize(colors=192)
gif=[];durations=[]
for i,card in enumerate(cards):
    gif.append(card.quantize(palette=palette));durations.append(2300)
    following=cards[(i+1)%len(cards)]
    for n in range(1,7):
        gif.append(Image.blend(card,following,n/7).quantize(palette=palette));durations.append(70)
gif[0].save(OUT/'platform-tour.gif',save_all=True,append_images=gif[1:],duration=durations,loop=0,optimize=True,disposal=1)
print('Built mission-banner.gif and platform-tour.gif')
