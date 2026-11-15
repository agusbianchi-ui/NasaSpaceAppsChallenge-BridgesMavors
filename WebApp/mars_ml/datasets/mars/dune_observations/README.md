# Mars dune observations

No Mars dune observation pixels or per-dune labels have been acquired or
validated. Dataset metadata lives in the sibling `dataset.json` files.

Future work must define:

- Instrument and product identifiers (HiRISE, CTX, or another PDS product).
- Acquisition timestamps and observation geometry.
- Projection, map scale and effective ground sample distance.
- Surface-change evidence and uncertainty.
- Environmental context (wind, pressure, temperature) with provenance and
  whether it is simultaneous, modelled or climatological.

Do not convert Sahara migration rates into Mars rates. See
`mars_ml/aeolian_dynamics/planetary_parameters.py`.
