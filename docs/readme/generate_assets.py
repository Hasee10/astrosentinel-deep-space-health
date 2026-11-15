"""Rebuild README animations: python docs/readme/generate_assets.py (Pillow)."""
from pathlib import Path
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FONT = Path('C:/Windows/Fonts/consola.ttf')
if not FONT.exists():
    FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
def font(size):
    return ImageFont.truetype(str(FONT), size)

BG='#06121e'; GRID='#102534'; MINT='#85f4ce'; BLUE='#64b5ff'; CORAL='#ff8c9e'; WHITE='#edf6ff'; MUTED='#8da9be'

def cursor(d,x,y,click=False):
    pattern=['10000000','11000000','12100000','12210000','12221000','12222100','12222210','12211111','12121000','11012100','00012100','00001100']
    for yy,row in enumerate(pattern):
        for xx,c in enumerate(row):
            if c!='0':d.rectangle((x+xx*3,y+yy*3,x+xx*3+2,y+yy*3+2),fill=WHITE if c=='2' else BG)
    if click:d.rectangle((x-10,y-10,x+30,y+40),outline=MINT,width=2)

def astronaut(d,x,y,scale=5):
    sprite=['000000111111000000','000011222222110000','000122333333221000','001223333333322100','001233444443332100','001233444443332100','001223333333322100','000122222222221000','000011222222110000','001112211112211100','012222222222222210','122222255552222221','122122255552221221','122122222222221221','011122222222221110','000122222222221000','000122211112221000','000122210012221000','001222210012222100','001111110011111100']
    colors={'1':'#4a7591','2':'#d5e9ed','3':'#163b56','4':BLUE,'5':CORAL}
    for yy,row in enumerate(sprite):
        for xx,c in enumerate(row):
            if c!='0':d.rectangle((x+xx*scale,y+yy*scale,x+(xx+1)*scale-1,y+(yy+1)*scale-1),fill=colors[c])

def canvas(size):
    im=Image.new('RGB',size,BG);d=ImageDraw.Draw(im)
    for x in range(0,size[0],32):d.line((x,0,x,size[1]),fill=GRID)
    for y in range(0,size[1],32):d.line((0,y,size[0],y),fill=GRID)
    return im

