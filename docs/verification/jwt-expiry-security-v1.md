# Require JWT expiration

Access and refresh validators previously verified expiration only when present. Correctly signed tokens with no expiration could therefore have unlimited lifetime. Both validators now require exp and sub claims. Current token issuers already include expiration, so normal tokens and separate signing keys stay unchanged. Missing or null expiration is rejected; no refresh rotation or key change.

27 focused offline auth/security tests passed, including absent/null expiration, absent subject, valid/expired tokens, wrong key, unsigned token and refresh/access confusion. This does not allow an attacker without the signing key to forge tokens, and is not a claim that the authentication system is fully audited.
