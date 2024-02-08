import numpy as np
import pytest

from mrmustard import math
from mrmustard.physics.triples import *

r"""
Tests the Bargmann triples.
"""


class TestTriples:
    r"""
    Tests the Bargmann triples.
    """

    def test_incompatible_shapes(self):
        match = "incompatible shape"
        
        with pytest.raises(ValueError, match=match):
            coherent_state_Abc_triples([1, 2], [3, 4, 5])
        
        with pytest.raises(ValueError, match=match):
            coherent_state_Abc_triples([1, 2], [3, 4, 5])
        
        with pytest.raises(ValueError, match=match):
            squeezed_vacuum_state_Abc_triples([1, 2], [3, 4, 5])

        with pytest.raises(ValueError, match=match):
            displaced_squeezed_vacuum_state_Abc_triples([1, 2], [3, 4, 5], 6, 7)

    @pytest.mark.parametrize("n_modes", [1, 3])
    def test_vacuum_state_Abc_triples(self, n_modes):
        A, b, c = vacuum_state_Abc_triples(n_modes)
        
        assert np.allclose(A, np.zeros((n_modes, n_modes)))
        assert np.allclose(b, np.zeros((n_modes)))
        assert np.allclose(c, 1.0)

    @pytest.mark.parametrize("x", [0, [1], [2, 3]])
    @pytest.mark.parametrize("y", [4, [5], [6, 7]])
    def test_coherent_state_Abc_triples(self, x, y):
        A, b, c = coherent_state_Abc_triples(x, y)

        x = math.atleast_1d(x, math.complex128)
        y = math.atleast_1d(y, math.complex128)
        n_modes = max(len(x), len(y))
        if len(x) == 1:
            x = math.tile(x, (n_modes,))
        if len(y) == 1:
            y = math.tile(y, (n_modes,))
        
        assert np.allclose(A, np.zeros((n_modes, n_modes)))
        assert np.allclose(b, x + 1j*y)
        assert np.allclose(c, np.exp(-0.5 * (x**2 + y**2)))

    @pytest.mark.parametrize("r", [0.1])
    @pytest.mark.parametrize("phi", [0.2])
    def test_squeezed_vacuum_state_Abc_triples(self, r, phi):
        A, b, c = squeezed_vacuum_state_Abc_triples(r, phi)

        assert np.allclose(A, -0.09768127-0.01980097j)
        assert np.allclose(b, 0)
        assert np.allclose(c, 0.9975072676192522)
    
    @pytest.mark.parametrize("x", [0, [0.1], [0.2, 0.3]])
    @pytest.mark.parametrize("y", [0.4, [0.5], [0.6, 0.7]])
    @pytest.mark.parametrize("r", [0, [0.1], [0.2, 0.3]])
    @pytest.mark.parametrize("phi", [0.4, [0.5], [0.6, 0.7]])
    def test_displaced_squeezed_vacuum_state_Abc_triples(self, x, y, r, phi):
        A, b, c = displaced_squeezed_vacuum_state_Abc_triples(x, y, r, phi)

        x = math.atleast_1d(x, math.complex128)
        y = math.atleast_1d(y, math.complex128)
        r = math.atleast_1d(r, math.complex128)
        phi = math.atleast_1d(phi, math.complex128)
        n_modes = max(len(r), len(phi), len(x), len(y))
        if len(x) == 1:
            x = math.tile(x, (n_modes,))
        if len(y) == 1:
            y = math.tile(y, (n_modes,))
        if len(r) == 1:
            r = math.tile(r, (n_modes,))
        if len(phi) == 1:
            phi = math.tile(phi, (n_modes,))

        A1 = math.diag(-math.sinh(r) / math.cosh(r) * math.exp(1j * phi))
        b1 = (x + 1j * y) + (x - 1j * y) * math.sinh(r) / math.cosh(r) * math.exp(1j * phi)
        c1 = math.exp(
            -0.5 * (x**2 + y**2)
            - 0.5 * (x - 1j * y) ** 2 * math.sinh(r) / math.cosh(r) * math.exp(1j * phi)
        ) / math.sqrt(math.cosh(r))

        assert np.allclose(A, A1)
        assert np.allclose(b, b1)
        assert np.allclose(c, c1)

    # @pytest.mark.parametrize("r", [0.1])
    # @pytest.mark.parametrize("phi", [0.2])
    # def test_two_mode_squeezed_vacuum_state_Abc_triples(self, r, phi):
    #     A, b, c = two_mode_squeezed_vacuum_state_Abc_triples(r, phi)

    #     print(A)  # weird        
    #     assert False
        
    @pytest.mark.parametrize("nbar", [0.1])
    def test_thermal_state_Abc_triples(self, nbar):
        A, b, c = thermal_state_Abc_triples(nbar)

        A1 = [[0, 0.09090909], [0.09090909, 0]]
        b1 = 0
        c1 = 1 / (np.array(nbar) + 1)

        assert np.allclose(A, A1)
        assert np.allclose(b, b1)
        assert np.allclose(c, c1)
   
    @pytest.mark.parametrize("theta", [0.1])
    def test_rotation_gate_Abc_triples(self, theta):
        A, b, c = rotation_gate_Abc_triples(theta)

        A1 = [[0, 0.99500417+0.09983342j], [0.99500417+0.09983342j, 0]]
        b1 = 0
        c1 = 1

        assert np.allclose(A, A1)
        assert np.allclose(b, b1)
        assert np.allclose(c, c1)

    def test_displacement_gate_Abc_triples(self):
        pass

    def test_squeezing_gate_Abc_triples(self):
        pass

    def test_beamsplitter_gate_Abc_triples(self):
        pass

    def test_attenuator_Abc_triples(self):
        pass

    def test_amplifier_Abc_triples(self):
        pass

    def test_fock_damping_Abc_triples(self):
        pass


    