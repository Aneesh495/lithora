# Notebooks

These are reproducible views of the package's outputs, not hidden computational
dependencies. Each script imports the installed `lithora` package and the
cached data, runs the same code the CLI and tests use, and prints or saves a
figure. Nothing here implements analysis that lives only in a notebook; delete
the notebooks and the package still does everything.

Run them after `make bootstrap` and `make acquire-gnss`, from the repository
root so the data cache resolves:

```
python notebooks/01_regional_comparison.py
python notebooks/02_strain_scale_sweep.py
```

They are plain `.py` scripts so they run in CI and diff cleanly in Git. Convert
to a notebook interface with jupytext if desired; the logic stays in the
package.
