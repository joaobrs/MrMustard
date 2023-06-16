#Copyright 2023 Xanadu Quantum Technologies Inc.

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
from typing import List
from mrmustard.math import Math
from mrmustard.lab.representations import Representation
from mrmustard.lab.representations.data import ArrayData
from mrmustard.typing import Scalar, Tensor, RealMatrix, RealVector, Matrix
# from mrmustard.math.caching import tensor_int_cache

math = Math()

class Fock(Representation):
    r""" Fock representation of a state.
    
    Args:
        data: the data used to represent the state to be encoded as Fock representation, it will be
              fed to an ArrayData object
    """

    def __init__(self, array:np.array) -> None:
        super().__init__()
        self.data = ArrayData(array=array) 


    @property
    def number_means(self) -> Tensor:
        probs = self.probability()
        nb_modes = range(len(probs.shape))
        modes = list(nb_modes) # NOTE : there is probably a more optimized way of doing this
        marginals = [math.sum(probs, axes=modes[:k] + modes[k + 1 :]) for k in nb_modes]
        result = [math.sum(m * math.arange(len(m), dtype=m.dtype)) for m in marginals]
        return math.astensor(result)
    

    @property
    def number_cov(self) -> RealMatrix:
        raise NotImplementedError("number_cov not yet implemented for non-gaussian states")
    

    @property
    def number_variances(self) -> Tensor:
        probs = self.probability()
        modes = list(range(len(probs.shape)))
        marginals = [math.sum(probs, axes=modes[:k] + modes[k + 1 :]) for k in range(len(modes))]
        t = marginals[0].dtype
        result = [
                (math.sum(m * math.arange(m.shape[0], dtype=t) ** 2)
                 - math.sum(m * math.arange(m.shape[0], dtype=t)) ** 2) 
                 for m in marginals
                 ]
        return math.astensor(result)


    @property
    def von_neumann_entropy(self) -> float:
        raise NotImplementedError("von_neumann_entropy not implemented for Fock representation") 
        # # @tensor_int_cache
        # def oscillator_eigenstates(q: RealVector, cutoff: int) -> Tensor:
        #     r"""Harmonic oscillator eigenstate wavefunctions `\psi_n(q) = <q|n>` for n = 0, 1, 2, ..., cutoff-1.

        #     Args:
        #         q (Vector): a vector containing the q points at which the function is evaluated (units of \sqrt{\hbar})
        #         cutoff (int): maximum number of photons

        #     Returns:
        #         Tensor: a tensor of shape ``(cutoff, len(q))``. The entry with index ``[n, j]`` represents the eigenstate evaluated
        #             with number of photons ``n`` evaluated at position ``q[j]``, i.e., `\psi_n(q_j) = <q_j|n>`.

        #     .. details::

        #         .. admonition:: Definition
        #             :class: defn

        #         The q-quadrature eigenstates are defined as

        #         .. math::

        #             \psi_n(x) = 1/sqrt[2^n n!](\frac{\omega}{\pi \hbar})^{1/4}
        #                 \exp{-\frac{\omega}{2\hbar} x^2} H_n(\sqrt{\frac{\omega}{\pi}} x)

        #         where :math:`H_n(x)` is the (physicists) `n`-th Hermite polynomial.
        #     """
        #     omega_over_hbar = math.cast(1 / settings.HBAR, "float64")
        #     x_tensor = math.sqrt(omega_over_hbar) * math.cast(q, "float64")  # unit-less vector

        #     # prefactor term (\Omega/\hbar \pi)**(1/4) * 1 / sqrt(2**n)
        #     prefactor = (omega_over_hbar / np.pi) ** (1 / 4) * math.sqrt(2 ** (-math.arange(0, cutoff)))

        #     # Renormalized physicist hermite polys: Hn / sqrt(n!)
        #     R = np.array([[2 + 0j]])  # to get the physicist polys

        #     def f_hermite_polys(xi):
        #         poly = math.hermite_renormalized(R, 2 * math.astensor([xi], "complex128"), 1 + 0j, cutoff)
        #         return math.cast(poly, "float64")

        #     hermite_polys = math.map_fn(f_hermite_polys, x_tensor)

        #     # (real) wavefunction
        #     psi = math.exp(-(x_tensor**2 / 2)) * math.transpose(prefactor * hermite_polys)
        #     return psi

    # NOTE : this is for transformations!
    # def validate_contraction_indices(in_idx:List[int], out_idx:List[int], M:int) -> bool:
    #     r""" Validates the indices used for the contraction of a tensor.

    #     Args:
    #         in_idx: the indices (counting from 0) of the kraus operator that contract with the ket
    #         out_idx: the indices (counting from 0) of the kraus operator that are leftover
    #         M: dimension of the ket

    #     Returns:
    #         True if all went well and the indices are not problematic

    #     Raises:
    #         ValueError: if the indices used for the contraction are incorrect        
    #     """
    #     if (len(set(in_idx)) != len(in_idx)) or (len(set(out_idx)) != len(out_idx)):
    #         raise ValueError("Should not contain repeated indices.")
        
    #     elif not set(range(M)).intersection(out_idx).issubset(set(in_idx)):
    #         wrong = set(range(M)).intersection(out_idx) - set(in_idx)
    #         raise ValueError(f"Indices {wrong} are trying to replace uncontracted indices.")
        
    #     else:
    #         return True