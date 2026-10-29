import numpy as np,pytest
onnx=pytest.importorskip('onnx')
from onnx import helper,TensorProto
from ctc_graph import reduced_ctc_model
import onnxruntime as ort

@pytest.mark.parametrize('opset',[11,18])
def test_ctc_graph_exact_reduction_and_source_preserved(tmp_path,opset):
    graph=helper.make_graph([helper.make_node('Identity',['x'],['probs'])],'test',[helper.make_tensor_value_info('x',TensorProto.FLOAT,[None,None,5])],[helper.make_tensor_value_info('probs',TensorProto.FLOAT,[None,None,5])])
    model=helper.make_model(graph,opset_imports=[helper.make_opsetid('',opset)]);model.ir_version=10
    source=tmp_path/'rec.onnx';onnx.save(model,str(source));original=source.read_bytes();target=reduced_ctc_model(source)
    assert source.read_bytes()==original and target==reduced_ctc_model(source)
    session=ort.InferenceSession(str(target),providers=['CPUExecutionProvider'])
    probs=np.array([[[.1,.5,.2,.1,.1],[.1,.1,.1,.6,.1],[.5,.5,0,0,0]]],np.float32)
    ids,scores=session.run(None,{'x':probs})
    np.testing.assert_array_equal(ids,probs.argmax(-1));np.testing.assert_allclose(scores,probs.max(-1))
