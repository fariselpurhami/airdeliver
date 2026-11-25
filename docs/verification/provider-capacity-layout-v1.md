# Provider capacity domain ownership

Eight existing modules move under app.services.provider_capacity. Every original
implementation byte is preserved, as the adjacent SHA256 manifest proves. Old
app.services imports remain compatibility modules that resolve to the exact same
module object, not copied state or shallow star exports. Existing callers and
monkeypatch-based tests keep their current imports in this stage.

Sixteen identity/monkeypatch tests plus content-manifest validation protect this
boundary. The initial 262 focused tests passed with real Redis, no provider
calls. Full PostgreSQL and both storage CI matrices remain required on the final
head. No admission/usage/policy behavior changes. The separate quota-axes work
is not included. No deployment, owner migration, provider/payment calls or spend.
