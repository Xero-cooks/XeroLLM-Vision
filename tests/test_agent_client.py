import base64,io
from PIL import Image
from agent_client import normalize_messages

def test_png_is_converted_client_side_without_mutating_input():
    b=io.BytesIO();Image.new('RGBA',(64,32),(10,20,30,255)).save(b,format='PNG');url='data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
    messages=[{'role':'user','content':[{'type':'text','text':'Look'},{'type':'image_url','image_url':{'url':url}}]}]
    output=normalize_messages(messages);new=output[0]['content'][1]['image_url']['url']
    assert new.startswith('data:image/jpeg;base64,') and messages[0]['content'][1]['image_url']['url']==url
    with Image.open(io.BytesIO(base64.b64decode(new.split(',',1)[1]))) as image:assert image.size==(64,32) and image.format=='JPEG'

def test_jpeg_and_tool_history_are_unchanged():
    messages=[{'role':'assistant','content':None,'tool_calls':[]},{'role':'user','content':[{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,not-decoded-here'}}]}]
    assert normalize_messages(messages)==messages
