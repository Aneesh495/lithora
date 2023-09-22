# Diagrams

Editable Mermaid sources (`.mmd`) with checked rendered SVG exports. Regenerate
with the mermaid CLI:

```
npx @mermaid-js/mermaid-cli -i <name>.mmd -o <name>.svg
```

| Diagram | Covers |
|---|---|
| `components.svg` | Module structure and dependencies in the Rust core |
| `reconstruct_path.svg` | One complete reconstruction data path |
| `plate_circuit.svg` | Plate-circuit graph and composition order |
| `frame_transform.svg` | Coordinate and reference-frame transformations |
| `timeseries_fit.svg` | GNSS trend/seasonal/offset fitting and uncertainty |
| `vector_transport.svg` | Tangent-frame transport in the learned model |
| `buffered_splits.svg` | Spatially buffered cross-validation folds |
| `dual_clock.svg` | Separate modern and geological clocks |
| `data_acquisition.svg` | Acquisition, caching, provenance, frame guard |
| `sequence_state.svg` | Rotation-sequence state lifecycle |
| `failure_recovery.svg` | Atomic checkpointing and failure handling |
| `evidence_lineage.svg` | Source-to-evidence-to-verifier lineage |
| `testing_layers.svg` | Test and campaign structure across layers |

These are kept in sync with the source; if a mechanism changes, update the
matching `.mmd` and re-render.
