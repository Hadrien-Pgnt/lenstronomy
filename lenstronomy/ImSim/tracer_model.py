from lenstronomy.ImSim.image_model import ImageModel
from lenstronomy.LightModel.light_model import LightModel
from lenstronomy.ImSim.image2source_mapping import Image2SourceMapping
from lenstronomy.Util import util
import numpy as np


class TracerModel(ImageModel):
    """
    linear version class, inherits ImageModel.

    When light models use pixel-based profile types, such as 'SLIT_STARLETS',
    the WLS linear inversion is replaced by the regularized inversion performed by an external solver.
    The current pixel-based solver is provided by the SLITronomy plug-in.
    """
    def __init__(self, data_class, psf_class=None, lens_model_class=None, source_model_class=None,
                 lens_light_model_class=None, point_source_class=None, extinction_class=None,
                 tracer_source_class=None, kwargs_numerics=None, likelihood_mask=None,
                 psf_error_map_bool_list=None, kwargs_pixelbased=None):
        """

        :param data_class: ImageData() instance
        :param psf_class: PSF() instance
        :param lens_model_class: LensModel() instance
        :param source_model_class: LightModel() instance
        :param lens_light_model_class: LightModel() instance
        :param point_source_class: PointSource() instance
        :param tracer_source_class: LightModel() instance describing the tracers of the source
        :param kwargs_numerics: keyword arguments passed to the Numerics module
        :param likelihood_mask: 2d boolean array of pixels to be counted in the likelihood calculation/linear
         optimization
        :param psf_error_map_bool_list: list of boolean of length of point source models.
         Indicates whether PSF error map is used for the point source model stated as the index.
        :param kwargs_pixelbased: keyword arguments with various settings related to the pixel-based solver
         (see SLITronomy documentation) being applied to the point sources.
        """
        if likelihood_mask is None:
            likelihood_mask = np.ones_like(data_class.data)
        self.likelihood_mask = np.array(likelihood_mask, dtype=bool)
        self._mask1d = util.image2array(self.likelihood_mask)
        super(TracerModel, self).__init__(data_class, psf_class=psf_class, lens_model_class=lens_model_class,
                                          source_model_class=source_model_class,
                                          lens_light_model_class=lens_light_model_class,
                                          point_source_class=point_source_class, extinction_class=extinction_class,
                                          kwargs_numerics=kwargs_numerics, kwargs_pixelbased=kwargs_pixelbased)
        if psf_error_map_bool_list is None:
            psf_error_map_bool_list = [True] * len(self.PointSource.point_source_type_list)
        self._psf_error_map_bool_list = psf_error_map_bool_list
        if tracer_source_class is None:
            tracer_source_class = LightModel(light_model_list=[])
        self.tracer_mapping = Image2SourceMapping(lensModel=lens_model_class, sourceModel=tracer_source_class)
        self.tracer_source_class = tracer_source_class

    def tracer_model(self, kwargs_tracer, kwargs_lens, kwargs_source, kwargs_extinction=None, kwargs_special=None,
                     de_lensed=False):
        """
        tracer model as a convolved surface brightness weighted quantity
        conv(tracer * surface brightness) / conv(surface brightness)

        :param kwargs_tracer:
        :param kwargs_lens:
        :param kwargs_source:
        :return:
        """
        source_light = self._source_surface_brightness_analytical_numerics(kwargs_source, kwargs_lens,
                                                                           kwargs_extinction,
                                                                           kwargs_special=kwargs_special,
                                                                           de_lensed=de_lensed)
        source_light_conv = self.ImageNumerics.re_size_convolve(source_light, unconvolved=False)
        tracer = self._tracer_model_source(kwargs_tracer, kwargs_lens, de_lensed=de_lensed)
        tracer_brightness_conv = self.ImageNumerics.re_size_convolve(tracer * source_light, unconvolved=False)
        return tracer_brightness_conv / source_light_conv

    def _tracer_model_source(self, kwargs_tracer, kwargs_lens, de_lensed=False, k=None):
        """

        :param kwargs_tracer:
        :param kwargs_lens:
        :return:
        """
        ra_grid, dec_grid = self.ImageNumerics.coordinates_evaluate
        if de_lensed is True:
            source_light = self.tracer_source_class.surface_brightness(ra_grid, dec_grid, kwargs_tracer, k=k)
        else:
            source_light = self.tracer_mapping.image_flux_joint(ra_grid, dec_grid, kwargs_lens, kwargs_tracer, k=k)
        return source_light
