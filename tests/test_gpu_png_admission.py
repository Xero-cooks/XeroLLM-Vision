import io

from PIL import Image

from payload_transformer import gpu_admitted


class FakeGPUEngine:
    torch = object()  # presence is what the helper keys on


class FakeCPUEngine:
    torch = None


def _png(mode='RGB', size=(64, 32)):
    color = (10, 20, 30) if mode == 'RGB' else (10, 20, 30, 255)
    buffer = io.BytesIO()
    Image.new(mode, size, color).save(buffer, format='PNG')
    return buffer.getvalue()


def test_png_is_transcoded_for_the_jpeg_only_gpu_decoder():
    out = gpu_admitted(_png(), FakeGPUEngine())
    assert out[:2] == b'\xff\xd8'
    with Image.open(io.BytesIO(out)) as im:
        assert im.format == 'JPEG' and im.size == (64, 32)


def test_rgba_png_is_flattened_to_rgb_jpeg():
    out = gpu_admitted(_png('RGBA'), FakeGPUEngine())
    with Image.open(io.BytesIO(out)) as im:
        assert im.format == 'JPEG' and im.mode == 'RGB'


def test_jpeg_passes_through_byte_identical():
    buffer = io.BytesIO()
    Image.new('RGB', (8, 8), (1, 2, 3)).save(buffer, format='JPEG')
    blob = buffer.getvalue()
    assert gpu_admitted(blob, FakeGPUEngine()) == blob


def test_cpu_staging_passes_bytes_through_untouched():
    blob = _png()
    assert gpu_admitted(blob, FakeCPUEngine()) is blob


def test_undecodable_bytes_are_left_for_the_engine_to_report():
    blob = b'not an image at all'
    assert gpu_admitted(blob, FakeGPUEngine()) == blob
