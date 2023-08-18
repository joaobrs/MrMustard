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
from typing import Optional
from mrmustard.math import Math
from mrmustard.lab.representations.wigner import Wigner
from mrmustard.lab.representations.data.gaussian_data import GaussianData
from mrmustard.typing import Matrix, Vector, Scalar
from mrmustard import settings

math = Math()


class WignerDM(Wigner):
    r"""The WignerDM representation is to characterize the mixed Gaussian state with its wigner quasiprobabilistic distribution in phase space,
    which is a Gaussian function. This Gaussian function is characterized by a mean vector and a covariance matrix.


    Args:
        cov: the covaraince matrix
        means: the means vector
        coeffs: coefficients of the state

    """

    def __init__(self, cov: Matrix, means: Vector, coeffs: Scalar = 1.0) -> None:
        # Check the covariance matrices is real symmetric
        if not all(math.imag(cov) == 0) or not math.transpose(cov) == cov:
            raise ValueError("The covariance matrix is not real or symmetric!")
        # Check the mean vector is real
        if not all(math.imag(means) == 0):
            raise ValueError("The mean vector is not real!")
        self.data = GaussianData(cov=cov, means=means, coeffs=coeffs)

    @property
    def purity(self) -> Optional[float]:
        purity_list = []
        for i in range(self.data.cov[-1]):
            purity_list.append(1 / math.sqrt(math.det((2 / settings.HBAR) * self.data.cov[i, :])))
        return purity_list
