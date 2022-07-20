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

import pytest
from hypothesis import given, strategies as st
from hypothesis.extra.numpy import arrays

import numpy as np
from scipy.stats import poisson

from mrmustard.math import Math
from mrmustard.lab import (
    PNRDetector,
    Coherent,
    Sgate,
    Vacuum,
    S2gate,
    BSgate,
    Attenuator,
    Homodyne,
    Heterodyne,
    TMSV,
    Dgate,
    Fock,
)
from mrmustard import physics, settings

math = Math()
np.random.seed(137)
hbar = settings.HBAR


class TestPNRDetector:
    """tests related to PNR detectors"""

    @given(
        alpha=st.complex_numbers(min_magnitude=0, max_magnitude=1),
        eta=st.floats(0, 1),
        dc=st.floats(0, 0.2),
    )
    def test_detector_coherent_state(self, alpha, eta, dc):
        """Tests the correct Poisson statistics are generated when a coherent state hits an imperfect detector"""
        detector = PNRDetector(efficiency=eta, dark_counts=dc, modes=[0])
        ps = Coherent(x=alpha.real, y=alpha.imag) << detector
        expected = poisson.pmf(k=np.arange(len(ps)), mu=eta * np.abs(alpha) ** 2 + dc)
        assert np.allclose(ps, expected)

    @given(
        r=st.floats(0, 0.5),
        phi=st.floats(0, 2 * np.pi),
        eta=st.floats(0, 1),
        dc=st.floats(0, 0.2),
    )
    def test_detector_squeezed_state(self, r, phi, eta, dc):
        """Tests the correct mean and variance are generated when a squeezed state hits an imperfect detector"""
        S = Sgate(r=r, phi=phi)
        ps = Vacuum(1) >> S >> PNRDetector(efficiency=eta, dark_counts=dc)
        assert np.allclose(np.sum(ps), 1.0)
        mean = np.arange(len(ps)) @ ps.numpy()
        expected_mean = eta * np.sinh(r) ** 2 + dc
        assert np.allclose(mean, expected_mean)
        variance = np.arange(len(ps)) ** 2 @ ps.numpy() - mean**2
        expected_variance = eta * np.sinh(r) ** 2 * (1 + eta * (1 + 2 * np.sinh(r) ** 2)) + dc
        assert np.allclose(variance, expected_variance)

    @given(
        r=st.floats(0, 0.5),
        phi=st.floats(0, 2 * np.pi),
        eta_s=st.floats(0, 1),
        eta_i=st.floats(0, 1),
        dc_s=st.floats(0, 0.2),
        dc_i=st.floats(0, 0.2),
    )
    def test_detector_two_mode_squeezed_state(self, r, phi, eta_s, eta_i, dc_s, dc_i):
        """Tests the correct mean and variance are generated when a two mode squeezed state hits an imperfect detector"""
        pnr = PNRDetector(efficiency=[eta_s, eta_i], dark_counts=[dc_s, dc_i])
        ps = Vacuum(2) >> S2gate(r=r, phi=phi) >> pnr
        n = np.arange(len(ps))
        mean_s = np.sum(ps, axis=1) @ n
        n_s = eta_s * np.sinh(r) ** 2
        expected_mean_s = n_s + dc_s
        mean_i = np.sum(ps, axis=0) @ n
        n_i = eta_i * np.sinh(r) ** 2
        expected_mean_i = n_i + dc_i
        expected_mean_s = n_s + dc_s
        var_s = np.sum(ps, axis=1) @ n**2 - mean_s**2
        var_i = np.sum(ps, axis=0) @ n**2 - mean_i**2
        expected_var_s = n_s * (n_s + 1) + dc_s
        expected_var_i = n_i * (n_i + 1) + dc_i
        covar = n @ ps.numpy() @ n - mean_s * mean_i
        expected_covar = eta_s * eta_i * (np.sinh(r) * np.cosh(r)) ** 2
        assert np.allclose(mean_s, expected_mean_s)
        assert np.allclose(mean_i, expected_mean_i)
        assert np.allclose(var_s, expected_var_s)
        assert np.allclose(var_i, expected_var_i)
        assert np.allclose(covar, expected_covar)

    def test_postselection(
        self,
    ):
        """Check the correct state is heralded for a two-mode squeezed vacuum with perfect detector"""
        n_mean = 1.0
        n_measured = 1
        cutoff = 3
        detector = PNRDetector(efficiency=1.0, dark_counts=0.0, cutoffs=[cutoff])
        S2 = S2gate(r=np.arcsinh(np.sqrt(n_mean)), phi=0.0)
        proj_state = (Vacuum(2) >> S2 >> detector)[n_measured]
        success_prob = math.real(math.trace(proj_state))
        proj_state = proj_state / math.trace(proj_state)
        # outputs the ket/dm in the third mode by projecting the first and second in 1,2 photons
        expected_prob = 1 / (1 + n_mean) * (n_mean / (1 + n_mean)) ** n_measured
        assert np.allclose(success_prob, expected_prob)
        expected_state = np.zeros_like(proj_state)
        expected_state[n_measured, n_measured] = 1.0
        assert np.allclose(proj_state, expected_state)

    @given(eta=st.floats(0, 1))
    def test_loss_probs(self, eta):
        "Checks that a lossy channel is equivalent to quantum efficiency on detection probs"
        ideal_detector = PNRDetector(efficiency=1.0, dark_counts=0.0)
        lossy_detector = PNRDetector(efficiency=eta, dark_counts=0.0)
        S = Sgate(r=0.2, phi=[0.0, 0.7])
        BS = BSgate(theta=1.4, phi=0.0)
        L = Attenuator(transmissivity=eta)
        dms_lossy = Vacuum(2) >> S[0, 1] >> BS[0, 1] >> lossy_detector[0]
        dms_ideal = Vacuum(2) >> S[0, 1] >> BS[0, 1] >> L[0] >> ideal_detector[0]
        assert np.allclose(dms_lossy, dms_ideal)