def save(frames,name,durations):
    palette_image=Image.new('RGB',(frames[0].width,frames[0].height*min(8,len(frames))))
    for i,im in enumerate(frames[::max(1,len(frames)//8)][:8]):palette_image.paste(im,(0,i*im.height))
    palette=palette_image.quantize(colors=128)
    packed=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    packed[0].save(OUT/name,save_all=True,append_images=packed[1:],duration=durations,loop=0,optimize=True,disposal=1)

frames=[]
for i in range(80):
    t=i/80;im=canvas((1200,440));d=ImageDraw.Draw(im)
    d.text((40,26),'[ ASTROSENTINEL / MISSION SYSTEMS ]',font=font(16),fill=MINT)
    d.text((36,87),'ASTROSENTINEL',font=font(56),fill=WHITE)
    if i%12<6:d.rectangle((443,146,463,150),fill=MINT)
    d.text((40,171),'BEYOND EARTH. AHEAD OF RISK.',font=font(22),fill=MINT)
    d.text((40,217),'OBSERVE  >  ASSESS  >  TRANSMIT'[:min(30,i+1)],font=font(16),fill=MUTED)
    d.text((40,282),'300 CREW PROFILES',font=font(18),fill=WHITE)
    d.text((40,312),'030 MISSION DAYS  /  SYNTHETIC',font=font(16),fill=MUTED)
    # A pixel astronaut floats between the terminal and the medical telemetry.
    astronaut(d,618,160+int(8*math.sin(t*math.tau)),6)
    for n in range(8):
        x=565+n*23;y=350+int(12*math.sin(n*.7+t*math.tau))
        d.rectangle((x,y,x+4,y+4),fill=BLUE)
    for idx,(title,sub,col) in enumerate([('SANS / OPTIC NERVE','PERSONAL BASELINE + ONSD',MINT),('VENOUS / FLOW','JUGULAR AREA + FLOW CLASS',CORAL)]):
        y=62+idx*150;active=(i//40)==idx
        d.rectangle((790,y,1158,y+126),fill='#0b2030',outline=col if active else '#2a4355',width=2)
        d.text((812,y+15),title,font=font(20),fill=col)
        d.text((812,y+46),sub,font=font(14),fill=MUTED)
        points=[(812+x,y+91+int(9*math.sin(x/22+t*math.tau))) for x in range(0,320,4)]
        d.line(points,fill=col,width=2)
        scan=812+(i*6)%320;d.line((scan,y+74,scan,y+108),fill=WHITE,width=2)
    phase=(math.sin(t*math.tau-math.pi/2)+1)/2
    cursor(d,1082,109+int(phase*150),i%40 in [16,17,18])
    d.rectangle((0,394,1200,440),fill='#0c2331')
    d.text((40,409),'SIMULATION ONLINE',font=font(14),fill=MINT)
    d.text((388,409),'INDEPENDENT OUTCOMES / EXPLAINABLE EVIDENCE',font=font(14),fill=MUTED)
    d.rectangle((1120,410,1130,420),fill=MINT if i%16<8 else '#254a49')
    frames.append(im)
save(frames,'mission-banner.gif',90)

# Illustrative anatomy and signal movement; never a fabricated clinical plot.
frames=[]
for i in range(64):
    t=i/64;im=canvas((1200,340));d=ImageDraw.Draw(im)
    for x,title,subtitle,col in [(28,'01 / SANS','EYE + OPTIC-NERVE MONITORING',MINT),(620,'02 / VENOUS STASIS','JUGULAR AREA + FLOW MONITORING',CORAL)]:
        d.rectangle((x,20,x+550,296),fill='#0b1e2c',outline='#2a4355',width=2)
        d.text((x+22,37),title,font=font(23),fill=col)
        d.text((x+22,73),subtitle,font=font(15),fill=MUTED)
    # Stylized eye cross-section and optic nerve with a moving scan line.
    d.ellipse((75,125,275,249),outline=MINT,width=3)
    d.ellipse((107,157,155,217),outline=BLUE,width=3)
    d.ellipse((121,175,139,199),fill=BLUE)
    d.line((271,165,410,145),fill=MINT,width=4);d.line((271,209,410,229),fill=MINT,width=4)
    sx=85+(i*6)%320;d.line((sx,118,sx,256),fill='#30584f',width=2)
    d.line((350,164,350,210),fill=WHITE,width=2)
    d.line((343,164,357,164),fill=WHITE,width=2);d.line((343,210,357,210),fill=WHITE,width=2)
    d.text((428,152),'ONSD',font=font(18),fill=MINT)
    d.text((428,183),'SCAN',font=font(15),fill=MUTED)
    # Flow particles travel through a stylized vein as an illustrative signal.
    d.line((658,151,1126,151),fill=CORAL,width=4);d.line((658,235,1126,235),fill=CORAL,width=4)
    for n in range(13):
        progress=(n/13+t)%1;x=671+int(progress*434)
        y=188+int(17*math.sin(n*1.5+t*math.tau))
        d.rectangle((x,y,x+10,y+6),fill=CORAL if n%3 else BLUE)
    d.text((680,259),'OBSERVE FLOW / RETAIN MEASUREMENT QUALITY',font=font(13),fill=MUTED)
    d.text((40,312),'ILLUSTRATIVE ANATOMY + MOTION / SYNTHETIC RESEARCH / NO DIAGNOSTIC OUTPUT',font=font(15),fill=MUTED)
    cursor(d,400+int(600*(.5-.5*math.cos(t*math.tau))),235)
    frames.append(im)
save(frames,'medical-signals.gif',90)

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
    # Cursor-guided captured screens, followed by a diagonal pixel-block wipe.
    targets=[(230,376),(51,270),(430,295),(385,453),(355,345),(610,431),(458,294)]
    for n in range(18):
        im=card.copy();d=ImageDraw.Draw(im)
        p=min(1,n/12);p=p*p*(3-2*p)
        target=targets[i];x=int(820+(target[0]-820)*p);y=int(130+(target[1]-130)*p)
        cursor(d,x,y,n in [13,14])
        d.rectangle((0,607,int(960*(i+n/18)/len(cards)),611),fill=MINT)
        gif.append(im.quantize(palette=palette,dither=Image.Dither.NONE));durations.append(95)
    following=cards[(i+1)%len(cards)]
    for n in range(1,7):
        im=card.copy()
        for y in range(0,612,36):
            for x in range(0,960,40):
                if (x/960+y/612)/2<n/6:
                    im.paste(following.crop((x,y,min(x+40,960),min(y+36,612))),(x,y))
        gif.append(im.quantize(palette=palette,dither=Image.Dither.NONE));durations.append(65)
gif[0].save(OUT/'platform-tour.gif',save_all=True,append_images=gif[1:],duration=durations,loop=0,optimize=True,disposal=1)
print('Built pixel mission banner, medical signals and cursor-guided platform tour')
