"""Image hint validation, not image identity or product evidence."""
import base64
import binascii
import re


def image_data_url(value):
    if not isinstance(value,str) or not value or len(value)>8_000_000:raise ValueError('invalid_image_payload')
    encoded=value
    declared=None
    if value.startswith('data:'):
        match=re.fullmatch(r'data:(image/(?:jpeg|png|webp|gif));base64,(.+)',value,re.S)
        if not match:raise ValueError('invalid_image_uri')
        declared,encoded=match.groups()
    try:raw=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error):raise ValueError('invalid_image_encoding') from None
    if not raw or len(raw)>6_000_000:raise ValueError('invalid_image_size')
    mime=('image/jpeg' if raw.startswith(b'\xff\xd8\xff') else 'image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else
          'image/webp' if raw.startswith(b'RIFF') and raw[8:12]==b'WEBP' else 'image/gif' if raw.startswith((b'GIF87a',b'GIF89a')) else None)
    if mime is None or declared not in {None,mime}:raise ValueError('invalid_image_type')
    return 'data:'+mime+';base64,'+encoded


def hint_text(completion,max_chars=256):
    choice=completion.choices[0] if completion and completion.choices else None
    value=getattr(getattr(choice,'message',None),'content',None)
    if getattr(choice,'finish_reason',None)=='length' or not isinstance(value,str) or not value.strip() or len(value)>max_chars:
        raise ValueError('invalid_image_hint')
    if re.search(r'https?://|[<>]',value):raise ValueError('invalid_image_hint')
    return ' '.join(value.split())
