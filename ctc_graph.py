"""Append exact CTC argmax/max to ONNX so GPUs transfer IDs/scores, not full logits.
The original pinned model is never overwritten. This is not model quantization.
"""
from __future__ import annotations
import hashlib,pathlib

def reduced_ctc_model(source:pathlib.Path)->pathlib.Path:
    import onnx
    from onnx import TensorProto,helper
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    target=source.parent/'optimized'/f'{source.stem}-ctc-v1-{digest[:16]}.onnx'
    if target.exists():return target
    model=onnx.load(str(source))
    if len(model.graph.output)!=1:raise ValueError('expected one recognizer probability output')
    output=model.graph.output[0]
    if len(output.type.tensor_type.shape.dim)!=3:raise ValueError('expected N,T,C recognition output')
    if output.type.tensor_type.elem_type not in (TensorProto.FLOAT,TensorProto.FLOAT16):raise ValueError('unexpected recognizer output dtype')
    ids='gateway_ctc_ids';scores='gateway_ctc_scores';opset=next(o.version for o in model.opset_import if o.domain in ('','ai.onnx'))
    model.graph.node.append(helper.make_node('ArgMax',[output.name],[ids],axis=2,keepdims=0))
    if opset>=18:
        axes=helper.make_tensor('gateway_ctc_axis',TensorProto.INT64,[1],[2]);model.graph.initializer.append(axes)
        model.graph.node.append(helper.make_node('ReduceMax',[output.name,axes.name],[scores],keepdims=0))
    else:model.graph.node.append(helper.make_node('ReduceMax',[output.name],[scores],axes=[2],keepdims=0))
    dtype=output.type.tensor_type.elem_type
    del model.graph.output[:]
    model.graph.output.extend([helper.make_tensor_value_info(ids,TensorProto.INT64,[None,None]),helper.make_tensor_value_info(scores,dtype,[None,None])])
    onnx.checker.check_model(model)
    target.parent.mkdir(exist_ok=True);temporary=target.with_suffix('.partial');onnx.save(model,str(temporary));temporary.replace(target)
    return target
