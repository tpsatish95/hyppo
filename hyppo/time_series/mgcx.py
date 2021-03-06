from .base import TimeSeriesTest
from ._utils import _CheckInputs, compute_stat, compute_scale_at_lag
from ..independence import MGC


class MGCX(TimeSeriesTest):
    r"""
    Class for running the MGCX test for independence of time series.

    MGCX is an independence test between two (paired) time series of
    not necessarily equal dimensions. The population parameter is 0 if and only if the
    time series are independent. It is based upon energy distance between distributions.

    Parameters
    ----------
    compute_distance : callable(), optional (default: euclidean)
        A function that computes the distance among the samples within each
        data matrix. Set to `None` if `x` and `y` are already distance
        matrices. To call a custom function, either create the distance matrix
        before-hand or create a function of the form ``compute_distance(x)``
        where `x` is the data matrix for which pairwise distances are
        calculated.

    max_lag : int, optional (default: 0)
        The maximum number of lags in the past to check dependence between `x` and the
        shifted `y`. Also the :math:`M` hyperparmeter below.

    See Also
    --------
    MGC: Multiscale graph correlation test statistic and p-value.
    DcorrX: Cross distance correlation test statistic and p-value.

    Notes
    -----
    The statistic can be derived as follows:

    Let :math:`x` and :math:`y` be :math:`(n, p)` and :math:`(n, q)` series
    respectively, which each contain :math:`y` observations of the series :math:`(X_t)`
    and :math:`(Y_t)`. Similarly, let :math:`x[j:n]` be the :math:`(n-j, p)` last
    :math:`n-j` observations of :math:`x`. Let :math:`y[0:(n-j)]` be the
    :math:`(n-j, p)` first :math:`n-j` observations of :math:`y`. Let :math:`M` be the
    maximum lag hyperparameter. The cross distance correlation is,

    .. math::

        \mathrm{MGCX}_n (x, y) =  \sum_{j=0}^M frac{n-j}{n}
                                  \mathrm{MGC}_n (x[j:n], y[0:(n-j)])

    References
    ----------
    .. [#1DcorX] Mehta, R., Chung, J., Shen C., Xu T., Vogelstein, J. T. (2019).
                A Consistent Independence Test for Multivariate Time-Series.
                *ArXiv*
    """

    def __init__(self, compute_distance=None, max_lag=0):
        TimeSeriesTest.__init__(self, compute_distance=compute_distance)
        self.max_lag = max_lag

    def _statistic(self, x, y):
        r"""
        Helper function that calculates the MGCX test statistic.

        Parameters
        ----------
        x, y : ndarray
            Input data matrices. `x` and `y` must have the same number of
            samples. That is, the shapes must be `(n, p)` and `(n, q)` where
            `n` is the number of samples and `p` and `q` are the number of
            dimensions. Alternatively, `x` and `y` can be distance matrices,
            where the shapes must both be `(n, n)`.

        Returns
        -------
        stat : float
            The computed MGCX statistic.
        opt_lag : int
            The computed optimal lag.
        opt_scale : tuple
            The computed optimal scale as a pair of two elements.
        """

        stat, opt_lag = compute_stat(x, y, MGC, self.compute_distance, self.max_lag)
        self.stat = stat
        self.opt_lag = opt_lag

        # Run the test at the optimal lag to get the optimal scale.
        opt_scale = compute_scale_at_lag(x, y, opt_lag, self.compute_distance)
        self.opt_scale = opt_scale

        return stat, opt_lag, opt_scale

    def test(self, x, y, reps=1000, workers=1):
        r"""
        Calculates the MGCX test statistic and p-value.

        Parameters
        ----------
        x, y : ndarray
            Input data matrices. `x` and `y` must have the same number of
            samples. That is, the shapes must be `(n, p)` and `(n, q)` where
            `n` is the number of samples and `p` and `q` are the number of
            dimensions. Alternatively, `x` and `y` can be distance matrices,
            where the shapes must both be `(n, n)`.
        reps : int, optional (default: 1000)
            The number of replications used to estimate the null distribution
            when using the permutation test used to calculate the p-value.
        workers : int, optional (default: 1)
            The number of cores to parallelize the p-value computation over.
            Supply -1 to use all cores available to the Process.
        auto : bool (default: True)
            Automatically uses fast approximation when sample size and size of array
            is greater than 20. If True, and sample size is greater than 20, a fast
            chi2 approximation will be run. Parameters ``reps`` and ``workers`` are
            irrelevant in this case.

        Returns
        -------
        stat : float
            The computed MGCX statistic.
        pvalue : float
            The computed MGCX p-value.
        mgcx_dict : dict
            Contains additional useful returns containing the following keys:

                - opt_lag : int
                    The optimal lag that maximizes the strength of the relationship
                    with respect to lag.
                - opt_scale : tuple
                    The optimal scale that maximizes the strength of the relationship
                    with respect to scale.

        Examples
        --------
        The optimal scale should be global `[n, n]` for cases of linear correlation.

        >>> import numpy as np
        >>> from hyppo.time_series import MGCX
        >>> np.random.seed(456)
        >>> x = np.arange(7)
        >>> y = x
        >>> stat, pvalue, mgcx_dict = MGCX().test(x, y, reps = 100)
        >>> '%.1f, %.2f, [%d, %d]' % (stat, pvalue, mgcx_dict['opt_scale'][0],
        ... mgcx_dict['opt_scale'][1])
        '1.0, 0.02, [7, 7]'

        The increasing the max_lag can increase the ability to identify dependence.

        >>> import numpy as np
        >>> from hyppo.time_series import MGCX
        >>> np.random.seed(1234)
        >>> x = np.random.permutation(10)
        >>> y = np.roll(x, -1)
        >>> stat, pvalue, mgcx_dict = MGCX(max_lag=1).test(x, y, reps=1000)
        >>> '%.1f, %.2f, %d' % (stat, pvalue, mgcx_dict['opt_lag'])
        '1.1, 0.01, 1'

        In addition, the inputs can be distance matrices. Using this is the,
        same as before, except the ``compute_distance`` parameter must be set
        to ``None``.

        >>> import numpy as np
        >>> from hyppo.time_series import MGCX
        >>> np.random.seed(789)
        >>> x = np.ones((10, 10)) - np.identity(10)
        >>> y = 2 * x
        >>> mgcx = MGCX(compute_distance=None)
        >>> stat, pvalue, mgcx_dict = mgcx.test(x, y)
        >>> '%.1f, %.2f' % (stat, pvalue)
        '1.0, 0.00'
        """
        check_input = _CheckInputs(
            x, y, max_lag=self.max_lag, compute_distance=self.compute_distance
        )
        x, y = check_input()

        stat, pvalue, stat_list = super(MGCX, self).test(x, y, reps, workers)
        mgcx_dict = {"opt_lag": stat_list[1], "opt_scale": stat_list[2]}

        return stat, pvalue, mgcx_dict
