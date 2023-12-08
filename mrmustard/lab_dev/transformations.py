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

"""
The classes representing transformations in quantum circuits.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple, Union

from mrmustard import math
from .circuits import Circuit, Network
from .circuit_components import CircuitComponent
from .utils import make_parameter
from .wires import Wires


class Transformation(CircuitComponent):
    r"""
    Base class for all transformations.
    """


class Unitary(Transformation):
    r"""
    Base class for all unitary transformations.
    """

    def __init__(self, name, modes):
        super().__init__(name, modes_in_ket=modes, modes_out_ket=modes)

    def __rshift__(self, other: CircuitComponent):
        r"""
        Returns a ``Circuit`` with two connected components, namely
        ``self`` and ``other.light_copy()``.
        """
        network = Network()
        for m in self.modes:
            network.ket[m] = self.wires.out_ket[m]
        
        other_cp = other.light_copy()
        for m in other_cp.modes:
            try:
                network.ket[m].connect(other_cp.wires.in_ket[m])
            except KeyError:
                pass
            network.ket[m] = other_cp.wires.out_ket[m]
        return Circuit.from_components([self, other_cp], network)


        # modes_out_self = set(self.wires.out_ket.modes)
        # if isinstance(other_cp, CircuitComponent):
        #     modes_in_other = set(other_cp.wires.in_ket.modes)
        #     for m in modes_out_self.intersection(modes_in_other):
        #         self.wires.out_ket[m].connect(other_cp.wires.in_ket[m])
        # return to_circuit([self, other_cp])


class Dgate(Unitary):
    r"""

    If ``len(modes) > 1`` the gate is applied in parallel to all of the modes provided.

    If a parameter is a single float, the parallel instances of the gate share that parameter.

    To apply mode-specific values use a list of floats. One can optionally set bounds for each
    parameter, which the optimizer will respect.

    Args:
        x (float or List[float]): the list of displacements along the x axis
        x_bounds (float, float): bounds for the displacement along the x axis
        x_trainable (bool): whether x is a trainable variable
        y (float or List[float]): the list of displacements along the y axis
        y_bounds (float, float): bounds for the displacement along the y axis
        y_trainable bool: whether y is a trainable variable
        modes (optional, List[int]): the list of modes this gate is applied to
    """

    def __init__(
        self,
        x: Union[float, Sequence[float]] = 0.0,
        y: Union[float, Sequence[float]] = 0.0,
        x_trainable: bool = False,
        y_trainable: bool = False,
        x_bounds: Tuple[Optional[float], Optional[float]] = (None, None),
        y_bounds: Tuple[Optional[float], Optional[float]] = (None, None),
        modes: Optional[Sequence[int]] = None,
    ) -> None:
        m = max(len(math.atleast_1d(x)), len(math.atleast_1d(y)))
        super().__init__("Dgate", modes=modes or list(range(m)))
        self._add_parameter(make_parameter(x_trainable, x, "x", x_bounds))
        self._add_parameter(make_parameter(y_trainable, y, "y", y_bounds))
