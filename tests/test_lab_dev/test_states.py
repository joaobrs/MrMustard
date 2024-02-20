# Copyright 2023 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the state subpackage."""

# pylint: disable=protected-access, missing-function-docstring

import numpy as np
import pytest

from mrmustard.lab_dev.states import Coherent, DM, Ket, Vacuum
from mrmustard.lab_dev.wires import Wires


class TestKet:
    r"""
    Tests for the ``Ket`` class.
    """

    @pytest.mark.parametrize("name", [None, "my_ket"])
    @pytest.mark.parametrize("modes", [[0], [0, 1], [3, 19, 2]])
    def test_init(self, name, modes):
        state = Ket(name, modes)

        assert state.name == name or ""
        assert state.modes == sorted(modes)
        assert state.wires == Wires(modes_out_ket=modes)

class TestDM:
    r"""
    Tests for the ``DM`` class.
    """

    @pytest.mark.parametrize("name", [None, "my_dm"])
    @pytest.mark.parametrize("modes", [[0], [0, 1], [3, 19, 2]])
    def test_init(self, name, modes):
        state = DM(name, modes)

        assert state.name == name or ""
        assert state.modes == sorted(modes)
        assert state.wires == Wires(modes_out_bra=modes, modes_out_ket=modes)


class TestVacuum:
    r"""
    Tests for the ``Vacuum`` class.
    """

    @pytest.mark.parametrize("modes", [[0], [0, 1], [3, 19, 2]])
    def test_init(self, modes):
        state = Vacuum(modes)

        assert state.name == "Vacuum"
        assert state.modes == sorted(modes)


class TestCoherent:
    r"""
    Tests for the ``Coherent`` class.
    """

    modes = [0, [1, 2], [9, 7]]
    x = [1, 1, [1, 2]]
    y = [3, [3, 4], [3, 4]]

    @pytest.mark.parametrize("modes,x,y", zip(modes, x, y))
    def test_init(self, modes, x, y):
        state = Coherent(x, y, modes=modes)

        assert state.name == "Coherent"
        assert state.modes == [modes] if not isinstance(modes, list) else sorted(modes)

    def test_init_error(self):
        
