# Explicit Arabic capacity evidence

The existing literal hard-feature gate now recognizes a bounded list of explicit
Arabic RAM/storage and MB/GB/TB labels, Arabic-Indic digits, decimal separator,
and minimum/maximum phrases. Customer spans stay literal. It does not translate
arbitrary prose, infer capacities from a product category or change kind identity.
Decimal/binary unit families remain separate. RAM is not storage; SSD is not an
alias for generic storage. Ambiguous variant values do not satisfy a capacity.

Twenty-five additional tests cover same-kind conversion, wrong-kind rejection,
SI/IEC separation, malformed/ambiguous data, Arabic bounds and the actual grounded
ShoppingBrief/CatalogResult required/excluded gate. All55 capacity tests pass. Ambiguous Arabic name variants cannot become single-capacity evidence.
This narrows CAP13/23/26 implementation breadth. General multilingual extraction,
assignment, live model quality and physical compatibility remain unverified.
No provider calls, model changes, owner steps, data changes or Granite interference.
