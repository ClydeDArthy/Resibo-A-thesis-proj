# RESIBO Gait module — first integration build

This package is the first implementation layer for the `Gait/` directory in
`Resibo-A-thesis-proj`.

## Existing detector handoff

The current detection notebook calls:

```python
result = gait_module(
    person_crop=person_crop,
    master_id=master_id,
    frame_index=frame_index,
)
```

The package preserves that interface conceptually through `GaitPipeline.update()`.

## Important input distinction

The detector supplies an RGB person crop. GaitBase in the project is documented
as operating on normalized silhouette sequences. Therefore this first build does
**not** convert RGB crops into a guessed silhouette and does not run GaitBase on
RGB data.

The intended path is:

```text
YOLO11 + BoT-SORT
        |
        +--> master_id + person crop
        |
        v
   silhouette extraction
        |
        v
normalized silhouette sequence [T, 64, 64]
        |
        v
      GaitBase
        |
        v
 track-level embedding
```

A validated silhouette extractor and the exact OpenGait checkpoint/config still
need to be connected before real GaitBase inference is enabled.

## Example

```python
from Gait import GaitPipeline

pipeline = GaitPipeline()

# Called by the detector for each tracked person.
result = pipeline.update(master_id, frame_index, person_crop)

# Once the upstream silhouette extractor produces the corresponding mask:
result = pipeline.update_silhouette(master_id, frame_index, silhouette_mask)
```

`master_id` remains a BoT-SORT track reference. It is not treated as a person's
identity.

## Next integration stages

1. Connect the project's validated silhouette extraction method.
2. Connect the exact OpenGait/GaitBase config and checkpoint already used in the
   project's gait experiments.
3. Add track-level reference comparison and similarity output.
4. Add the covariate classifier and gait sensitivity analysis.
5. Connect those outputs to `resibo/` so a RESIBO discrepancy can route the
   active track back through the gait diagnostic path.
