"""Small reproducible label check; not a substitute for real screenshot evaluation."""
import json,pathlib
from config import Settings
from gpu_ocr_engine import DualT4UltrafastOCREncoder
from benchmark_700toks import fixture

def main()->None:
    engine=DualT4UltrafastOCREncoder(Settings())
    try:
        frame=engine.encode(fixture(0));text=' '.join(e.text for e in frame.elements).casefold()
        labels=['Dashboard','API Keys','Logs','Settings','Deploy Gateway','Healthy','Submit','Cancel']+[f'Service {i}' for i in range(1,9)]
        matched={label:label.casefold() in text for label in labels}
        result={'kind':'ACTUAL_OCR_SYNTHETIC_LABEL_CHECK_NOT_REAL_WORLD_ACCURACY','backend':engine.backend,'expected_labels':matched,'label_count':len(labels),'exact_substring_matches':sum(matched.values()),'elements':frame.public()['elements'],'limitations':'Single synthetic font/layout. Exact matching retains whitespace errors. No click success, icon or semantic quality validation.'}
        out=pathlib.Path('evidence/synthetic-quality.json');out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(result,indent=2))
        print(json.dumps({k:v for k,v in result.items() if k!='elements'},indent=2))
    finally:engine.close()

if __name__=='__main__':main()
