ICON Integration
================

This builds a singularity container

```
sudo singularity build --sandbox icon-artifact.sif icon-artifact.def
```

Getting a shell into the container after the build

```
sudo singularity shell --writable icon-artifact.sif
```
