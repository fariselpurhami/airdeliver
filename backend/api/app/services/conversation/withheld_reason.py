"""Fixed reason codes for withheld model copy (log-safe)."""
import re


def withheld_reason(exc):
    """Fixed reason code for logs. Never echoes model output or exception text
    unless it is one of our own short constant validator messages."""
    if type(exc) is ValueError:
        msg=str(exc)
        if re.fullmatch(r'[A-Za-z_ ]{1,64}',msg):return msg.strip().lower().replace(' ','_')
        return 'validator_rejected'
    if type(exc).__name__=='ValidationError':return 'schema_invalid'
    if isinstance(exc,TimeoutError):return 'timeout'
    return 'provider_or_unexpected_error'
