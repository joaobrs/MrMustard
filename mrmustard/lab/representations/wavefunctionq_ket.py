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

import numpy as np
from mrmustard.typing import Scalar, Tensor
from mrmustard.math import Math

math = Math()
from mrmustard.lab.representations.wavefunctionq import WaveFunctionQ


class WaveFunctionQKet(WaveFunctionQ):
    r"""WavefunctionQ representation of a ket state.

    Args:
        qs: q-variable points
        array: q-Wavefunction values correspoidng qs
    """

    def __init__(self, qs: np.array, wavefunctionq: np.array):
        super().__init__(qs=qs, wavefunctionq=wavefunctionq)

    @property
    def purity(self) -> Scalar:
        return 1.0

    @property
    def norm(self) -> float:
        return math.abs(math.norm(self.data.array))

    @property
    def probability(self) -> Tensor:
        return math.abs(self.data.array, real=True)
