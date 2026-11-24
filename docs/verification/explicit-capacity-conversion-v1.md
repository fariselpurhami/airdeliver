# Explicit capacity unit conversion

Hard capacity checks now compare explicit SI MB/GB/TB by exact decimal powers
of1000 and IEC MiB/GiB/TiB by powers of1024. Decimal and binary families never
mix. Product-kind identity remains required: RAM is not storage, SSD is not HDD
or generic storage. Exact requests remain equality; explicit minimum/maximum
bounds remain directional. Ambiguous variant strings do not become maxima.

Eighteen new tests cover fraction/boundary values, exact versus minimum/maximum,
SI/IEC separation, wrong-kind/ambiguous rejection and actual CatalogResult plus
ShoppingBrief required/excluded gates. Existing16384MB not equal16GB remains
true;16000MB equals16GB. No LLM-based unit or compatibility inference. This
narrows CAP13/26 implementation breadth; multilingual extraction/assignment and
physical compatibility remain unverified. No provider or owner-machine calls,
model changes, restarts, data writes or Granite sequence changes.
