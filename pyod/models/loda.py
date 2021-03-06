# -*- coding: utf-8 -*-
"""Loda: Lightweight on-line detector of anomalies
Adapted from tilitools (https://github.com/nicococo/tilitools) by
"""
# Author: Yue Zhao <zhaoy@cmu.edu>
# License: BSD 2 clause

from __future__ import division
from __future__ import print_function

import numpy as np
from sklearn.utils.validation import check_is_fitted
from sklearn.utils import check_array

from .base import BaseDetector


class LODA(BaseDetector):
    """Loda: Lightweight on-line detector of anomalies. See
    :cite:`pevny2016loda` for more information.

    Parameters
    ----------
    contamination : float in (0., 0.5), optional (default=0.1)
        The amount of contamination of the data set,
        i.e. the proportion of outliers in the data set. Used when fitting to
        define the threshold on the decision function.

    n_bins : int, optional (default = 10)
        The number of bins for the histogram.

    n_random_cuts : int, optional (default = 100)
        The number of random cuts.

    Attributes
    ----------
    decision_scores_ : numpy array of shape (n_samples,)
        The outlier scores of the training data.
        The higher, the more abnormal. Outliers tend to have higher
        scores. This value is available once the detector is
        fitted.

    threshold_ : float
        The threshold is based on ``contamination``. It is the
        ``n_samples * contamination`` most abnormal samples in
        ``decision_scores_``. The threshold is calculated for generating
        binary outlier labels.

    labels_ : int, either 0 or 1
        The binary labels of the training data. 0 stands for inliers
        and 1 for outliers/anomalies. It is generated by applying
        ``threshold_`` on ``decision_scores_``.
    """

    def __init__(self, contamination=0.1, n_bins=10, n_random_cuts=100):
        super(LODA, self).__init__(contamination=contamination)
        self.n_bins = n_bins
        self.n_random_cuts = n_random_cuts
        self.weights = np.ones(n_random_cuts, dtype=float) / n_random_cuts

    def fit(self, X, y=None):
        """Fit detector. y is ignored in unsupervised methods.

        Parameters
        ----------
        X : numpy array of shape (n_samples, n_features)
            The input samples.

        y : Ignored
            Not used, present for API consistency by convention.

        Returns
        -------
        self : object
            Fitted estimator.
        """
        # validate inputs X and y (optional)
        X = check_array(X)
        self._set_n_classes(y)
        pred_scores = np.zeros([X.shape[0], 1])

        n_components = X.shape[1]
        n_nonzero_components = np.sqrt(n_components)
        n_zero_components = n_components - np.int(n_nonzero_components)

        self.projections_ = np.random.randn(self.n_random_cuts, n_components)
        self.histograms_ = np.zeros((self.n_random_cuts, self.n_bins))
        self.limits_ = np.zeros((self.n_random_cuts, self.n_bins + 1))
        for i in range(self.n_random_cuts):
            rands = np.random.permutation(n_components)[:n_zero_components]
            self.projections_[i, rands] = 0.
            projected_data = self.projections_[i, :].dot(X.T)
            self.histograms_[i, :], self.limits_[i, :] = np.histogram(
                projected_data, bins=self.n_bins, density=False)
            self.histograms_[i, :] += 1e-12
            self.histograms_[i, :] /= np.sum(self.histograms_[i, :])

            # calculate the scores for the training samples
            inds = np.searchsorted(self.limits_[i, :self.n_bins - 1],
                                   projected_data, side='left')
            pred_scores[:, 0] += -self.weights[i] * np.log(
                self.histograms_[i, inds])

        self.decision_scores_ = (pred_scores / self.n_random_cuts).ravel()
        self._process_decision_scores()

        return self

    def decision_function(self, X):
        """Predict raw anomaly score of X using the fitted detector.

        The anomaly score of an input sample is computed based on different
        detector algorithms. For consistency, outliers are assigned with
        larger anomaly scores.

        Parameters
        ----------
        X : numpy array of shape (n_samples, n_features)
            The training input samples. Sparse matrices are accepted only
            if they are supported by the base estimator.

        Returns
        -------
        anomaly_scores : numpy array of shape (n_samples,)
            The anomaly score of the input samples.
        """
        check_is_fitted(self, ['projections_', 'decision_scores_',
                               'threshold_', 'labels_'])

        X = check_array(X)
        pred_scores = np.zeros([X.shape[0], 1])
        for i in range(self.n_random_cuts):
            projected_data = self.projections_[i, :].dot(X.T)
            inds = np.searchsorted(self.limits_[i, :self.n_bins - 1],
                                   projected_data, side='left')
            pred_scores[:, 0] += -self.weights[i] * np.log(
                self.histograms_[i, inds])
        pred_scores /= self.n_random_cuts
        return pred_scores.ravel()
