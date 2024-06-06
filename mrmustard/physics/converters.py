# Copyright 2024 Xanadu Quantum Technologies Inc.

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
This module contains the functions to convert between different representations.

Though MrMustard runs internally only with Fock and Bargmann representations, it supports different representations in the initialization and the result part.

The conversions exist:

* From Bargmann representation to Fock representation (for all quantum objects);
* From Bargmann representation to phase space representation (for only quantum states);
* From Bargmann representation to quadrature representation (for only quantum states);
* From phase space representation to Bargmann representation (for all quantum objects);
* From quadrature representation to Bargmann representation (for only quantum states);

The first one is to use the function ``to_fock`` for all quantum objects.
The following two conversions have been encapsuled into the CircuitComponent object ``DsMap`` and ``BtoQMap`` in order to compute the representation change on each wire.
The forth conversion uses the functions with the name ``wigner_to_bargmann`` in ``bargmann.py`` for all quantum objects.
The last one is to apply the CircuitComponent object that inverses the ``BtoQMap`` (equals to the dual of this operator).

Some examples:

1. From Bargmann representation to Fock representation conversion is realized by using the ``hermite_renormalized`` function, which can be considered as a Map gate as well.

.. code-block::

    ╔═══════╗       ╔════════════════════╗
    ║ |psi> ║─────▶ ║ hermite_normalized ║─────▶
    ╚═══════╝       ╚════════════════════╝

2. From Bargmann representation to phase space representation, the Map on the ket wire can be illustrated as

.. code-block::

    ╔═══════╗       ╔═══════╗
    ║ |psi> ║─────▶ ║ DsMap ║─────▶
    ╚═══════╝       ╚═══════╝

3. From Bargmann representation to quadrature representation, the Map on the ket wire can be illustrated as

.. code-block::

    ╔═══════╗       ╔═════════╗
    ║ |psi> ║─────▶ ║ BtoQMap ║─────▶
    ╚═══════╝       ╚═════════╝

5. From quadrature representation to Bargmann representation, the Map on the ket wire uses the dual of the ``BtoQMap``

.. code-block::

    ╔═══════╗       ╔══════════════╗
    ║ |psi> ║─────▶ ║ BtoQMap.dual ║─────▶
    ╚═══════╝       ╚══════════════╝

"""

from typing import Iterable, Union, Optional
from mrmustard.physics.representations import Representation, Bargmann, Fock
from mrmustard import math, settings


def to_fock(rep: Representation, shape: Optional[Union[int, Iterable[int]]] = None) -> Fock:
    r"""A function to map ``Representation``\s to ``Fock`` representations.

    If the given ``rep`` is ``Fock``, this function simply returns ``rep``.

    Args:
        rep: The orginal representation of the object.
        shape: The shape of the returned representation. If ``shape``is given as an ``int``, it is broadcasted
            to all the dimensions. If ``None``, it defaults to the value of ``AUTOCUTOFF_MAX_CUTOFF`` in
            the settings.

    Raises:
        ValueError: If the size of the shape given is not compatible with the representation.

    Returns:
        A ``Fock`` representation object.

    .. code-block::

        >>> from mrmustard.physics.converters import to_fock
        >>> from mrmustard.physics.representations import Bargmann, Fock
        >>> from mrmustard.physics.triples import displacement_gate_Abc

        >>> bargmann = Bargmann(*displacement_gate_Abc(x=0.1, y=[0.2, 0.3]))
        >>> fock = to_fock(bargmann, shape=10)
        >>> assert isinstance(fock, Fock)

    """
    if isinstance(rep, Bargmann):
        if not shape:
            shape = (settings.AUTOCUTOFF_MAX_CUTOFF,) * rep.ansatz.num_vars
        else:
            shape = (shape,) * rep.ansatz.num_vars if isinstance(shape, int) else shape
        if rep.ansatz.num_vars != len(shape):
            msg = f"Given shape ``{shape}`` has length {len(shape)} which is "
            msg += f"{'less' if len(shape) < rep.ansatz.num_vars else 'more'} than "
            msg += f"the number of variables of this ansatz ({rep.ansatz.num_vars})."
            raise ValueError(msg)

        array = [math.hermite_renormalized(A, b, c, shape) for A, b, c in zip(rep.A, rep.b, rep.c)]
        fock = Fock(math.astensor(array), batched=True)
        fock._original_bargmann_data = rep.data
        return fock
    return rep
