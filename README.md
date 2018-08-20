# aesop

[![Build Status](https://travis-ci.org/bmorris3/aesop.svg?branch=master)](https://travis-ci.org/bmorris3/aesop) [![Documentation Status](https://readthedocs.org/projects/arces/badge/?version=latest)](http://arces.readthedocs.io/en/latest/?badge=latest) [![Powered by Astropy Badge](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)](http://www.astropy.org) [![status](http://joss.theoj.org/papers/6737355abd6a7b0c20d22c7094576696/status.svg)](http://joss.theoj.org/papers/6737355abd6a7b0c20d22c7094576696)
[![DOI](https://zenodo.org/badge/108436109.svg)](https://zenodo.org/badge/latestdoi/108436109)

ARC Echelle Spectroscopic Observation Pipeline (aesop)


The ARC Echelle Spectroscopic Observation Pipeline, or ``aesop``, is a high resolution 
spectroscopy software toolkit tailored for observations from the Astrophysics Research 
Consortium (ARC) Echelle Spectrograph mounted on the ARC 3.5 m Telescope at Apache 
Point Observatory. ``aesop`` picks up where the traditional IRAF reduction scripts leave 
off, offering an open development, object-oriented Pythonic analysis framework for echelle
spectra. 

Basic functionality of ``aesop`` includes: (1) blaze function normalization by polynomial 
fits to observations of early-type stars, (2) an additional/alternative robust least-squares 
normalization method, (3) radial velocity measurements (or offset removals) via 
cross-correlation with model spectra, including barycentric radial velocity calculations, 
(4) concatenation of multiple echelle orders into a simple 1D spectrum, and (5) approximate
flux calibration. 

For more info, [read the docs](http://arces.readthedocs.io/en/latest/?badge=latest)!


#### Citation

If you make use of `aesop` in your research, please cite our JOSS paper: 

```
@article{Morris2018,
  doi = {10.21105/joss.00854},
  url = {https://doi.org/10.21105/joss.00854},
  year  = {2018},
  month = {aug},
  publisher = {The Open Journal},
  volume = {3},
  number = {28},
  pages = {854},
  author = {Brett M. Morris and Trevor Dorn-Wallenstein},
  title = {aesop: {ARC} Echelle Spectroscopic Observation Pipeline},
  journal = {Journal of Open Source Software}
}
```
