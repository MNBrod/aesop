"""
Tools for organizing, normalizing echelle spectra.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares
from scipy.stats import binned_statistic

from astropy.io import fits
import astropy.units as u
from astropy.time import Time
from astropy.stats import mad_std
from specutils.io import read_fits

from .spectral_type import query_for_T_eff
from .phoenix import get_phoenix_model_spectrum
from .masking import get_spectrum_mask
from .activity import true_h_centroid, true_k_centroid

__all__ = ["EchelleSpectrum", "slice_spectrum", "interpolate_spectrum",
           "cross_corr"]


class Spectrum1D(object):
    """
    Simple 1D spectrum object.

    A ``Spectrum1D`` object can be used to describe one order of an echelle
    spectrum, for example.

    If the spectrum is initialized with ``wavelength``s that are not strictly
    increasing, ``Spectrum1D`` will sort the ``wavelength``, ``flux`` and
    ``mask`` arrays so that ``wavelength`` is monotonically increasing.
    """
    @u.quantity_input(wavelength=u.Angstrom)
    def __init__(self, wavelength=None, flux=None, name=None, mask=None,
                 wcs=None, meta=dict(), time=None, continuum_normalized=None):
        """
        Parameters
        ----------
        wavelength : `~numpy.ndarray`
            Wavelengths
        flux : `~numpy.ndarray`
            Fluxes
        name : str (optional)
            Name for the spectrum
        mask : `~numpy.ndarray` (optional)
            Boolean mask of the same shape as ``flux``
        wcs : `~specutils.Spectrum1DLookupWCS` (optional)
            Store the WCS parameters
        meta : dict (optional)
            Metadata dictionary.
        continuum_normalized : bool (optional)
            Is this spectrum continuum normalized?
        """

        # Are wavelengths stored in increasing order?
        wl_inc = np.all(np.diff(wavelength) > 0)

        # If not, force them to be, to simplify linear interpolation later.
        if not wl_inc:
            wl_sort = np.argsort(wavelength)
            wavelength = wavelength[wl_sort]
            flux = flux[wl_sort]
            if mask is not None:
                mask = mask[wl_sort]

        self.wavelength = wavelength
        self.wavelength_unit = wavelength.unit
        self.flux = flux
        self.name = name
        self.mask = mask
        self.wcs = wcs
        self.meta = meta
        self.time = time
        self.continuum_normalized = continuum_normalized

    def plot(self, ax=None, normed=False, flux_offset=0, **kwargs):
        """
        Plot the spectrum.

        Parameters
        ----------
        ax : `~matplotlib.axes.Axes` (optional)
            The `~matplotlib.axes.Axes` to draw on, if provided.
        kwargs
            All other keyword arguments are passed to `~matplotlib.pyplot.plot`

        """
        if ax is None:
            ax = plt.gca()

        flux_80th_percentile = np.percentile(self.masked_flux, 80)

        if normed:
            flux = self.masked_flux / flux_80th_percentile
        else:
            flux = self.masked_flux

        ax.plot(self.masked_wavelength, flux + flux_offset, **kwargs)
        #ax.set_xlim([self.masked_wavelength.value.min(),
        #             self.masked_wavelength.value.max()])
        ax.set(xlabel='Wavelength [{0}]'.format(self.wavelength_unit),
               ylabel='Flux')
        if self.name is not None:
            ax.set_title(self.name)

    @property
    def masked_wavelength(self):
        if self.mask is not None:
            return self.wavelength[self.mask]
        else:
            return self.wavelength

    @property
    def masked_flux(self):
        if self.mask is not None:
            return self.flux[self.mask]
        else:
            return self.flux

    @classmethod
    def from_specutils(cls, spectrum1d, name=None, **kwargs):
        """
        Convert a `~specutils.Spectrum1D` object into our Spectrum1D object.

        Parameters
        ----------
        spectrum1d : `~specutils.Spectrum1D`
            Input spectrum
        name : str
            Target/spectrum name
        """
        return cls(wavelength=spectrum1d.wavelength, flux=spectrum1d.flux,
                   mask=spectrum1d._mask, name=name, **kwargs)

    @classmethod
    def from_array(cls, wavelength, flux, dispersion_unit=None, name=None,
                   **kwargs):
        """
        Initialize a spectrum with the same call signature as
        `~specutils.Spectrum1D.from_array`.

        Parameters
        ----------
        wavelength : `~astropy.units.Quantity`
            Spectrum wavelengths
        flux : `~astropy.units.Quantity` or `~numpy.ndarray`
            Spectrum fluxes
        dispersion_unit : `~astropy.units.Unit` (optional)
            Unit of the wavelength
        name : str (optional)
            Name of the target/spectrum
        """
        if not hasattr(wavelength, 'unit') and dispersion_unit is not None:
            wavelength = wavelength * dispersion_unit
        return cls(wavelength=wavelength, flux=flux, name=name, **kwargs)

    def __repr__(self):
        wl_unit = u.Angstrom
        min_wavelength = self.wavelength.min()
        max_wavelength = self.wavelength.max()

        if self.name is not None:
            name_str = '"{0}" '.format(self.name)
        else:
            name_str = ''

        return ("<Spectrum1D: {0}{1:.1f}-{2:.1f} {3}>"
                .format(name_str, min_wavelength.to(wl_unit).value,
                        max_wavelength.to(wl_unit).value, wl_unit))

class EchelleSpectrum(object):
    """
    Echelle spectrum of one or more spectral orders.

    The spectral orders will be indexed in order of increasing wavelength.
    """
    def __init__(self, spectrum_list, header=None, name=None, fits_path=None,
                 time=None):
        """
        Parameters
        ----------
        spectrum_list : list of `~aesop.Spectrum1D` objects
            List of `~aesop.Spectrum1D` objects for the spectra in each echelle
            order.
        header : `astropy.io.fits.header.Header` (optional)
            FITS header object associated with the echelle spectrum.
        name : str (optional)
            Name of the target or a name for the spectrum
        fits_path : str  (optional)
            Path where FITS file was opened from.
        time : `~astropy.time.Time` (optional)
            Time at which the spectrum was taken
        """
        # Sort the spectra in the list in order of increasing wavelength
        self.spectrum_list = sorted(spectrum_list,
                                    key=lambda x: x.wavelength.min())
        self.header = header
        self.name = name
        self.fits_path = fits_path
        self.standard_star_props = {}
        self.model_spectrum = None

        if header is not None and time is None:
            time = Time(header['JD'], format='jd')

        self.time = time

    @classmethod
    def from_fits(cls, path):
        """
        Load an echelle spectrum from a FITS file.

        Parameters
        ----------
        path : str
            Path to the FITS file
        """
        spectrum_list = [Spectrum1D.from_specutils(s)
                         for s in read_fits.read_fits_spectrum1d(path)]
        header = fits.getheader(path)

        name = header.get('OBJNAME', None)
        return cls(spectrum_list, header=header, name=name, fits_path=path)

    def get_order(self, order):
        """
        Get the spectrum from a specific spectral order

        Parameters
        ----------
        order : int
            Echelle order to return

        Returns
        -------
        spectrum : `~specutils.Spectrum1D`
            One order from the echelle spectrum
        """
        return self.spectrum_list[order]

    def __getitem__(self, index):
        return self.spectrum_list[index]

    def __len__(self):
        return len(self.spectrum_list)

    def fit_order(self, spectral_order, polynomial_order, plots=False):
        """
        Fit a spectral order with a polynomial.

        Ignore fluxes near the CaII H & K wavelengths.

        Parameters
        ----------
        spectral_order : int
            Spectral order index
        polynomial_order : int
            Polynomial order

        Returns
        -------
        fit_params : `~numpy.ndarray`
            Best-fit polynomial coefficients
        """
        spectrum = self.get_order(spectral_order)
        mean_wavelength = spectrum.wavelength.mean()

        mask_wavelengths = ((abs(spectrum.wavelength - true_h_centroid) > 6.5*u.Angstrom) &
                            (abs(spectrum.wavelength - true_k_centroid) > 6.5*u.Angstrom))

        fit_params = np.polyfit(spectrum.wavelength[mask_wavelengths] - mean_wavelength,
                                spectrum.flux[mask_wavelengths], polynomial_order)

        if plots:
            plt.figure()
            # plt.plot(spectrum.wavelength, spectrum.flux)
            plt.plot(spectrum.wavelength[mask_wavelengths],
                     spectrum.flux[mask_wavelengths])
            plt.plot(spectrum.wavelength,
                     np.polyval(fit_params,
                                spectrum.wavelength - mean_wavelength))
            plt.show()
        return fit_params
    
    def predict_continuum(self, spectral_order, fit_params):
        """
        Predict continuum spectrum given results from a polynomial fit from
        `EchelleSpectrum.fit_order`.

        Parameters
        ----------
        spectral_order : int
            Spectral order index
        fit_params : `~numpy.ndarray`
            Best-fit polynomial coefficients

        Returns
        -------
        flux_fit : `~numpy.ndarray`
            Predicted flux in the continuum for this order
        """
        spectrum = self.get_order(spectral_order)
        mean_wavelength = spectrum.wavelength.mean()
        flux_fit = np.polyval(fit_params, 
                              spectrum.wavelength - mean_wavelength)
        return flux_fit

    def continuum_normalize_from_standard(self, standard_spectrum,
                                          polynomial_order, only_orders=None,
                                          plot_masking=False, plot_fit=False):
        """
        Normalize the spectrum by a polynomial fit to the standard's
        spectrum.

        Parameters
        ----------
        standard_spectrum : `EchelleSpectrum`
            Spectrum of the standard object
        polynomial_order : int
            Fit the standard's spectrum with a polynomial of this order
        only_orders : `~numpy.ndarray`
            Only do the continuum normalization for these echelle orders.
        plot_masking : bool
            Plot the masked-out low S/N regions
        plot_fit : bool
            Plot the polynomial fit to the standard star spectrum
        """

        # Copy some attributes of the standard star's EchelleSpectrum object into
        # a dictionary on the target star's EchelleSpectrum object.
        attrs = ['name', 'fits_path', 'header']
        for attr in attrs:
            self.standard_star_props[attr] = getattr(standard_spectrum, attr)

        if only_orders is None:
            only_orders = range(len(self.spectrum_list))

        for spectral_order in only_orders:
            # Extract one spectral order at a time to normalize
            standard_order = standard_spectrum.get_order(spectral_order)
            target_order = self.get_order(spectral_order)

            target_mask = get_spectrum_mask(standard_order, plot=plot_masking)

            # Fit the standard's flux in this order with a polynomial
            # fit_params = standard_spectrum.fit_order(spectral_order,
            #                                          polynomial_order)

            fit_params = standard_spectrum.fit_order(spectral_order,
                                                     polynomial_order,
                                                     plots=plot_fit)

            # Normalize the target's flux with the continuum fit from the standard
            target_continuum_fit = self.predict_continuum(spectral_order,
                                                          fit_params)

            target_continuum_normalized_flux = target_order.flux / target_continuum_fit

            normalized_target_spectrum = Spectrum1D(wavelength=target_order.wavelength,
                                                    flux=target_continuum_normalized_flux,
                                                    wcs=target_order.wcs,
                                                    mask=target_mask,
                                                    continuum_normalized=True)
            normalized_target_spectrum.meta['normalization'] = target_continuum_fit

            # Replace this order's spectrum with the continuum-normalized one
            self.spectrum_list[spectral_order] = normalized_target_spectrum

    def continuum_normalize_lstsq(self, polynomial_order, only_orders=None,
                                  plot=False, fscale_mad_factor=0.2):
        """
        Normalize the spectrum with a robust least-squares polynomial fit to the
        spectrum of each order.

        Parameters
        ----------
        standard_spectrum : `EchelleSpectrum`
            Spectrum of the standard object
        polynomial_order : int
            Fit the standard's spectrum with a polynomial of this order
        only_orders : `~numpy.ndarray` (optional)
            Only do the continuum normalization for these echelle orders.
        plot_masking : bool (optional)
            Plot the masked-out low S/N regions
        plot_fit : bool (optional)
            Plot the polynomial fit to the standard star spectrum
        fscale_mad_factor : float (optional)
            The robust least-squares fitter will reject outliers by keeping
            the standard deviation of inliers close to ``fscale_mad_factor``
            times the median absolute deviation (MAD) of the fluxes.
        """
        if only_orders is None:
            only_orders = range(len(self.spectrum_list))

        for spectral_order in only_orders:
            # Extract one spectral order at a time to normalize
            s = self.get_order(spectral_order)

            x0 = np.concatenate([np.zeros(polynomial_order),
                                 [s.flux.value.mean()]])
            fscale = fscale_mad_factor * mad_std(s.flux.value)
            args = (s.wavelength.value, s.flux.value)
            res_lsq = least_squares(_residuals, x0, args=args)

            model_simple = _poly_model(res_lsq.x, args[0])

            res_robust = least_squares(_residuals, x0, loss='cauchy',
                                       f_scale=fscale, args=args)

            model_robust = _poly_model(res_robust.x, args[0])

            target_continuum_normalized_flux = s.flux / model_robust

            normalized_target_spectrum = Spectrum1D(wavelength=s.wavelength,
                                                    flux=target_continuum_normalized_flux,
                                                    wcs=s.wcs, mask=s.mask,
                                                    continuum_normalized=True)

            # Replace this order's spectrum with the continuum-normalized one
            self.spectrum_list[spectral_order] = normalized_target_spectrum

            if plot:
                fig, ax = plt.subplots(1, 2, figsize=(10, 4))

                ax[0].set_title('standard star only')
                ax[0].plot(s.wavelength.value, s.flux.value, color='k')
                ax[0].plot(s.wavelength.value, model_simple, color='DodgerBlue',
                           lw=3, label='simple lstsq')
                ax[0].plot(s.wavelength.value, model_robust, color='r', lw=3,
                           label='robust lstsq')
                ax[0].legend()

                ax[1].set_title('continuum normalized (robust polynomial)')
                ax[1].plot(s.wavelength, s.flux.value/model_robust, color='k')


    def offset_wavelength_solution(self, wavelength_offset):
        """
        Offset the wavelengths by a constant amount in a specific order.

        Parameters
        ----------
        spectral_order : int
            Echelle spectrum order to correct
        wavelength_offset : `~astropy.units.Quantity`
            Offset the wavelengths by this amount
        """
        for spectrum in self.spectrum_list:
            spectrum.wavelength += wavelength_offset

    def rv_wavelength_shift(self, spectral_order, T_eff=None, plot=False):
        """
        Solve for the radial velocity wavelength shift.

        Parameters
        ----------
        spectral_order : int
            Echelle spectrum order to shift
        """
        order = self.spectrum_list[spectral_order]

        if self.model_spectrum is None:
            if T_eff is None:
                T_eff = query_for_T_eff(self.name)
            self.model_spectrum = get_phoenix_model_spectrum(T_eff)

        model_slice = slice_spectrum(self.model_spectrum,
                                     order.masked_wavelength.min(),
                                     order.masked_wavelength.max(),
                                     norm=order.masked_flux.max())

        delta_lambda_obs = np.abs(np.diff(order.wavelength.value[0:2]))[0]
        delta_lambda_model = np.abs(np.diff(model_slice.wavelength.value[0:2]))[0]
        smoothing_kernel_width = delta_lambda_obs/delta_lambda_model

        interp_target_slice = interpolate_spectrum(order,
                                                   model_slice.wavelength)

        rv_shift = cross_corr(interp_target_slice, model_slice,
                              kernel_width=smoothing_kernel_width)

        if plot:
            plt.figure()
            plt.plot(order.masked_wavelength + rv_shift, order.masked_flux,
                     label='shifted spectrum')
            # plt.plot(interp_target_slice.wavelength, interp_target_slice.flux,
            #          label='spec interp')
            # plt.plot(model_slice.wavelength,
            #          gaussian_filter1d(model_slice.flux, smoothing_kernel_width),
            #          label='smoothed model')
            plt.plot(model_slice.wavelength,
                     gaussian_filter1d(model_slice.flux, smoothing_kernel_width),
                     label='smooth model')

            plt.legend()
            plt.show()

        return rv_shift

    def __repr__(self):
        wl_unit = u.Angstrom
        min_wavelength = min([s.wavelength.min() for s in self.spectrum_list])
        max_wavelength = max([s.wavelength.max() for s in self.spectrum_list])
        return ("<EchelleSpectrum: {0} orders, {1:.1f}-{2:.1f} {3}>"
                .format(len(self.spectrum_list),
                        min_wavelength.to(wl_unit).value,
                        max_wavelength.to(wl_unit).value, wl_unit))

    def to_Spectrum1D(self, mad_outlier_factor=3):
        """
        Convert this echelle spectrum into a simple 1D spectrum.

        In wavelength regions where two spectral orders overlap, take the mean
        of the overlapping region.

        Parameters
        ----------
        mad_outlier_factor : float
            Mask positive outliers ``max_outlier_factor`` times the median
            absolute deviation plus the median of the fluxes.

        Returns
        -------
        spectrum : `~aesop.Spectrum1D`
            Simple 1D spectrum.
        """
        nonoverlapping_wavelengths = []
        nonoverlapping_fluxes = []
        dispersion_unit = None

        for i in range(1, len(self.spectrum_list) - 1):
            current_order = self.spectrum_list[i]

            previous_order = self.spectrum_list[i-1]

            next_order = self.spectrum_list[i+1]

            previous_max = previous_order.masked_wavelength.max()
            current_min = current_order.masked_wavelength.min()
            current_max = current_order.masked_wavelength.max()
            next_min = next_order.masked_wavelength.min()

            # Find the non-overlapping parts of each order, and add them to the
            # non-overlapping list
            nonoverlapping = ((current_order.masked_wavelength > previous_max) &
                              (current_order.masked_wavelength < next_min))

            if dispersion_unit is None:
                dispersion_unit = current_order.masked_wavelength[0].unit

            nonoverlapping_wavelengths.append(current_order.masked_wavelength[nonoverlapping].value)
            nonoverlapping_fluxes.append(current_order.masked_flux[nonoverlapping].value)

            current_overlapping = current_order.masked_wavelength > next_min
            next_overlapping = next_order.masked_wavelength < current_max

            # Does this order overlap with the next order?
            if np.count_nonzero(current_overlapping) > 0:
                # Find the overlapping parts between each order and the next order, and take
                # the mean of the two in the overlapping wavelength region, after interpolating
                # onto a common wavelength grid

                ol_wl_min = current_order.masked_wavelength[current_overlapping].min()
                ol_wl_max = current_order.masked_wavelength[current_overlapping].max()
                n_wl = 0.5 * (np.count_nonzero(current_overlapping) + np.count_nonzero(next_overlapping))

                common_wavelength_grid = np.linspace(ol_wl_min.value, ol_wl_max.value, int(n_wl))
                current_overlap_interp = np.interp(common_wavelength_grid,
                                                   current_order.masked_wavelength[current_overlapping].value,
                                                   current_order.masked_flux[current_overlapping].value)
                next_overlap_interp = np.interp(common_wavelength_grid,
                                                next_order.masked_wavelength[next_overlapping].value,
                                                next_order.masked_flux[next_overlapping].value)

                nonoverlapping_wavelengths.append(common_wavelength_grid)
                nonoverlapping_fluxes.append(np.mean([current_overlap_interp, next_overlap_interp], axis=0))

        nonoverlapping_fluxes = np.concatenate(nonoverlapping_fluxes)
        nonoverlapping_wavelengths = (np.concatenate(nonoverlapping_wavelengths)
                                      * dispersion_unit)

        # Compute binned mean flux for outlier masking
        bs = binned_statistic(nonoverlapping_wavelengths, nonoverlapping_fluxes,
                              bins=300, statistic='median')
        bincenters = 0.5 * (bs.bin_edges[1:] + bs.bin_edges[:-1])
        binmedians = bs.statistic
        median_interp = np.interp(nonoverlapping_wavelengths,
                                  bincenters, binmedians)

        mad = mad_std(abs(median_interp - nonoverlapping_fluxes))

        outliers = (nonoverlapping_fluxes > mad_outlier_factor * mad +
                    np.median(nonoverlapping_fluxes))

        # Also mask outliers that are very low flux
        outliers |= nonoverlapping_fluxes < -0.5

        return Spectrum1D(wavelength=nonoverlapping_wavelengths,
                          flux=nonoverlapping_fluxes, continuum_normalized=True,
                          mask=np.logical_not(outliers),
                          meta=dict(header=self.header))


def slice_spectrum(spectrum, min_wavelength, max_wavelength, norm=None):
    """
    Return a slice of a spectrum on a smaller wavelength range.

    Parameters
    ----------
    spectrum : `Spectrum1D`
        Spectrum to slice.
    min_wavelength : `~astropy.units.Quantity`
        Minimum wavelength to include in new slice
    max_wavelength : `~astropy.units.Quantity`
        Maximum wavelength to include in new slice
    norm : float
        Normalize the new slice fluxes by ``norm`` divided by the maximum flux
        of the new slice.

    Returns
    -------
    sliced_spectrum : `Spectrum1D`
    """
    in_range = ((spectrum.wavelength < max_wavelength) &
                (spectrum.wavelength > min_wavelength))

    wavelength = spectrum.wavelength[in_range]

    if norm is None:
        flux = spectrum.flux[in_range]
    else:
        flux = spectrum.flux[in_range] * norm / spectrum.flux[in_range].max()

    return Spectrum1D.from_array(wavelength, flux,
                                 dispersion_unit=spectrum.wavelength_unit)


def interpolate_spectrum(spectrum, new_wavelengths):
    """
    Linearly interpolate a spectrum onto a new wavelength grid.

    Parameters
    ----------
    spectrum : `Spectrum1D`
        Spectrum to interpolate onto new wavelengths
    new_wavelengths : `~astropy.units.Quantity`
        New wavelengths to interpolate the spectrum onto

    Returns
    -------
    interp_spec : `Spectrum1D`
        Interpolated spectrum.
    """

    sort_order = np.argsort(spectrum.masked_wavelength.to(u.Angstrom).value)
    sorted_spectrum_wavelengths = spectrum.masked_wavelength.to(u.Angstrom).value[sort_order]
    sorted_spectrum_fluxes = spectrum.masked_flux[sort_order]

    new_flux = np.interp(new_wavelengths.to(u.Angstrom).value,
                         sorted_spectrum_wavelengths,
                         sorted_spectrum_fluxes)

    return Spectrum1D.from_array(new_wavelengths, new_flux,
                                 dispersion_unit=spectrum.wavelength_unit)


def cross_corr(target_spectrum, model_spectrum, kernel_width):
    """
    Cross correlate an observed spectrum with a model.

    Convolve the model with a Gaussian kernel.

    Parameters
    ----------
    target_spectrum : `Spectrum1D`
        Observed spectrum of star
    model_spectrum : `Spectrum1D`
        Model spectrum of star
    kernel_width : float
        Smooth the model spectrum with a kernel of this width, in units of the
        wavelength step size in the model
    Returns
    -------
    wavelength_shift : `~astropy.units.Quantity`
        Wavelength shift required to shift the target spectrum to the rest-frame
    """

    smoothed_model_flux = gaussian_filter1d(model_spectrum.masked_flux,
                                            kernel_width)

    corr = np.correlate(target_spectrum.masked_flux,
                        smoothed_model_flux, mode='same')

    max_corr_ind = np.argmax(corr)
    index_shift = corr.shape[0]/2 - max_corr_ind

    delta_wavelength = np.median(np.abs(np.diff(target_spectrum.masked_wavelength)))

    wavelength_shift = index_shift * delta_wavelength
    return wavelength_shift


def _poly_model(p, x):
    """
    Polynomial model for lstsq continuum normalization
    """
    x_mean = x.mean()
    return np.polyval(p, x - x_mean)


def _residuals(p, x, y):
    """
    Model residuals for lstsq continuum normalization
    """
    return _poly_model(p, x) - y
