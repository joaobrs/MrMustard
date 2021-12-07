# Copyright 2021 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from mrmustard.types import *
from mrmustard.utils.parametrized import Parametrized
from mrmustard.lab.abstract import State, FockMeasurement
from mrmustard.physics import fock, gaussian
from mrmustard.math import Math; math = Math()
from mrmustard.lab.states import DisplacedSqueezed, Coherent
from mrmustard import settings

__all__ = ["PNRDetector", "ThresholdDetector", "Homodyne", "Heterodyne"]


class PNRDetector(Parametrized, FockMeasurement):
    r"""
    Photon Number Resolving detector. If len(modes) > 1 the detector is applied in parallel to all of the modes provided.
    If a parameter is a single float, the parallel instances of the detector share that parameter.
    To apply mode-specific parmeters use a list of floats.
    One can optionally set bounds for each parameter, which the optimizer will respect.
    It can be supplied the full conditional detection probabilities, or it will compute them from
    the quantum efficiency (binomial) and the dark count probability (possonian).
    Arguments:
        efficiency (float or List[float]): list of quantum efficiencies for each detector
        efficiency_trainable (bool): whether the efficiency is trainable
        efficiency_bounds (Tuple[float, float]): bounds for the efficiency
        dark_counts (float or List[float]): list of expected dark counts
        dark_counts_trainable (bool): whether the dark counts are trainable
        dark_counts_bounds (Tuple[float, float]): bounds for the dark counts
        max_cutoffs (int or List[int]): largest Fock space cutoffs that the detector should expect
        stochastic_channel (Optional 2d array): if supplied, this stochastic_channel will be used for belief propagation
        modes (Optional List[int]): list of modes to apply the detector to
    """

    def __init__(
        self,
        efficiency: Union[float, List[float]] = 1.0,
        dark_counts: Union[float, List[float]] = 0.0,
        efficiency_trainable: bool = False,
        dark_counts_trainable: bool = False,
        efficiency_bounds: Tuple[Optional[float], Optional[float]] = (0.0, 1.0),
        dark_counts_bounds: Tuple[Optional[float], Optional[float]] = (0.0, None),
        stochastic_channel: Matrix = None,
        modes: List[int] = None,
    ):
        num_modes = max(len(math.atleast_1d(efficiency)), len(math.atleast_1d(dark_counts)))
        Parametrized.__init__(
            self,
            efficiency=efficiency,
            dark_counts=dark_counts,
            efficiency_trainable=efficiency_trainable,
            dark_counts_trainable=dark_counts_trainable,
            efficiency_bounds=efficiency_bounds,
            dark_counts_bounds=dark_counts_bounds,
            stochastic_channel=stochastic_channel,
            modes=modes or list(range(num_modes)),
        )

        self.recompute_stochastic_channel()

    def should_recompute_stochastic_channel(self):
        return self.efficiency_trainable or self.dark_counts_trainable

    def recompute_stochastic_channel(self, cutoffs: List[int] = None):
        if cutoffs is None:
            cutoffs = [settings.PNR_INTERNAL_CUTOFF]*len(self._modes)
        self._internal_stochastic_channel = []
        if self._stochastic_channel is not None:
            self._internal_stochastic_channel = self._stochastic_channel
        else:
            for c, qe, dc in zip(cutoffs, math.atleast_1d(self.efficiency)[:], math.atleast_1d(self.dark_counts)[:]):
                dark_prior = fock.math.poisson(max_k=c, rate=dc)
                condprob = fock.math.binomial_conditional_prob(success_prob=qe, dim_in=c, dim_out=c)
                self._internal_stochastic_channel.append(fock.math.convolve_probs_1d(condprob, [dark_prior, fock.math.eye(c)[0]]))



class ThresholdDetector(Parametrized, FockMeasurement):
    r"""
    Threshold detector: any Fock component other than vacuum counts toward a click in the detector.
    If len(modes) > 1 the detector is applied in parallel to all of the modes provided.
    If a parameter is a single float, its value is applied to all of the parallel instances of the detector.
    To apply mode-specific values use a list of floats.
    It can be supplied the full conditional detection probabilities, or it will compute them from
    the quantum efficiency (binomial) and the dark count probability (bernoulli).
    Arguments:
        conditional_probs (Optional 2d array): if supplied, these probabilities will be used for belief propagation
        efficiency (float or List[float]): list of quantum efficiencies for each detector
        dark_count_prob (float or List[float]): list of dark count probabilities for each detector
        max_cutoffs (int or List[int]): largest Fock space cutoffs that the detector should expect
    """

    def __init__(
        self,
        efficiency: Union[float, List[float]] = 1.0,
        dark_count_prob: Union[float, List[float]] = 0.0,
        efficiency_trainable: bool = False,
        dark_count_prob_trainable: bool = False,
        efficiency_bounds: Tuple[Optional[float], Optional[float]] = (0.0, 1.0),
        dark_count_prob_bounds: Tuple[Optional[float], Optional[float]] = (0.0, None),
        conditional_probs=None,
        modes: List[int] = None,
    ):

        Parametrized.__init__(
            self,
            efficiency=efficiency,
            dark_count_prob=dark_count_prob,
            efficiency_trainable=efficiency_trainable,
            dark_count_prob_trainable=dark_count_prob_trainable,
            efficiency_bounds=efficiency_bounds,
            dark_count_prob_bounds=dark_count_prob_bounds,
            conditional_probs=conditional_probs,
            modes=modes,
        )

        self.recompute_stochastic_channel()

    def should_recompute_stochastic_channel(self):
        return self.efficiency_trainable or self.dark_counts_trainable

    def recompute_stochastic_channel(self):
        self._stochastic_channel = []
        if self._conditional_probs is not None:
            self._stochastic_channel = self.conditional_probs
        else:
            for cut, qe, dc in zip(self._max_cutoffs, self.efficiency[:], self.dark_count_prob[:]):
                row1 = ((1.0 - qe) ** fock.math.arange(cut))[None, :] - dc
                row2 = 1.0 - row1
                rest = fock.math.zeros((cut - 2, cut), dtype=row1.dtype)
                condprob = fock.math.concat([row1, row2, rest], axis=0)
                self._stochastic_channel.append(condprob)

    @property
    def stochastic_channel(self) -> List[Matrix]:
        if self._stochastic_channel is None:
            self._stochastic_channel = fock.stochastic_channel()
        return self._stochastic_channel


class Homodyne(Parametrized, State):
    r"""
    Heterodyne measurement on given modes.
    """
    def __new__(cls,
            quadrature_angles: Union[float, List[float]],
            results: Union[float, List[float]] = 1.0,
            modes: List[int] = None):
        quadrature_angles = gaussian.math.astensor(quadrature_angles, dtype="float64")
        results = gaussian.math.astensor(results, dtype="float64")
        x = results * gaussian.math.cos(quadrature_angles)
        y = results * gaussian.math.sin(quadrature_angles)
        instance = DisplacedSqueezed(r=settings.HOMODYNE_SQUEEZING, phi=2*quadrature_angles, x=x, y=y)
        instance.__class__ = cls
        return instance

    def __init__(self, *args, **kwargs):
        pass


class Heterodyne(Parametrized, State):
    r"""
    Heterodyne measurement on given modes.
    """
    def __new__(cls,
            x: Union[float, List[float]] = 0.0,
            y: Union[float, List[float]] = 0.0,
            modes: List[int] = None):
        instance = Coherent(x=x, y=y, modes=modes)
        instance.__class__ = cls
        return instance

    def __init__(self, *args, **kwargs):
        pass
