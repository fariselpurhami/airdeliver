import base64
from dataclasses import replace
from io import BytesIO
from unittest.mock import Mock
import pytest
from PIL import Image
from app.services.ai_commerce_engine import AICommerceEngine,EngineLimits,ValidationError
import app.services.ai_commerce_engine as module


def engine(**limits):
    return AICommerceEngine(opensearch_client=object(),milvus_client=object(),embedding_model=object(),
        limits=replace(EngineLimits(),**limits))


def payload(fmt='PNG',size=(12,8),mode='RGBA'):
    with Image.new(mode,size) as im:
        out=BytesIO();im.save(out,format=fmt)
    return base64.b64encode(out.getvalue()).decode()


@pytest.mark.parametrize('prefix',['','data:image/png;base64,'])
def test_real_image_preserves_rgb_dimensions_and_data_uri(prefix):
    with engine()._decode_image_bounded(prefix+payload()) as image:
        assert image.mode=='RGB' and image.size==(12,8)
        assert len(image.tobytes())==12*8*3


@pytest.mark.parametrize('value',['not base64!','',base64.b64encode(b'not an image').decode()])
def test_invalid_bytes_rejected(value):
    with pytest.raises(ValidationError):engine()._decode_image_bounded(value)


def test_encoded_and_decoded_limits_precede_image_open(monkeypatch):
    opened=Mock(side_effect=AssertionError('must not parse'))
    monkeypatch.setattr(module.Image,'open',opened)
    with pytest.raises(ValidationError):engine(max_image_encoded_chars=4)._decode_image_bounded('A'*8)
    with pytest.raises(ValidationError):engine(max_image_bytes=2)._decode_image_bounded(base64.b64encode(b'123').decode())
    opened.assert_not_called()


@pytest.mark.parametrize('limits',[{'max_image_pixels':90},{'max_image_edge':10}])
def test_actual_png_dimensions_rejected_before_decode_and_rgb_allocation(monkeypatch,limits):
    encoded=payload()
    monkeypatch.setattr(Image.Image,'convert',Mock(side_effect=AssertionError('RGB allocation must not occur')))
    with pytest.raises(ValidationError,match='pixel limit'):engine(**limits)._decode_image_bounded(encoded)


def test_truncated_image_fails_closed():
    encoded=payload();raw=base64.b64decode(encoded)
    with pytest.raises(ValidationError):engine()._decode_image_bounded(base64.b64encode(raw[:45]).decode())


@pytest.mark.asyncio
async def test_invalid_image_never_reaches_model_registry(monkeypatch):
    get_model=Mock(side_effect=AssertionError('model must not load'))
    monkeypatch.setattr(module.model_registry,'get_vision_stack',get_model)
    with pytest.raises(ValidationError):await engine()._encode_image_to_vector('invalid!')
    get_model.assert_not_called()