class TestHomodyneDetector:
    """tests related to homodyne detectors"""

    @pytest.mark.parametrize(
        "homodyne_args",
        [
            {"modes": [1], "quadrature_angle": 0, "result": [0.3]},
            {"modes": [1], "quadrature_angle": 0, "result": None},
        ],
    )
    def test_homodyne_mode_kwargs(self, homodyne_args):
        """Test that S gates and Homodyne mesurements are applied to the correct modes via the `modes` kwarg.

        Here the initial state is a "diagonal" (angle=pi/2) squeezed state in mode 0
        and a "vertical" (angle=0) squeezed state in mode 1.

        Because the modes are separable, measuring in one mode should leave the state in the
        other mode unchaged.
        """

        S1 = Sgate(modes=[0], r=1, phi=np.pi / 2)
        S2 = Sgate(modes=[1], r=1, phi=0)
        initial_state = Vacuum(2) >> S1 >> S2
        final_state = initial_state << Homodyne(**homodyne_args)

        expected_state = Vacuum(1) >> S1

        assert np.allclose(final_state.dm(), expected_state.dm())

    @given(s=st.floats(min_value=0.0, max_value=10.0), X=st.floats(-10.0, 10.0))
    def test_homodyne_on_2mode_squeezed_vacuum(self, s, X):
        """Check that homodyne detection on TMSV for q-quadrature (``quadrature_angle=0.0``)"""
        homodyne = Homodyne(quadrature_angle=0.0, result=X)
        r = homodyne.r.value
        remaining_state = TMSV(r=np.arcsinh(np.sqrt(abs(s)))) << homodyne[0]
        cov = (
            np.diag(
                [
                    1 - 2 * s / (1 / np.tanh(r) * (1 + s) + s),
                    1 + 2 * s / (1 / np.tanh(r) * (1 + s) - s),
                ]
            )
            * hbar
            / 2.0
        )
        assert np.allclose(remaining_state.cov, cov)
        means = np.array(
            [2 * np.sqrt(s * (1 + s)) * X / (np.exp(-2 * r) + 1 + 2 * s), 0.0]
        ) * np.sqrt(2 * hbar)
        assert np.allclose(remaining_state.means, means)

    @given(s=st.floats(1.0, 10.0), X=st.floats(-10.0, 10.0), angle=st.floats(0, np.pi))
    def test_homodyne_on_2mode_squeezed_vacuum_with_angle(self, s, X, angle):
        """Check that homodyne detection on TMSV works with an arbitrary quadrature angle"""
        homodyne = Homodyne(quadrature_angle=angle, result=X)
        r = homodyne.r.value
        remaining_state = TMSV(r=np.arcsinh(np.sqrt(abs(s)))) << homodyne[0]
        denom = 1 + 2 * s * (s + 1) + (2 * s + 1) * np.cosh(2 * r)
        cov = (
            hbar
            / 2
            * np.array(
                [
                    [
                        1
                        + 2 * s
                        - 2
                        * s
                        * (s + 1)
                        * (1 + 2 * s + np.cosh(2 * r) + np.cos(2 * angle) * np.sinh(2 * r))
                        / denom,
                        2 * s * (1 + s) * np.sin(2 * angle) * np.sinh(2 * r) / denom,
                    ],
                    [
                        2 * s * (1 + s) * np.sin(2 * angle) * np.sinh(2 * r) / denom,
                        (
                            1
                            + 2 * s
                            + (1 + 2 * s * (1 + s)) * np.cosh(2 * r)
                            + 2 * s * (s + 1) * np.cos(2 * angle) * np.sinh(2 * r)
                        )
                        / denom,
                    ],
                ]
            )
        )
        assert np.allclose(remaining_state.cov, cov)
        # TODO: figure out why this is not working
        # denom = 1 + 2 * s * (1 + s) + (1 + 2 * s) * np.cosh(2 * r)
        # means = (
        #     np.array(
        #         [
        #             np.sqrt(s * (1 + s))
        #             * X
        #             * (np.cos(angle) * (1 + 2 * s + np.cosh(2 * r)) + np.sinh(2 * r))
        #             / denom,
        #             -np.sqrt(s * (1 + s)) * X * (np.sin(angle) * (1 + 2 * s + np.cosh(2 * r))) / denom,
        #         ]
        #     )
        #     * np.sqrt(2 * hbar)
        # )
        # assert np.allclose(remaining_state.means, means)

    @given(
        s=st.floats(min_value=0.0, max_value=10.0),
        X=st.floats(-10.0, 10.0),
        d=arrays(np.float64, 4, elements=st.floats(-10.0, 10.0)),
    )
    def test_homodyne_on_2mode_squeezed_vacuum_with_displacement(self, s, X, d):
        """Check that homodyne detection on displaced TMSV works"""
        tmsv = TMSV(r=np.arcsinh(np.sqrt(s))) >> Dgate(x=d[:2], y=d[2:])
        homodyne = Homodyne(modes=[0], quadrature_angle=0.0, result=X)
        r = homodyne.r.value
        remaining_state = tmsv << homodyne[0]
        xb, xa, pb, pa = d
        means = np.array(
            [
                xa
                + (2 * np.sqrt(s * (s + 1)) * (X - xb))
                / (1 + 2 * s + np.cosh(2 * r) - np.sinh(2 * r)),
                pa
                + (2 * np.sqrt(s * (s + 1)) * pb) / (1 + 2 * s + np.cosh(2 * r) + np.sinh(2 * r)),
            ]
        ) * np.sqrt(2 * hbar)
        assert np.allclose(remaining_state.means, means)

    N_MEAS = 500  # number of homodyne measurements to perform
    NUM_STDS = 10.0
    std_10 = NUM_STDS / np.sqrt(N_MEAS)

    def test_sampling_mean_and_std_vacuum(self):
        """Tests that the mean and standard deviation estimates of many homodyne
        measurements are in agreement with the expected values for the
        vacuum state"""

        results = np.empty((self.N_MEAS, 2))
        for idx in range(self.N_MEAS):
            results[idx, :] = Vacuum(1) << Homodyne(0.0, result=None, modes=[0])

        assert np.allclose(results.mean(axis=0)[0], 0.0, atol=self.std_10, rtol=0)
        assert np.allclose(results.std(axis=0)[0], 1.0, atol=self.std_10, rtol=0)

    def test_sampling_mean_coherent(self):
        """Tests that the mean and standard deviation estimates of many homodyne
        measurements are in agreement with the expected values for a
        coherent state"""

        x = 2
        y = 1

        results = np.empty((self.N_MEAS, 2))
        for idx in range(self.N_MEAS):
            results[idx, :] = Coherent(x, y) << Homodyne(0.0, result=None, modes=[0])

        assert np.allclose(results.mean(axis=0)[0], x**2, atol=self.std_10, rtol=0)


