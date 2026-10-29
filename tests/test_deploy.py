import ast,json,zipfile,io,base64
from deploy_kaggle import prepare

def test_bootstrap_is_private_bounded_and_resolves_source_imports(tmp_path):
    metadata=prepare('testowner',tmp_path)
    assert metadata['is_private'] is True and metadata['enable_gpu'] is True
    source=(tmp_path/'bootstrap.py').read_text();tree=ast.parse(source)
    assert 'sys.path.insert(0,str(root))' in source and "os.environ['OCR_BACKEND']='gpu'" in source
    assert 'secrets.token_urlsafe' in source and 'process.terminate()' in source
    call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='b64decode')
    payload=ast.literal_eval(call.args[0]);z=zipfile.ZipFile(io.BytesIO(base64.b64decode(payload)));names=z.namelist()
    assert 'runtime_env.py' in names and 'ctc_graph.py' in names
    assert not any('kaggle.json' in n or '.local-auth' in n for n in names)
