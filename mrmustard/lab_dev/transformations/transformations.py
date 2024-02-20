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
import numpy as np

from mrmustard import math
from .base import Unitary, Channel
from ...physics.representations import Bargmann
from ...physics import triples
from ..utils import make_parameter

__all__ = ["Attenuator", "Dgate"]


class Dgate(Unitary):
    r"""
    Phase space displacement gate.

    If ``x`` and/or ``y`` are iterables, their length must be equal to `1` or `N`. If their length is equal to `1`,
    all the modes share the same parameters.

    .. code-block ::

        >>> import numpy as np
        >>> from mrmustard.lab_dev import Dgate

        >>> gate = Dgate(0.1, [0.2, 0.3], modes=[1, 2])
        >>> assert gate.modes == [1, 2]
        >>> assert np.allclose(gate.x.value, [0.1, 0.1])
        >>> assert np.allclose(gate.y.value, [0.2, 0.3])

    To apply mode-specific values use a list of floats, one can optionally set bounds for each
    parameter, which the optimizer will respect.

    Args:
        x: The displacements along the `x` axis.
        x_bounds: The bounds for the displacement along the `x` axis.
        x_trainable: Whether `x` is a trainable variable.
        y: The displacements along the `y` axis.
        y_bounds: The bounds for the displacement along the `y` axis.
        y_trainable: Whether `y` is a trainable variable.
        modes: The modes this gate is applied to.

    .. details::

        The displacement gate is a Gaussian gate defined as

        .. math::
            D(\alpha) = \exp(\alpha a^\dagger -\alpha^* a) = \exp\left(-i\sqrt{2}(\re(\alpha) \hat{p} -\im(\alpha) \hat{x})/\sqrt{\hbar}\right)

        where :math:`\alpha = x + iy`.
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

    @property
    def representation(self) -> Bargmann:
        # check the representation of the base class (always ``None``, unless this gate
        # was obtained with the methods ``adjoint`` or ``dual``)
        super_rep = super().representation
        if super_rep:
            return super_rep
        
        num_modes = len(self.modes)

        xs = math.atleast_1d(self.x.value)
        if len(xs) == 1:
            xs = np.array([xs[0] for _ in range(num_modes)])
        ys = math.atleast_1d(self.y.value)
        if len(ys) == 1:
            ys = np.array([ys[0] for _ in range(num_modes)])

        return Bargmann(*triples.displacement_gate_Abc(xs, ys))


class Attenuator(Channel):
    r"""The noisy attenuator channel.

    If ``transmissivity`` andis an iterable, its length must be equal to `1` or `N`. If it length is equal to `1`,
    all the modes share the same transmissivity.

    .. code-block ::

        >>> import numpy as np
        >>> from mrmustard.lab_dev import Attenuator

        >>> channel = Attenuator(0.1, modes=[1, 2])
        >>> assert channel.modes == [1, 2]
        >>> assert np.allclose(channel.transmissivity.value, [0.1, 0.1])
        >>> assert np.allclose(channel.nbar.value, 0)

    Args:
        transmissivity: The transmissivity.
        nbar: The average number of photons in the thermal state.
        transmissivity_trainable: Whether the transmissivity is a trainable variable.
        nbar_trainable: Whether nbar is a trainable variable.
        transmissivity_bounds: The bounds for the transmissivity.
        nbar_bounds: The bounds for the average number of photons in the thermal state.
        modes: The modes this gate is applied to.

    .. details::

        The attenuator is defined as

        .. math::
            ??@yuan
    """

    def __init__(
        self,
        transmissivity: Union[Optional[float], Optional[list[float]]] = 1.0,
        nbar: float = 0.0,
        transmissivity_trainable: bool = False,
        nbar_trainable: bool = False,
        transmissivity_bounds: Tuple[Optional[float], Optional[float]] = (0.0, 1.0),
        nbar_bounds: Tuple[Optional[float], Optional[float]] = (0.0, None),
        modes: Optional[list[int]] = None,
    ):
        super().__init__(
            modes=modes or list(range(len(math.atleast_1d(transmissivity)))), name="Att"
        )
        self._add_parameter(
            make_parameter(
                transmissivity_trainable,
                transmissivity,
                "transmissivity",
                transmissivity_bounds,
                None,
            )
        )
        self._add_parameter(make_parameter(nbar_trainable, nbar, "nbar", nbar_bounds))

    @property
    def representation(self) -> Bargmann:
        # check the representation of the base class (always ``None``, unless this gate
        # was obtained with the methods ``adjoint`` or ``dual``)
        super_rep = super().representation
        if super_rep:
            return super_rep
        
        eta = self.transmissivity.value
        return Bargmann(*triples.attenuator_Abc(eta))