class TestHeterodyneDetector:
    """tests related to heterodyne detectors"""

    def test_heterodyne_mode_kwargs(self):
        """Test that S gates and Heterodyne mesurements are applied to the correct modes via the `modes` kwarg.

        Here the initial state is a "diagonal" (angle=pi/2) squeezed state in mode 0
        and a "vertical" (angle=0) squeezed state in mode 1.

        Because the modes are separable, measuring in one mode should leave the state in the
        other mode unchaged.
        """

        S1 = Sgate(modes=[0], r=1, phi=np.pi / 2)
        S2 = Sgate(modes=[1], r=1, phi=0)
        initial_state = Vacuum(2) >> S1 >> S2
        final_state = initial_state << Heterodyne(modes=[1])

        expected_state = Vacuum(1) >> S1

        assert np.allclose(final_state.dm(), expected_state.dm())

    @given(
        s=st.floats(min_value=0.0, max_value=10.0),
        x=st.floats(-10.0, 10.0),
        y=st.floats(-10.0, 10.0),
        d=arrays(np.float64, 4, elements=st.floats(-10.0, 10.0)),
    )
    def test_heterodyne_on_2mode_squeezed_vacuum_with_displacement(
        self, s, x, y, d
    ):  # TODO: check if this is correct
        """Check that heterodyne detection on TMSV works with an arbitrary displacement"""
        tmsv = TMSV(r=np.arcsinh(np.sqrt(s))) >> Dgate(x=d[:2], y=d[2:])
        heterodyne = Heterodyne(modes=[0], x=x, y=y)
        remaining_state = tmsv << heterodyne[0]
        cov = hbar / 2 * np.array([[1, 0], [0, 1]])
        assert np.allclose(remaining_state.cov, cov)
        xb, xa, pb, pa = d
        means = (
            np.array(
                [
                    xa * (1 + s) + np.sqrt(s * (1 + s)) * (x - xb),
                    pa * (1 + s) + np.sqrt(s * (1 + s)) * (pb - y),
                ]
            )
            * np.sqrt(2 * hbar)
            / (1 + s)
        )
        assert np.allclose(remaining_state.means, means, atol=1e-5)


class TestNormalization:
    """tests evaluating normalization of output states after projection"""

    def test_norm_1mode(self):
        """Checks that projecting a single mode coherent state onto a number state
        returns the expected norm."""
        assert np.allclose(
            Coherent(2.0) << Fock(3),
            np.abs((2.0**3) / np.sqrt(6) * np.exp(-0.5 * 4.0)) ** 2,
        )

    @pytest.mark.parametrize(
        "normalize, expected_norm",
        ([True, 1.0], [False, (2.0**3) / np.sqrt(6) * np.exp(-0.5 * 4.0)]),
    )
    def test_norm_2mode(self, normalize, expected_norm):
        """Checks that projecting a two-mode coherent state onto a number state
        produces a state with the expected norm."""
        leftover = Coherent(x=[2.0, 2.0]) << Fock(3, normalize=normalize)[0]
        assert np.isclose(expected_norm, physics.norm(leftover), atol=1e-5)

    def test_norm_2mode_gaussian_normalized(self):
        """Checks that after projection the norm of the leftover state is as expected."""
        leftover = Coherent(x=[2.0, 2.0]) << Coherent(x=1.0, normalize=True)[0]
        assert np.isclose(1.0, physics.norm(leftover), atol=1e-5)
