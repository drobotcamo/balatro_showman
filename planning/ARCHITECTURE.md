# Active Architecture

```text
asset metadata + sprites + backgrounds
                |
                v
       synthetic scene generator
                |
                v
        detector training dataset
                |
                v
video -> frame sampler -> object detector ----+
                                      OCR ----+-> cleaned frame observations
                                                |
                                                v
                                      tracking and stabilization
                                                |
                                                v
                                      composed game state
                                                |
                                                v
                                      event/action inference
                                                |
                                                v
                                      versioned datasets
                                                |
                                                v
                                      analysis and learning
```

## Design Principles

- State reconstruction is the primary product; learning is a downstream
  consumer.
- Synthetic labels are authoritative for synthetic data, but real-frame
  evaluation is mandatory.
- Every stage writes a versioned, inspectable artifact.
- Uncertainty and unknown values are represented explicitly.
- CPU and DirectML execution are supported for development; batch GPU execution
  is an optimization, not a different pipeline.
- Object identity, object attributes, and object relationships are separate
  concepts.
- The pipeline must support the whole visible game, not only shop decisions.

## Boundary

The active implementation must not import from `legacy/`. Reusable sprites and
game metadata may be copied or adapted after their provenance is recorded.
