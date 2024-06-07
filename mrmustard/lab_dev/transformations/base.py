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
This module contains the base classes for the available unitaries and channels on quantum states.

In the docstrings defining the available unitaries we provide a definition in terms of
the symplectic matrix :math:`S` and the real vector :math:`d`. For deterministic Gaussian channels,
we use the two matrices :math:`X` and :math:`Y` and the vector :math:`d`. Additionally, we
provide the ``(A, b, c)`` triples that define the transformation in the Fock Bargmann
representation.
"""

# pylint: disable=import-outside-toplevel
from __future__ import annotations

from typing import Optional, Sequence
from mrmustard.utils.typing import RealMatrix, RealVector
from mrmustard import math
from mrmustard.lab_dev.wires import Wires
from mrmustard.physics.representations import Bargmann, Fock
from mrmustard import physics
from ..circuit_components import CircuitComponent

__all__ = ["Transformation", "Operation", "Unitary", "Map", "Channel"]


class Transformation(CircuitComponent):
    r"""
    Base class for all transformations. Currently provides the ability to compute the inverse
    of the transformation.
    """

    @classmethod
    def from_quadrature(
        cls,
        modes_out: Sequence[int],
        modes_in: Sequence[int],
        triple: tuple,
        phi: float = 0,
        name: Optional[str] = None,
    ) -> Operation:
        r"""Initialize an Operation from the given quadrature triple."""
        from mrmustard.lab_dev.circuit_components_utils import BtoQ

        QtoB_out = BtoQ(modes_out, phi).inverse()
        QtoB_in = BtoQ(modes_in, phi).inverse().dual
        QQ = cls(modes_out, modes_in, Bargmann(*triple))
        BB = QtoB_in >> QQ >> QtoB_out
        return cls(modes_out, modes_in, BB.representation, name)

    @classmethod
    def from_bargmann(
        cls,
        modes_out: Sequence[int],
        modes_in: Sequence[int],
        triple: tuple,
        name: Optional[str] = None,
    ) -> Operation:
        r"""Initialize a Transformation from the given Bargmann triple."""
        return cls(modes_out, modes_in, Bargmann(*triple), name)

    def inverse(self) -> Transformation:
        r"""Returns the mathematical inverse of the transformation, if it exists.
        Note that it can be unphysical, for example when the original is not unitary.

        Returns:
            Transformation: the inverse of the transformation.

        Raises:
            NotImplementedError: if the inverse of this transformation is not supported.
        """
        if not len(self.wires.input) == len(self.wires.output):
            raise NotImplementedError(
                "Only Transformations with the same number of input and output wires are supported."
            )
        if not isinstance(self.representation, Bargmann):
            raise NotImplementedError("Only Bargmann representation is supported.")
        if self.representation.ansatz.batch_size > 1:
            raise NotImplementedError("Batched transformations are not supported.")

        # compute the inverse
        A, b, _ = self.dual.representation.conj().triple  # apply X(.)X
        almost_inverse = self._from_attributes(
            Bargmann(math.inv(A[0]), -math.inv(A[0]) @ b[0], 1 + 0j), self.wires
        )
        almost_identity = (
            self @ almost_inverse
        )  # TODO: this is not efficient, need to get c from formula
        invert_this_c = almost_identity.representation.c
        actual_inverse = self._from_attributes(
            Bargmann(math.inv(A[0]), -math.inv(A[0]) @ b[0], 1 / invert_this_c),
            self.wires,
            self.name + "_inv",
        )
        return actual_inverse

    def __repr__(self) -> str:
        return super().__repr__().replace("CircuitComponent", self.__class__.__name__)


class Operation(Transformation):
    r"""A CircuitComponent with input and output wires, on the ket side."""

    def __init__(
        self,
        modes_out: tuple[int, ...] = (),
        modes_in: tuple[int, ...] = (),
        representation: Optional[Bargmann | Fock] = None,
        name: Optional[str] = None,
    ):
        super().__init__(
            modes_out_ket=modes_in,
            modes_in_ket=modes_out,
            representation=representation,
            name=name or self.__class__.__name__,
        )
        if representation is not None:
            self._representation = representation


class Unitary(Operation):
    r"""
    Base class for all unitary transformations.

    Arguments:
        name: The name of this transformation.
        modes: The modes that this transformation acts on.
    """
    def __rshift__(self, other: CircuitComponent) -> CircuitComponent:
        r"""
        Contracts ``self`` and ``other`` as it would in a circuit, adding the adjoints when
        they are missing.

        Returns a ``Unitary`` when ``other`` is a ``Unitary``, a ``Channel`` when ``other`` is a
        ``Channel``, and a ``CircuitComponent`` otherwise.
        """
        ret = super().__rshift__(other)

        if isinstance(other, Unitary):
            return Unitary._from_attributes(ret.representation, ret.wires)
        elif isinstance(other, Channel):
            return Channel._from_attributes(ret.representation, ret.wires)
        return ret

    @classmethod
    def from_symplectic(
        cls,
        modes: Sequence[int],
        symplectic: RealMatrix,
        displacement: RealVector,
        name: Optional[str] = None,
    ) -> Unitary:
        r"""Initialize a Unitary from the given symplectic matrix in qqpp basis.
        I.e. the axes are ordered as [q0, q1, ..., p0, p1, ...].
        """
        if symplectic.shape[-2:] != (2 * len(modes), 2 * len(modes)):
            raise ValueError(
                "Symplectic matrix and number of modes don't match. "
                + f"Modes imply shape {(2 * len(modes), 2 * len(modes))}, "
                + f"but shape is {symplectic.shape[-2:]}."
            )
        A, b, c = physics.bargmann.wigner_to_bargmann_U(symplectic, displacement)
        return Unitary._from_attributes(
            representation=Bargmann(A, b, c),
            wires=Wires(set(), set(), set(modes), set(modes)),
            name=name,
        )


class Map(Transformation):
    r"""A CircuitComponent more general than Channels, which are CPTP maps.

    Arguments:
        modes_out: The output modes of this Map.
        modes_in: The input modes of this Map.
        representation: The representation of this Map.
        name: The name of this Map.
    """

    def __init__(
        self,
        modes_out: tuple[int, ...] = (),
        modes_in: tuple[int, ...] = (),
        representation: Optional[Bargmann | Fock] = None,
        name: Optional[str] = None,
    ):
        super().__init__(
            modes_out_bra=modes_out,
            modes_in_bra=modes_in,
            modes_out_ket=modes_out,
            modes_in_ket=modes_in,
            representation=representation,
            name=name or self.__class__.__name__,
        )


class Channel(Map):
    r"""
    Base class for all CPTP channels.

    Arguments:
        modes_out: The output modes of this Channel.
        modes_in: The input modes of this Channel.
        representation: The representation of this Channel.
        name: The name of this Channel
    """

    def __rshift__(self, other: CircuitComponent) -> CircuitComponent:
        r"""
        Contracts ``self`` and ``other`` as it would in a circuit, adding the adjoints when
        they are missing.

        Returns a ``Channel`` when ``other`` is a ``Channel`` or a ``Unitary``, and a ``CircuitComponent`` otherwise.
        """
        ret = super().__rshift__(other)
        if isinstance(other, (Channel, Unitary)):
            return Channel._from_attributes(ret.representation, ret.wires)
        return ret
