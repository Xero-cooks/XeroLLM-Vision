from dataclasses import dataclass,asdict
import html,re
@dataclass(frozen=True)
class UIElement:
    text:str
    box:tuple[float,float,float,float]
    confidence:float
    role:str='unknown' # Never fabricate buttons, active state or accessibility roles from text.
    def public(self)->dict:return asdict(self)
def reading_order(elements:list[UIElement])->list[UIElement]:
    """Recursive XY cut at non-overlapping whitespace; horizontal split before columns."""
    if len(elements)<2:return elements
    for axis in (1,0):
        ordered=sorted(elements,key=lambda e:e.box[axis]); edge=ordered[0].box[axis+2]
        for i,e in enumerate(ordered[1:],1):
            if e.box[axis]-edge>8:return reading_order(ordered[:i])+reading_order(ordered[i:])
            edge=max(edge,e.box[axis+2])
    return sorted(elements,key=lambda e:(e.box[1],e.box[0]))
def serialize(elements:list[UIElement],w:int,h:int,frame_id:str,captured_at:str,latency_ms:float)->str:
    if w<=0 or h<=0:raise ValueError("positive image dimensions required")
    def norm(x,dimension):return max(0,min(1000,round(1000*x/dimension)))
    lines=[]; line=[];anchor=None
    for e in reading_order(elements):
        x0,y0,x1,y1=e.box; y=norm((y0+y1)/2,h)
        text=html.escape(re.sub(r'[\x00-\x1f\x7f]',' ',e.text),quote=True).replace('|','&#124;')
        px=max(0,min(w-1,round((x0+x1)/2)));py=max(0,min(h-1,round((y0+y1)/2)))
        fragment=f'{text} [pixel_x:{px}, pixel_y:{py}; norm_x:{norm((x0+x1)/2,w):03}, norm_y:{y:03}; conf:{e.confidence:.2f}]'
        if anchor is not None and abs(y-anchor)>12:
            lines.append(' | '.join(line));line=[];anchor=None
        if anchor is None:anchor=y
        line.append(fragment)
    if line:lines.append(' | '.join(line))
    attrs=f'id="{html.escape(frame_id,quote=True)}" res="{w}x{h}" captured_at="{html.escape(captured_at,quote=True)}" ocr_ms="{latency_ms:.2f}" coords="pixel_centers_and_normalized_0_1000" roles="unknown" click_targets="not_inferred"'
    return f'<ui_screen {attrs}>\n'+'\n'.join(lines)+'\n</ui_screen>'
