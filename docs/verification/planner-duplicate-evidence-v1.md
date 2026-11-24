# Planner and reviewer JSON evidence integrity

Setup/target scope planners and replacement/query reviewers now use a bounded
object-only JSON decoder rejecting duplicate keys at every nesting level, NaN,
nonobjects, deep and oversize content. Duplicate feature-map keys could previously
silently erase a hard requirement; false then true reviewer keys could become a
positive verdict. All such responses now fail closed with existing fallback or
clarification. Native schemas/review semantics unchanged; legacy map wire format
remains supported when unambiguous. No extra provider call or keyword router.

Eleven new tests drive actual parsers and all four review boundaries, including
nested scope erasure and duplicate false/true approvals. Existing native Groq SDK
loopback schema, scope continuity and component tests retained. No claim model
semantic/physical compatibility is proven. No owner/provider execution, restart,
Granite/model/cache/index changes. Narrow CAP13/23/26 evidence-gap hardening.
